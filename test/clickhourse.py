import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import clickhouse_connect
from datetime import datetime, timedelta
import numpy as np
from decimal import Decimal
import io
from typing import Dict, Any, Optional


# 导入原有的技术指标计算器类
class TechnicalIndicatorCalculator:
    """技术指标计算器 - 包含MA, MACD, ATR, RSI, KDJ, CCI、BOLL等指标"""

    def __init__(self, host: str, username: str, password: str, database: str, port: int = 8123):
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.port = port
        self.client = None

    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                username=self.username,
                password=self.password,
                database=self.database,
                port=self.port
            )
            return True
        except Exception as e:
            st.error(f"❌ 连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.client is not None

    def convert_decimal_to_float(self, df: pd.DataFrame) -> pd.DataFrame:
        """将Decimal类型转换为float"""
        for col in df.columns:
            if df[col].dtype == object:
                if len(df) > 0 and isinstance(df[col].iloc[0], Decimal):
                    df[col] = df[col].astype(float)
        return df

    def get_table_structure(self, table_name: str):
        """查看表结构"""
        if not self.is_connected():
            st.error("❌ 请先连接数据库")
            return pd.DataFrame()

        try:
            query = f"DESCRIBE {table_name}"
            result = self.client.query(query)

            # 调试信息
            st.info(
                f"查询返回 {len(result.result_rows)} 行，每行 {len(result.result_rows[0]) if result.result_rows else 0} 列")

            # 动态处理列名
            if result.result_rows:
                num_columns = len(result.result_rows[0])
                # 使用常见的表结构列名
                possible_columns = ['name', 'type', 'default_type', 'default_expression', 'comment', 'codec_expression',
                                    'ttl_expression']
                columns = possible_columns[:num_columns] if num_columns <= len(possible_columns) else [f'col_{i}' for i
                                                                                                       in range(
                        num_columns)]

                df = pd.DataFrame(result.result_rows, columns=columns)
                return df
            else:
                st.warning("表结构查询返回空结果")
                return pd.DataFrame()

        except Exception as e:
            st.error(f"❌ 获取表结构失败: {e}")
            return pd.DataFrame()

    def calculate_ma_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算移动平均线指标"""
        if df.empty:
            return df

        result_df = df.copy()
        if result_df['close_price'].dtype == object:
            result_df['close_price'] = pd.to_numeric(result_df['close_price'], errors='coerce')

        ma_periods = [5, 10, 20, 60, 120]
        for period in ma_periods:
            ma_column = f'MA{period}'
            ma_values = result_df['close_price'].rolling(window=period, min_periods=period).mean()
            result_df[ma_column] = ma_values.round(4)

        return result_df

    def calculate_macd_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算MACD指标"""
        if df.empty:
            return df

        result_df = df.copy()
        if result_df['close_price'].dtype == object:
            result_df['close_price'] = pd.to_numeric(result_df['close_price'], errors='coerce')

        # 计算EMA12和EMA26
        result_df['EMA12'] = result_df['close_price'].ewm(span=12, adjust=False).mean()
        result_df['EMA26'] = result_df['close_price'].ewm(span=26, adjust=False).mean()

        # 计算DIF线
        result_df['DIF'] = result_df['EMA12'] - result_df['EMA26']

        # 计算DEA线
        result_df['DEA'] = result_df['DIF'].ewm(span=9, adjust=False).mean()

        # 计算MACD柱状图
        result_df['MACD'] = (result_df['DIF'] - result_df['DEA']) * 2

        # 计算MACD信号
        result_df['MACD_signal'] = 0
        golden_cross = (result_df['DIF'] > result_df['DEA']) & (result_df['DIF'].shift(1) <= result_df['DEA'].shift(1))
        death_cross = (result_df['DIF'] < result_df['DEA']) & (result_df['DIF'].shift(1) >= result_df['DEA'].shift(1))
        result_df.loc[golden_cross, 'MACD_signal'] = 1
        result_df.loc[death_cross, 'MACD_signal'] = -1

        return result_df

    def calculate_atr_indicators(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算ATR指标"""
        if df.empty:
            return df

        result_df = df.copy()
        price_columns = ['high_price', 'low_price', 'close_price']
        for col in price_columns:
            if col in result_df.columns and result_df[col].dtype == object:
                result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

        # 计算真实波幅 (TR)
        high_low = result_df['high_price'] - result_df['low_price']
        high_prev_close = abs(result_df['high_price'] - result_df['close_price'].shift(1))
        low_prev_close = abs(result_df['low_price'] - result_df['close_price'].shift(1))
        result_df['TR'] = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)

        # 计算ATR
        result_df[f'ATR{period}'] = result_df['TR'].rolling(window=period).mean().round(4)

        return result_df

    def calculate_rsi_indicators(self, df: pd.DataFrame, periods: list = [6, 12, 24]) -> pd.DataFrame:
        """计算RSI指标"""
        if df.empty:
            return df

        result_df = df.copy()
        if result_df['close_price'].dtype == object:
            result_df['close_price'] = pd.to_numeric(result_df['close_price'], errors='coerce')

        delta = result_df['close_price'].diff()

        for period in periods:
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=period, min_periods=period).mean()
            avg_loss = loss.rolling(window=period, min_periods=period).mean()

            rs = avg_gain / avg_loss
            rs = rs.replace([np.inf, -np.inf], float('nan'))

            result_df[f'RSI{period}'] = 100 - (100 / (1 + rs))

            # 处理特殊情况
            zero_loss_mask = (avg_loss == 0) & (avg_gain > 0)
            zero_gain_mask = (avg_gain == 0) & (avg_loss >= 0)
            result_df.loc[zero_loss_mask, f'RSI{period}'] = 100.0
            result_df.loc[zero_gain_mask, f'RSI{period}'] = 0.0
            result_df[f'RSI{period}'] = result_df[f'RSI{period}'].clip(0, 100)

        return result_df

    def calculate_kdj_indicators(self, df: pd.DataFrame, n: int = 9, m: int = 3) -> pd.DataFrame:
        """计算KDJ指标"""
        if df.empty:
            return df

        result_df = df.copy()
        price_columns = ['high_price', 'low_price', 'close_price']
        for col in price_columns:
            if col in result_df.columns and result_df[col].dtype == object:
                result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

        # 计算RSV
        lowest_low = result_df['low_price'].rolling(window=n).min()
        highest_high = result_df['high_price'].rolling(window=n).max()
        result_df['RSV'] = ((result_df['close_price'] - lowest_low) / (highest_high - lowest_low)) * 100

        # 初始化K、D值
        result_df['K'] = 50.0
        result_df['D'] = 50.0

        # 递归计算K值和D值
        for i in range(1, len(result_df)):
            if pd.notna(result_df['RSV'].iloc[i]):
                result_df.loc[result_df.index[i], 'K'] = (2 / 3) * result_df['K'].iloc[i - 1] + (1 / 3) * \
                                                         result_df['RSV'].iloc[i]
                result_df.loc[result_df.index[i], 'D'] = (2 / 3) * result_df['D'].iloc[i - 1] + (1 / 3) * \
                                                         result_df['K'].iloc[i]
            else:
                result_df.loc[result_df.index[i], 'K'] = result_df['K'].iloc[i - 1]
                result_df.loc[result_df.index[i], 'D'] = result_df['D'].iloc[i - 1]

        # 计算J值
        result_df['J'] = 3 * result_df['K'] - 2 * result_df['D']

        return result_df

    def calculate_cci_indicators(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """计算CCI指标"""
        if df.empty:
            return df

        result_df = df.copy()
        price_columns = ['high_price', 'low_price', 'close_price']
        for col in price_columns:
            if col in result_df.columns and result_df[col].dtype == object:
                result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

        # 计算典型价格 (TP)
        result_df['TP'] = (result_df['high_price'] + result_df['low_price'] + result_df['close_price']) / 3

        # 计算TP的移动平均
        result_df['TP_MA'] = result_df['TP'].rolling(window=period).mean()

        # 计算平均偏差
        def mean_deviation_calculation(x):
            mean_val = np.mean(x)
            return np.mean(np.abs(x - mean_val))

        result_df['mean_deviation'] = result_df['TP'].rolling(window=period).apply(
            mean_deviation_calculation, raw=True
        )

        # 计算CCI
        result_df[f'CCI{period}'] = (result_df['TP'] - result_df['TP_MA']) / (0.015 * result_df['mean_deviation'])

        return result_df

    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, k: float = 2) -> pd.DataFrame:
        """计算布林线指标"""
        if df.empty:
            return df

        result_df = df.copy()
        if result_df['close_price'].dtype == object:
            result_df['close_price'] = pd.to_numeric(result_df['close_price'], errors='coerce')

        # 计算中轨
        result_df[f'BOLL_MID{period}'] = result_df['close_price'].rolling(window=period).mean()

        # 计算标准差
        result_df[f'BOLL_STD{period}'] = result_df['close_price'].rolling(window=period).std()

        # 计算上下轨
        result_df[f'BOLL_UPPER{period}'] = result_df[f'BOLL_MID{period}'] + k * result_df[f'BOLL_STD{period}']
        result_df[f'BOLL_LOWER{period}'] = result_df[f'BOLL_MID{period}'] - k * result_df[f'BOLL_STD{period}']

        return result_df

    def get_price_data(self, contract_code: str, trading_year: str, additional_filters: str = "") -> pd.DataFrame:
        """获取价格数据"""
        if not self.is_connected():
            st.error("❌ 请先连接数据库")
            return pd.DataFrame()

        base_query = f"""
        SELECT 
            contract_code,
            trading_day,
            close_price,
            opening_price as open_price,
            highest_price as high_price,
            lowest_price as low_price,
            hold_amount as open_interest
        FROM quotation.new_day_price 
        WHERE trading_year = '{trading_year}' 
          AND contract_code = '{contract_code}'
          AND close_price > 0
        """

        if additional_filters:
            base_query += f" AND {additional_filters}"

        base_query += " ORDER BY trading_day"

        try:
            result = self.client.query(base_query)
            df = pd.DataFrame(result.result_rows, columns=result.column_names)

            if 'trading_day' in df.columns:
                df['trading_day'] = pd.to_datetime(df['trading_day'])

            df = self.convert_decimal_to_float(df)
            return df
        except Exception as e:
            st.error(f"❌ 查询数据失败: {e}")
            return pd.DataFrame()

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        if df.empty:
            return df

        result_df = df.copy()

        # 计算各个指标
        result_df = self.calculate_ma_indicators(result_df)
        result_df = self.calculate_macd_indicators(result_df)
        result_df = self.calculate_atr_indicators(result_df)
        result_df = self.calculate_rsi_indicators(result_df)
        result_df = self.calculate_kdj_indicators(result_df)
        result_df = self.calculate_cci_indicators(result_df)
        result_df = self.calculate_bollinger_bands(result_df)

        return result_df

    def get_technical_analysis(self, df: pd.DataFrame, latest_days: int = 10) -> Dict[str, Any]:
        """生成技术指标综合分析报告"""
        if df.empty:
            return {}

        recent_data = df.tail(latest_days).copy()
        latest_row = recent_data.iloc[-1]

        analysis = {
            'total_days': len(df),
            'analysis_period': latest_days,
            'current_price': float(recent_data['close_price'].iloc[-1]) if not recent_data.empty else 0,
            'ma_analysis': {},
            'macd_analysis': {},
            'rsi_analysis': {},
            'kdj_analysis': {},
            'atr_analysis': {},
            'cci_analysis': {},
            'boll_analysis': {},
            'comprehensive_signals': []
        }

        # MA分析
        ma_columns = [col for col in df.columns if col.startswith('MA') and len(col) <= 5]
        for ma_col in ma_columns:
            if ma_col in latest_row:
                analysis['ma_analysis'][ma_col] = float(latest_row[ma_col])

        # MACD分析
        if 'DIF' in latest_row and 'DEA' in latest_row:
            analysis['macd_analysis'] = {
                'DIF': float(latest_row['DIF']),
                'DEA': float(latest_row['DEA']),
                'MACD': float(latest_row.get('MACD', 0)),
                'signal': '金叉' if latest_row.get('MACD_signal') == 1 else '死叉' if latest_row.get(
                    'MACD_signal') == -1 else '无信号'
            }

        # RSI分析
        rsi_columns = [col for col in df.columns if col.startswith('RSI') and not col.endswith('_signal')]
        for rsi_col in rsi_columns:
            if rsi_col in latest_row:
                rsi_value = float(latest_row[rsi_col])
                analysis['rsi_analysis'][rsi_col] = {
                    'value': rsi_value,
                    'signal': '超买' if rsi_value > 70 else '超卖' if rsi_value < 30 else '正常'
                }

        # KDJ分析
        if all(col in latest_row for col in ['K', 'D', 'J']):
            analysis['kdj_analysis'] = {
                'K': float(latest_row['K']),
                'D': float(latest_row['D']),
                'J': float(latest_row['J']),
                'signal': '金叉' if latest_row.get('KDJ_signal') == 1 else '死叉' if latest_row.get(
                    'KDJ_signal') == -1 else '无信号'
            }

        # ATR分析
        if 'ATR14' in latest_row:
            analysis['atr_analysis'] = {
                'ATR': float(latest_row['ATR14']),
                'volatility': '高波动' if float(latest_row['ATR14']) > float(recent_data['ATR14'].mean()) else '低波动'
            }

        return analysis


# Streamlit 应用
def main():
    st.set_page_config(
        page_title="技术指标计算器",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📈 技术指标计算器可视化界面")
    st.markdown("---")

    # 初始化session state
    if 'calculator' not in st.session_state:
        st.session_state.calculator = None
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    if 'price_data' not in st.session_state:
        st.session_state.price_data = None
    if 'indicators_df' not in st.session_state:
        st.session_state.indicators_df = None

    # 侧边栏配置
    st.sidebar.header("🔧 配置参数")

    # 数据库配置
    st.sidebar.subheader("数据库配置")
    host = st.sidebar.text_input("主机地址", value="")
    port = st.sidebar.number_input("端口", value=8123, min_value=1, max_value=65535)
    username = st.sidebar.text_input("用户名", value="")
    password = st.sidebar.text_input("密码", value="", type="password")
    database = st.sidebar.text_input("数据库", value="")

    # 连接状态显示
    if st.session_state.connected:
        st.sidebar.success("✅ 数据库已连接")
    else:
        st.sidebar.warning("⚠️ 数据库未连接")

    # 连接数据库
    if st.sidebar.button("🔗 连接数据库", use_container_width=True):
        with st.spinner("正在连接数据库..."):
            calculator = TechnicalIndicatorCalculator(host, username, password, database, port)
            if calculator.connect():
                st.session_state.calculator = calculator
                st.session_state.connected = True
                st.sidebar.success("✅ 数据库连接成功！")
                st.rerun()
            else:
                st.session_state.connected = False
                st.sidebar.error("❌ 数据库连接失败")

    # 断开连接
    if st.session_state.connected and st.sidebar.button("🔌 断开连接", use_container_width=True):
        st.session_state.calculator = None
        st.session_state.connected = False
        st.session_state.price_data = None
        st.session_state.indicators_df = None
        st.sidebar.info("🔌 数据库连接已断开")
        st.rerun()

    st.sidebar.markdown("---")

    # 数据查询参数
    st.sidebar.subheader("数据查询参数")
    contract_code = st.sidebar.text_input("合约代码", value="MA302")
    trading_year = st.sidebar.text_input("交易年份", value="2022")

    # 指标选择
    st.sidebar.subheader("技术指标选择")
    calc_ma = st.sidebar.checkbox("移动平均线 (MA)", value=True)
    calc_macd = st.sidebar.checkbox("MACD", value=True)
    calc_rsi = st.sidebar.checkbox("RSI", value=True)
    calc_kdj = st.sidebar.checkbox("KDJ", value=True)
    calc_atr = st.sidebar.checkbox("ATR", value=True)
    calc_cci = st.sidebar.checkbox("CCI", value=True)
    calc_boll = st.sidebar.checkbox("布林线", value=True)

    # 主内容区
    tab1, tab2, tab3, tab4 = st.tabs(["📊 数据查询", "📈 技术指标", "🔍 分析报告", "💾 数据导出"])

    with tab1:
        st.header("数据查询")

        if not st.session_state.connected:
            st.warning("⚠️ 请先连接数据库")
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 查看表结构", use_container_width=True):
                    with st.spinner("获取表结构中..."):
                        table_structure = st.session_state.calculator.get_table_structure("new_day_price")
                        if not table_structure.empty:
                            st.success("✅ 表结构获取成功")
                            st.dataframe(table_structure, use_container_width=True)
                        else:
                            st.error("❌ 获取表结构失败")

            with col2:
                if st.button("📥 获取价格数据", use_container_width=True):
                    with st.spinner("查询价格数据中..."):
                        price_data = st.session_state.calculator.get_price_data(contract_code, trading_year)
                        if not price_data.empty:
                            st.session_state.price_data = price_data
                            st.success(f"✅ 成功获取 {len(price_data)} 条价格数据")

                            # 显示数据统计
                            st.subheader("数据统计")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("数据条数", len(price_data))
                            with col2:
                                st.metric("开始日期", price_data['trading_day'].min().strftime('%Y-%m-%d'))
                            with col3:
                                st.metric("结束日期", price_data['trading_day'].max().strftime('%Y-%m-%d'))
                            with col4:
                                st.metric("最新收盘价", f"{price_data['close_price'].iloc[-1]:.2f}")

                            # 显示数据表格
                            st.subheader("价格数据预览")
                            st.dataframe(price_data.tail(20), use_container_width=True)

                            # 绘制价格图表
                            st.subheader("价格走势图")
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=price_data['trading_day'], y=price_data['close_price'],
                                                     mode='lines', name='收盘价', line=dict(color='#1f77b4')))
                            fig.update_layout(title=f"{contract_code} 价格走势",
                                              xaxis_title="日期",
                                              yaxis_title="价格",
                                              height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error("❌ 未找到价格数据")

    with tab2:
        st.header("技术指标计算")

        if not st.session_state.connected:
            st.warning("⚠️ 请先连接数据库")
        elif st.session_state.price_data is None:
            st.warning("⚠️ 请先获取价格数据")
        else:
            price_data = st.session_state.price_data

            if st.button("🔄 计算技术指标", use_container_width=True):
                with st.spinner("计算技术指标中..."):
                    result_df = price_data.copy()

                    # 根据选择计算指标
                    if calc_ma:
                        result_df = st.session_state.calculator.calculate_ma_indicators(result_df)
                    if calc_macd:
                        result_df = st.session_state.calculator.calculate_macd_indicators(result_df)
                    if calc_rsi:
                        result_df = st.session_state.calculator.calculate_rsi_indicators(result_df)
                    if calc_kdj:
                        result_df = st.session_state.calculator.calculate_kdj_indicators(result_df)
                    if calc_atr:
                        result_df = st.session_state.calculator.calculate_atr_indicators(result_df)
                    if calc_cci:
                        result_df = st.session_state.calculator.calculate_cci_indicators(result_df)
                    if calc_boll:
                        result_df = st.session_state.calculator.calculate_bollinger_bands(result_df)

                    st.session_state.indicators_df = result_df
                    st.success("✅ 技术指标计算完成！")

            if st.session_state.indicators_df is not None:
                indicators_df = st.session_state.indicators_df

                # 显示指标数据
                st.subheader("技术指标数据")
                st.dataframe(indicators_df.tail(20), use_container_width=True)

                # 绘制技术指标图表
                st.subheader("技术指标图表")

                # 价格和MA图表
                if calc_ma and any(col.startswith('MA') for col in indicators_df.columns):
                    fig_ma = go.Figure()
                    fig_ma.add_trace(go.Scatter(x=indicators_df['trading_day'], y=indicators_df['close_price'],
                                                mode='lines', name='收盘价', line=dict(color='black', width=1)))

                    # 添加各周期MA线
                    colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
                    ma_columns = [col for col in indicators_df.columns if col.startswith('MA') and len(col) <= 5]
                    for i, ma_col in enumerate(ma_columns):
                        fig_ma.add_trace(go.Scatter(x=indicators_df['trading_day'], y=indicators_df[ma_col],
                                                    mode='lines', name=ma_col,
                                                    line=dict(color=colors[i % len(colors)])))

                    fig_ma.update_layout(title="移动平均线 (MA)", height=400)
                    st.plotly_chart(fig_ma, use_container_width=True)

                # MACD图表
                if calc_macd and all(col in indicators_df.columns for col in ['DIF', 'DEA', 'MACD']):
                    fig_macd = make_subplots(rows=2, cols=1,
                                             subplot_titles=('MACD线', 'MACD柱状图'),
                                             vertical_spacing=0.1,
                                             shared_xaxes=True)  # 修复参数名

                    fig_macd.add_trace(go.Scatter(x=indicators_df['trading_day'], y=indicators_df['DIF'],
                                                  mode='lines', name='DIF', line=dict(color='blue')), row=1, col=1)
                    fig_macd.add_trace(go.Scatter(x=indicators_df['trading_day'], y=indicators_df['DEA'],
                                                  mode='lines', name='DEA', line=dict(color='red')), row=1, col=1)

                    colors_macd = ['green' if x >= 0 else 'red' for x in indicators_df['MACD']]
                    fig_macd.add_trace(go.Bar(x=indicators_df['trading_day'], y=indicators_df['MACD'],
                                              name='MACD', marker_color=colors_macd), row=2, col=1)

                    fig_macd.update_layout(height=500, showlegend=True)
                    st.plotly_chart(fig_macd, use_container_width=True)

                # RSI图表
                if calc_rsi and any(col.startswith('RSI') for col in indicators_df.columns):
                    fig_rsi = go.Figure()
                    rsi_columns = [col for col in indicators_df.columns if
                                   col.startswith('RSI') and not col.endswith('_signal')]

                    for rsi_col in rsi_columns:
                        fig_rsi.add_trace(go.Scatter(x=indicators_df['trading_day'], y=indicators_df[rsi_col],
                                                     mode='lines', name=rsi_col))

                    # 添加超买超卖线
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超买线")
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超卖线")

                    fig_rsi.update_layout(title="RSI指标", height=400)
                    st.plotly_chart(fig_rsi, use_container_width=True)

    with tab3:
        st.header("技术分析报告")

        if not st.session_state.connected:
            st.warning("⚠️ 请先连接数据库")
        elif st.session_state.indicators_df is None:
            st.warning("⚠️ 请先计算技术指标")
        else:
            indicators_df = st.session_state.indicators_df

            analysis = st.session_state.calculator.get_technical_analysis(indicators_df)

            if analysis:
                # 总体信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("分析天数", analysis['total_days'])
                with col2:
                    st.metric("当前价格", f"{analysis['current_price']:.2f}")
                with col3:
                    st.metric("分析周期", analysis['analysis_period'])
                with col4:
                    signal_count = len(analysis['comprehensive_signals'])
                    st.metric("信号数量", signal_count)

                # 各指标分析
                st.subheader("📊 各指标状态")

                # MA分析
                if analysis['ma_analysis']:
                    st.write("**移动平均线 (MA):**")
                    ma_cols = st.columns(len(analysis['ma_analysis']))
                    for i, (ma_name, ma_value) in enumerate(analysis['ma_analysis'].items()):
                        with ma_cols[i]:
                            st.metric(ma_name, f"{ma_value:.2f}")

                # MACD分析
                if analysis['macd_analysis']:
                    st.write("**MACD指标:**")
                    macd = analysis['macd_analysis']
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("DIF", f"{macd['DIF']:.4f}")
                    with col2:
                        st.metric("DEA", f"{macd['DEA']:.4f}")
                    with col3:
                        st.metric("MACD", f"{macd['MACD']:.4f}")
                    with col4:
                        signal_color = "🟢" if macd['signal'] == '金叉' else "🔴" if macd['signal'] == '死叉' else "⚪"
                        st.metric("信号", f"{signal_color} {macd['signal']}")

                # RSI分析
                if analysis['rsi_analysis']:
                    st.write("**RSI指标:**")
                    rsi_cols = st.columns(len(analysis['rsi_analysis']))
                    for i, (rsi_name, rsi_data) in enumerate(analysis['rsi_analysis'].items()):
                        with rsi_cols[i]:
                            color = "🔴" if rsi_data['signal'] == '超买' else "🟢" if rsi_data[
                                                                                        'signal'] == '超卖' else "⚪"
                            st.metric(rsi_name, f"{rsi_data['value']:.2f}",
                                      delta=color + " " + rsi_data['signal'])

                # KDJ分析
                if analysis['kdj_analysis']:
                    st.write("**KDJ指标:**")
                    kdj = analysis['kdj_analysis']
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("K值", f"{kdj['K']:.2f}")
                    with col2:
                        st.metric("D值", f"{kdj['D']:.2f}")
                    with col3:
                        st.metric("J值", f"{kdj['J']:.2f}")
                    with col4:
                        signal_color = "🟢" if kdj['signal'] == '金叉' else "🔴" if kdj['signal'] == '死叉' else "⚪"
                        st.metric("信号", f"{signal_color} {kdj['signal']}")

                # ATR分析
                if analysis['atr_analysis']:
                    st.write("**ATR指标:**")
                    atr = analysis['atr_analysis']
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("ATR值", f"{atr['ATR']:.4f}")
                    with col2:
                        volatility_color = "🔴" if atr['volatility'] == '高波动' else "🟢"
                        st.metric("波动性", f"{volatility_color} {atr['volatility']}")

    with tab4:
        st.header("数据导出")

        if not st.session_state.connected:
            st.warning("⚠️ 请先连接数据库")
        elif st.session_state.indicators_df is None:
            st.warning("⚠️ 请先计算技术指标")
        else:
            indicators_df = st.session_state.indicators_df

            st.subheader("导出选项")

            col1, col2 = st.columns(2)

            with col1:
                export_format = st.selectbox("导出格式", ["CSV", "Excel"])
                filename = st.text_input("文件名", value=f"technical_indicators_{contract_code}")

            with col2:
                include_all_data = st.checkbox("包含所有数据", value=True)
                if not include_all_data:
                    num_rows = st.number_input("导出最近N行数据", min_value=1, max_value=len(indicators_df), value=100)

            if st.button("📤 导出数据", use_container_width=True):
                export_df = indicators_df if include_all_data else indicators_df.tail(num_rows)

                if export_format == "CSV":
                    csv = export_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载CSV文件",
                        data=csv,
                        file_name=f"{filename}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:  # Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        export_df.to_excel(writer, sheet_name='技术指标', index=False)

                    st.download_button(
                        label="下载Excel文件",
                        data=output.getvalue(),
                        file_name=f"{filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                st.success("✅ 数据导出准备完成！")

    # 页脚
    st.markdown("---")
    st.markdown("技术指标计算器 © 2024 | 基于Streamlit构建")


if __name__ == "__main__":
    main()
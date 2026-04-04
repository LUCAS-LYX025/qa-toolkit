import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
import io


class BIAnalyzer:
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls', '.json']

    def show_upload_section(self):
        """显示文件上传区域"""
        st.markdown("### 📁 数据上传")

        # 先显示模板下载
        self.download_templates()

        st.markdown("---")

        # 再显示文件上传
        uploaded_file = st.file_uploader(
            "上传数据文件",
            type=self.supported_formats,
            help=f"支持的文件格式: {', '.join(self.supported_formats)}",
            key="bi_data_upload"
        )

        return uploaded_file

    def download_templates(self):
        """提供标准模板下载"""
        st.markdown("#### 📥 下载数据模板")

        # Excel模板
        excel_template = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02', '2024-01-03'],
            '产品': ['产品A', '产品B', '产品C'],
            '销售额': [1500.00, 2300.50, 1800.00],
            '数量': [10, 15, 12],
            '地区': ['北京', '上海', '广州'],
            '客户评分': [4.5, 4.2, 4.7]
        })

        excel_buffer = io.BytesIO()
        excel_template.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                label="📊 Excel模板",
                data=excel_buffer.getvalue(),
                file_name="BI数据模板.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col2:
            # CSV模板
            csv_template = excel_template.to_csv(index=False)
            st.download_button(
                label="📁 CSV模板",
                data=csv_template,
                file_name="BI数据模板.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col3:
            # JSON模板
            json_template = excel_template.to_json(orient='records', force_ascii=False, indent=2)
            st.download_button(
                label="📋 JSON模板",
                data=json_template,
                file_name="BI数据模板.json",
                mime="application/json",
                use_container_width=True
            )

    def load_data(self, uploaded_file):
        """加载数据文件"""
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('.json'):
                df = pd.read_json(uploaded_file)
            else:
                return None, "不支持的文件格式"

            return df, "数据加载成功"
        except Exception as e:
            return None, f"数据加载失败: {str(e)}"

    def data_preview(self, df):
        """数据预览"""
        st.subheader("📋 数据预览")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总行数", len(df))
        with col2:
            st.metric("总列数", len(df.columns))
        with col3:
            st.metric("缺失值", df.isnull().sum().sum())
        with col4:
            st.metric("重复行", df.duplicated().sum())

        # 显示数据前几行
        st.dataframe(df.head(10), use_container_width=True)

        # 数据类型信息
        st.subheader("🔍 数据类型信息")
        dtype_info = pd.DataFrame({
            '列名': df.columns,
            '数据类型': df.dtypes,
            '非空值数量': df.count(),
            '缺失值数量': df.isnull().sum(),
            '唯一值数量': [df[col].nunique() for col in df.columns]
        })
        st.dataframe(dtype_info, use_container_width=True)

    def basic_statistics(self, df):
        """基础统计分析"""
        st.subheader("📊 基础统计分析")

        # 选择数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_cols:
            col1, col2 = st.columns(2)

            with col1:
                selected_num_col = st.selectbox("选择数值列", numeric_cols, key="stats_num_col")
                if selected_num_col:
                    stats = df[selected_num_col].describe()
                    st.dataframe(stats, use_container_width=True)

            with col2:
                # 分布直方图
                if selected_num_col:
                    fig = px.histogram(df, x=selected_num_col,
                                       title=f"{selected_num_col} 分布直方图",
                                       nbins=30)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("未找到数值列进行统计分析")

    def create_pivot_table(self, df):
        """创建数据透视表"""
        st.subheader("🔍 数据透视表分析")

        all_columns = df.columns.tolist()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()

        col1, col2, col3 = st.columns(3)

        with col1:
            index_col = st.selectbox("行索引", categorical_cols, key="pivot_index")
        with col2:
            columns_col = st.selectbox("列索引", [None] + categorical_cols, key="pivot_columns")
        with col3:
            values_col = st.selectbox("计算值", numeric_cols, key="pivot_values")

        agg_func = st.selectbox("聚合函数", ['sum', 'mean', 'count', 'min', 'max'], key="pivot_agg")

        if st.button("生成透视表", key="generate_pivot"):
            try:
                if values_col and index_col:
                    pivot_df = pd.pivot_table(df,
                                              values=values_col,
                                              index=index_col,
                                              columns=columns_col,
                                              aggfunc=agg_func,
                                              fill_value=0)

                    st.dataframe(pivot_df, use_container_width=True)

                    # 透视表可视化
                    fig = px.imshow(pivot_df,
                                    title=f"透视表热力图 - {values_col} by {index_col}",
                                    aspect="auto")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"生成透视表失败: {str(e)}")

    def time_series_analysis(self, df):
        """时间序列分析"""
        st.subheader("📈 时间序列分析")

        # 自动检测时间列
        date_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    pd.to_datetime(df[col])
                    date_columns.append(col)
                except:
                    continue

        if not date_columns:
            st.warning("未检测到时间序列列")
            return

        col1, col2, col3 = st.columns(3)

        with col1:
            date_col = st.selectbox("选择时间列", date_columns, key="ts_date_col")
        with col2:
            value_col = st.selectbox("选择数值列",
                                     df.select_dtypes(include=[np.number]).columns.tolist(),
                                     key="ts_value_col")
        with col3:
            freq = st.selectbox("时间频率", ['D', 'W', 'M', 'Q', 'Y'], key="ts_freq")

        if date_col and value_col:
            try:
                # 转换时间列
                df_temp = df.copy()
                df_temp[date_col] = pd.to_datetime(df_temp[date_col])
                df_temp = df_temp.set_index(date_col)

                # 重采样
                resampled = df_temp[value_col].resample(freq).mean()

                # 绘制时间序列图
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=resampled.index, y=resampled.values,
                                         mode='lines+markers',
                                         name=value_col))

                fig.update_layout(title=f"{value_col} 时间序列趋势",
                                  xaxis_title="时间",
                                  yaxis_title=value_col)

                st.plotly_chart(fig, use_container_width=True)

                # 显示统计信息
                st.subheader("时间序列统计")
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

                with col_stat1:
                    st.metric("平均值", f"{resampled.mean():.2f}")
                with col_stat2:
                    st.metric("标准差", f"{resampled.std():.2f}")
                with col_stat3:
                    st.metric("最大值", f"{resampled.max():.2f}")
                with col_stat4:
                    st.metric("最小值", f"{resampled.min():.2f}")

            except Exception as e:
                st.error(f"时间序列分析失败: {str(e)}")

    def correlation_analysis(self, df):
        """相关性分析"""
        st.subheader("🔗 相关性分析")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < 2:
            st.warning("需要至少2个数值列进行相关性分析")
            return

        # 计算相关系数矩阵
        corr_matrix = df[numeric_cols].corr()

        # 绘制热力图
        fig = px.imshow(corr_matrix,
                        title="相关性热力图",
                        aspect="auto",
                        color_continuous_scale='RdBu_r')

        st.plotly_chart(fig, use_container_width=True)

        # 显示详细的相关系数
        st.subheader("详细相关系数")
        st.dataframe(corr_matrix, use_container_width=True)

    def create_dashboard(self, df):
        """创建综合仪表板"""
        st.subheader("🎯 综合数据仪表板")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()

        if not numeric_cols:
            st.warning("没有数值列可用于创建仪表板")
            return

        # 仪表板配置
        col1, col2 = st.columns(2)

        with col1:
            x_axis = st.selectbox("X轴", categorical_cols + numeric_cols, key="dashboard_x")
        with col2:
            y_axis = st.selectbox("Y轴", numeric_cols, key="dashboard_y")

        chart_type = st.selectbox("图表类型",
                                  ["散点图", "折线图", "柱状图", "箱线图", "面积图"],
                                  key="chart_type")

        if st.button("生成仪表板", key="generate_dashboard"):
            try:
                if chart_type == "散点图" and x_axis and y_axis:
                    fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                elif chart_type == "折线图" and x_axis and y_axis:
                    fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                elif chart_type == "柱状图" and x_axis and y_axis:
                    fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
                elif chart_type == "箱线图" and x_axis and y_axis:
                    fig = px.box(df, x=x_axis, y=y_axis, title=f"{y_axis} 分布 by {x_axis}")
                elif chart_type == "面积图" and x_axis and y_axis:
                    fig = px.area(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                else:
                    st.error("请选择有效的图表配置")
                    return

                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"生成图表失败: {str(e)}")

    def export_report(self, df):
        """导出分析报告"""
        st.subheader("💾 导出分析报告")

        report_type = st.selectbox("选择报告格式", ["Excel", "CSV", "HTML"], key="report_type")

        if st.button("生成报告", key="generate_report"):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if report_type == "Excel":
                    # 创建Excel报告
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='原始数据', index=False)

                        # 添加统计信息
                        stats_df = df.describe()
                        stats_df.to_excel(writer, sheet_name='统计信息')

                        # 添加相关性矩阵
                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                        if numeric_cols:
                            corr_df = df[numeric_cols].corr()
                            corr_df.to_excel(writer, sheet_name='相关性分析')

                    output.seek(0)
                    st.download_button(
                        label="📥 下载Excel报告",
                        data=output.getvalue(),
                        file_name=f"BI分析报告_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                elif report_type == "CSV":
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 下载CSV数据",
                        data=csv_data,
                        file_name=f"数据导出_{timestamp}.csv",
                        mime="text/csv"
                    )

                elif report_type == "HTML":
                    # 生成HTML报告
                    html_report = self.generate_html_report(df)
                    st.download_button(
                        label="📥 下载HTML报告",
                        data=html_report,
                        file_name=f"BI分析报告_{timestamp}.html",
                        mime="text/html"
                    )

            except Exception as e:
                st.error(f"生成报告失败: {str(e)}")

    def generate_html_report(self, df):
        """生成HTML格式的报告 - 美化版本"""

        # 生成数据统计信息
        numeric_stats = df.describe().to_html(classes='stats-table') if not df.select_dtypes(
            include=[np.number]).empty else "<p>无数值列统计信息</p>"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>BI数据分析报告</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}

                .header {{
                    background: linear-gradient(135deg, #2c3e50, #3498db);
                    color: white;
                    padding: 40px;
                    text-align: center;
                    position: relative;
                }}

                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 100" fill="%23ffffff20"><polygon points="0,0 1000,50 1000,100 0,100"/></svg>');
                    background-size: cover;
                }}

                .header h1 {{
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    font-weight: 300;
                    position: relative;
                }}

                .header p {{
                    font-size: 1.1em;
                    opacity: 0.9;
                    position: relative;
                }}

                .content {{
                    padding: 40px;
                }}

                .section {{
                    margin-bottom: 40px;
                    padding: 30px;
                    background: #f8f9fa;
                    border-radius: 10px;
                    border-left: 5px solid #3498db;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                }}

                .section:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                }}

                .section h2 {{
                    color: #2c3e50;
                    margin-bottom: 20px;
                    font-size: 1.5em;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}

                .section h2::before {{
                    content: '📊';
                    font-size: 1.2em;
                }}

                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }}

                .metric-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                    border-top: 4px solid #3498db;
                    transition: all 0.3s ease;
                }}

                .metric-card:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                }}

                .metric-value {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #2c3e50;
                    margin: 10px 0;
                }}

                .metric-label {{
                    color: #7f8c8d;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                }}

                th {{
                    background: linear-gradient(135deg, #3498db, #2980b9);
                    color: white;
                    padding: 15px;
                    text-align: left;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-size: 0.9em;
                }}

                td {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #ecf0f1;
                    transition: background 0.3s ease;
                }}

                tr:hover td {{
                    background: #f8f9fa;
                }}

                tr:last-child td {{
                    border-bottom: none;
                }}

                .stats-table th {{
                    background: linear-gradient(135deg, #e74c3c, #c0392b);
                }}

                .data-preview {{
                    max-height: 400px;
                    overflow-y: auto;
                    border: 1px solid #bdc3c7;
                    border-radius: 8px;
                }}

                .footer {{
                    text-align: center;
                    padding: 30px;
                    background: #2c3e50;
                    color: white;
                    margin-top: 40px;
                }}

                .footer p {{
                    margin: 5px 0;
                    opacity: 0.8;
                }}

                .highlight {{
                    background: linear-gradient(120deg, #a8e6cf 0%, #dcedc1 100%);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-weight: 500;
                }}

                @media (max-width: 768px) {{
                    .metrics-grid {{
                        grid-template-columns: 1fr;
                    }}

                    .content {{
                        padding: 20px;
                    }}

                    .section {{
                        padding: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📈 BI数据分析报告</h1>
                    <p>专业数据洞察与可视化分析</p>
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>

                <div class="content">
                    <!-- 数据概览部分 -->
                    <div class="section">
                        <h2>数据概览</h2>
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">总数据量</div>
                                <div class="metric-value">{len(df):,}</div>
                                <div class="metric-desc">行记录</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">特征数量</div>
                                <div class="metric-value">{len(df.columns)}</div>
                                <div class="metric-desc">数据列</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">数据完整性</div>
                                <div class="metric-value">{((1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100):.1f}%</div>
                                <div class="metric-desc">非空比例</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">内存占用</div>
                                <div class="metric-value">{df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB</div>
                                <div class="metric-desc">存储空间</div>
                            </div>
                        </div>

                        <div style="margin-top: 20px;">
                            <p><span class="highlight">数据类型分布:</span></p>
                            <ul style="list-style: none; columns: 2; gap: 20px;">
                                <li>📄 数值类型: <strong>{len(df.select_dtypes(include=[np.number]).columns)}</strong> 列</li>
                                <li>📝 文本类型: <strong>{len(df.select_dtypes(include=['object']).columns)}</strong> 列</li>
                                <li>📅 日期时间: <strong>{len(df.select_dtypes(include=['datetime']).columns)}</strong> 列</li>
                                <li>🔠 分类数据: <strong>{len(df.select_dtypes(include=['category']).columns)}</strong> 列</li>
                            </ul>
                        </div>
                    </div>

                    <!-- 数据预览部分 -->
                    <div class="section">
                        <h2>数据预览</h2>
                        <p>显示前10行数据样本：</p>
                        <div class="data-preview">
                            {df.head(10).to_html(classes='data-table', index=False, escape=False)}
                        </div>
                    </div>

                    <!-- 统计信息部分 -->
                    <div class="section">
                        <h2>统计信息</h2>
                        <p>数值列的详细统计分析：</p>
                        {numeric_stats}
                    </div>

                    <!-- 数据质量部分 -->
                    <div class="section">
                        <h2>数据质量评估</h2>
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">缺失值</div>
                                <div class="metric-value">{df.isnull().sum().sum():,}</div>
                                <div class="metric-desc">空值数量</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">重复行</div>
                                <div class="metric-value">{df.duplicated().sum():,}</div>
                                <div class="metric-desc">重复记录</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">唯一值率</div>
                                <div class="metric-value">{((df.nunique().sum() / (len(df) * len(df.columns))) * 100):.1f}%</div>
                                <div class="metric-desc">数据多样性</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">数据密度</div>
                                <div class="metric-value">{((df.count().sum() / (len(df) * len(df.columns))) * 100):.1f}%</div>
                                <div class="metric-desc">填充程度</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="footer">
                    <p>📧 报告生成工具: BI数据分析系统</p>
                    <p>⚡ 版本: 2.0 | 生成引擎: Python + Pandas</p>
                    <p>© 2024 智能数据分析平台 - 专业的数据洞察解决方案</p>
                </div>
            </div>

            <script>
                // 简单的交云效果
                document.addEventListener('DOMContentLoaded', function() {{
                    // 表格行悬停效果
                    const tables = document.querySelectorAll('table');
                    tables.forEach(table => {{
                        const rows = table.querySelectorAll('tr');
                        rows.forEach((row, index) => {{
                            if (index > 0) {{ // 跳过表头
                                row.style.transition = 'all 0.3s ease';
                                row.addEventListener('mouseenter', function() {{
                                    this.style.transform = 'scale(1.02)';
                                    this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
                                }});
                                row.addEventListener('mouseleave', function() {{
                                    this.style.transform = 'scale(1)';
                                    this.style.boxShadow = 'none';
                                }});
                            }}
                        }});
                    }});

                    // 数字计数动画
                    const metricValues = document.querySelectorAll('.metric-value');
                    metricValues.forEach(metric => {{
                        const originalText = metric.textContent;
                        if (/\\d+/.test(originalText)) {{
                            metric.style.opacity = '0';
                            setTimeout(() => {{
                                metric.style.transition = 'opacity 0.5s ease';
                                metric.style.opacity = '1';
                            }}, 100);
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html_content
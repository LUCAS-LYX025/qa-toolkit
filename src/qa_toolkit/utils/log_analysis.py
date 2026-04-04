import streamlit as st
import pandas as pd
import json


class LogAnalyzerUtils:
    """日志分析工具辅助类"""

    @staticmethod
    def apply_text_filters(line, text_filters, logic_operator="AND"):
        """应用文本过滤器 - 支持多条件组合查询"""
        if not text_filters:
            return True

        include_line = True if logic_operator == "AND" else False

        for filter_config in text_filters:
            filter_type = filter_config.get('type')
            filter_value = filter_config.get('value')
            filter_operator = filter_config.get('operator', '包含')  # 默认操作符
            filter_match = False

            # 处理CSV列筛选条件
            if filter_type == 'keyword' and filter_config.get('column'):
                column_name = filter_config.get('column')

                # 从行中提取该列的值 - 支持多种分隔符
                try:
                    # 尝试多种可能的分隔符
                    separators = ['\t', '|', ',']
                    columns = None

                    for sep in separators:
                        if sep in line:
                            columns = line.split(sep)
                            break

                    # 如果没有找到分隔符，使用空格分割
                    if columns is None:
                        columns = line.split()

                    if st.session_state.csv_columns and len(columns) == len(st.session_state.csv_columns):
                        column_index = st.session_state.csv_columns.index(column_name)
                        column_value = columns[column_index].strip()

                        # 检查是否为空值（包括None、null、空字符串等）
                        def is_empty_value(value):
                            if value is None:
                                return True
                            value_str = str(value).strip().lower()
                            return value_str in ['', 'none', 'null', 'nan', 'undefined', 'null']

                        if filter_operator == '有值':
                            filter_match = not is_empty_value(column_value)  # 有具体内容
                        elif filter_operator == '没有值':
                            filter_match = is_empty_value(column_value)  # 值为空
                        elif filter_operator == '包含':
                            filter_match = filter_value.lower() in column_value.lower()
                        elif filter_operator == '等于':
                            filter_match = column_value == filter_value
                        elif filter_operator == '开头为':
                            filter_match = column_value.startswith(filter_value)
                        elif filter_operator == '结尾为':
                            filter_match = column_value.endswith(filter_value)

                        # 调试信息
                        print(
                            f"DEBUG - 列: {column_name}, 值: '{column_value}', 操作符: {filter_operator}, 匹配: {filter_match}")

                except Exception as e:
                    print(f"DEBUG - 解析错误: {e}")
                    filter_match = False

            # 日志级别过滤
            # 日志级别过滤 - 修复DEBUG判断
            elif filter_type == "log_level":
                level_match = False
                if "错误" in filter_value and any(word in line.upper() for word in [' ERROR', ' ERR ', ']ERROR', ']ERR']):
                    level_match = True
                if "警告" in filter_value and any(
                        word in line.upper() for word in [' WARN', ' WARNING', ']WARN', ']WARNING']):
                    level_match = True
                if "信息" in filter_value and any(
                        word in line.upper() for word in [' INFO', ' INFORMATION', ']INFO', ']INFORMATION']):
                    level_match = True
                if "调试" in filter_value and any(word in line.upper() for word in [' DEBUG', ' DBG', ']DEBUG', ']DBG']):
                    level_match = True
                filter_match = level_match

            # IP地址过滤
            elif filter_type == "ip_filter":
                filter_match = filter_value in line

            # 状态码过滤
            elif filter_type == "status_code":
                codes = [code.strip() for code in filter_value.split(',')]
                filter_match = any(
                    f" {code} " in line or line.endswith(f" {code}") or f" {code}" in line for code in codes)

            # 普通关键词过滤
            elif filter_type == "keyword":
                filter_match = filter_value.lower() in line.lower()

            # 仅显示错误
            elif filter_type == "show_only_errors":
                filter_match = any(word in line.upper() for word in ['ERROR', 'ERR', 'FAIL', 'EXCEPTION'])

            # 隐藏调试
            elif filter_type == "hide_debug":
                filter_match = not any(word in line.upper() for word in ['DEBUG', 'DBG'])

            # 根据逻辑运算符组合结果
            if logic_operator == "AND":
                include_line = include_line and filter_match
                if not include_line:  # AND 逻辑下有一个不匹配就可以提前退出
                    break
            else:  # OR 逻辑
                include_line = include_line or filter_match
                if include_line:  # OR 逻辑下有一个匹配就可以提前退出
                    break

        return include_line

    @staticmethod
    def apply_json_filters(df, json_filters, logic_operator="AND"):
        """应用JSON字段过滤器 - 支持多条件组合查询"""
        if not json_filters or df.empty:
            return df

        mask = pd.Series([True] * len(df))

        for filter_config in json_filters:
            column = filter_config.get('column')
            field = filter_config.get('field')
            value = filter_config.get('value')
            value_range = filter_config.get('value_range')

            if not column or not field:
                continue

            def check_json_condition(row):
                try:
                    if pd.isna(row[column]):
                        return False
                    if isinstance(row[column], str):
                        json_data = json.loads(row[column])
                        if field in json_data:
                            field_value = json_data[field]

                            # 范围筛选
                            if value_range:
                                if isinstance(field_value, (int, float)):
                                    return value_range[0] <= field_value <= value_range[1]
                                return False

                            # 值筛选
                            if value:
                                return str(value).lower() in str(field_value).lower()

                            return True  # 如果没有值和范围，只要有这个字段就返回True
                except:
                    pass
                return False

            column_mask = df.apply(check_json_condition, axis=1)

            if logic_operator == "AND":
                mask = mask & column_mask
            else:  # OR 逻辑
                mask = mask | column_mask

        return df[mask]

    @staticmethod
    def detect_log_level(line):
        """检测日志级别 - 修复DEBUG判断"""
        line_upper = line.upper()
        # 添加空格或方括号前缀，避免匹配到单词中的部分
        if any(word in line_upper for word in [' ERROR', ' ERR ', ']ERROR', ']ERR']):
            return "🔴 错误"
        elif any(word in line_upper for word in [' WARN', ' WARNING', ']WARN', ']WARNING']):
            return "🟡 警告"
        elif any(word in line_upper for word in [' INFO', ' INFORMATION', ']INFO', ']INFORMATION']):
            return "🔵 信息"
        elif any(word in line_upper for word in [' DEBUG', ' DBG', ']DEBUG', ']DBG']):
            return "🟢 调试"
        else:
            return "⚪ 其他"

    @staticmethod
    def extract_timestamp(line):
        """提取时间戳（简化版本）"""
        import re
        # 常见的时间戳格式
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
            r'\d{2}:\d{2}:\d{2}',
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        return "未知时间"

    @staticmethod
    def find_keyword_position(line, keyword):
        """查找关键词位置"""
        if not keyword:
            return "未指定"
        position = line.lower().find(keyword.lower())
        if position != -1:
            return f"第 {position + 1} 字符"
        return "未找到"

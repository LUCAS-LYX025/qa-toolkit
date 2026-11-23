"""
JSON和文件操作工具类
包含JSON比较、键计数和文件名提取功能
"""

import os
import re
import streamlit as st
from pathlib import Path
from typing import Union, List, Any, Dict


class JSONFileUtils:
    """
    JSON和文件操作工具类
    提供JSON比较、键计数和文件名提取等功能
    """

    # 递归遍历深度上限，防止深嵌套或循环引用导致 RecursionError。
    MAX_TRAVERSAL_DEPTH = 200

    def __init__(self):
        """初始化工具类"""
        self.comparison_stats = {
            'differences_count': 0,
            'keys_compared': 0
        }

    def get_filename(self, filepath: Union[str, Path], with_extension: bool = True) -> str:
        """从文件路径中提取文件名"""
        filepath = str(filepath)
        basename = os.path.basename(filepath)

        if not with_extension:
            basename = os.path.splitext(basename)[0]

        return basename

    def get_filename_advanced(self, filepath: Union[str, Path],
                              with_extension: bool = True,
                              clean_special_chars: bool = False) -> str:
        """高级文件名提取函数，提供更多选项"""
        filename = self.get_filename(filepath, with_extension)

        if clean_special_chars:
            if with_extension:
                name, ext = os.path.splitext(filename)
                name = re.sub(r'[^\w\-]', '_', name)
                filename = name + ext
            else:
                filename = re.sub(r'[^\w\-]', '_', filename)

        return filename

    def compare_json(self, obj1: Any, obj2: Any, path: str = "",
                     _visited=None, _depth: int = 0) -> List[str]:
        """比较两个JSON对象的差异（带循环引用与深度上限防护）"""
        if _visited is None:
            _visited = set()
        if _depth > self.MAX_TRAVERSAL_DEPTH:
            return [f"嵌套层级超过上限 {self.MAX_TRAVERSAL_DEPTH}: {path}"]

        differences = []
        self.comparison_stats['keys_compared'] += 1

        if type(obj1) != type(obj2):
            diff_msg = f"类型不同: {path} ({type(obj1).__name__} vs {type(obj2).__name__})"
            differences.append(diff_msg)
            self.comparison_stats['differences_count'] += 1
            return differences

        if isinstance(obj1, (dict, list)):
            pair_key = (id(obj1), id(obj2))
            if pair_key in _visited:
                return differences
            _visited = _visited | {pair_key}

        if isinstance(obj1, dict):
            all_keys = set(obj1.keys()) | set(obj2.keys())
            for key in all_keys:
                new_path = f"{path}.{key}" if path else key
                if key in obj1 and key not in obj2:
                    diff_msg = f"键缺失于JSON2: {new_path}"
                    differences.append(diff_msg)
                    self.comparison_stats['differences_count'] += 1
                elif key not in obj1 and key in obj2:
                    diff_msg = f"键缺失于JSON1: {new_path}"
                    differences.append(diff_msg)
                    self.comparison_stats['differences_count'] += 1
                else:
                    differences.extend(self.compare_json(
                        obj1[key], obj2[key], new_path, _visited, _depth + 1
                    ))
        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                diff_msg = f"数组长度不同: {path} ({len(obj1)} vs {len(obj2)})"
                differences.append(diff_msg)
                self.comparison_stats['differences_count'] += 1
            else:
                for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                    differences.extend(self.compare_json(
                        item1, item2, f"{path}[{i}]", _visited, _depth + 1
                    ))
        else:
            if obj1 != obj2:
                diff_msg = f"值不同: {path} ({obj1} vs {obj2})"
                differences.append(diff_msg)
                self.comparison_stats['differences_count'] += 1

        return differences

    def count_keys(self, obj: Any, _visited=None, _depth: int = 0) -> int:
        """计算JSON对象中的键数量（带循环引用与深度上限防护）"""
        if _visited is None:
            _visited = set()
        if _depth > self.MAX_TRAVERSAL_DEPTH:
            return 0

        if isinstance(obj, (dict, list)):
            if id(obj) in _visited:
                return 0
            _visited = _visited | {id(obj)}

        if isinstance(obj, dict):
            count = len(obj)
            for value in obj.values():
                count += self.count_keys(value, _visited, _depth + 1)
            return count
        elif isinstance(obj, list):
            count = 0
            for item in obj:
                count += self.count_keys(item, _visited, _depth + 1)
            return count
        else:
            return 0

    def get_comparison_stats(self) -> Dict[str, int]:
        """获取比较统计信息"""
        return self.comparison_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.comparison_stats = {
            'differences_count': 0,
            'keys_compared': 0
        }

    def analyze_json_structure(self, obj: Any, current_level: int = 0) -> Dict[str, Any]:
        """分析JSON结构"""
        analysis = {
            'type': type(obj).__name__,
            'level': current_level,
            'size': len(obj) if hasattr(obj, '__len__') else 1,
            'children': []
        }

        # 对于基本类型，保存值信息
        if not isinstance(obj, (dict, list)):
            analysis['value'] = str(obj)

        if isinstance(obj, dict):
            for key, value in obj.items():
                child_analysis = self.analyze_json_structure(value, current_level + 1)
                child_analysis['key'] = key
                analysis['children'].append(child_analysis)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                child_analysis = self.analyze_json_structure(item, current_level + 1)
                child_analysis['index'] = i
                analysis['children'].append(child_analysis)

        return analysis

    def get_json_depth(self, obj: Any, current_depth: int = 0,
                       _visited=None) -> int:
        """计算JSON对象的最大深度（带循环引用与深度上限防护）"""
        if _visited is None:
            _visited = set()
        if current_depth >= self.MAX_TRAVERSAL_DEPTH:
            return current_depth

        if isinstance(obj, (dict, list)):
            if id(obj) in _visited:
                return current_depth
            _visited = _visited | {id(obj)}

        if isinstance(obj, dict):
            if obj:
                return max(
                    self.get_json_depth(value, current_depth + 1, _visited)
                    for value in obj.values()
                )
            return current_depth + 1
        elif isinstance(obj, list):
            if obj:
                return max(
                    self.get_json_depth(item, current_depth + 1, _visited)
                    for item in obj
                )
            return current_depth + 1
        else:
            return current_depth

    def display_json_structure(self, structure: Dict[str, Any], level: int = 0):
        """显示JSON结构树 - 优化版本"""
        indent = "  " * level
        node_type = structure['type']

        if node_type == 'dict':
            st.text(f"{indent}📁 对象 (键数量: {structure['size']})")
            for child in structure['children']:
                key_name = child.get('key', '')
                # 方案1：使用 st.text() 保持原始格式
                st.text(f"{indent}  🔑 {key_name}:")
                self.display_json_structure(child, level + 1)
        elif node_type == 'list':
            st.text(f"{indent}📋 数组 (元素数量: {structure['size']})")
            for child in structure['children']:
                index = child.get('index', 0)
                # 方案2：使用 st.write() 但不带 end 参数
                st.write(f"{indent}  📍 [{index}]:")
                self.display_json_structure(child, level + 1)
        else:
            value = structure.get('value', '')
            if value:
                # 方案3：使用 st.code() 显示值
                st.text(f"{indent}📄 {node_type}: {value}")
            else:
                st.text(f"{indent}📄 {node_type}")

    def execute_jsonpath(self, json_data: Any, expression: str) -> List[Any]:
        """执行JSONPath查询"""
        try:
            # 这里可以使用 jsonpath-ng 库，如果没有安装可以使用简化实现
            return self._simple_jsonpath(json_data, expression)
        except Exception as e:
            raise Exception(f"JSONPath执行错误: {e}")

    def _simple_jsonpath(self, data: Any, path: str) -> List[Any]:
        """简化版JSONPath实现"""
        if path == "$":
            return [data]

        # 处理函数调用如 .length()
        if path.endswith('.length()'):
            prop_path = path[:-9]  # 移除 .length()
            if prop_path == "$":
                if isinstance(data, list):
                    return [len(data)]
                elif isinstance(data, dict):
                    return [len(data)]
                else:
                    return [1]
            else:
                # 获取路径对应的值，然后计算长度
                target_data = self._evaluate_path(data, prop_path[1:] if prop_path.startswith('$') else prop_path)
                if target_data and isinstance(target_data[0], (list, dict)):
                    return [len(target_data[0])]
                else:
                    return [len(target_data)] if target_data else [0]

        # 移除开头的 $ 符号
        if path.startswith("$"):
            path = path[1:]

        return self._evaluate_path(data, path)

    def _evaluate_path(self, data: Any, path: str) -> List[Any]:
        """完整的JSONPath评估实现"""
        if not path:
            return [data]

        results = []

        # 处理递归下降操作符 ..
        if path.startswith(".."):
            remaining = path[2:]

            # 首先检查当前层级是否匹配剩余路径
            if remaining:
                if remaining.startswith('.'):
                    remaining = remaining[1:]
                results.extend(self._evaluate_path(data, remaining))

            # 递归搜索所有子层级
            if isinstance(data, dict):
                for value in data.values():
                    results.extend(self._evaluate_path(value, path))  # 继续递归下降
                    if remaining:
                        results.extend(self._evaluate_path(value, remaining))
            elif isinstance(data, list):
                for item in data:
                    results.extend(self._evaluate_path(item, path))  # 继续递归下降
                    if remaining:
                        results.extend(self._evaluate_path(item, remaining))
            return results

        # 处理通配符 *
        if path == "*":
            if isinstance(data, dict):
                return list(data.values())
            elif isinstance(data, list):
                return data
            return []

        # 处理所有元素选择 $..*
        if path.startswith("*"):
            remaining = path[1:]
            if isinstance(data, dict):
                for value in data.values():
                    results.extend(self._evaluate_path(value, remaining))
            elif isinstance(data, list):
                for item in data:
                    results.extend(self._evaluate_path(item, remaining))
            return results

        # 处理数组切片 [start:end:step]
        if path.startswith("["):
            close_bracket = path.find(']')
            if close_bracket == -1:
                return []

            index_expr = path[1:close_bracket]
            remaining = path[close_bracket + 1:]

            if isinstance(data, list):
                # 处理切片 [start:end:step]
                if ':' in index_expr:
                    slice_results = self._handle_slice(data, index_expr, remaining)
                    results.extend(slice_results)
                # 处理过滤器 [?(@.condition)]
                elif index_expr.startswith('?(@'):
                    filter_results = self._apply_filter(data, index_expr[3:-1], remaining)
                    results.extend(filter_results)
                # 处理多个索引 [0,1]
                elif ',' in index_expr:
                    indices = [idx.strip() for idx in index_expr.split(',')]
                    for idx_str in indices:
                        if idx_str.isdigit() or (idx_str.startswith('-') and idx_str[1:].isdigit()):
                            idx = int(idx_str)
                            if -len(data) <= idx < len(data):
                                adjusted_idx = idx if idx >= 0 else len(data) + idx
                                results.extend(self._evaluate_path(data[adjusted_idx], remaining))
                # 处理单个索引 [0], [-1]
                elif index_expr.isdigit() or (index_expr.startswith('-') and index_expr[1:].isdigit()):
                    idx = int(index_expr)
                    if -len(data) <= idx < len(data):
                        adjusted_idx = idx if idx >= 0 else len(data) + idx
                        results.extend(self._evaluate_path(data[adjusted_idx], remaining))
                # 处理通配符 [*]
                elif index_expr == '*':
                    for item in data:
                        results.extend(self._evaluate_path(item, remaining))
            return results

        # 处理属性访问 .property
        if path.startswith("."):
            next_dot = path.find('.', 1)
            next_bracket = path.find('[', 1)

            # 找到下一个分隔符
            separators = [sep for sep in [next_dot, next_bracket] if sep != -1]
            next_sep = min(separators) if separators else len(path)

            prop = path[1:next_sep]
            remaining = path[next_sep:] if next_sep < len(path) else ""

            if isinstance(data, dict):
                if prop in data:
                    results.extend(self._evaluate_path(data[prop], remaining))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and prop in item:
                        results.extend(self._evaluate_path(item[prop], remaining))
            return results

        # 处理直接属性访问（没有前导点）
        if '.' in path or '[' in path:
            # 找到第一个分隔符
            dot_pos = path.find('.')
            bracket_pos = path.find('[')

            first_sep = min([pos for pos in [dot_pos, bracket_pos] if pos != -1])
            prop = path[:first_sep]
            remaining = path[first_sep:]

            if isinstance(data, dict) and prop in data:
                results.extend(self._evaluate_path(data[prop], remaining))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and prop in item:
                        results.extend(self._evaluate_path(item[prop], remaining))
        else:
            # 单个属性
            if isinstance(data, dict) and path in data:
                return [data[path]]
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and path in item:
                        results.append(item[path])

        return results

    def _evaluate_simple_path(self, data: Any, path: str) -> List[Any]:
        """评估简单路径表达式"""
        if not path:
            return [data]

        # 处理点表示法 .property
        if path.startswith('.'):
            path = path[1:]  # 移除开头的点

        # 查找下一个分隔符
        dot_pos = path.find('.')
        bracket_pos = path.find('[')

        # 确定下一个路径段
        if dot_pos == -1 and bracket_pos == -1:
            # 最后一个路径段
            return self._get_property(data, path)
        elif bracket_pos != -1 and (dot_pos == -1 or bracket_pos < dot_pos):
            # 下一个是数组访问 [index]
            prop = path[:bracket_pos]
            remaining = path[bracket_pos:]

            if prop:  # 有属性名，如 books[0]
                current_data = self._get_property(data, prop)
            else:  # 直接数组访问，如 [0]
                current_data = [data] if data is not None else []

            results = []
            for item in current_data:
                results.extend(self._process_array_access(item, remaining))
            return results
        else:
            # 下一个是属性访问 .property
            prop = path[:dot_pos]
            remaining = path[dot_pos:]

            current_data = self._get_property(data, prop)
            results = []
            for item in current_data:
                results.extend(self._evaluate_simple_path(item, remaining))
            return results

    def _get_property(self, data: Any, prop: str) -> List[Any]:
        """获取属性值"""
        if prop == '*':
            # 通配符 - 获取所有属性/元素
            if isinstance(data, dict):
                return list(data.values())
            elif isinstance(data, list):
                return data
            else:
                return []
        elif data is None:
            return []
        elif isinstance(data, dict) and prop in data:
            return [data[prop]]
        elif isinstance(data, list):
            # 对于数组，尝试在每个元素上获取属性
            results = []
            for item in data:
                if isinstance(item, dict) and prop in item:
                    results.append(item[prop])
            return results
        else:
            return []

    def _process_array_access(self, data: Any, path: str) -> List[Any]:
        """处理数组访问 [index] 或 [*]"""
        if not path.startswith('[') or ']' not in path:
            return []

        close_bracket = path.find(']')
        index_expr = path[1:close_bracket]
        remaining = path[close_bracket + 1:]

        if not isinstance(data, list):
            return []

        results = []

        if index_expr == '*':
            # 通配符 - 所有数组元素
            for item in data:
                if remaining:
                    results.extend(self._evaluate_simple_path(item, remaining))
                else:
                    results.append(item)
        elif index_expr.isdigit():
            # 数字索引
            index = int(index_expr)
            if 0 <= index < len(data):
                item = data[index]
                if remaining:
                    results.extend(self._evaluate_simple_path(item, remaining))
                else:
                    results.append(item)
        elif ',' in index_expr:
            # 多个索引 [0,1,2]
            indices = [idx.strip() for idx in index_expr.split(',')]
            for idx_str in indices:
                if idx_str.isdigit():
                    idx = int(idx_str)
                    if 0 <= idx < len(data):
                        item = data[idx]
                        if remaining:
                            results.extend(self._evaluate_simple_path(item, remaining))
                        else:
                            results.append(item)
        elif ':' in index_expr:
            # 切片 [start:end:step]
            results.extend(self._process_slice(data, index_expr, remaining))
        elif index_expr.startswith('?('):
            # 过滤器
            filter_expr = index_expr[2:-1]  # 移除 ?( 和 )
            results.extend(self._apply_filter(data, filter_expr, remaining))
        else:
            # 其他情况，尝试作为属性过滤器
            results.extend(self._apply_filter(data, index_expr, remaining))

        return results

    def _process_slice(self, data: list, slice_expr: str, remaining: str) -> List[Any]:
        """处理数组切片"""
        parts = slice_expr.split(':')
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else len(data)
        step = int(parts[2]) if len(parts) > 2 and parts[2] else 1

        results = []
        for i in range(start, end, step):
            if i < len(data):
                item = data[i]
                if remaining:
                    results.extend(self._evaluate_simple_path(item, remaining))
                else:
                    results.append(item)
        return results

    def _handle_slice(self, data: List[Any], slice_expr: str, remaining: str) -> List[Any]:
        """处理数组切片操作"""
        if not isinstance(data, list):
            return []

        parts = slice_expr.split(':')

        # 解析起始位置
        start = int(parts[0]) if parts[0] else 0
        if start < 0:
            start = max(0, len(data) + start)

        # 解析结束位置
        end = int(parts[1]) if len(parts) > 1 and parts[1] else len(data)
        if end < 0:
            end = max(0, len(data) + end)

        # 解析步长
        step = int(parts[2]) if len(parts) > 2 and parts[2] else 1

        results = []
        for i in range(start, end, step):
            if 0 <= i < len(data):
                results.extend(self._evaluate_path(data[i], remaining))

        return results

    def _apply_filter(self, data: List[Any], filter_expr: str, remaining: str) -> List[Any]:
        """应用过滤器表达式"""
        if not isinstance(data, list):
            return []

        results = []

        for item in data:
            if self._matches_filter(item, filter_expr):
                results.extend(self._evaluate_path(item, remaining))

        return results

    def _matches_filter(self, item: Any, filter_expr: str) -> bool:
        """检查项目是否匹配过滤器条件"""
        if not isinstance(item, dict):
            return False

        # 处理属性存在性检查 ?(@.isbn)
        if filter_expr.replace(' ', '') == '.isbn' or filter_expr == 'isbn':
            return 'isbn' in item

        # 处理相等比较 ==
        if '==' in filter_expr:
            parts = filter_expr.split('==', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            value = parts[1].strip().strip('"\'')

            if prop in item:
                if isinstance(item[prop], (int, float)):
                    try:
                        return float(item[prop]) == float(value)
                    except ValueError:
                        return str(item[prop]) == value
                else:
                    return str(item[prop]) == value

        # 处理不等比较 !=
        elif '!=' in filter_expr:
            parts = filter_expr.split('!=', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            value = parts[1].strip().strip('"\'')

            if prop in item:
                return str(item[prop]) != value

        # 处理数值比较 <, >, <=, >=
        elif '<=' in filter_expr:
            parts = filter_expr.split('<=', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            value = parts[1].strip()

            if prop in item and isinstance(item[prop], (int, float)):
                try:
                    return float(item[prop]) <= float(value)
                except ValueError:
                    return False

        elif '>=' in filter_expr:
            parts = filter_expr.split('>=', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            value = parts[1].strip()

            if prop in item and isinstance(item[prop], (int, float)):
                try:
                    return float(item[prop]) >= float(value)
                except ValueError:
                    return False

        elif '<' in filter_expr and not '<=' in filter_expr:
            parts = filter_expr.split('<', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            value = parts[1].strip()

            if prop in item and isinstance(item[prop], (int, float)):
                try:
                    return float(item[prop]) < float(value)
                except ValueError:
                    return False

        elif '>' in filter_expr and not '>=' in filter_expr:
            parts = filter_expr.split('>', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            value = parts[1].strip()

            if prop in item and isinstance(item[prop], (int, float)):
                try:
                    return float(item[prop]) > float(value)
                except ValueError:
                    return False

        # 处理正则表达式匹配 =~
        elif '=~' in filter_expr:
            parts = filter_expr.split('=~', 1)
            prop = parts[0].replace('@.', '').replace('.', '').strip()
            pattern = parts[1].strip().strip('/')

            if prop in item:
                import re
                try:
                    # 检查是否有标志
                    if '/' in pattern and pattern.rfind('/') > pattern.find('/'):
                        regex_parts = pattern.rsplit('/', 1)
                        pattern_str = regex_parts[0]
                        flags = regex_parts[1] if len(regex_parts) > 1 else ''
                        re_flags = re.IGNORECASE if 'i' in flags else 0
                        return bool(re.search(pattern_str, str(item[prop]), re_flags))
                    else:
                        return bool(re.search(pattern, str(item[prop])))
                except re.error:
                    return False

        return False


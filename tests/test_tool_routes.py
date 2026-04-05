import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.config.constants import TOOL_CATEGORIES
from qa_toolkit.config.tool_routes import INLINE_TOOL_CATEGORIES, PAGE_TOOL_CONFIG


def test_all_tool_categories_are_explicitly_covered_by_router_registry():
    tool_names = set(TOOL_CATEGORIES.keys())
    page_tool_names = set(PAGE_TOOL_CONFIG.keys())

    uncovered = tool_names - INLINE_TOOL_CATEGORIES - page_tool_names
    overlap = INLINE_TOOL_CATEGORIES & page_tool_names

    assert not uncovered, f"以下工具未接入显式路由注册表: {sorted(uncovered)}"
    assert not overlap, f"以下工具同时声明为 inline 和 page 路由: {sorted(overlap)}"


def test_page_tool_config_contains_required_fields():
    required_fields = {"module_path", "function_name", "page_label"}
    for tool_name, config in PAGE_TOOL_CONFIG.items():
        assert required_fields.issubset(config.keys()), f"{tool_name} 缺少路由配置字段"
        assert all(str(config[field]).strip() for field in required_fields), f"{tool_name} 路由配置存在空值"


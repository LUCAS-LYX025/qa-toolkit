import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.config.constants import HEADLINE_STYLES


def test_headline_hero_uses_in_page_trigger_nodes_instead_of_links() -> None:
    assert 'href="?hero_tool=' not in HEADLINE_STYLES
    assert 'data-trigger-key="hero_tool_trigger_regex"' in HEADLINE_STYLES
    assert 'data-trigger-key="hero_tool_trigger_json"' in HEADLINE_STYLES
    assert 'data-trigger-key="hero_tool_trigger_logs"' in HEADLINE_STYLES
    assert 'data-trigger-key="hero_tool_trigger_api"' in HEADLINE_STYLES

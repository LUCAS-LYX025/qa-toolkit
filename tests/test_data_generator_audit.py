"""数据生成工具专项审计回归（Issues #448-#459 / DG-01 ~ DG-12）。"""
import datetime
import random
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.config.constants import PASSWORD_OPTIONS  # noqa: E402
from qa_toolkit.core import data_generator_registry as dg_reg  # noqa: E402
from qa_toolkit.tools.data_generator import DataGenerator  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_registry():
    dg_reg.reset_data_generator_registry()
    yield
    dg_reg.reset_data_generator_registry()


def test_dg01_password_length_conflict_is_rejected():
    gen = DataGenerator()
    with pytest.raises(ValueError, match="不足以覆盖"):
        gen.generate_random_password(2, PASSWORD_OPTIONS, rng=random.Random(7))
    assert len(gen.generate_random_password(8, PASSWORD_OPTIONS, rng=random.Random(7))) == 8


def test_dg02_all_mobile_prefixes_produce_eleven_digits():
    gen = DataGenerator()
    numbers = [gen.generate_random_phone_number("移动", rng=random.Random(seed)) for seed in range(300)]
    assert {len(number) for number in numbers} == {11}
    assert all(number.isdigit() for number in numbers)


def test_dg03_id_card_never_has_future_birth_date():
    gen = DataGenerator()
    reference = datetime.datetime(2026, 1, 1, 9, 0, 0)
    for seed in range(200):
        card = gen.generate_random_id_card("北京市", "男", 0, 100, rng=random.Random(seed),
                                           reference_date=reference)
        birth = datetime.datetime.strptime(card[6:14], "%Y%m%d")
        assert birth <= reference


def test_dg04_inverted_age_range_has_readable_error():
    gen = DataGenerator()
    with pytest.raises(ValueError, match="最小年龄（60）不能大于最大年龄（18）"):
        gen.generate_random_id_card("北京市", "男", 60, 18, rng=random.Random(1))


def test_dg05_faker_id_card_must_pass_constraints():
    gen = DataGenerator()
    gen.faker_available = True
    gen.fake = SimpleNamespace(ssn=lambda: "110101199003072316")
    card = gen.generate_conditional_id_card("北京市", "男", 60, 70)
    assert 1956 <= int(card[6:10]) <= 1966
    assert int(card[16]) % 2 == 1


def test_dg06_faker_seed_is_reproducible():
    gen = DataGenerator()
    if not gen.is_faker_available():
        pytest.skip("Faker 未安装")
    first = gen.generate_faker_data("人物信息", "随机姓名", 4, seed=20261126)
    second = gen.generate_faker_data("人物信息", "随机姓名", 4, seed=20261126)
    assert first == second and len(first) == 4


def test_dg07_unknown_faker_combination_raises():
    gen = DataGenerator()
    if not gen.is_faker_available():
        pytest.skip("Faker 未安装")
    with pytest.raises(ValueError, match="不支持的 Faker 数据组合"):
        gen.generate_faker_data("不存在的类别", "不存在的类型", 3)


def test_dg08_unknown_sex_is_not_guessed():
    gen = DataGenerator()
    text = gen.format_profile_data({"name": "测试用户", "sex": "X", "username": "u1"})
    assert "性别： 未知" in text
    assert "性别： 男" not in text
    text = gen.format_profile_data({"name": "测试用户", "sex": "F", "website": "https://example.com"})
    assert "性别： 女" in text and "https://example.com" in text


def test_dg09_generated_html_content_is_escaped():
    from qa_toolkit.core.i18n import th

    page_src = (ROOT / "src/qa_toolkit/ui/pages/data_generator_page.py").read_text(encoding="utf-8")
    snippet = page_src[page_src.index("def display_generated_results"):page_src.index("def display_structured_results")]
    assert "html.escape(str(content))" in snippet
    # 标题经 i18n 的 th() 输出：先翻译再转义，安全性不弱于直接 html.escape
    assert 'th(t("📋 生成结果 - {title}", title=title))' in snippet
    assert th("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert "html.escape(str(st.session_state.faker_result))" in page_src


def test_dg10_scenarios_and_boundary_fields_are_registry_driven():
    from qa_toolkit.core.data_generator_registry import (
        BoundaryFieldSpec, DatasetScenarioSpec, register_boundary_field, register_dataset_scenario,
    )

    gen = DataGenerator()
    register_dataset_scenario(DatasetScenarioSpec(
        key="custom_lead", label="自定义线索", description="", fields=("id",),
        builder=lambda **kwargs: {"id": "CUSTOM-1", "batch_tag": kwargs["batch_token"]},
    ))
    register_boundary_field(BoundaryFieldSpec(
        key="custom_code", label="自定义编码", description="",
        builder=lambda gen_, ctx, add_case: add_case("空值", "异常值", "", "应拒绝"),
    ))
    assert "自定义线索" in gen.get_test_data_scenarios()
    assert "自定义编码" in gen.get_boundary_field_templates()
    assert gen.generate_test_dataset("custom_lead", count=1)[0]["id"] == "CUSTOM-1"
    assert gen.generate_boundary_test_cases("custom_code", seed=1)[0]["case_name"] == "空值"
    with pytest.raises(ValueError, match="已注册"):
        register_dataset_scenario(DatasetScenarioSpec("custom_lead", "x", "", ()))


def test_dg10_registry_follows_conventions():
    spec = dg_reg.get_dataset_scenario("注册登录账号")
    with pytest.raises(FrozenInstanceError):
        spec.label = "changed"
    dg_reg.get_dataset_scenarios().clear()
    assert "注册登录账号" in dg_reg.get_dataset_scenarios()
    summary = dg_reg.get_registry_summary()
    assert set(summary) == {"造数场景", "边界字段", "生成地区", "扩展场景数", "扩展字段数"}


def test_dg11_locale_is_selectable_on_page():
    assert "en_US" in dg_reg.get_locales()
    app = AppTest.from_file(str(ROOT / "src/qa_toolkit/streamlit_app.py"), default_timeout=30).run()
    assert not app.exception, [item.value for item in app.exception]
    assert any(getattr(item, "label", "") == "生成地区" for item in app.selectbox)
    assert any("注册式扩展" in getattr(item, "value", "") for item in app.caption)


def test_dg13_navigation_bridge_retries_hidden_trigger():
    app_src = (ROOT / "src/qa_toolkit/streamlit_app.py").read_text(encoding="utf-8")
    bridge = app_src[app_src.index("def render_tool_card_click_bridge"):
                     app_src.index("def render_hero_tool_triggers")]
    assert "setTimeout(clickWhenReady, 60)" in bridge
    assert "bridgePending" in bridge
    assert "attempts++ < 20" in bridge


def test_dg12_min_length_one_has_no_contradictory_case():
    gen = DataGenerator()
    cases = gen.generate_boundary_test_cases("用户名", seed=3, min_length=1, max_length=1)
    assert not [case for case in cases if case["case_name"] == "长度不足"]
    normal = [case for case in cases if case["case_name"] == "最大长度边界"]
    assert normal and normal[0]["expected"] == "应通过"

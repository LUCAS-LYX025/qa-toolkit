"""数据生成工具专项审计探针（测试专家 + 产品工程师双视角）。

record 的第二项为 True 表示问题坐实。修复前应为 N/N，修复后应为 0/N。
只读探针：不修改业务数据，不联网，不输出敏感信息。
"""
import datetime
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.config.constants import PASSWORD_OPTIONS  # noqa: E402
from qa_toolkit.tools.data_generator import DataGenerator  # noqa: E402

RESULTS = []


def record(case_id, reproduced, detail):
    RESULTS.append((case_id, reproduced, detail))
    print(f"{case_id}: {'REPRODUCED' if reproduced else 'resolved'} - {detail}", flush=True)


def _config():
    return (ROOT / "src/qa_toolkit/config").as_posix(), (ROOT / "src/qa_toolkit/tools/data_generator.py").read_text(encoding="utf-8")


def probe_01_password_length():
    gen = DataGenerator()
    try:
        value = gen.generate_random_password(2, PASSWORD_OPTIONS, rng=random.Random(7))
    except ValueError as exc:
        bad = False
        detail = f"已显式拒绝冲突参数: {exc}"
    else:
        bad = len(value) != 2
        detail = f"请求 2 位、勾选 4 类字符，实际生成 {len(value)} 位"
    record("DG-01", bad, detail)


def probe_02_mobile_prefix_length():
    gen = DataGenerator()
    lengths = {len(gen.generate_random_phone_number("移动", rng=random.Random(seed))) for seed in range(300)}
    bad = lengths != {11}
    record("DG-02", bad, f"移动号段 300 次生成出现位数 {sorted(lengths)}（含 4 位号段时应补 7 位）")


def probe_03_future_birth_date():
    gen = DataGenerator()
    reference = datetime.datetime(2026, 1, 1, 9, 0, 0)
    found = ""
    for seed in range(400):
        card = gen.generate_random_id_card("北京市", "男", 0, 100, rng=random.Random(seed), reference_date=reference)
        birth = datetime.datetime.strptime(card[6:14], "%Y%m%d")
        if birth > reference:
            found = f"{seed}:{card[6:14]}"
            break
    record("DG-03", bool(found), f"0 岁场景生成晚于生成时刻的出生日期 {found or '未发现'}")


def probe_04_inverted_age_range():
    gen = DataGenerator()
    try:
        gen.generate_random_id_card("北京市", "男", 60, 18, rng=random.Random(1))
        bad = False
        detail = "已友好拒绝"
    except ValueError as exc:
        bad = "empty range" in str(exc) or "randint" in str(exc)
        detail = (f"抛出底层随机库异常: {exc}" if bad else f"已显式校验: {exc}")
    record("DG-04", bad, detail)


def probe_05_faker_ignores_identity_constraints():
    gen = DataGenerator()
    gen.faker_available = True
    gen.fake = SimpleNamespace(ssn=lambda: "110101199003072316")  # 1990 男，固定值
    card = gen.generate_conditional_id_card("北京市", "男", 60, 70)
    birth_year = int(card[6:10])
    bad = birth_year > 1966  # 2026 年时 60 岁以上应不晚于 1966
    record("DG-05", bad,
           (f"指定 60-70 岁却返回 {birth_year} 年出生（Faker 值原样透传）" if bad
            else f"指定 60-70 岁返回 {birth_year} 年出生，已过约束校验"))


def probe_06_faker_seed_ignored():
    gen = DataGenerator()
    first = gen.generate_faker_data("人物信息", "随机姓名", 5, seed=20261126)
    second = gen.generate_faker_data("人物信息", "随机姓名", 5, seed=20261126)
    bad = first != second
    record("DG-06", bad, "传 seed 后两次生成结果不同，无法复现" if bad else "同 seed 两次结果一致")


def probe_07_unknown_faker_combo_silent():
    gen = DataGenerator()
    try:
        result = gen.generate_faker_data("不存在的类别", "不存在的类型", 3)
    except ValueError as exc:
        bad = False
        detail = f"已显式拒绝未知组合: {exc}"
    else:
        bad = result == []
        detail = "未知类别/子类别静默返回空列表，页面无任何错误提示"
    record("DG-07", bad, detail)


def probe_08_unknown_sex_defaults_to_male():
    gen = DataGenerator()
    text = gen.format_profile_data({"name": "测试用户", "sex": "X", "username": "u1"})
    bad = "性别： 男" in text
    record("DG-08", bad, "未知性别被写成“男”，凭空补数据" if bad else "未知性别显示为“未知”")


def probe_09_raw_html_in_results():
    _, src = _config()
    app_src = (ROOT / "src/qa_toolkit/streamlit_app.py").read_text(encoding="utf-8")
    snippet = app_src[app_src.index("def display_generated_results"):app_src.index("def display_structured_results")]
    bad = ('<div class="result-box">{content}</div>' in snippet
           and "html.escape" not in snippet)
    record("DG-09", bad, "生成内容未转义直接拼进 unsafe_allow_html 的 HTML")


def probe_10_no_registry_extension_point():
    _, src = _config()
    registry = ROOT / "src/qa_toolkit/core/data_generator_registry.py"
    registry_src = registry.read_text(encoding="utf-8") if registry.exists() else ""
    bad = ("register_dataset_scenario" not in registry_src
           or "register_boundary_field" not in registry_src
           or "dg_reg.get_dataset_scenario" not in src)
    record("DG-10", bad, "造数场景/边界字段无注册式扩展点" if bad else "场景、字段与地区均由注册表驱动")


def probe_11_locale_hardcoded_in_ui():
    app_src = (ROOT / "src/qa_toolkit/streamlit_app.py").read_text(encoding="utf-8")
    bad = "generator = DataGenerator()" in app_src or "生成地区" not in app_src
    record("DG-11", bad,
           "DataGenerator 支持 locale，但页面固定 zh_CN，无法生成多地区数据" if bad
           else "页面提供生成地区选择并传入 DataGenerator")


def probe_12_boundary_case_self_contradiction():
    gen = DataGenerator()
    cases = gen.generate_boundary_test_cases("用户名", seed=3, min_length=1, max_length=1)
    short = [c for c in cases if c["case_name"] == "长度不足"]
    bad = bool(short) and len(str(short[0]["value"])) >= 1 and short[0]["expected"] == "应拒绝"
    record("DG-12", bad, "min_length=1 时“长度不足”样例长 1 位，按自身规则应通过却标记应拒绝")


def probe_13_navigation_bridge_has_no_retry():
    app_src = (ROOT / "src/qa_toolkit/streamlit_app.py").read_text(encoding="utf-8")
    start = app_src.index("def render_tool_card_click_bridge")
    end = app_src.index("def render_hero_tool_triggers")
    bridge = app_src[start:end]
    bad = "setTimeout" not in bridge or "bridgePending" not in bridge
    record("DG-13", bad, "工具卡片桥接只尝试一次，隐藏按钮未就绪时点击丢失" if bad else "桥接会重试等待隐藏按钮就绪")


def main():
    print("=== 数据生成工具专项审计探针（13 项） ===", flush=True)
    probe_01_password_length()
    probe_02_mobile_prefix_length()
    probe_03_future_birth_date()
    probe_04_inverted_age_range()
    probe_05_faker_ignores_identity_constraints()
    probe_06_faker_seed_ignored()
    probe_07_unknown_faker_combo_silent()
    probe_08_unknown_sex_defaults_to_male()
    probe_09_raw_html_in_results()
    probe_10_no_registry_extension_point()
    probe_11_locale_hardcoded_in_ui()
    probe_12_boundary_case_self_contradiction()
    probe_13_navigation_bridge_has_no_retry()
    reproduced = sum(1 for _, bad, _ in RESULTS if bad)
    print(f"共 {reproduced}/{len(RESULTS)} 项坐实（修复前应为 {len(RESULTS)}/{len(RESULTS)}，修复后应为 0/{len(RESULTS)}）", flush=True)


if __name__ == "__main__":
    main()

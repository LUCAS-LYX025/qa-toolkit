import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.tools.data_generator import DataGenerator


def test_generate_test_dataset_is_reproducible_with_seed():
    generator = DataGenerator()

    first_batch = generator.generate_test_dataset(
        "注册登录账号",
        count=3,
        seed=20260404,
        batch_tag="regcase",
        email_domain="qa.test",
    )
    second_batch = generator.generate_test_dataset(
        "注册登录账号",
        count=3,
        seed=20260404,
        batch_tag="regcase",
        email_domain="qa.test",
    )

    assert first_batch == second_batch
    assert len(first_batch) == 3
    assert len({item["username"] for item in first_batch}) == 3
    assert all(item["email"].endswith("@qa.test") for item in first_batch)
    assert all(item["batch_tag"] == "regcase" for item in first_batch)


def test_generate_order_dataset_keeps_payment_fields_consistent():
    generator = DataGenerator()

    orders = generator.generate_test_dataset("订单支付记录", count=12, seed=7, batch_tag="pay")

    assert len(orders) == 12
    for order in orders:
        order_amount = float(order["order_amount"])
        discount_amount = float(order["discount_amount"])
        pay_amount = float(order["pay_amount"])

        assert pay_amount == pytest.approx(max(order_amount - discount_amount, 0))
        if order["pay_status"] == "待支付":
            assert order["pay_time"] == ""
            assert order["order_status"] == "待支付"


def test_generate_employee_dataset_normalizes_batch_tag_and_formats_employee_no():
    generator = DataGenerator()

    employees = generator.generate_test_dataset(
        "企业员工档案",
        count=2,
        seed=2025,
        batch_tag=" Regression 01 ",
        email_domain="corp.test",
    )

    assert len(employees) == 2
    assert all(item["batch_tag"] == "regression01" for item in employees)
    assert employees[0]["employee_no"].startswith("EMP-REGRESSION01-")
    assert all(item["email"].endswith("@corp.test") for item in employees)


def test_generate_shipping_dataset_marks_first_record_as_default():
    generator = DataGenerator()

    records = generator.generate_test_dataset("收货地址簿", count=5, seed=99, batch_tag="addr")

    assert len(records) == 5
    assert records[0]["is_default"] == "是"
    assert all(record["address_id"].startswith("ADDR-ADDR-") for record in records)
    assert all(record["district_area_code"] for record in records)


def test_generate_boundary_cases_supports_type_filter_and_expected_values():
    generator = DataGenerator()

    cases = generator.generate_boundary_test_cases(
        "邮箱",
        seed=123,
        include_valid=True,
        include_boundary=False,
        include_invalid=True,
        email_domain="qa.test",
    )

    assert cases
    assert all(item["case_type"] != "边界值" for item in cases)
    assert cases[0]["case_id"] == "EMAIL-01"
    assert any(item["case_name"] == "常规邮箱" and item["value"].endswith("@qa.test") for item in cases)
    assert any(item["case_name"] == "缺少@" and item["expected"] == "应拒绝" for item in cases)


def test_generate_boundary_cases_for_amount_respects_switches():
    generator = DataGenerator()

    cases = generator.generate_boundary_test_cases(
        "金额",
        amount_min=10,
        amount_max=100,
        include_valid=False,
        include_boundary=True,
        include_invalid=True,
    )

    assert cases
    assert all(item["case_type"] != "正常值" for item in cases)
    assert any(item["case_name"] == "最小值边界" and item["value"] == "10.00" for item in cases)
    assert any(item["case_name"] == "超出小数精度" and item["expected"] == "应拒绝" for item in cases)


def test_generate_test_dataset_rejects_unknown_scenario():
    generator = DataGenerator()

    with pytest.raises(ValueError):
        generator.generate_test_dataset("未知场景", count=1)


def test_format_profile_data_rejects_unsafe_expression_string():
    generator = DataGenerator()

    result = generator.format_profile_data("__import__('os').system('echo hacked')")

    assert result.startswith("格式化数据时出错:")
    assert "hacked" in result


def test_format_profile_data_accepts_json_object_string():
    generator = DataGenerator()
    raw = (
        '{"name":"张三","sex":"F","birthdate":"1990-01-02",'
        '"mail":"zhangsan@example.com","job":"测试工程师","address":"浙江省杭州市 西湖区",'
        '"company":"示例科技","website":["https://example.com"],"username":"zhangsan"}'
    )

    result = generator.format_profile_data(raw)

    assert "姓名： 张三" in result
    assert "性别： 女" in result
    assert "电子邮箱： zhangsan@example.com" in result

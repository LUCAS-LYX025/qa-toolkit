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


def test_generate_test_dataset_rejects_unknown_scenario():
    generator = DataGenerator()

    with pytest.raises(ValueError):
        generator.generate_test_dataset("未知场景", count=1)

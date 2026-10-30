import csv
from collections import Counter
from pathlib import Path

ORDERS_CSV = Path(__file__).resolve().parents[3] / "data" / "orders.csv"


def _load_orders() -> list[dict[str, str]]:
    with ORDERS_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_orders_csv_when_loaded_has_failed_orders() -> None:
    orders = _load_orders()

    assert len(orders) == 500
    assert len({order["order_id"] for order in orders}) == 500
    assert any(order["status"] == "failed" for order in orders)


def test_orders_csv_when_loaded_only_failed_orders_have_reason() -> None:
    for order in _load_orders():
        assert (order["status"] == "failed") == bool(order["failure_reason"])


def test_orders_csv_when_last_24_hours_has_stable_top_three_causes() -> None:
    recent = Counter(
        order["failure_reason"]
        for order in _load_orders()
        if order["status"] == "failed" and float(order["hours_ago"]) < 24
    )

    top_three = [reason for reason, _ in recent.most_common(3)]

    assert top_three == ["payment_timeout", "inventory_unavailable", "card_declined"]

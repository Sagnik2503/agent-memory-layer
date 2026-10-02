"""HTTP tests for GET /api/dashboard and month navigation.

Single test seam (per spec): the FastAPI HTTP surface via TestClient,
against the isolated seeded database set up in conftest.py.
"""

from datetime import date, timedelta

import pytest


def _previous_month(today: date | None = None) -> str:
    today = today or date.today()
    return (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def _numbers(value):
    if isinstance(value, dict):
        return [n for item in value.values() for n in _numbers(item)]
    if isinstance(value, list):
        return [n for item in value for n in _numbers(item)]
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    return []


def test_dashboard_endpoint_defaults_to_current_month(client, seeded_db):
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == date.today().strftime("%Y-%m")
    assert data["totals_by_currency"] == {"INR": 2350.0, "USD": 138.75}


def test_dashboard_endpoint_scopes_totals_to_requested_month(client, seeded_db):
    prev_month = _previous_month()

    response = client.get("/api/dashboard", params={"month": prev_month})

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == prev_month
    assert data["totals_by_currency"] == {"INR": 1050.0, "USD": 45.99}


def test_dashboard_totals_are_never_summed_across_currencies(client, seeded_db):
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    totals = data["totals_by_currency"]

    assert set(totals) == {"INR", "USD"}
    assert totals["INR"] == 2350.0
    assert totals["USD"] == 138.75
    assert "total" not in data

    combined = 2350.0 + 138.75
    assert combined not in _numbers(data)


def test_dashboard_endpoint_rejects_malformed_month(client, seeded_db):
    for bad_month in ("banana", "2026-13", "2026/09", "09-2026"):
        response = client.get("/api/dashboard", params={"month": bad_month})
        assert response.status_code == 400, bad_month


def test_dashboard_endpoint_returns_honest_empty_totals_for_a_month_without_data(
    client, seeded_db
):
    response = client.get("/api/dashboard", params={"month": "1999-01"})

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "1999-01"
    assert data["totals_by_currency"] == {}


def test_dashboard_page_serves_totals_from_the_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Coming soon" not in response.text
    assert 'id="dashboard-totals"' in response.text

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "/api/dashboard" in script.text


def test_month_navigation_arrows_appear_on_every_page(client):
    for path in ("/", "/expenses", "/budgets"):
        response = client.get(path)
        assert response.status_code == 200, path
        html = response.text
        assert 'data-month-step="-1"' in html, path
        assert 'data-month-step="1"' in html, path
        assert 'id="month-label"' in html, path


CANONICAL_CATEGORIES = {
    "food",
    "transport",
    "shopping",
    "bills",
    "entertainment",
    "health",
    "personal_care",
    "other",
}


def test_dashboard_breakdown_uses_canonical_labels_and_never_mixes_currencies(
    client, seeded_db
):
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    breakdown = data["category_breakdown"]
    assert breakdown, "the seeded month has spending in every currency"

    labels = {entry["category"] for entry in breakdown}
    assert labels <= CANONICAL_CATEGORIES

    by_key = {(e["category"], e["currency"]): e for e in breakdown}
    assert by_key[("bills", "INR")]["amount"] == 2100.0
    assert by_key[("food", "INR")]["amount"] == 250.0
    assert by_key[("shopping", "USD")]["amount"] == 120.0
    assert by_key[("transport", "USD")]["amount"] == 18.75

    # Percentages are shares within one currency, never across currencies.
    assert by_key[("bills", "INR")]["percentage"] == pytest.approx(
        2100.0 / 2350.0 * 100
    )
    assert by_key[("transport", "USD")]["percentage"] == pytest.approx(
        18.75 / 138.75 * 100
    )

    # The month's cross-currency total appears nowhere in the payload.
    assert 2350.0 + 138.75 not in _numbers(data)


def test_dashboard_breakdown_scopes_to_the_requested_month(client, seeded_db):
    response = client.get("/api/dashboard", params={"month": _previous_month()})

    assert response.status_code == 200
    breakdown = response.json()["category_breakdown"]
    labels = {entry["category"] for entry in breakdown}
    assert labels == {"entertainment", "health", "personal_care", "other"}
    by_key = {(e["category"], e["currency"]): e for e in breakdown}
    assert by_key[("health", "INR")]["amount"] == 450.0
    assert by_key[("personal_care", "INR")]["amount"] == 600.0
    assert by_key[("entertainment", "USD")]["amount"] == 15.99
    assert by_key[("other", "USD")]["amount"] == 30.0


def test_dashboard_upcoming_bills_include_overdue_marked_and_due_soon_unmarked(
    client, seeded_db, seed_subscriptions
):
    today = date.today()
    seed_subscriptions(
        [
            {
                "merchant": "Netflix",
                "amount": 15.99,
                "currency": "USD",
                "category": "entertainment",
                "frequency": "monthly",
                "next_due_date": today - timedelta(days=3),
            },
            {
                "merchant": "Gym",
                "amount": 800.0,
                "currency": "INR",
                "category": "health",
                "frequency": "monthly",
                "next_due_date": today + timedelta(days=2),
            },
            {
                "merchant": "Domain renewal",
                "amount": 1200.0,
                "currency": "INR",
                "category": "bills",
                "frequency": "yearly",
                "next_due_date": today + timedelta(days=30),
            },
        ]
    )

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    bills = response.json()["upcoming_bills"]
    assert [b["merchant"] for b in bills] == ["Netflix", "Gym"]

    by_merchant = {b["merchant"]: b for b in bills}
    assert by_merchant["Netflix"]["overdue"] is True
    assert by_merchant["Netflix"]["due_date"] == (
        today - timedelta(days=3)
    ).isoformat()
    assert by_merchant["Netflix"]["amount"] == 15.99
    assert by_merchant["Netflix"]["currency"] == "USD"

    assert by_merchant["Gym"]["overdue"] is False
    assert by_merchant["Gym"]["due_date"] == (today + timedelta(days=2)).isoformat()


def test_dashboard_upcoming_bills_are_an_honest_empty_list_when_none_are_due(
    client, seeded_db
):
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json()["upcoming_bills"] == []


def test_dashboard_recent_expenses_are_the_five_newest_first(
    client, seeded_db, seed_expenses
):
    today = date.today()
    # The shared seeds sit on days 1-5; three more push the month past five.
    seed_expenses(
        [
            {
                "date": today.replace(day=6),
                "merchant": "Bookshop",
                "category": "other",
                "subcategory": None,
                "amount": 45.0,
                "currency": "INR",
            },
            {
                "date": today.replace(day=7),
                "merchant": "Bakery",
                "category": "food",
                "subcategory": "snacks",
                "amount": 90.0,
                "currency": "INR",
            },
            {
                "date": today.replace(day=8),
                "merchant": "Metro card",
                "category": "transport",
                "subcategory": "commute",
                "amount": 200.0,
                "currency": "INR",
            },
        ]
    )

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    recent = response.json()["recent_expenses"]
    assert len(recent) == 5
    assert [r["date"] for r in recent] == [
        today.replace(day=8).isoformat(),
        today.replace(day=7).isoformat(),
        today.replace(day=6).isoformat(),
        today.replace(day=5).isoformat(),
        today.replace(day=3).isoformat(),
    ]

    newest = recent[0]
    assert newest["merchant"] == "Metro card"
    assert newest["amount"] == 200.0
    assert newest["currency"] == "INR"
    for entry in recent:
        assert entry["merchant"]
        assert entry["currency"]
        assert isinstance(entry["amount"], float)


def test_dashboard_recent_expenses_are_scoped_to_the_requested_month(
    client, seeded_db
):
    response = client.get("/api/dashboard", params={"month": _previous_month()})

    assert response.status_code == 200
    recent = response.json()["recent_expenses"]
    merchants = [r["merchant"] for r in recent]
    assert merchants == ["Corner Shop", "Pharmacy", "Netflix", "Salon"]


def test_dashboard_empty_month_keeps_bills_anchored_to_today(
    client, seeded_db, seed_subscriptions
):
    """Breakdown, recent and totals are month-scoped; bills answer "what is
    about to hit my account", so they are anchored to today instead."""
    today = date.today()
    seed_subscriptions(
        [
            {
                "merchant": "Netflix",
                "amount": 15.99,
                "currency": "USD",
                "category": "entertainment",
                "frequency": "monthly",
                "next_due_date": today,
            }
        ]
    )

    response = client.get("/api/dashboard", params={"month": "1999-01"})

    assert response.status_code == 200
    data = response.json()
    assert data["category_breakdown"] == []
    assert data["recent_expenses"] == []
    assert data["totals_by_currency"] == {}
    assert [b["merchant"] for b in data["upcoming_bills"]] == ["Netflix"]
    assert data["upcoming_bills"][0]["overdue"] is False


def _budgets_by_category(data):
    return {status["category"]: status for status in data["budget_statuses"]}


def test_dashboard_reports_budget_statuses_straddling_the_threshold_and_the_limit(
    client, seeded_db, seed_budgets
):
    # bills sits below the 80% warning threshold (70%), food sits above it but
    # under the limit (83.3%), the overall Budget is past its limit (117.5%).
    seed_budgets([(None, 2000.0), ("food", 300.0), ("bills", 3000.0)])

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert len(data["budget_statuses"]) == 3

    overall = _budgets_by_category(data)[None]
    assert overall["budget_amount"] == 2000.0
    assert overall["spent_amount"] == 2350.0
    assert overall["remaining"] == -350.0
    assert overall["percentage_used"] == pytest.approx(117.5)
    assert overall["is_over_budget"] is True

    food = _budgets_by_category(data)["food"]
    assert food["budget_amount"] == 300.0
    assert food["spent_amount"] == 250.0
    assert food["remaining"] == 50.0
    assert food["percentage_used"] == pytest.approx(83.3333, rel=1e-4)
    assert food["is_over_budget"] is False

    bills = _budgets_by_category(data)["bills"]
    assert bills["budget_amount"] == 3000.0
    assert bills["spent_amount"] == 2100.0
    assert bills["remaining"] == 900.0
    assert bills["percentage_used"] == pytest.approx(70.0)
    assert bills["is_over_budget"] is False


def test_dashboard_budget_spent_respects_the_per_currency_rule(
    client, seeded_db, seed_budgets
):
    # Budgets are single-currency limits (INR): the month's USD spending
    # ($138.75) must never be added to them, and a budget whose category only
    # has USD spending counts as untouched rather than over budget.
    seed_budgets([(None, 2000.0), ("shopping", 100.0)])

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    by_category = _budgets_by_category(data)

    overall = by_category[None]
    assert overall["spent_amount"] == 2350.0
    assert overall["currency"] == "INR"
    assert overall["spent_amount"] + 138.75 not in _numbers(data)

    shopping = by_category["shopping"]
    assert shopping["spent_amount"] == 0.0
    assert shopping["remaining"] == 100.0
    assert shopping["percentage_used"] == 0.0
    assert shopping["is_over_budget"] is False


def test_dashboard_budget_spent_is_scoped_to_the_requested_month(
    client, seeded_db, seed_budgets
):
    seed_budgets([(None, 2000.0)])

    current = client.get("/api/dashboard").json()["budget_statuses"][0]
    past = client.get(
        "/api/dashboard", params={"month": _previous_month()}
    ).json()["budget_statuses"][0]

    assert current["spent_amount"] == 2350.0
    assert current["is_over_budget"] is True
    assert past["spent_amount"] == 1050.0
    assert past["is_over_budget"] is False
    assert past["percentage_used"] == pytest.approx(52.5)


def test_dashboard_budget_sitting_exactly_at_the_limit_is_not_flagged_over(
    client, seeded_db, seed_budgets
):
    seed_budgets([("bills", 2100.0)])

    response = client.get("/api/dashboard")

    bills = _budgets_by_category(response.json())["bills"]
    assert bills["percentage_used"] == pytest.approx(100.0)
    assert bills["remaining"] == 0.0
    assert bills["is_over_budget"] is False


def test_dashboard_budget_at_exactly_the_warning_threshold_reports_80_percent(
    client, seeded_db, seed_budgets
):
    seed_budgets([("food", 312.5)])

    response = client.get("/api/dashboard")

    food = _budgets_by_category(response.json())["food"]
    assert food["percentage_used"] == pytest.approx(80.0)
    assert food["is_over_budget"] is False


def test_dashboard_reports_an_empty_budget_list_when_no_budgets_are_set(
    client, seeded_db
):
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json()["budget_statuses"] == []


def test_dashboard_page_has_a_budget_status_container(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="dashboard-budgets"' in response.text

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "budget_statuses" in script.text


def test_dashboard_page_has_containers_for_breakdown_bills_and_recent(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    for container_id in ("dashboard-breakdown", "dashboard-bills", "dashboard-recent"):
        assert f'id="{container_id}"' in html, container_id

    script = client.get("/static/app.js")
    assert script.status_code == 200
    for contract_field in ("category_breakdown", "upcoming_bills", "recent_expenses"):
        assert contract_field in script.text, contract_field

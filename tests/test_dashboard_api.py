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

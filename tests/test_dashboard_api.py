"""HTTP tests for GET /api/dashboard and month navigation.

Single test seam (per spec): the FastAPI HTTP surface via TestClient,
against the isolated seeded database set up in conftest.py.
"""

from datetime import date, timedelta


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

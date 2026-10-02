"""HTTP tests for GET /api/expenses and the static UI shell.

Single test seam (per spec): the FastAPI HTTP surface via TestClient,
against the isolated seeded database set up in conftest.py.
"""

from datetime import date, timedelta


def test_no_write_endpoints_for_expenses_budgets_or_subscriptions(client):
    for path in ("/api/expenses", "/api/budgets", "/api/subscriptions"):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            response = client.request(method, path, json={"amount": 100})
            assert response.status_code in (404, 405), f"{method} {path}"


def test_static_pages_are_served_with_navigation(client):
    for path in ("/", "/expenses", "/budgets"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html"), path
        html = response.text
        assert 'href="/"' in html, path
        assert 'href="/expenses"' in html, path
        assert 'href="/budgets"' in html, path


def test_pages_not_yet_built_render_honest_placeholders(client):
    for path in ("/budgets",):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "Coming soon" in response.text, path


def test_expenses_page_pulls_the_month_from_the_endpoint(client):
    response = client.get("/expenses")
    assert response.status_code == 200
    assert "/static/app.js" in response.text

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "/api/expenses" in script.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")


def test_expenses_endpoint_rejects_malformed_month(client, seeded_db):
    for bad_month in ("banana", "2026-13", "2026/09", "09-2026"):
        response = client.get("/api/expenses", params={"month": bad_month})
        assert response.status_code == 400, bad_month


def test_expenses_endpoint_totals_are_grouped_by_currency(client, seeded_db):
    response = client.get("/api/expenses")

    assert response.status_code == 200
    data = response.json()
    assert data["totals_by_currency"] == {"INR": 2350.0, "USD": 138.75}
    assert "total" not in data


def test_expenses_endpoint_scopes_to_requested_month(client, seeded_db):
    today = date.today()
    prev_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    response = client.get("/api/expenses", params={"month": prev_month})

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == prev_month
    items = data["items"]
    assert len(items) == 4
    for item in items:
        assert item["date"].startswith(prev_month)
    assert {i["merchant"] for i in items} == {"Netflix", "Pharmacy", "Salon", "Corner Shop"}


def test_expenses_endpoint_defaults_to_current_month(client, seeded_db):
    response = client.get("/api/expenses")

    assert response.status_code == 200
    data = response.json()
    current_month = date.today().strftime("%Y-%m")
    assert data["month"] == current_month

    items = data["items"]
    assert len(items) == 4
    for item in items:
        assert item["date"].startswith(current_month)

    by_merchant = {i["merchant"]: i for i in items}
    assert by_merchant["Cafe Mocha"] == {
        "date": date.today().replace(day=2).isoformat(),
        "merchant": "Cafe Mocha",
        "category": "food",
        "subcategory": "coffee",
        "amount": 250.0,
        "currency": "INR",
    }
    assert by_merchant["Uber"]["currency"] == "USD"
    assert by_merchant["Uber"]["amount"] == 18.75

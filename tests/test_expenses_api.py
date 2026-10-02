"""HTTP tests for GET /api/expenses and the static UI shell.

Single test seam (per spec): the FastAPI HTTP surface via TestClient,
against the isolated seeded database set up in conftest.py.
"""

import re
from datetime import date, timedelta

from app.agent.state import ExpenseCategory


def _previous_month() -> str:
    return (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


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


def test_expenses_endpoint_filters_by_category(client, seeded_db):
    response = client.get("/api/expenses", params={"category": "food"})

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == date.today().strftime("%Y-%m")
    assert [i["merchant"] for i in data["items"]] == ["Cafe Mocha"]
    assert all(i["category"] == "food" for i in data["items"])
    # Totals describe the rows actually returned — still never summed across
    # currencies.
    assert data["totals_by_currency"] == {"INR": 250.0}


def test_expenses_endpoint_rejects_unknown_category(client, seeded_db):
    response = client.get("/api/expenses", params={"category": "Subscriptions"})

    assert response.status_code == 400
    detail = response.json()["detail"]
    for canonical in (
        "food",
        "transport",
        "shopping",
        "bills",
        "entertainment",
        "health",
        "personal_care",
        "other",
    ):
        assert canonical in detail, canonical


def test_expenses_endpoint_searches_merchant_by_substring(client, seeded_db):
    mixed_case = client.get("/api/expenses", params={"q": "uBe"})
    assert mixed_case.status_code == 200
    assert [i["merchant"] for i in mixed_case.json()["items"]] == ["Uber"]
    assert mixed_case.json()["totals_by_currency"] == {"USD": 18.75}

    prev_month = _previous_month()
    partial = client.get("/api/expenses", params={"month": prev_month, "q": "shop"})
    assert partial.status_code == 200
    assert [i["merchant"] for i in partial.json()["items"]] == ["Corner Shop"]


def test_expenses_endpoint_treats_search_wildcards_literally(client, seeded_db):
    response = client.get("/api/expenses", params={"q": "%"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_expenses_endpoint_combines_month_category_and_search(client, seeded_db):
    prev_month = _previous_month()

    response = client.get(
        "/api/expenses",
        params={"month": prev_month, "category": "health", "q": "phar"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == prev_month
    assert [i["merchant"] for i in data["items"]] == ["Pharmacy"]
    assert data["totals_by_currency"] == {"INR": 450.0}

    # Every filter must hold: health + "shop" matches nothing in either month.
    mismatch = client.get(
        "/api/expenses", params={"category": "health", "q": "shop"}
    )
    assert mismatch.status_code == 200
    assert mismatch.json()["items"] == []


def test_expenses_endpoint_empty_filter_result_is_an_honest_empty_payload(
    client, seeded_db
):
    response = client.get(
        "/api/expenses",
        params={"month": _previous_month(), "category": "food"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["month"] == _previous_month()
    assert data["items"] == []
    assert data["totals_by_currency"] == {}


def test_expenses_items_carry_id_description_and_subscription_origin(
    client, seeded_db, seed_subscriptions, seed_expenses
):
    today = date.today()
    (subscription,) = seed_subscriptions(
        [
            {
                "merchant": "Spotify",
                "amount": 119.0,
                "currency": "INR",
                "category": "entertainment",
                "frequency": "monthly",
                "next_due_date": today.replace(day=10),
            }
        ]
    )
    seed_expenses(
        [
            {
                "date": today.replace(day=4),
                "merchant": "Spotify",
                "category": "entertainment",
                "subcategory": "music",
                "amount": 119.0,
                "currency": "INR",
                "description": "Family plan",
                "subscription_id": subscription.id,
            }
        ]
    )

    response = client.get("/api/expenses")
    assert response.status_code == 200
    by_merchant = {i["merchant"]: i for i in response.json()["items"]}

    spotify = by_merchant["Spotify"]
    assert isinstance(spotify["id"], int)
    assert spotify["description"] == "Family plan"
    assert spotify["from_subscription"] is True
    assert by_merchant["Cafe Mocha"]["from_subscription"] is False


def test_expenses_page_offers_exactly_the_canonical_category_filter(client):
    response = client.get("/expenses")
    assert response.status_code == 200
    options = re.findall(r'<option value="([^"]*)"', response.text)

    assert options[0] == ""  # the "no filter" choice comes first
    assert set(options[1:]) == {c.value for c in ExpenseCategory}
    assert len(options) == 1 + len(ExpenseCategory)


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
    cafe = by_merchant["Cafe Mocha"]
    assert isinstance(cafe["id"], int)
    assert {k: v for k, v in cafe.items() if k != "id"} == {
        "date": date.today().replace(day=2).isoformat(),
        "merchant": "Cafe Mocha",
        "category": "food",
        "subcategory": "coffee",
        "amount": 250.0,
        "currency": "INR",
        "description": None,
        "from_subscription": False,
    }
    assert by_merchant["Uber"]["currency"] == "USD"
    assert by_merchant["Uber"]["amount"] == 18.75

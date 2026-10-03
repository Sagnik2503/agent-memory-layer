"""HTTP tests for the Expense row chat deep-links (issue 07).

Single test seam (per spec): the FastAPI HTTP surface via TestClient.
Hovering a row, opening the panel, and the composer prefill are verified in
the browser; these tests pin what the seam can see — that no write route
exists for an Expense, and that the served client wires both row actions to
the chat composer with an instruction the agent can resolve.
"""

import re


def test_no_write_endpoint_exists_for_an_expense(client):
    """Neither the collection nor a single Expense (the deep-link's target)
    accepts a write: the UI never mutates data, it only opens the chat."""
    for path in ("/api/expenses", "/api/expenses/42"):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            response = client.request(method, path, json={"amount": 100})
            assert response.status_code in (404, 405), f"{method} {path}"


def test_client_writes_nothing_anywhere_but_the_chat_endpoint(client):
    """Row actions must not fetch a write of their own: the served client
    issues no verb beyond GET and the unchanged POST /chat."""
    script = client.get("/static/app.js")
    assert script.status_code == 200
    text = script.text

    assert '"/chat"' in text
    methods = set(re.findall(r'method:\s*"([A-Z]+)"', text))
    assert "POST" in methods, "the composer's write to /chat is gone"
    assert methods <= {"GET", "POST"}, methods


def test_expense_rows_offer_edit_and_delete_chat_actions(client):
    script = client.get("/static/app.js")
    assert script.status_code == 200
    text = script.text

    assert '"Edit in chat"' in text
    assert '"Delete in chat"' in text
    # Both actions route into the composer rather than an inline editor.
    assert 'id="chat-input"' in client.get("/expenses").text
    assert "chat-input" in text


def test_row_deep_link_instruction_identifies_the_expense(client):
    """The prefilled instruction must pin down one Expense for the agent:
    every field it names comes from the GET /api/expenses item contract."""
    script = client.get("/static/app.js")
    assert script.status_code == 200
    text = script.text

    for field in (
        "item.id",
        "item.date",
        "item.merchant",
        "item.amount",
        "item.currency",
        "item.category",
    ):
        assert field in text, field

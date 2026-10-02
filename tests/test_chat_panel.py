"""HTTP tests for the collapsible chat panel (issue 06).

Single test seam (per spec): the FastAPI HTTP surface via TestClient.
Panel interaction — toggling, state persistence, thread-id survival,
sending messages — is verified in the browser, not here; these tests pin
the served markup, the client wiring, and the unchanged /chat contract.
"""

import re


def test_chat_panel_is_served_collapsed_on_every_page(client):
    for path in ("/", "/expenses", "/budgets"):
        response = client.get(path)
        assert response.status_code == 200, path
        html = response.text

        panel = re.search(r"<aside[^>]*id=\"chat-panel\"[^>]*>", html)
        assert panel, f"chat panel missing from {path}"
        # Collapsed by default: the served markup ships the panel hidden.
        assert "hidden" in panel.group(0), f"chat panel not collapsed in {path}"

        assert 'id="chat-toggle"' in html, path
        assert 'aria-expanded="false"' in html, path


def test_chat_panel_has_a_composer_on_every_page(client):
    for path in ("/", "/expenses", "/budgets"):
        response = client.get(path)
        assert response.status_code == 200, path
        html = response.text
        assert 'id="chat-composer"' in html, path
        assert 'id="chat-input"' in html, path
        assert 'id="chat-log"' in html, path


def test_chat_panel_client_wires_composer_to_the_existing_endpoint(client):
    script = client.get("/static/app.js")
    assert script.status_code == 200
    text = script.text
    # The composer must POST /chat and carry the thread identifier the
    # server keys conversation history on, persisting both panel state
    # and history in client-side storage.
    assert '"/chat"' in text
    assert "thread_id" in text
    assert "localStorage" in text


def test_chat_endpoint_contract_still_requires_a_thread_id(client):
    """The panel speaks the existing contract: message + thread_id.

    Validation runs before the agent is invoked, so this asserts the
    request shape without spending an LLM call.
    """
    missing_thread = client.post("/chat", json={"message": "How are you?"})
    assert missing_thread.status_code == 422
    assert "thread_id" in str(missing_thread.json()["detail"])

    missing_message = client.post("/chat", json={"thread_id": "abc"})
    assert missing_message.status_code == 422
    assert "message" in str(missing_message.json()["detail"])


def test_chat_panel_introduces_no_write_endpoints_and_needs_no_cors(client):
    for path in ("/", "/expenses", "/budgets"):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            response = client.request(method, path, json={})
            assert response.status_code in (404, 405), f"{method} {path}"
        # Same origin: pages and assets are served without CORS headers.
        page = client.get(path)
        assert "access-control-allow-origin" not in page.headers, path

    asset = client.get("/static/app.js")
    assert "access-control-allow-origin" not in asset.headers

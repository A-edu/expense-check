"""Tests for the Expense Check JSON API. No real model calls."""

import pytest
from fastapi.testclient import TestClient

from app import db, llm, rules
from app.main import app

PITCH_TEXT = "Dinner for 3 people, 620 SAR, no receipt."

PITCH_LINE = {
    "description": "Dinner for 3",
    "category": "meal",
    "amount": 620,
    "people": 3,
    "nights": 1,
    "has_receipt": False,
}


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    """A client on a database that lives only for this test."""
    monkeypatch.setenv("EXPENSE_CHECK_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    return TestClient(app)


@pytest.fixture
def fake_model(monkeypatch) -> None:
    """The pitch line from the model, and a summary that ignores the flags."""
    monkeypatch.setattr(llm, "extract_lines", lambda text: [dict(PITCH_LINE)])
    monkeypatch.setattr(llm, "summarise", lambda checked: "All lines comply.")


def check(client: TestClient, text: str = PITCH_TEXT):
    return client.post(
        "/api/claims/check", json={"text": text, "submitted_by": "abdulaziz"}
    )


def ids(flags: list) -> list:
    return [flag["rule_id"] for flag in flags]


def submitted_claim(client: TestClient) -> dict:
    claim = check(client).json()
    response = client.post(f"/api/claims/{claim['id']}/submit")
    assert response.status_code == 200
    return response.json()


def test_pitch_example_flags_meal_and_receipt(client: TestClient, fake_model) -> None:
    response = check(client)

    assert response.status_code == 200
    claim = response.json()
    assert claim["status"] == "draft"
    assert claim["submitted_by"] == "abdulaziz"
    assert claim["policy_version"] == rules.load_policy()["version"]
    assert claim["total"] == 620
    assert claim["violation_count"] == 2
    assert claim["review_count"] == 0
    assert len(claim["lines"]) == 1
    assert ids(claim["lines"][0]["flags"]) == ["MEAL-01", "RCPT-01"]
    assert claim["decisions"] == []


def test_summary_cannot_clear_flags(client: TestClient, fake_model) -> None:
    claim = check(client).json()

    assert claim["summary"] == "All lines comply."
    assert ids(claim["lines"][0]["flags"]) == ["MEAL-01", "RCPT-01"]
    assert claim["violation_count"] == 2


def test_unknown_category_from_the_model_is_rejected(
    client: TestClient, monkeypatch
) -> None:
    snack_line = {**PITCH_LINE, "category": "snack"}
    monkeypatch.setattr(llm, "extract_lines", lambda text: [snack_line])
    monkeypatch.setattr(llm, "summarise", lambda checked: "unused")

    response = check(client)

    assert response.status_code == 422
    assert "snack" in response.json()["detail"]


def test_extraction_failure_is_a_bad_gateway(client: TestClient, monkeypatch) -> None:
    def explode(text: str) -> list:
        raise llm.LLMError("model unavailable")

    monkeypatch.setattr(llm, "extract_lines", explode)

    response = check(client)

    assert response.status_code == 502
    assert "model unavailable" in response.json()["detail"]


def test_summary_failure_falls_back_to_the_template(
    client: TestClient, monkeypatch
) -> None:
    def explode(checked: dict) -> str:
        raise RuntimeError("summary model down")

    monkeypatch.setattr(llm, "extract_lines", lambda text: [dict(PITCH_LINE)])
    monkeypatch.setattr(llm, "summarise", explode)

    response = check(client)

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "1 lines" in summary
    assert "620.00 SAR" in summary
    assert "2 violations" in summary
    assert "0 for review" in summary
    assert "MEAL-01" in summary
    assert "RCPT-01" in summary


def test_missing_model_config_returns_503(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = check(client)

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_full_flow_from_check_to_approval(client: TestClient, fake_model) -> None:
    claim = check(client).json()

    submitted = client.post(f"/api/claims/{claim['id']}/submit")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    listed = client.get("/api/claims", params={"status": "submitted"})
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [claim["id"]]
    assert "lines" not in listed.json()[0]

    decided = client.post(
        f"/api/claims/{claim['id']}/decision",
        json={"decision": "approve", "comment": "ok"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    decisions = decided.json()["decisions"]
    assert len(decisions) == 1
    assert decisions[0]["decision"] == "approve"
    assert decisions[0]["comment"] == "ok"

    assert client.get("/api/claims", params={"status": "submitted"}).json() == []


def test_return_needs_a_comment(client: TestClient, fake_model) -> None:
    claim = submitted_claim(client)

    blank = client.post(
        f"/api/claims/{claim['id']}/decision",
        json={"decision": "return", "comment": "   "},
    )
    assert blank.status_code == 422
    assert client.get(f"/api/claims/{claim['id']}").json()["status"] == "submitted"

    returned = client.post(
        f"/api/claims/{claim['id']}/decision",
        json={"decision": "return", "comment": "Attach the receipt."},
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"
    assert returned.json()["decisions"][0]["comment"] == "Attach the receipt."


def test_decision_on_a_draft_is_rejected(client: TestClient, fake_model) -> None:
    claim = check(client).json()

    response = client.post(
        f"/api/claims/{claim['id']}/decision",
        json={"decision": "approve", "comment": ""},
    )

    assert response.status_code == 409
    assert client.get(f"/api/claims/{claim['id']}").json()["decisions"] == []


def test_submitting_twice_is_rejected(client: TestClient, fake_model) -> None:
    claim = submitted_claim(client)

    response = client.post(f"/api/claims/{claim['id']}/submit")

    assert response.status_code == 409
    assert response.json()["detail"] == "claim is submitted, not draft"


def test_unknown_claim_is_404(client: TestClient) -> None:
    assert client.get("/api/claims/999").status_code == 404
    assert client.post("/api/claims/999/submit").status_code == 404
    assert (
        client.post(
            "/api/claims/999/decision",
            json={"decision": "approve", "comment": ""},
        ).status_code
        == 404
    )


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
def test_text_must_be_one_to_two_thousand_chars(
    client: TestClient, text: str
) -> None:
    assert check(client, text).status_code == 422


def test_claim_survives_a_fresh_connection(client: TestClient, fake_model) -> None:
    claim = check(client).json()

    conn = db.connect()
    try:
        stored = db.get_claim(conn, claim["id"])
    finally:
        conn.close()

    assert stored is not None
    assert stored["total"] == 620
    assert ids(stored["lines"][0]["flags"]) == ["MEAL-01", "RCPT-01"]

    assert TestClient(app).get(f"/api/claims/{claim['id']}").json()["id"] == claim["id"]

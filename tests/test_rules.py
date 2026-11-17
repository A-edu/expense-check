"""Tests for the Expense Check rules engine."""

import copy
import json

import pytest

from app.rules import check_claim, check_line, load_policy


@pytest.fixture
def policy() -> dict:
    """A policy built here, independent of app/policy.json."""
    return {
        "version": "test-v1",
        "currency": "SAR",
        "rules": [
            {
                "id": "MEAL-01",
                "type": "max_per_person",
                "category": "meal",
                "limit": 150,
                "text": "Meals are capped at 150 SAR per person.",
            },
            {
                "id": "TAXI-01",
                "type": "max_per_line",
                "category": "taxi",
                "limit": 100,
                "text": "Taxi lines are capped at 100 SAR.",
            },
            {
                "id": "HOTEL-01",
                "type": "max_per_night",
                "category": "hotel",
                "limit": 600,
                "text": "Hotels are capped at 600 SAR per night.",
            },
            {
                "id": "RCPT-01",
                "type": "receipt_required_above",
                "category": "*",
                "limit": 50,
                "text": "Lines above 50 SAR need a receipt.",
            },
            {
                "id": "CAT-01",
                "type": "manual_review",
                "category": "other",
                "text": "Other lines are reviewed by a human.",
            },
        ],
    }


def make_line(**overrides) -> dict:
    line = {
        "description": "test line",
        "category": "meal",
        "amount": 100,
        "people": 1,
        "nights": 1,
        "has_receipt": True,
    }
    line.update(overrides)
    return line


def ids(flags: list) -> list:
    return [flag["rule_id"] for flag in flags]


def test_shipped_policy_loads_with_unique_ids() -> None:
    shipped = load_policy()
    rule_ids = [rule["id"] for rule in shipped["rules"]]
    assert rule_ids
    assert len(rule_ids) == len(set(rule_ids))
    assert shipped["currency"] == "SAR"


def test_duplicate_rule_ids_raise(tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "version": "dup-v1",
                "currency": "SAR",
                "rules": [
                    {"id": "X-01", "type": "max_per_line", "category": "taxi", "limit": 10},
                    {"id": "X-01", "type": "max_per_line", "category": "taxi", "limit": 20},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_policy(str(path))


def test_demo_line_flags_meal_and_receipt(policy: dict) -> None:
    line = {
        "description": "Dinner for 3",
        "category": "meal",
        "amount": 620,
        "people": 3,
        "nights": 1,
        "has_receipt": False,
    }
    assert ids(check_line(line, policy)) == ["MEAL-01", "RCPT-01"]


def test_meal_at_limit_per_person_is_allowed(policy: dict) -> None:
    assert check_line(make_line(amount=450, people=3), policy) == []


def test_meal_over_limit_per_person_flags(policy: dict) -> None:
    assert ids(check_line(make_line(amount=450.03, people=3), policy)) == ["MEAL-01"]


def test_taxi_at_limit_is_allowed(policy: dict) -> None:
    assert check_line(make_line(category="taxi", amount=100), policy) == []


def test_taxi_over_limit_flags(policy: dict) -> None:
    assert ids(check_line(make_line(category="taxi", amount=101), policy)) == ["TAXI-01"]


def test_hotel_at_limit_per_night_is_allowed(policy: dict) -> None:
    assert check_line(make_line(category="hotel", amount=1200, nights=2), policy) == []


def test_hotel_over_limit_per_night_flags(policy: dict) -> None:
    assert ids(check_line(make_line(category="hotel", amount=1300, nights=2), policy)) == [
        "HOTEL-01"
    ]


def test_receipt_not_required_at_limit(policy: dict) -> None:
    assert check_line(make_line(amount=50, has_receipt=False), policy) == []


def test_receipt_required_above_limit(policy: dict) -> None:
    flags = check_line(make_line(amount=50.01, has_receipt=False), policy)
    assert ids(flags) == ["RCPT-01"]
    assert flags[0]["severity"] == "violation"


def test_over_limit_with_receipt_flags_only_the_limit(policy: dict) -> None:
    flags = check_line(make_line(category="taxi", amount=250, has_receipt=True), policy)
    assert ids(flags) == ["TAXI-01"]


def test_other_category_is_review_severity(policy: dict) -> None:
    flags = check_line(make_line(category="other", amount=20, has_receipt=True), policy)
    assert ids(flags) == ["CAT-01"]
    assert flags[0]["severity"] == "review"


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "snack"},
        {"amount": 0},
        {"amount": -5},
        {"people": 0},
        {"nights": 0},
    ],
)
def test_invalid_lines_raise(policy: dict, overrides: dict) -> None:
    with pytest.raises(ValueError):
        check_line(make_line(**overrides), policy)


def test_changing_the_meal_limit_changes_the_result(policy: dict) -> None:
    line = make_line(amount=450, people=1)
    assert ids(check_line(line, policy)) == ["MEAL-01"]

    looser = copy.deepcopy(policy)
    looser["rules"][0]["limit"] = 500
    assert check_line(line, looser) == []


def test_check_claim_totals_and_counts(policy: dict) -> None:
    lines = [
        make_line(description="Dinner for 2", amount=300, people=2),
        make_line(description="Airport taxi", category="taxi", amount=150),
        make_line(description="Misc", category="other", amount=80),
    ]
    result = check_claim(lines, policy)

    assert result["policy_version"] == "test-v1"
    assert len(result["lines"]) == 3
    assert result["total"] == 530
    assert result["violation_count"] == 1
    assert result["review_count"] == 1
    assert ids(result["lines"][0]["flags"]) == []
    assert ids(result["lines"][1]["flags"]) == ["TAXI-01"]
    assert ids(result["lines"][2]["flags"]) == ["CAT-01"]
    assert result["lines"][0]["description"] == "Dinner for 2"


def test_flag_messages_include_rule_id_and_numbers(policy: dict) -> None:
    flags = check_line(make_line(category="taxi", amount=250), policy)
    message = flags[0]["message"]
    assert "TAXI-01" in message
    assert "250" in message
    assert "100" in message

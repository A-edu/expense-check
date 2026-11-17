"""Rules engine for Expense Check.

Checks expense lines against a written policy loaded from JSON.
Standard library only: no web framework, no database, no network.
"""

import json
import math
from pathlib import Path
from typing import Any, Optional

POLICY_PATH = Path(__file__).with_name("policy.json")

CATEGORIES = ("meal", "taxi", "hotel", "other")

KNOWN_RULE_TYPES = (
    "max_per_person",
    "max_per_line",
    "max_per_night",
    "receipt_required_above",
    "manual_review",
)


def load_policy(path: Optional[str] = None) -> dict:
    """Load the policy JSON, defaulting to app/policy.json."""
    policy_file = Path(path) if path is not None else POLICY_PATH
    with policy_file.open(encoding="utf-8") as handle:
        policy = json.load(handle)

    seen = set()
    for rule in policy["rules"]:
        rule_id = rule["id"]
        if rule_id in seen:
            raise ValueError(f"duplicate rule id: {rule_id}")
        seen.add(rule_id)

        rule_type = rule.get("type")
        if rule_type not in KNOWN_RULE_TYPES:
            raise ValueError(f"unknown rule type for {rule_id}: {rule_type!r}")
        if rule_type != "manual_review" and not _is_number(rule.get("limit")):
            raise ValueError(f"rule {rule_id} needs a numeric limit")
    return policy


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number(value: Any, field: str) -> float:
    if not _is_number(value):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _validate(line: dict) -> dict:
    """Return the line with defaults filled in, or raise ValueError."""
    category = line.get("category")
    if category not in CATEGORIES:
        raise ValueError(f"unknown category: {category!r}")

    amount = _number(line.get("amount"), "amount")

    if not math.isfinite(amount):
        raise ValueError(f"amount must be finite, got {amount}")
    if amount <= 0:
        raise ValueError(f"amount must be greater than 0, got {amount}")

    people = line.get("people", 1)
    nights = line.get("nights", 1)
    if isinstance(people, bool) or not isinstance(people, int):
        raise ValueError(f"people must be an integer, got {people!r}")
    if isinstance(nights, bool) or not isinstance(nights, int):
        raise ValueError(f"nights must be an integer, got {nights!r}")
    if people < 1:
        raise ValueError(f"people must be at least 1, got {people}")
    if nights < 1:
        raise ValueError(f"nights must be at least 1, got {nights}")

    has_receipt = line.get("has_receipt", False)
    if not isinstance(has_receipt, bool):
        raise ValueError(f"has_receipt must be a boolean, got {has_receipt!r}")
    return {
        "description": str(line.get("description", "")),
        "category": category,
        "amount": amount,
        "people": people,
        "nights": nights,
        "has_receipt": has_receipt,
    }


def _money(amount: float, currency: str) -> str:
    return f"{amount:.2f} {currency}"


def _check_rule(rule: dict, line: dict, currency: str) -> Optional[dict]:
    """Return a flag dict if this rule is broken by the line, else None."""
    rule_id = rule["id"]
    rule_type = rule["type"]
    limit = float(rule["limit"]) if "limit" in rule else None
    amount = line["amount"]

    if rule_type == "max_per_person":
        # Compare the line total against the allowance; the per-person figure is
        # only for the message.
        if round(amount, 2) > round(limit * line["people"], 2):
            per_person = round(amount / line["people"], 2)
            message = (
                f"{rule_id}: {_money(amount, currency)} for {line['people']} people is "
                f"{_money(per_person, currency)} per person, above the "
                f"{_money(limit, currency)} per-person limit."
            )
            return {"rule_id": rule_id, "severity": "violation", "message": message}
        return None

    if rule_type == "max_per_line":
        if amount <= limit:
            return None
        message = (
            f"{rule_id}: {_money(amount, currency)} is above the "
            f"{_money(limit, currency)} per-line limit."
        )
        return {"rule_id": rule_id, "severity": "violation", "message": message}

    if rule_type == "max_per_night":
        if round(amount, 2) > round(limit * line["nights"], 2):
            per_night = round(amount / line["nights"], 2)
            message = (
                f"{rule_id}: {_money(amount, currency)} for {line['nights']} nights is "
                f"{_money(per_night, currency)} per night, above the "
                f"{_money(limit, currency)} per-night limit."
            )
            return {"rule_id": rule_id, "severity": "violation", "message": message}
        return None

    if rule_type == "receipt_required_above":
        if line["has_receipt"] or amount <= limit:
            return None
        message = (
            f"{rule_id}: {_money(amount, currency)} line has no receipt; "
            f"a receipt is required above {_money(limit, currency)}."
        )
        return {"rule_id": rule_id, "severity": "violation", "message": message}

    if rule_type == "manual_review":
        message = (
            f"{rule_id}: category {line['category']!r} needs manual review "
            f"for {_money(amount, currency)}."
        )
        return {"rule_id": rule_id, "severity": "review", "message": message}

    raise ValueError(f"unknown rule type: {rule_type!r}")


def _flags_for(line: dict, policy: dict) -> list[dict]:
    """Apply every matching rule to an already validated line."""
    currency = policy.get("currency", "SAR")
    flags = []
    for rule in policy["rules"]:
        category = rule.get("category")
        if category != "*" and category != line["category"]:
            continue
        flag = _check_rule(rule, line, currency)
        if flag is not None:
            flags.append(flag)
    return flags


def check_line(line: dict, policy: dict) -> list[dict]:
    """Return the flags raised for one expense line."""
    return _flags_for(_validate(line), policy)


def check_claim(lines: list[dict], policy: dict) -> dict:
    """Check every line and summarise the claim."""
    checked_lines = []
    total = 0.0
    violation_count = 0
    review_count = 0

    for line in lines:
        checked = _validate(line)
        flags = _flags_for(checked, policy)
        checked_lines.append({**checked, "flags": flags})
        total += checked["amount"]
        for flag in flags:
            if flag["severity"] == "violation":
                violation_count += 1
            else:
                review_count += 1

    return {
        "policy_version": policy["version"],
        "lines": checked_lines,
        "total": round(total, 2),
        "violation_count": violation_count,
        "review_count": review_count,
    }


if __name__ == "__main__":
    DEMO_LINE = {
        "description": "Dinner for 3",
        "category": "meal",
        "amount": 620,
        "people": 3,
        "nights": 1,
        "has_receipt": False,
    }
    print(json.dumps(check_claim([DEMO_LINE], load_policy()), indent=2))

"""Rules engine for Expense Check.

Checks expense lines against a written policy loaded from JSON.
Standard library only: no web framework, no database, no network.
"""

import json
from pathlib import Path
from typing import Any, Optional

POLICY_PATH = Path(__file__).with_name("policy.json")

CATEGORIES = ("meal", "taxi", "hotel", "other")


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
    return policy


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _validate(line: dict) -> dict:
    """Return the line with defaults filled in, or raise ValueError."""
    category = line.get("category")
    if category not in CATEGORIES:
        raise ValueError(f"unknown category: {category!r}")

    amount = _number(line.get("amount"), "amount")
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

    return {
        "description": str(line.get("description", "")),
        "category": category,
        "amount": amount,
        "people": people,
        "nights": nights,
        "has_receipt": bool(line.get("has_receipt", False)),
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
        # Currency rounding: compare in cents to avoid float drift at the limit.
        per_person = round(amount / line["people"], 2)
        if per_person <= limit:
            return None
        message = (
            f"{rule_id}: {_money(amount, currency)} for {line['people']} people is "
            f"{_money(per_person, currency)} per person, above the "
            f"{_money(limit, currency)} per-person limit."
        )
        return {"rule_id": rule_id, "severity": "violation", "message": message}

    if rule_type == "max_per_line":
        if amount <= limit:
            return None
        message = (
            f"{rule_id}: {_money(amount, currency)} is above the "
            f"{_money(limit, currency)} per-line limit."
        )
        return {"rule_id": rule_id, "severity": "violation", "message": message}

    if rule_type == "max_per_night":
        per_night = round(amount / line["nights"], 2)
        if per_night <= limit:
            return None
        message = (
            f"{rule_id}: {_money(amount, currency)} for {line['nights']} nights is "
            f"{_money(per_night, currency)} per night, above the "
            f"{_money(limit, currency)} per-night limit."
        )
        return {"rule_id": rule_id, "severity": "violation", "message": message}

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


def check_line(line: dict, policy: dict) -> list[dict]:
    """Return the flags raised for one expense line."""
    checked = _validate(line)
    currency = policy.get("currency", "SAR")
    flags = []
    for rule in policy["rules"]:
        category = rule.get("category")
        if category != "*" and category != checked["category"]:
            continue
        flag = _check_rule(rule, checked, currency)
        if flag is not None:
            flags.append(flag)
    return flags


def check_claim(lines: list[dict], policy: dict) -> dict:
    """Check every line and summarise the claim."""
    checked_lines = []
    total = 0.0
    violation_count = 0
    review_count = 0

    for line in lines:
        flags = check_line(line, policy)
        checked_lines.append({**line, "flags": flags})
        total += float(line["amount"])
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

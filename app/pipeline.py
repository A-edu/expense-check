"""Run one expense claim through extract -> rules -> summarise and store it."""

from contextlib import closing

from app import db, llm, rules


def run_check(text: str, submitted_by: str) -> dict:
    """Check the text with the model and the rules engine, then store a draft."""
    lines = llm.extract_lines(text)
    if not lines:
        raise ValueError("No expense lines found in the text.")
    result = rules.check_claim(lines, rules.load_policy())
    summary = _summary(result)

    with closing(db.connect()) as conn:
        claim_id = db.save_claim(
            conn,
            submitted_by=submitted_by,
            raw_text=text,
            checked=result,
            summary=summary,
        )
        claim = db.get_claim(conn, claim_id)
    if claim is None:
        raise RuntimeError(f"claim {claim_id} is missing after insert")
    return claim


def _summary(checked: dict) -> str:
    """Use the model summary only when it names every flagged rule id."""
    try:
        summary = llm.summarise(checked)
    except Exception:
        return llm.template_summary(checked)
    rule_ids = llm.flagged_rule_ids(checked)
    if any(rule_id not in summary for rule_id in rule_ids):
        return llm.template_summary(checked)
    return summary

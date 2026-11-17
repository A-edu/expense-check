"""SQLite storage for Expense Check claims, lines and decisions."""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Optional

DEFAULT_DB = "expense_check.db"

STATUSES = ("draft", "submitted", "approved", "returned")

CLAIM_COLUMNS = (
    "id",
    "submitted_by",
    "status",
    "policy_version",
    "total",
    "violation_count",
    "review_count",
    "summary",
    "created_at",
)

STATUS_CHECK = ", ".join(f"'{status}'" for status in STATUSES)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submitted_by TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ({STATUS_CHECK})),
    policy_version TEXT NOT NULL,
    total REAL NOT NULL,
    violation_count INTEGER NOT NULL,
    review_count INTEGER NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    people INTEGER NOT NULL,
    nights INTEGER NOT NULL,
    has_receipt INTEGER NOT NULL,
    flags_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    comment TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
"""


def db_path() -> str:
    """The database file, from EXPENSE_CHECK_DB when it is set."""
    return os.environ.get("EXPENSE_CHECK_DB") or DEFAULT_DB


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    """Open the database and create any missing tables."""
    conn = sqlite3.connect(path if path is not None else db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def init_db(path: Optional[str] = None) -> None:
    """Create the tables on startup if they are missing."""
    with closing(connect(path)):
        pass


def save_claim(
    conn: sqlite3.Connection,
    *,
    submitted_by: str,
    raw_text: str,
    checked: dict,
    summary: str,
) -> int:
    """Store a checked claim as a draft and return its id."""
    now = _now()
    cursor = conn.execute(
        "INSERT INTO claims (submitted_by, raw_text, status, policy_version, total,"
        " violation_count, review_count, summary, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            submitted_by,
            raw_text,
            "draft",
            checked["policy_version"],
            checked["total"],
            checked["violation_count"],
            checked["review_count"],
            summary,
            now,
            now,
        ),
    )
    claim_id = int(cursor.lastrowid)
    for position, line in enumerate(checked["lines"], start=1):
        conn.execute(
            "INSERT INTO lines (claim_id, position, description, category, amount,"
            " people, nights, has_receipt, flags_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                position,
                line["description"],
                line["category"],
                line["amount"],
                line["people"],
                line["nights"],
                1 if line["has_receipt"] else 0,
                json.dumps(line["flags"]),
            ),
        )
    conn.commit()
    return claim_id


def get_claim(conn: sqlite3.Connection, claim_id: int) -> Optional[dict]:
    """Return one claim with its lines and decisions, or None."""
    row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    if row is None:
        return None
    claim = _claim(row)
    claim["lines"] = _lines(conn, claim_id)
    claim["decisions"] = _decisions(conn, claim_id)
    return claim


def list_claims(conn: sqlite3.Connection, status: Optional[str] = None) -> list[dict]:
    """Return claims without their lines, newest first."""
    if status is None:
        rows = conn.execute(
            "SELECT * FROM claims ORDER BY created_at DESC, id DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM claims WHERE status = ? ORDER BY created_at DESC, id DESC",
            (status,),
        ).fetchall()
    return [_claim(row) for row in rows]


def set_status(conn: sqlite3.Connection, claim_id: int, status: str) -> None:
    """Move a claim to another status."""
    conn.execute(
        "UPDATE claims SET status = ?, updated_at = ? WHERE id = ?",
        (status, _now(), claim_id),
    )
    conn.commit()


def add_decision(
    conn: sqlite3.Connection, claim_id: int, decision: str, comment: str
) -> None:
    """Store a decision and move the claim to approved or returned."""
    status = "approved" if decision == "approve" else "returned"
    now = _now()
    conn.execute(
        "INSERT INTO decisions (claim_id, decision, comment, decided_at)"
        " VALUES (?, ?, ?, ?)",
        (claim_id, decision, comment, now),
    )
    conn.execute(
        "UPDATE claims SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, claim_id),
    )
    conn.commit()


def _claim(row: sqlite3.Row) -> dict:
    return {name: row[name] for name in CLAIM_COLUMNS}


def _lines(conn: sqlite3.Connection, claim_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT description, category, amount, people, nights, has_receipt, flags_json"
        " FROM lines WHERE claim_id = ? ORDER BY position",
        (claim_id,),
    ).fetchall()
    return [
        {
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
            "people": row["people"],
            "nights": row["nights"],
            "has_receipt": bool(row["has_receipt"]),
            "flags": json.loads(row["flags_json"]),
        }
        for row in rows
    ]


def _decisions(conn: sqlite3.Connection, claim_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, decision, comment, decided_at FROM decisions"
        " WHERE claim_id = ? ORDER BY id",
        (claim_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

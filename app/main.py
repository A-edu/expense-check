"""JSON API for Expense Check."""

import sqlite3
from contextlib import asynccontextmanager, closing
from typing import Iterator, Literal, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from app import db, llm, pipeline

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI) -> Iterator[None]:
    db.init_db()
    yield


app = FastAPI(title="Expense Check", lifespan=lifespan)


class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    submitted_by: str = ""

    @field_validator("text")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("text must not be empty")
        return text


class DecisionRequest(BaseModel):
    decision: Literal["approve", "return"]
    comment: str = ""


def get_conn() -> Iterator[sqlite3.Connection]:
    with closing(db.connect()) as conn:
        yield conn


@app.post("/api/claims/check")
def check_claim(body: CheckRequest) -> dict:
    problem = llm.config_problem()
    if problem is not None:
        raise HTTPException(status_code=503, detail=problem)
    try:
        return pipeline.run_check(body.text, body.submitted_by)
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/claims/{claim_id}/submit")
def submit_claim(
    claim_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    claim = _claim_or_404(conn, claim_id)
    if claim["status"] != "draft":
        raise HTTPException(
            status_code=409, detail=f"claim is {claim['status']}, not draft"
        )
    db.set_status(conn, claim_id, "submitted")
    return _claim_or_404(conn, claim_id)


@app.get("/api/claims")
def list_claims(
    status: Optional[str] = None, conn: sqlite3.Connection = Depends(get_conn)
) -> list[dict]:
    return db.list_claims(conn, status)


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return _claim_or_404(conn, claim_id)


@app.post("/api/claims/{claim_id}/decision")
def decide_claim(
    claim_id: int,
    body: DecisionRequest,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    claim = _claim_or_404(conn, claim_id)
    if claim["status"] != "submitted":
        raise HTTPException(
            status_code=409, detail=f"claim is {claim['status']}, not submitted"
        )
    comment = body.comment.strip()
    if body.decision == "return" and not comment:
        raise HTTPException(
            status_code=422, detail="returning a claim needs a comment"
        )
    db.add_decision(conn, claim_id, body.decision, comment)
    return _claim_or_404(conn, claim_id)


def _claim_or_404(conn: sqlite3.Connection, claim_id: int) -> dict:
    claim = db.get_claim(conn, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"claim {claim_id} not found")
    return claim

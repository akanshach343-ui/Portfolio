from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
import sqlite3
import os
import re
from datetime import datetime

app = FastAPI(title="Akansha Portfolio API")

# ── DB SETUP ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "challenge.db")

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS challenge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            challenge_description TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

init_db()

# ── SCHEMAS ───────────────────────────────────────────────
class ChallengeIn(BaseModel):
    name: str
    email: str
    challenge: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Name too long")
        return v

    @field_validator("email")
    @classmethod
    def email_valid(cls, v):
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("challenge")
    @classmethod
    def challenge_not_empty(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Please describe the challenge in at least 10 characters")
        if len(v) > 2000:
            raise ValueError("Challenge description too long (max 2000 chars)")
        return v


# ── API ROUTES ────────────────────────────────────────────
@app.post("/api/challenge")
async def submit_challenge(data: ChallengeIn):
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO challenge_requests (name, email, challenge_description, submitted_at) VALUES (?,?,?,?)",
            (data.name, data.email, data.challenge, datetime.utcnow().isoformat())
        )
        con.commit()
        row_id = cur.lastrowid
    finally:
        con.close()

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "Challenge received. I'll get back to you with the work done.",
            "id": row_id
        }
    )


@app.get("/api/challenges")
async def list_challenges(request: Request):
    """Admin: list all submitted challenges."""
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute("SELECT id, name, email, challenge_description, submitted_at FROM challenge_requests ORDER BY submitted_at DESC")
        rows = cur.fetchall()
    finally:
        con.close()

    return {
        "count": len(rows),
        "challenges": [
            {"id": r[0], "name": r[1], "email": r[2], "challenge": r[3], "submitted_at": r[4]}
            for r in rows
        ]
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── STATIC FILES (frontend) ───────────────────────────────
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")
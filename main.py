# from fastapi import FastAPI, HTTPException, Request
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse, JSONResponse
# from pydantic import BaseModel, EmailStr, field_validator
# import sqlite3
# import os
# import re
# from datetime import datetime

# app = FastAPI(title="Akansha Portfolio API")

# # ── DB SETUP ─────────────────────────────────────────────
# DB_PATH = os.path.join(os.path.dirname(__file__), "challenge.db")

# def init_db():
#     con = sqlite3.connect(DB_PATH)
#     cur = con.cursor()
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS challenge_requests (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             email TEXT NOT NULL,
#             challenge_description TEXT NOT NULL,
#             submitted_at TEXT NOT NULL
#         )
#     """)
#     con.commit()
#     con.close()

# init_db()

# # ── SCHEMAS ───────────────────────────────────────────────
# class ChallengeIn(BaseModel):
#     name: str
#     email: str
#     challenge: str

#     @field_validator("name")
#     @classmethod
#     def name_not_empty(cls, v):
#         v = v.strip()
#         if len(v) < 2:
#             raise ValueError("Name must be at least 2 characters")
#         if len(v) > 100:
#             raise ValueError("Name too long")
#         return v

#     @field_validator("email")
#     @classmethod
#     def email_valid(cls, v):
#         v = v.strip().lower()
#         if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
#             raise ValueError("Invalid email address")
#         return v

#     @field_validator("challenge")
#     @classmethod
#     def challenge_not_empty(cls, v):
#         v = v.strip()
#         if len(v) < 10:
#             raise ValueError("Please describe the challenge in at least 10 characters")
#         if len(v) > 2000:
#             raise ValueError("Challenge description too long (max 2000 chars)")
#         return v


# # ── API ROUTES ────────────────────────────────────────────
# @app.post("/api/challenge")
# async def submit_challenge(data: ChallengeIn):
#     con = sqlite3.connect(DB_PATH)
#     try:
#         cur = con.cursor()
#         cur.execute(
#             "INSERT INTO challenge_requests (name, email, challenge_description, submitted_at) VALUES (?,?,?,?)",
#             (data.name, data.email, data.challenge, datetime.utcnow().isoformat())
#         )
#         con.commit()
#         row_id = cur.lastrowid
#     finally:
#         con.close()

#     return JSONResponse(
#         status_code=201,
#         content={
#             "status": "success",
#             "message": "Challenge received. I'll get back to you with the work done.",
#             "id": row_id
#         }
#     )


# @app.get("/api/challenges")
# async def list_challenges(request: Request):
#     """Admin: list all submitted challenges."""
#     con = sqlite3.connect(DB_PATH)
#     try:
#         cur = con.cursor()
#         cur.execute("SELECT id, name, email, challenge_description, submitted_at FROM challenge_requests ORDER BY submitted_at DESC")
#         rows = cur.fetchall()
#     finally:
#         con.close()

#     return {
#         "count": len(rows),
#         "challenges": [
#             {"id": r[0], "name": r[1], "email": r[2], "challenge": r[3], "submitted_at": r[4]}
#             for r in rows
#         ]
#     }


# @app.get("/api/health")
# async def health():
#     return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# # ── STATIC FILES (frontend) ───────────────────────────────
# app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

"""
Akansha Portfolio — FastAPI backend
- Uses PostgreSQL on Render (DATABASE_URL env var)
- Falls back to SQLite for local development
- Admin dashboard at /admin  (password-protected via ADMIN_PASSWORD env var)
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, field_validator
import os, re, secrets
from datetime import datetime

# ── choose DB driver at startup ──────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")   # set this on Render

if DATABASE_URL:
    # PostgreSQL — Render injects  postgres://...  but psycopg2 needs postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    import psycopg2
    import psycopg2.extras
    USE_PG = True
else:
    import sqlite3
    USE_PG = False
    DB_PATH = os.path.join(os.path.dirname(__file__), "challenge.db")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "raycreates2025")

app = FastAPI(title="Akansha Portfolio API", docs_url="/api/docs")
security = HTTPBasic()

# ── DB helpers ───────────────────────────────────────────────
def get_conn():
    if USE_PG:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)

def init_db():
    con = get_conn()
    cur = con.cursor()
    if USE_PG:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS challenge_requests (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                challenge_description TEXT NOT NULL,
                submitted_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
    else:
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

# ── schema ────────────────────────────────────────────────────
class ChallengeIn(BaseModel):
    name: str
    email: str
    challenge: str

    @field_validator("name")
    @classmethod
    def name_ok(cls, v):
        v = v.strip()
        if len(v) < 2:   raise ValueError("Name must be at least 2 characters")
        if len(v) > 100: raise ValueError("Name too long")
        return v

    @field_validator("email")
    @classmethod
    def email_ok(cls, v):
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("challenge")
    @classmethod
    def challenge_ok(cls, v):
        v = v.strip()
        if len(v) < 10:   raise ValueError("Describe the challenge in at least 10 characters")
        if len(v) > 2000: raise ValueError("Too long (max 2000 chars)")
        return v

# ── auth helper ───────────────────────────────────────────────
def require_admin(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username.encode(), b"admin")
    ok_pass = secrets.compare_digest(creds.password.encode(), ADMIN_PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401,
                            detail="Wrong password",
                            headers={"WWW-Authenticate": 'Basic realm="Admin"'})
    return creds.username

# ── API routes ────────────────────────────────────────────────
@app.post("/api/challenge")
async def submit_challenge(data: ChallengeIn):
    con = get_conn()
    try:
        cur = con.cursor()
        now = datetime.utcnow().isoformat()
        if USE_PG:
            cur.execute(
                "INSERT INTO challenge_requests (name, email, challenge_description, submitted_at) VALUES (%s,%s,%s,%s) RETURNING id",
                (data.name, data.email, data.challenge, now)
            )
            row_id = cur.fetchone()[0]
        else:
            cur.execute(
                "INSERT INTO challenge_requests (name, email, challenge_description, submitted_at) VALUES (?,?,?,?)",
                (data.name, data.email, data.challenge, now)
            )
            row_id = cur.lastrowid
        con.commit()
    finally:
        con.close()

    return JSONResponse(status_code=201, content={
        "status": "success",
        "message": "Challenge received. I'll get back to you with the work done.",
        "id": row_id
    })


@app.get("/api/challenges")
async def list_challenges(_: str = Depends(require_admin)):
    """Protected: returns JSON list of all challenges."""
    con = get_conn()
    try:
        cur = con.cursor()
        if USE_PG:
            cur.execute("SELECT id, name, email, challenge_description, submitted_at FROM challenge_requests ORDER BY submitted_at DESC")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            for r in rows:
                if hasattr(r["submitted_at"], "isoformat"):
                    r["submitted_at"] = r["submitted_at"].isoformat()
        else:
            cur.execute("SELECT id, name, email, challenge_description, submitted_at FROM challenge_requests ORDER BY submitted_at DESC")
            rows = [{"id":r[0],"name":r[1],"email":r[2],"challenge":r[3],"submitted_at":r[4]} for r in cur.fetchall()]
    finally:
        con.close()
    return {"count": len(rows), "challenges": rows}


@app.get("/api/health")
async def health():
    db_type = "postgresql" if USE_PG else "sqlite (local)"
    return {"status": "ok", "db": db_type, "timestamp": datetime.utcnow().isoformat()}


# ── Admin dashboard HTML ──────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(_: str = Depends(require_admin)):
    return HTMLResponse(content=ADMIN_HTML)

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin — Challenge Submissions</title>
<style>
  :root {
    --ink: #19110A; --cream: #F4EFE6; --card: #EAE3D5;
    --orange: #E64E08; --green: #1E6B48; --muted: #8C7A68;
    --border: #D6C9B6; --red: #C0392B;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: var(--cream); color: var(--ink); }

  header {
    background: var(--ink); color: var(--cream);
    padding: 20px 40px; display: flex; justify-content: space-between; align-items: center;
  }
  header h1 { font-size: 1.1rem; font-weight: 600; }
  header span { font-size: .8rem; color: #6A5A48; }

  .stats-bar {
    background: var(--card); border-bottom: 1px solid var(--border);
    padding: 16px 40px; display: flex; gap: 40px;
  }
  .stat { display: flex; flex-direction: column; gap: 2px; }
  .stat-num { font-size: 1.6rem; font-weight: 700; color: var(--orange); }
  .stat-lbl { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }

  main { padding: 32px 40px; max-width: 1100px; }

  .toolbar {
    display: flex; gap: 12px; margin-bottom: 24px; align-items: center; flex-wrap: wrap;
  }
  .search-input {
    flex: 1; min-width: 200px; padding: 9px 14px;
    border: 1.5px solid var(--border); border-radius: 5px;
    font-size: .9rem; outline: none; background: white;
  }
  .search-input:focus { border-color: var(--orange); }
  .btn {
    padding: 9px 18px; border-radius: 5px; font-size: .82rem; font-weight: 500;
    cursor: pointer; border: 1.5px solid transparent;
  }
  .btn-refresh { background: var(--ink); color: var(--cream); }
  .btn-refresh:hover { background: #2D1E0A; }
  .btn-export  { background: white; color: var(--ink); border-color: var(--border); }
  .btn-export:hover { border-color: var(--ink); }

  table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 8px rgba(0,0,0,.06); }
  thead { background: var(--ink); color: var(--cream); }
  thead th { padding: 12px 16px; font-size: .72rem; letter-spacing: .09em; text-transform: uppercase; text-align: left; font-weight: 500; }
  tbody tr { border-bottom: 1px solid var(--border); transition: background .15s; }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: #FBF8F3; }
  td { padding: 14px 16px; font-size: .88rem; vertical-align: top; }
  td.challenge-cell { max-width: 360px; }
  .challenge-text { line-height: 1.55; color: var(--ink); }
  .challenge-text.clamped { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; cursor: pointer; }
  .badge-new {
    display: inline-block; background: var(--orange); color: white;
    font-size: .62rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    padding: 2px 7px; border-radius: 99px; margin-left: 6px; vertical-align: middle;
  }
  .email-link { color: var(--orange); text-decoration: none; }
  .email-link:hover { text-decoration: underline; }
  .date-cell { color: var(--muted); font-size: .8rem; white-space: nowrap; }
  .id-cell { color: var(--muted); font-size: .8rem; }

  .empty { text-align: center; padding: 60px; color: var(--muted); }
  .empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
  .empty p { font-size: .95rem; }

  #loading { text-align: center; padding: 48px; color: var(--muted); font-size: .95rem; }
  #error-msg { padding: 20px; background: #FDE8E8; border: 1px solid #F5C6C6; border-radius: 6px; color: var(--red); margin-bottom: 20px; font-size: .88rem; display: none; }

  .refresh-dot {
    display: inline-block; width: 8px; height: 8px;
    background: var(--green); border-radius: 50%; margin-right: 6px;
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1}50%{opacity:.3} }

  @media(max-width:700px){
    header, .stats-bar, main { padding-left: 18px; padding-right: 18px; }
    .stats-bar { gap: 24px; }
    table { font-size: .82rem; }
    td { padding: 10px 10px; }
  }
</style>
</head>
<body>
<header>
  <h1>🎯 Challenge Submissions</h1>
  <span><span class="refresh-dot"></span>Live — auto-refreshes every 30s</span>
</header>

<div class="stats-bar">
  <div class="stat"><div class="stat-num" id="s-total">—</div><div class="stat-lbl">Total</div></div>
  <div class="stat"><div class="stat-num" id="s-today">—</div><div class="stat-lbl">Today</div></div>
  <div class="stat"><div class="stat-num" id="s-new">—</div><div class="stat-lbl">Unread</div></div>
</div>

<main>
  <div class="toolbar">
    <input class="search-input" id="search" placeholder="Search by name, email, or challenge..." oninput="filterTable()" />
    <button class="btn btn-refresh" onclick="loadData()">↻ Refresh</button>
    <button class="btn btn-export" onclick="exportCSV()">↓ Export CSV</button>
  </div>
  <div id="error-msg"></div>
  <div id="loading">Loading submissions...</div>
  <table id="table" style="display:none">
    <thead>
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Email</th>
        <th>Challenge</th>
        <th>Submitted</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div id="empty" class="empty" style="display:none">
    <div class="empty-icon">📭</div>
    <p>No challenges submitted yet.<br>Share your website!</p>
  </div>
</main>

<script>
let allRows = [];
let seenIds = JSON.parse(localStorage.getItem('seen_ids') || '[]');

function fmt(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', {day:'2-digit',month:'short',year:'numeric'}) + ' ' +
         d.toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit'});
}

function isToday(iso) {
  const d = new Date(iso), n = new Date();
  return d.getDate()===n.getDate() && d.getMonth()===n.getMonth() && d.getFullYear()===n.getFullYear();
}

async function loadData() {
  try {
    const res = await fetch('/api/challenges');
    if (res.status === 401) { location.reload(); return; }
    if (!res.ok) throw new Error('Server error ' + res.status);
    const data = await res.json();
    allRows = data.challenges || [];

    // stats
    document.getElementById('s-total').textContent = allRows.length;
    document.getElementById('s-today').textContent = allRows.filter(r => isToday(r.submitted_at)).length;
    const newCount = allRows.filter(r => !seenIds.includes(r.id)).length;
    document.getElementById('s-new').textContent = newCount;

    document.getElementById('error-msg').style.display = 'none';
    renderTable(allRows);
  } catch(e) {
    const el = document.getElementById('error-msg');
    el.style.display = 'block';
    el.textContent = 'Could not load data: ' + e.message;
  }
}

function renderTable(rows) {
  document.getElementById('loading').style.display = 'none';
  if (!rows.length) {
    document.getElementById('table').style.display = 'none';
    document.getElementById('empty').style.display = 'block';
    return;
  }
  document.getElementById('empty').style.display = 'none';
  document.getElementById('table').style.display = 'table';

  document.getElementById('tbody').innerHTML = rows.map(r => {
    const isNew = !seenIds.includes(r.id);
    return `<tr>
      <td class="id-cell">#${r.id}</td>
      <td><strong>${esc(r.name)}</strong>${isNew ? '<span class="badge-new">new</span>' : ''}</td>
      <td><a href="mailto:${esc(r.email)}" class="email-link">${esc(r.email)}</a></td>
      <td class="challenge-cell">
        <div class="challenge-text clamped" onclick="toggleExpand(this)">${esc(r.challenge_description || r.challenge)}</div>
      </td>
      <td class="date-cell">${fmt(r.submitted_at)}</td>
    </tr>`;
  }).join('');

  // mark all as seen
  seenIds = allRows.map(r => r.id);
  localStorage.setItem('seen_ids', JSON.stringify(seenIds));
  document.getElementById('s-new').textContent = '0';
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toggleExpand(el) {
  el.classList.toggle('clamped');
}

function filterTable() {
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = q ? allRows.filter(r =>
    (r.name||'').toLowerCase().includes(q) ||
    (r.email||'').toLowerCase().includes(q) ||
    (r.challenge_description||r.challenge||'').toLowerCase().includes(q)
  ) : allRows;
  renderTable(filtered);
}

function exportCSV() {
  if (!allRows.length) return;
  const header = ['ID','Name','Email','Challenge','Submitted At'];
  const rows = allRows.map(r => [
    r.id, r.name, r.email,
    (r.challenge_description||r.challenge||'').replace(/"/g,'""'),
    r.submitted_at
  ].map(v => `"${v}"`).join(','));
  const csv = [header.join(','), ...rows].join('\\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  a.download = 'challenges_' + new Date().toISOString().split('T')[0] + '.csv';
  a.click();
}

loadData();
setInterval(loadData, 30000); // auto-refresh every 30s
</script>
</body>
</html>
"""

# ── Static files LAST ─────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
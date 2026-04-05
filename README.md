# MLH PE Hackathon 2026 — URL Shortener

**Track: Reliability Engineering**

A production-grade URL shortener built on the official MLH PE Hackathon 2026 template.
Stack: Flask · Peewee ORM · PostgreSQL · pytest · GitHub Actions

---

## Architecture
Client
|
v
Flask App (localhost:5000)
|-- POST /shorten     ? creates short code ? saves to PostgreSQL
|-- GET  /<code>      ? looks up code      ? redirects to target URL
|-- GET  /health      ? returns {"status":"ok"}
|-- GET  /urls        ? lists all active short URLs
v
PostgreSQL (hackathon_db ? short_urls table)

---

## Prerequisites

- Python 3.12+
- PostgreSQL 18
- uv package manager

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Setup and Run
```bash
# 1. Clone
git clone https://github.com/Shishir067/pe-hackathon-2026
cd pe-hackathon-2026

# 2. Install dependencies
uv sync

# 3. Create database
createdb -U postgres hackathon_db

# 4. Configure environment
cp .env.example .env
# Edit .env and set your DATABASE_PASSWORD

# 5. Create tables
uv run python -c "from app import create_app; from app.database import db; from app.models.url import ShortURL; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_tables([ShortURL], safe=True)"

# 6. Run
uv run run.py

# 7. Verify
curl http://localhost:5000/health
# ? {"status": "ok"}
```

---

## API Endpoints

### GET /health
Health check for load balancers.
Response 200: {"status": "ok"}

### POST /shorten
Create a short URL.
Request:  {"url": "https://example.com"}
Response 201: {"code": "abc123", "short_url": "/abc123", "target": "https://example.com"}
Response 400: {"error": "Field url is required"}
Response 422: {"error": "Invalid URL. Must start with http:// or https://"}

### GET /<code>
Redirect to target URL.
Response 302: redirects to target
Response 404: {"error": "Short URL not found"}
Response 410: {"error": "This short URL has been deactivated"}

### GET /urls
List all active short URLs.
Response 200: [{"code": "abc123", "target": "https://example.com", "hits": 5, ...}]

### GET /urls/<code>
Get details for one short URL.
Response 200: {"code": "abc123", "target": "...", "hits": 3, "is_active": true}
Response 404: {"error": "Not found"}

### DELETE /urls/<code>
Soft-delete a short URL.
Response 200: {"message": "Short URL abc123 deactivated"}
Response 404: {"error": "Not found"}

---

## Running Tests
```bash
# All tests
uv run pytest tests/ -v

# With coverage report
uv run pytest tests/ --cov=app --cov-report=term-missing
```

Expected: 24 tests passing, 81% coverage.

---

## Error Handling

| Scenario | Status | Response |
|---|---|---|
| Route not found | 404 | {"error": "Resource not found"} |
| Method not allowed | 405 | {"error": "Method not allowed"} |
| Internal server error | 500 | {"error": "Internal server error"} |
| Missing url field | 400 | {"error": "Field url is required"} |
| Invalid URL format | 422 | {"error": "Invalid URL..."} |
| Code not found | 404 | {"error": "Short URL not found"} |
| Deactivated code | 410 | {"error": "This short URL has been deactivated"} |

All errors return clean JSON. The app never returns a raw Python stack trace.

---

## Environment Variables

| Variable | Description |
|---|---|
| DATABASE_NAME | PostgreSQL database name (hackathon_db) |
| DATABASE_HOST | Database host (localhost) |
| DATABASE_PORT | Database port (5432) |
| DATABASE_USER | PostgreSQL username |
| DATABASE_PASSWORD | PostgreSQL password |
| FLASK_DEBUG | Enable debug mode (true/false) |

---

## CI/CD

GitHub Actions runs on every push:
- Installs dependencies with uv
- Spins up PostgreSQL service
- Runs 24 tests with coverage
- Enforces minimum 50% coverage
- Blocks deploy if any test fails

---

## Failure Modes

### Database unavailable
Symptom: All endpoints return 500 JSON error.
Fix: Check PostgreSQL is running. Restart with `pg_ctl start`.
The app catches the exception and returns clean JSON, never a stack trace.

### Duplicate short code collision
Symptom: Extremely rare. App retries up to 5 times before returning 500.
Fix: No action needed.

### Invalid input submitted
Symptom: Client sends bad data.
Fix: Input validation rejects all bad input before touching the DB.
Returns 400 or 422 with descriptive JSON error.

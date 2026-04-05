# MLH PE Hackathon 2026 — URL Shortener

**Track: Reliability Engineering**

A production-grade URL shortener built on the official MLH PE Hackathon 2026 template.

**Stack:** Flask · Peewee ORM · PostgreSQL · pytest · GitHub Actions

---

## Architecture

The service follows a simple three-layer architecture:

**Client → Flask App → PostgreSQL**

- Client sends a POST to `/shorten` with a long URL
- Flask validates the URL, generates a 6-character code, and saves it to PostgreSQL
- Client later visits `/<code>` and Flask looks it up and redirects to the original URL
- The `/health` endpoint lets load balancers verify the app is alive at any time

---

## Prerequisites

- Python 3.12+
- PostgreSQL 18
- uv package manager

Install uv on Windows:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Install uv on macOS / Linux:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Setup and Run

```
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
```

Verify it is running:

```
curl http://localhost:5000/health
```

Expected response: `{"status": "ok"}`

---

## API Endpoints

### POST /shorten

Create a short URL.

Request body:

```json
{"url": "https://example.com"}
```

Responses:

| Status | Body |
|--------|------|
| 201 | `{"code": "abc123", "short_url": "/abc123", "target": "https://example.com"}` |
| 400 | `{"error": "Field url is required"}` |
| 422 | `{"error": "Invalid URL. Must start with http:// or https://"}` |

---

### GET /\<code\>

Redirect to the original URL.

Responses:

| Status | Meaning |
|--------|---------|
| 302 | Redirects to target URL |
| 404 | `{"error": "Short URL not found"}` |
| 410 | `{"error": "This short URL has been deactivated"}` |

---

### GET /health

Health check endpoint used by load balancers.

Response: `200 {"status": "ok"}`

---

### GET /urls

List all active short URLs.

Response: `200` — array of URL objects

---

### GET /urls/\<code\>

Get details for one short URL.

| Status | Body |
|--------|------|
| 200 | `{"code": "abc123", "target": "...", "hits": 3, "is_active": true}` |
| 404 | `{"error": "Not found"}` |

---

### DELETE /urls/\<code\>

Soft-delete a short URL. Subsequent redirects to this code return 410.

| Status | Body |
|--------|------|
| 200 | `{"message": "Short URL abc123 deactivated"}` |
| 404 | `{"error": "Not found"}` |

---

## Running Tests

Run all tests:

```
uv run pytest tests/ -v
```

Run with coverage report:

```
uv run pytest tests/ --cov=app --cov-report=term-missing
```

Expected result: 24 tests passing, 81% total coverage.

---

## Error Handling

Every error returns clean JSON. The app never exposes a raw Python stack trace.

| Scenario | Status | Response |
|----------|--------|----------|
| Route not found | 404 | `{"error": "Resource not found", "status": 404}` |
| Method not allowed | 405 | `{"error": "Method not allowed", "status": 405}` |
| Internal server error | 500 | `{"error": "Internal server error", "status": 500}` |
| Missing url field | 400 | `{"error": "Field url is required"}` |
| Invalid URL format | 422 | `{"error": "Invalid URL. Must start with http:// or https://"}` |
| Code not found | 404 | `{"error": "Short URL not found"}` |
| Deactivated code | 410 | `{"error": "This short URL has been deactivated"}` |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_NAME | PostgreSQL database name (hackathon_db) |
| DATABASE_HOST | Database host (localhost) |
| DATABASE_PORT | Database port (5432) |
| DATABASE_USER | PostgreSQL username |
| DATABASE_PASSWORD | PostgreSQL password |
| FLASK_DEBUG | Enable debug mode (true/false) |

---

## CI/CD

GitHub Actions runs on every push and does the following:

1. Installs dependencies with uv
2. Spins up a PostgreSQL service container
3. Runs all 24 tests with coverage measurement
4. Enforces minimum 50% coverage
5. Blocks the deploy job if any test fails

CI workflow: `.github/workflows/ci.yml`

---

## Failure Modes

### Database unavailable

**Symptom:** All endpoints return a 500 JSON error body.

**Fix:** Check PostgreSQL is running. On Windows restart the PostgreSQL 18 service. The global error handler in `app/__init__.py` catches the connection exception and returns clean JSON instead of crashing.

### Duplicate short code collision

**Symptom:** Extremely rare — there are 62^6 (56 billion) possible codes. The app retries code generation up to 5 times before returning 500.

**Fix:** No action needed unless the database has billions of rows.

### Invalid input submitted

**Symptom:** Client sends non-JSON, a missing url field, or a malformed URL.

**Fix:** Input validation in `/shorten` rejects all bad input before it touches the database. Returns 400 for missing fields and 422 for invalid URLs, both with descriptive JSON error messages.

### Deactivated URL accessed

**Symptom:** A previously deleted short code returns 410 instead of redirecting.

**Fix:** This is expected behavior. The DELETE endpoint soft-deletes by setting `is_active=False`. The record stays in the database for audit purposes but no longer redirects.

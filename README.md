# NoteFlow

> **Showcase copy of a private production system; client data and integrations removed.** All names, emails, and sample data in this repository are fictitious. Source available for viewing; all rights reserved.

AI-powered clinical documentation automation for physical therapists. NoteFlow records audio during PT sessions, transcribes speech in real time via Deepgram, and generates structured SOAP notes with Claude. Completed notes are automatically entered into Kinnser EMR via a Playwright browser worker — eliminating documentation from the clinician's day.

---

## Architecture

```
Browser / Mobile
      │
      │ HTTPS
      ▼
┌─────────────┐        ┌──────────────────────────────┐
│  Next.js 14 │        │        FastAPI (Python 3.12)  │
│  (frontend) │◄──────►│  /api/auth  /api/notes        │
└─────────────┘  HTTP  │  /api/voice /api/billing      │
                       │  /api/kinnser /health         │
                       └──────────┬───────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              PostgreSQL 16    Redis 7    AWS S3 (PHI)
                    │             │
          ┌─────────┴─────────────┤
          │         Celery Workers │
          │  ┌──────────────────┐  │
          │  │ celery-worker    │  │
          │  │ Queues:          │  │
          │  │  note_processing │  │
          │  │  kinnser_entry   │  │
          │  └──────────────────┘  │
          │  ┌──────────────────┐  │
          │  │ playwright-worker│  │
          │  │ Queue:           │  │
          │  │  kinnser_entry   │  │
          │  └──────────────────┘  │
          └────────────────────────┘
```

**Key design decisions:**

- All PHI fields are encrypted at rest with AES-256-GCM before reaching Postgres
- Audio files are stored in S3 with SSE-KMS and never retained after transcription
- Kinnser EMR entry runs in an isolated Playwright worker (separate container) to contain browser state
- Magic-link email auth — no passwords stored
- HIPAA audit log table tracks every PHI access event

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker Desktop | 4.x+ |
| Docker Compose | v2.x (bundled with Docker Desktop) |
| Node.js | 20 LTS (for local frontend dev) |
| Python | 3.12 (for local backend dev) |
| PostgreSQL client (`psql`) | Optional, for direct DB access |

---

## Quick Start (Docker Compose)

```bash
# 1. Clone the repo
git clone https://github.com/your-org/noteflow.git
cd noteflow

# 2. Create your environment file
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET, MAGIC_LINK_SECRET, ENCRYPTION_KEY,
# DEEPGRAM_API_KEY, and ANTHROPIC_API_KEY

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Open the app
open http://localhost:3000
```

Services:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

Stop everything:

```bash
docker compose down
# To also remove volumes (wipes DB):
docker compose down -v
```

---

## Manual Setup (without Docker)

### Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (for Kinnser worker only)
playwright install chromium

# Copy and configure env
cp ../.env.example ../.env
# Edit .env with your local Postgres and Redis URLs

# Start FastAPI dev server (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

npm install

# Point at local backend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev   # http://localhost:3000
```

### Celery Workers (optional for local dev)

```bash
# General worker (note processing + Kinnser queue)
cd backend
celery -A workers.celery_app worker -Q note_processing,kinnser_entry -c 2 --loglevel=info

# Playwright worker (Kinnser browser automation only)
celery -A workers.celery_app worker -Q kinnser_entry -c 1 --loglevel=info
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Async Postgres DSN (`postgresql+asyncpg://...`) |
| `POSTGRES_PASSWORD` | Yes | Password for the `noteflow` Postgres user (docker-compose) |
| `REDIS_URL` | Yes | Redis DSN (`redis://host:6379/0`) |
| `JWT_SECRET` | Yes | 64-char random hex — signs access/refresh tokens |
| `JWT_ALGORITHM` | Yes | `HS256` (default) |
| `MAGIC_LINK_SECRET` | Yes | 64-char random hex — signs magic-link email tokens |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | No | Default `3600` (1 hour) |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | No | Default `604800` (7 days) |
| `DEEPGRAM_API_KEY` | Yes | Deepgram API key for real-time transcription |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude SOAP generation |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key (test: `sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE_PRICE_ID` | Yes | Stripe price ID for the subscription plan |
| `AWS_ACCESS_KEY_ID` | Yes | AWS IAM key with S3 read/write on the PHI bucket |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS IAM secret |
| `AWS_S3_BUCKET` | Yes | S3 bucket name for audio/document storage |
| `AWS_REGION` | Yes | AWS region (e.g., `us-east-1`) |
| `ENCRYPTION_KEY` | Yes | 32-byte AES key, base64-encoded — encrypts PHI fields |
| `KINNSER_BASE_URL` | Yes | Kinnser login URL (default `https://www.kinnser.net`) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins for CORS |
| `APP_ENV` | Yes | `development` or `production` |
| `SENTRY_DSN` | No | Sentry DSN — leave blank to disable |
| `NEXT_PUBLIC_API_URL` | Yes | Backend URL visible to the browser |

Generate secrets:

```bash
# JWT_SECRET and MAGIC_LINK_SECRET
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (DB + Redis ping) |
| `POST` | `/api/auth/magic-link` | Send magic-link login email |
| `POST` | `/api/auth/verify` | Exchange magic-link token for JWT |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/notes` | List notes for authenticated clinician |
| `POST` | `/api/notes` | Create note (triggers async processing) |
| `GET` | `/api/notes/{id}` | Get note detail |
| `PATCH` | `/api/notes/{id}` | Edit generated SOAP note |
| `POST` | `/api/voice/upload` | Upload audio file for transcription |
| `POST` | `/api/voice/stream` | WebSocket endpoint for live transcription |
| `POST` | `/api/billing/subscribe` | Create Stripe subscription |
| `POST` | `/api/billing/webhook` | Stripe webhook receiver |
| `GET` | `/api/billing/portal` | Stripe customer portal redirect |
| `POST` | `/api/kinnser/submit/{note_id}` | Queue Kinnser EMR entry for a note |
| `GET` | `/api/kinnser/status/{note_id}` | Poll Kinnser submission status |

Full interactive docs: http://localhost:8000/docs

---

## Development Workflow

### Branch strategy

```
main          — production-ready, protected
staging       — integration testing
feature/*     — feature branches, PR into staging
hotfix/*      — critical fixes, PR into main
```

### Running tests

```bash
# Backend unit + integration tests
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Frontend lint
cd frontend
npm run lint
```

### Code quality

```bash
# Backend
cd backend
black .
isort .
mypy .

# Frontend
cd frontend
npm run lint
```

---

## Database Migrations (Alembic)

```bash
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Create a new migration after changing SQLAlchemy models
docker compose exec backend alembic revision --autogenerate -m "add clinician table"

# Roll back one migration
docker compose exec backend alembic downgrade -1

# Show migration history
docker compose exec backend alembic history --verbose
```

For local dev (outside Docker):

```bash
cd backend
alembic upgrade head
```

---

## Testing

```bash
# Run all backend tests inside Docker
docker compose exec backend pytest tests/ -v

# Run a specific test file
docker compose exec backend pytest tests/test_notes.py -v

# Run Playwright integration tests (requires running services)
cd backend
pytest tests/integration/ -v --headed   # --headed shows browser
```

### Test database

Tests use a separate `noteflow_test` database. Set `TEST_DATABASE_URL` in your `.env` or the test config will fall back to SQLite in-memory.

---

## HIPAA Compliance Notes

NoteFlow is built with HIPAA technical safeguards in mind. **This is not a substitute for a formal HIPAA risk analysis or BAA review with your legal team.**

| Safeguard | Implementation |
|-----------|----------------|
| PHI encryption at rest | AES-256-GCM per-field, key in env var |
| PHI encryption in transit | TLS 1.2+ required in production |
| S3 storage | SSE-KMS encryption, private bucket, no public ACLs |
| Access control | JWT auth, role-based (clinician / admin) |
| Audit logging | Every PHI read/write logged to `audit_log` table |
| Minimum necessary | Audio deleted from S3 after transcription |
| Session timeout | Short-lived access tokens (1 hour default) |
| Breach notification | Sentry for anomaly detection + alerting |

Before going to production:

- [ ] Sign a BAA with AWS, Deepgram, Anthropic, and Sentry
- [ ] Enable Postgres SSL (`sslmode=require` in `DATABASE_URL`)
- [ ] Enable S3 bucket versioning and access logging
- [ ] Run a formal penetration test
- [ ] Document your risk analysis

---

## Deployment (Render)

NoteFlow is designed to deploy on [Render](https://render.com).

### Services to create in Render

| Render service type | Name | Source |
|--------------------|------|--------|
| Web Service | `noteflow-backend` | `./backend`, start cmd: `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Web Service | `noteflow-frontend` | `./frontend`, build: `npm run build`, start: `node server.js` |
| Background Worker | `noteflow-celery` | `./backend`, start: `celery -A workers.celery_app worker -Q note_processing,kinnser_entry -c 2` |
| Background Worker | `noteflow-playwright` | `./backend`, Dockerfile: `Dockerfile.playwright` |
| PostgreSQL | `noteflow-db` | Render managed Postgres 16 |
| Redis | `noteflow-redis` | Render managed Redis 7 |

### Environment variables on Render

Set all variables from `.env.example` in the Render dashboard under **Environment**. For `DATABASE_URL` and `REDIS_URL`, use the internal connection strings Render provides for managed services.

### Migrations on deploy

Add a pre-deploy command to the backend service:

```
alembic upgrade head
```

### Health check path

Set the health check path to `/health` for the backend service.

---

## Troubleshooting

**Postgres won't start / permission denied on volume**

```bash
docker compose down -v
docker compose up -d
```

**Backend can't reach Postgres**

Ensure `DATABASE_URL` uses the service name `postgres` as the host when running inside Docker, not `localhost`.

**Playwright worker fails with "browser not found"**

The `playwright-worker` service uses `Dockerfile.playwright` which runs `playwright install chromium`. If you're running the worker locally, run `playwright install chromium` in your virtualenv.

**Celery tasks not processing**

```bash
# Check worker is connected
docker compose exec celery-worker celery -A workers.celery_app inspect active

# Check Redis connectivity
docker compose exec redis redis-cli ping
```

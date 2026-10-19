#!/usr/bin/env bash
set -euo pipefail

echo "=== NoteFlow Dev Environment ==="

# Check for .env
if [ ! -f .env ]; then
    echo "No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "Please update .env with your actual credentials before running."
    exit 1
fi

# Start infrastructure
echo "Starting PostgreSQL and Redis..."
docker compose up -d postgres redis

# Wait for services
echo "Waiting for services to be healthy..."
docker compose exec postgres pg_isready -U noteflow -q || sleep 3

# Run migrations
echo "Running database migrations..."
cd backend
alembic upgrade head
cd ..

# Start backend
echo "Starting FastAPI backend..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start Celery worker
echo "Starting Celery worker..."
cd backend
celery -A app.workers.celery_app worker --loglevel=info --queues=note_processing,kinnser_entry --concurrency=2 &
WORKER_PID=$!
cd ..

# Start frontend
echo "Starting Next.js frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=== NoteFlow Running ==="
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Cleanup on exit
trap "kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null; docker compose stop postgres redis" EXIT

wait

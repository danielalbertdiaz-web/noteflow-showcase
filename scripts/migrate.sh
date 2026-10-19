#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

case "${1:-}" in
    create)
        if [ -z "${2:-}" ]; then
            echo "Usage: ./migrate.sh create <migration_name>"
            exit 1
        fi
        alembic revision --autogenerate -m "$2"
        ;;
    upgrade)
        alembic upgrade "${2:-head}"
        ;;
    downgrade)
        alembic downgrade "${2:--1}"
        ;;
    current)
        alembic current
        ;;
    history)
        alembic history
        ;;
    *)
        echo "Usage: ./migrate.sh {create|upgrade|downgrade|current|history} [args]"
        echo ""
        echo "Commands:"
        echo "  create <name>   Create a new migration"
        echo "  upgrade [rev]   Upgrade to revision (default: head)"
        echo "  downgrade [rev] Downgrade by revision (default: -1)"
        echo "  current         Show current revision"
        echo "  history         Show migration history"
        exit 1
        ;;
esac

web: bash -c 'cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'
worker: cd backend && celery -A app.workers.celery_app worker -B --loglevel=info
telegram: cd backend && python -m app.services.telegram_listener

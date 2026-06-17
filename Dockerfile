FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc git \
    && rm -rf /var/lib/apt/lists/*

# Copy the full repo first
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

EXPOSE 8000

# Default to web service (FastAPI)
# Uses Railway-provided PORT env var, falling back to 8000
CMD ["bash", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

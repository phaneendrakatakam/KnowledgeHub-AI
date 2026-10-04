FROM python:3.12-slim

WORKDIR /app

# PostgreSQL runtime library required by psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --default-timeout=300 \
    --retries=10 \
    -r requirements.txt

# Copy application
COPY backend ./backend
COPY frontend ./frontend
COPY documents ./documents

# KnowledgeHub uses flat imports such as:
# from auth import ...
# from db import ...
# from rag import ...
ENV PYTHONPATH=/app/backend

# Python logging/output
ENV PYTHONUNBUFFERED=1

# Cloud Run supplies PORT automatically.
# Local Docker testing defaults to 8080.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
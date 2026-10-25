FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser & OS system dependencies
RUN playwright install --with-deps chromium

# Copy backend code
COPY morphapi_v2/ ./morphapi_v2/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV MORPHAPI_V2_DB_PATH=/app/morphapi_v2.db

EXPOSE 8001

# Render dynamically sets $PORT; fallback to 8001 for local runs
CMD ["sh", "-c", "uvicorn morphapi_v2.api.app:app --host 0.0.0.0 --port ${PORT:-8001}"]

# Build context must be the repo root (see docker-compose.yml), since the
# editable installs in requirements.txt reference ../../backend-modules/*
# relative to this service's own directory - we preserve that same relative
# depth inside the image instead of flattening the tree.
FROM python:3.11-slim

WORKDIR /build
COPY backend-modules ./backend-modules
COPY apps/api-gateway ./apps/api-gateway

WORKDIR /build/apps/api-gateway
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

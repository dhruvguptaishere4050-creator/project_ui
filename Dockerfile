# Builds the React SPA and serves it from the FastAPI backend on a single port.
FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# The image installs the PostgreSQL driver too, so the same image works with
# either DATABASE_URL backend.
COPY backend/requirements.txt backend/requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt
COPY backend/app ./app
COPY --from=frontend /app/dist ./static
RUN mkdir -p /srv/data
ENV STATIC_DIR=/srv/static
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

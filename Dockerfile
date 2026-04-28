# ── STAGE 1: Construcción del Frontend ──
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── STAGE 2: Preparación del Backend ──
FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Instalamos dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código del backend
COPY . .

# Copiamos SOLO la carpeta compilada del frontend desde el Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Cloud Run inyecta la variable PORT
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 120
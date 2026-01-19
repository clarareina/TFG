# 1. Imagen base: Python 3.10 ligero
FROM python:3.10-slim

# 2. Evita archivos basura de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Directorio de trabajo en el contenedor
WORKDIR /app

# 4. Copiamos dependencias e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos TODO tu código al contenedor
COPY . .
COPY frontend/dist /app/frontend/dist

# 6. Cloud Run inyecta la variable PORT (normalmente 8080)
ENV PORT=8080

# 7. Comando de arranque
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
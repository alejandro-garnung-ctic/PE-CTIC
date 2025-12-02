# Dockerfile para servicio de autenticación
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY app.py .
COPY manage_users.py .
COPY admin.html .

# Crear directorio de usuarios
RUN mkdir -p /app/users_data && \
    chmod +x manage_users.py

EXPOSE 5000

CMD ["python", "app.py"]


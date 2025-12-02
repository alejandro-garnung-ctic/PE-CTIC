# Dockerfile para la webapp
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema (incluyendo pwd para obtener usuarios)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libc6 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY app.py .
COPY notebook_parser.py .
COPY templates/ ./templates/

# Crear directorios para volúmenes montados y estáticos
RUN mkdir -p /app/shared /app/users /app/static

# Exponer puerto
EXPOSE 80

# Ejecutar aplicación como root para poder usar puerto 80
# (En producción, usar gunicorn con un usuario no-root y un proxy reverso)
USER root
CMD ["python", "app.py"]


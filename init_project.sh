#!/bin/bash
# init_project.sh - Inicialización del entorno colaborativo PE-CTIC

# Crear directorios necesarios
mkdir -p shared/data shared/scripts shared/notebooks users jupyterlab auth/users_data nginx

# 🔥 ESTABLECER PROPIEDAD CORRECTA - usando el usuario actual
echo "🔧 Estableciendo permisos correctos..."

# Cambiar propiedad de los directorios al usuario actual (usar sudo si es necesario)
if [ -w . ]; then
    chown -R $(id -u):$(id -g) shared/ users/ auth/ jupyterlab/ 2>/dev/null || true
else
    sudo chown -R $(id -u):$(id -g) shared/ users/ auth/ jupyterlab/ 2>/dev/null || true
fi

# Establecer permisos correctos para directorios
chmod 755 shared/ shared/data/ shared/scripts/ 2>/dev/null || true
chmod 775 shared/notebooks/ 2>/dev/null || true  # Permisos de escritura para notebooks
chmod 755 users/ auth/ auth/users_data/ jupyterlab/ 2>/dev/null || true

# Establecer permisos correctos para archivos
find shared/data/ shared/scripts/ -type f -exec chmod 644 {} \; 2>/dev/null || true
find shared/notebooks/ -type f -name "*.ipynb" -exec chmod 664 {} \; 2>/dev/null || true  # Escritura para notebooks
find shared/notebooks/ -type f ! -name "*.ipynb" -exec chmod 644 {} \; 2>/dev/null || true
find users/ -type f -exec chmod 644 {} \; 2>/dev/null || true

# Crear archivos base con permisos correctos
echo '{}' > auth/users_data/users.json
echo '{}' > auth/users_data/tokens.json
chmod 644 auth/users_data/users.json auth/users_data/tokens.json

# Establecer propiedad de los archivos también
if [ -w . ]; then
    chown $(id -u):$(id -g) auth/users_data/users.json auth/users_data/tokens.json 2>/dev/null || true
else
    sudo chown $(id -u):$(id -g) auth/users_data/users.json auth/users_data/tokens.json 2>/dev/null || true
fi

# Crear archivo .env si no existe (opcional, para futuras configuraciones)
if [ ! -f ".env" ]; then
    echo "# Variables de entorno PE-CTIC" > .env
    echo "# JUPYTER_TOKEN=  # Token opcional para autenticación" >> .env
    chmod 644 .env
    if [ -w . ]; then
        chown $(id -u):$(id -g) .env 2>/dev/null || true
    else
        sudo chown $(id -u):$(id -g) .env 2>/dev/null || true
    fi
fi

echo "✅ Proyecto PE-CTIC inicializado"
echo ""
echo "Estructura creada:"
echo "  - shared/     : Datos y scripts compartidos"
echo "  - users/      : Directorios de usuarios"
echo "  - jupyterlab/  : Configuración de JupyterLab"
echo "  - nginx/       : Configuración del proxy reverso"
echo ""
echo "Propietario: $(id -un):$(id -gn)"
echo ""
echo "Para iniciar el entorno:"
echo "  docker compose up -d"
echo ""
echo "Acceso al sistema:"
echo "  - Login:        http://chomsky/pe-ctic/ (o http://localhost/pe-ctic/)"
echo "  - JupyterLab:   http://chomsky/lab (requiere login)"
echo "  - Webapp:       http://chomsky/pe-ctic/webapp/"
echo ""
echo "Para crear usuarios, ejecuta:"
echo "  docker compose exec auth python manage_users.py add -u nombre_usuario -p contraseña"
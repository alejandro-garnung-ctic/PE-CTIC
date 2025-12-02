#!/bin/bash
# fix_permissions.sh - Reparar permisos de archivos de PE-CTIC

echo "🔧 Reparando permisos de PE-CTIC..."

# Cambiar propiedad al usuario actual
sudo chown -R $(id -u):$(id -g) auth/users_data/
sudo chown -R $(id -u):$(id -g) users/
sudo chown -R $(id -u):$(id -g) shared/
sudo chown -R $(id -u):$(id -g) jupyterlab/

# Establecer permisos correctos
chmod 755 auth/users_data/
chmod 644 auth/users_data/*.json 2>/dev/null || true
chmod 755 users/
chmod 755 shared/
chmod 755 jupyterlab/

echo "✅ Permisos reparados"
echo "Propietario actual: $(ls -ld auth/users_data/ | awk '{print $3":"$4}')"

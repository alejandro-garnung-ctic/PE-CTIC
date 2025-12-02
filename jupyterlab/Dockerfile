# Dockerfile para JupyterLab - Entorno Python colaborativo
FROM jupyter/scipy-notebook:latest

USER root

# Instalar paquetes adicionales para estadística y análisis
RUN pip install --no-cache-dir \
    statsmodels \
    scikit-posthocs \
    pingouin \
    plotly \
    seaborn \
    openpyxl \
    jupyterlab-git \
    jupyterlab-lsp \
    python-lsp-server[all]

# Instalar herramientas para LaTeX en notebooks y gosu para cambio de usuario
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Solo crear estructura interna sin tocar permisos del host
RUN mkdir -p /home/shared_internal /home/users_internal && \
    # Directorios internos (no montados) pueden tener sus permisos
    chown -R jovyan:users /home/shared_internal /home/users_internal

# Script para configurar directorio de usuario al iniciar
RUN echo '#!/bin/bash\n\
USERNAME=$(echo $JUPYTER_TOKEN_USERNAME 2>/dev/null || echo "default")\n\
if [ ! -d "/home/users/$USERNAME" ]; then\n\
    mkdir -p "/home/users/$USERNAME"\n\
    chmod 755 "/home/users/$USERNAME"\n\
fi\n\
ln -sf "/home/users/$USERNAME" "/home/jovyan/my_work" 2>/dev/null || true\n\
exec "$@"' > /usr/local/bin/setup_user_dir.sh && \
    chmod +x /usr/local/bin/setup_user_dir.sh

# Configurar JupyterLab
RUN mkdir -p /home/jovyan/.jupyter && \
    chown -R jovyan:users /home/jovyan/.jupyter

# Ocultar directorio work (renombrarlo con punto para que sea oculto)
RUN if [ -d /home/jovyan/work ]; then mv /home/jovyan/work /home/jovyan/.work; fi

USER jovyan

WORKDIR /home/jovyan

# Configuración por defecto de JupyterLab
ENV JUPYTER_ENABLE_LAB=yes
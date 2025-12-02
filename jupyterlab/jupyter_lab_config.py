# Configuración para JupyterLab
c.ServerApp.allow_origin = '*'
c.ServerApp.allow_credentials = True
c.ServerApp.allow_root = True
c.ServerApp.allow_remote_access = True

# Deshabilitar autenticación nativa de Jupyter
c.ServerApp.token = ''
c.ServerApp.password = ''

# Configuraciones de seguridad
c.ServerApp.disable_check_xsrf = False
c.ServerApp.trust_xheaders = True

# Configuración del directorio de trabajo
c.ServerApp.root_dir = '/home/jovyan'

# Configuración importante para proxy
c.ServerApp.base_url = '/'
c.ServerApp.default_url = '/lab'

# Extensiones habilitadas
c.ServerApp.jpserver_extensions = {
    'jupyterlab': True,
    'jupyterlab_git': True,
    'jupyterlab_lsp': True,
    'nbdime': True,
}
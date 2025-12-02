"""
auth/app.py
Servicio de autenticación simple para PE-CTIC
Gestiona usuarios y genera tokens para JupyterLab
"""
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta

import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)  # Sesión expira en 8 horas
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
# Configuración para trabajar detrás de nginx con prefijo /pe-ctic/
# Las cookies se establecerán con path /pe-ctic/ para que funcionen con auth_request
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

USERS_FILE = '/app/users_data/users.json'
TOKENS_FILE = '/app/users_data/tokens.json'

def ensure_directory(filepath):
    """Asegurar que el directorio existe con permisos correctos"""
    directory = os.path.dirname(filepath)
    os.makedirs(directory, exist_ok=True)
    try:
        os.chmod(directory, 0o755)
    except:
        pass
    
    if os.path.exists(filepath) and os.path.isdir(filepath):
        print(f"⚠️  Convirtiendo directorio a archivo: {filepath}")
        # Mover el contenido si existe
        temp_dir = filepath + "_old"
        os.rename(filepath, temp_dir)
        # Crear el archivo
        with open(filepath, 'w') as f:
            f.write('{}')
        os.chmod(filepath, 0o644)
        
def load_users():
    """Cargar usuarios desde archivo"""
    ensure_directory(USERS_FILE)
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error cargando usuarios: {e}")
            return {}
    
    # Usuario admin por defecto
    default_users = {
        'admin': {
            'password': hash_password('admin'),
            'admin': True,
            'created': datetime.now().isoformat()
        }
    }
    save_users(default_users)
    return default_users

def save_users(users):
    """Guardar usuarios en archivo"""
    ensure_directory(USERS_FILE)
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        os.chmod(USERS_FILE, 0o644)
        print(f"✅ Usuarios guardados en {USERS_FILE}")
    except Exception as e:
        print(f"❌ Error guardando usuarios: {e}")
        raise

def hash_password(password):
    """Hash de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verificar contraseña"""
    return hash_password(password) == hashed

def load_tokens():
    """Cargar tokens activos"""
    ensure_directory(TOKENS_FILE)
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error cargando tokens: {e}")
    return {}

def save_tokens(tokens):
    """Guardar tokens"""
    ensure_directory(TOKENS_FILE)
    try:
        with open(TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        os.chmod(TOKENS_FILE, 0o644)
        print(f"✅ Tokens guardados en {TOKENS_FILE}")
        
        # 🔄 También guardar copia para JupyterLab
        jupyter_tokens_path = '/home/jovyan/.jupyter/tokens.json'
        ensure_directory(jupyter_tokens_path)
        with open(jupyter_tokens_path, 'w') as f:
            json.dump(tokens, f, indent=2)
        os.chmod(jupyter_tokens_path, 0o644)
        
    except Exception as e:
        print(f"❌ Error guardando tokens: {e}")
        raise

def generate_token(username):
    """Generar token único para usuario"""
    tokens = load_tokens()
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        'username': username,
        'created': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(days=30)).isoformat()
    }
    save_tokens(tokens)
    return token

@app.route('/')
def index():
    """Página de login - ahora accesible desde /pe-ctic/"""
    if 'username' in session:
        # Si ya está logueado, redirigir directamente a JupyterLab
        return redirect('/lab')
    
    # Si no está logueado, mostrar formulario de login
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PE-CTIC - Login</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #f5f5f5; }
            .login-container { max-width: 400px; margin: 100px auto; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="card shadow">
                <div class="card-body p-5">
                    <h2 class="text-center mb-4">PE-CTIC</h2>
                    <h5 class="text-center text-muted mb-4">Entorno Estadístico Colaborativo</h5>
                    <form method="POST" action="login">
                        <div class="mb-3">
                            <label class="form-label">Usuario</label>
                            <input type="text" name="username" class="form-control" required autofocus>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Contraseña</label>
                            <input type="password" name="password" class="form-control" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Entrar</button>
                    </form>
                    <hr class="my-4">
                    <div class="text-center">
                        <a href="/pe-ctic/webapp/" class="btn btn-outline-secondary btn-sm">
                            <i class="bi bi-book"></i> Visitar Webapp
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/login', methods=['POST'])
def login():
    """Procesar login"""
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        print(f"🔐 Intento de login: {username}")
        print(f"📝 Headers: {dict(request.headers)}")
        print(f"🍪 Cookies: {request.cookies}")
        print(f"📍 Host: {request.host}")
        print(f"🔗 URL: {request.url}")
        
        users = load_users()
        
        if username in users and verify_password(password, users[username]['password']):
            session['username'] = username
            session['is_admin'] = users[username].get('admin', False)
            session.permanent = True
            print(f"✅ Login exitoso: {username}")
            print(f"🎯 Redirigiendo a /lab")
            
            # Generar token inmediatamente
            token = generate_token(username)
            print(f"🔑 Token generado para {username}")
            
            # Redirigir a JupyterLab
            response = redirect('/lab')
            print(f"🔄 Response headers: {dict(response.headers)}")
            return response
        else:
            print(f"❌ Login fallido: {username}")
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>PE-CTIC - Login</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>body { background: #f5f5f5; } .login-container { max-width: 400px; margin: 100px auto; }</style>
            </head>
            <body>
                <div class="login-container">
                    <div class="card shadow">
                        <div class="card-body p-5">
                            <h2 class="text-center mb-4">PE-CTIC</h2>
                            <div class="alert alert-danger">Usuario o contraseña incorrectos</div>
                            <form method="POST" action="login">
                                <div class="mb-3">
                                    <label class="form-label">Usuario</label>
                                    <input type="text" name="username" class="form-control" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Contraseña</label>
                                    <input type="password" name="password" class="form-control" required>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Entrar</button>
                            </form>
                            <hr class="my-4">
                            <div class="text-center">
                                <p class="text-muted mb-2">¿Quieres ver los notebooks compartidos?</p>
                                <a href="/pe-ctic/webapp/" class="btn btn-outline-secondary btn-sm">
                                    <i class="bi bi-book"></i> Visitar Webapp
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            ''', error="Usuario o contraseña incorrectos"), 401
            
    except Exception as e:
        print(f"💥 Error en login: {e}")
        return f"Error interno del servidor: {e}", 500

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    if 'username' in session:
        username = session['username']
        session.clear()
        print(f"🔒 Logout exitoso: {username}")
        
    return redirect('/pe-ctic/')

@app.route('/api/verify-session', methods=['GET'])
def verify_session():
    """Verificar sesión activa (usado por nginx auth_request)"""
    # Este endpoint es llamado por nginx antes de permitir acceso a JupyterLab
    # Nginx pasa las cookies automáticamente, así que Flask puede leer la sesión
    try:
        if 'username' in session:
            # Sesión válida - retornar 200
            response = app.response_class('', status=200)
            response.headers['X-User'] = session.get('username', '')
            return response
        else:
            # No hay sesión válida - retornar 401
            return '', 401
    except Exception as e:
        print(f"❌ Error verificando sesión: {e}")
        return '', 401

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """Verificar token (usado por JupyterLab)"""
    data = request.json
    token = data.get('token', '')
    
    tokens = load_tokens()
    if token in tokens:
        token_info = tokens[token]
        # Verificar expiración
        expires = datetime.fromisoformat(token_info['expires'])
        if datetime.now() < expires:
            return jsonify({
                'valid': True,
                'username': token_info['username']
            })
    
    return jsonify({'valid': False}), 401

@app.route('/api/users', methods=['GET'])
def list_users():
    """Listar usuarios (solo admin)"""
    if 'username' not in session or not session.get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    users = load_users()
    return jsonify({
        'users': {user: {'admin': info.get('admin', False)} for user, info in users.items()}
    })

@app.route('/admin')
def admin_panel():
    """Panel de administración"""
    if 'username' not in session or not session.get('is_admin'):
        return redirect('/')
    
    with open('/app/admin.html', 'r') as f:
        return f.read()

@app.route('/api/users', methods=['POST'])
def add_user():
    """Añadir usuario (solo admin)"""
    if 'username' not in session or not session.get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    is_admin = data.get('admin', False)
    
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
    
    users = load_users()
    users[username] = {
        'password': hash_password(password),
        'admin': is_admin,
        'created': datetime.now().isoformat()
    }
    save_users(users)
    
    # Crear directorio del usuario automáticamente
    # En el contenedor auth, el volumen users está montado en /app/users
    user_dir = f'/app/users/{username}'
    try:
        os.makedirs(user_dir, exist_ok=True)
        os.chmod(user_dir, 0o755)
        
        # Crear archivo BIENVENIDO.txt con mensaje personalizado
        welcome_file = os.path.join(user_dir, 'BIENVENIDO.txt')
        welcome_message = f"""¡Bienvenido/a, {username}!

Este es tu directorio personal en el entorno colaborativo PE-CTIC.

📁 Estructura del entorno:
  - shared/          : Recursos compartidos (datos, scripts, notebooks)
  - users/{username}/ : Tu directorio personal (aquí estás)

💡 Instrucciones rápidas:
  1. Crea tus notebooks y scripts en /shared/notebooks/ y /shared/scripts/
  2. Añade los encabezados pertinentes de los metadatados de cada notebook 
  3. Puedes meter datos compartidos en /shared/data/
  4. Visita la webapp (http://chomsky/pe-ctic/webapp/) para ver todo el repositorio
  5. Todos los usuarios pueden ver y colaborar en los directorios
  6. Usa tu directorio personal para guardar y usar lo que quieras

⚠️ IMPORTANTE: Evita espacios y caracteres especiales en nombres de archivos y rutas.
   Usa guiones bajos (_) o guiones (-) en lugar de espacios para evitar problemas.

PE-CTIC - Píldoras de Estadística de CTIC
"""
        with open(welcome_file, 'w', encoding='utf-8') as f:
            f.write(welcome_message)
        os.chmod(welcome_file, 0o644)
        print(f"✓ Directorio creado: {user_dir}")
        print(f"✓ Archivo BIENVENIDO.txt creado")
    except Exception as e:
        print(f"⚠️ Error creando directorio {user_dir}: {e}")
        # Intentar también desde el host si es necesario
        try:
            import subprocess
            subprocess.run(['mkdir', '-p', user_dir], check=True)
            subprocess.run(['chmod', '755', user_dir], check=True)
            # Crear archivo BIENVENIDO.txt
            welcome_file = os.path.join(user_dir, 'BIENVENIDO.txt')
            welcome_message = f"""¡Bienvenido/a, {username}!

Este es tu directorio personal en el entorno colaborativo PE-CTIC.

📁 Estructura del entorno:
  - shared/          : Recursos compartidos (datos, scripts, notebooks)
  - users/{username}/ : Tu directorio personal (aquí estás)

💡 Instrucciones rápidas:
  1. Crea tus notebooks y scripts en /shared/notebooks/ y /shared/scripts/
  2. Añade los encabezados pertinentes de los metadatados de cada notebook 
  3. Puedes meter datos compartidos en /shared/data/
  4. Visita la webapp (http://chomsky/pe-ctic/webapp/) para ver todo el repositorio
  5. Todos los usuarios pueden ver y colaborar en los directorios
  6. Usa tu directorio personal para guardar y usar lo que quieras

⚠️ IMPORTANTE: Evita espacios y caracteres especiales en nombres de archivos y rutas.
   Usa guiones bajos (_) o guiones (-) en lugar de espacios para evitar problemas.

PE-CTIC - Píldoras de Estadística de CTIC
"""
            with open(welcome_file, 'w', encoding='utf-8') as f:
                f.write(welcome_message)
            subprocess.run(['chmod', '644', welcome_file], check=True)
            print(f"✓ Directorio creado (vía subprocess): {user_dir}")
            print(f"✓ Archivo BIENVENIDO.txt creado")
        except Exception as subprocess_error:
            print(f"⚠️ Error en subprocess: {subprocess_error}")
    
    return jsonify({'success': True, 'message': f'Usuario {username} creado'})

@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    """Eliminar usuario (solo admin)"""
    if 'username' not in session or not session.get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return jsonify({'success': True, 'message': f'Usuario {username} eliminado'})
    
    return jsonify({'error': 'Usuario no encontrado'}), 404

@app.route('/session-expired')
def session_expired():
    """Página cuando la sesión ha expirado"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PE-CTIC - Sesión Expirada</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #f5f5f5; }
            .expired-container { max-width: 400px; margin: 100px auto; }
        </style>
    </head>
    <body>
        <div class="expired-container">
            <div class="card shadow">
                <div class="card-body p-5 text-center">
                    <h2 class="text-center mb-4">PE-CTIC</h2>
                    <div class="alert alert-warning">
                        <h4>⏰ Sesión Expirada</h4>
                        <p>Tu sesión ha expirado por inactividad.</p>
                    </div>
                    <a href="/" class="btn btn-primary">Iniciar Sesión Nuevamente</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')
    
if __name__ == '__main__':
    ensure_directory(USERS_FILE)
    ensure_directory(TOKENS_FILE)
    print("🚀 Servicio de autenticación iniciado")
    app.run(host='0.0.0.0', port=5000, debug=True)

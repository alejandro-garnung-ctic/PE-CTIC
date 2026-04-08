"""
auth/app.py
Servicio de autenticación PE-CTIC: sesión Flask + tokens JupyterLab.
Login contra LDAP / Active Directory (misma configuración base que EmilIA).
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import subprocess
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, render_template_string, request, session

import ldap_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

TOKENS_FILE = "/app/users_data/tokens.json"

# Nombres cortos LDAP (sin dominio), separados por comas — acceso a /admin
def _admin_usernames() -> set[str]:
    raw = os.getenv("PE_CTIC_ADMIN_USERNAMES", "").strip()
    if not raw:
        return set()
    return {x.strip().casefold() for x in raw.split(",") if x.strip()}


def user_is_admin(username: str) -> bool:
    return username.strip().casefold() in _admin_usernames()


def ensure_directory(filepath: str) -> None:
    directory = os.path.dirname(filepath)
    os.makedirs(directory, exist_ok=True)
    try:
        os.chmod(directory, 0o755)
    except OSError:
        pass


def ensure_user_workspace(username: str) -> None:
    """Crea /app/users/{username} y BIENVENIDO.txt si no existen (volumen compartido)."""
    user_dir = f"/app/users/{username}"
    welcome_file = os.path.join(user_dir, "BIENVENIDO.txt")
    welcome_message = f"""¡Bienvenido/a, {username}!

Este es tu directorio personal en el entorno colaborativo PE-CTIC.

📁 Estructura del entorno:
  - shared/          : Recursos compartidos (datos, scripts, notebooks)
  - users/{username}/ : Tu directorio personal (aquí estás)

💡 Instrucciones rápidas:
  1. Crea tus notebooks y scripts en /shared/notebooks/ y /shared/scripts/
  2. Añade los encabezados pertinentes de los metadatados de cada notebook
  3. Puedes meter datos compartidos en /shared/data/
  4. Visita la webapp para ver el repositorio de notebooks compartidos
  5. Todos los usuarios pueden ver y colaborar en los directorios
  6. Usa tu directorio personal para guardar y usar lo que quieras

⚠️ IMPORTANTE: Evita espacios y caracteres especiales en nombres de archivos y rutas.
   Usa guiones bajos (_) o guiones (-) en lugar de espacios para evitar problemas.

PE-CTIC - Píldoras de Estadística de CTIC
"""
    try:
        os.makedirs(user_dir, exist_ok=True)
        os.chmod(user_dir, 0o755)
        if not os.path.isfile(welcome_file):
            with open(welcome_file, "w", encoding="utf-8") as f:
                f.write(welcome_message)
            os.chmod(welcome_file, 0o644)
        logger.info("Directorio usuario listo: %s", user_dir)
    except OSError as exc:
        logger.warning("No se pudo crear directorio %s: %s", user_dir, exc)
        try:
            subprocess.run(["mkdir", "-p", user_dir], check=True)
            subprocess.run(["chmod", "755", user_dir], check=True)
            if not os.path.isfile(welcome_file):
                with open(welcome_file, "w", encoding="utf-8") as f:
                    f.write(welcome_message)
                subprocess.run(["chmod", "644", welcome_file], check=True)
        except (OSError, subprocess.CalledProcessError) as exc2:
            logger.warning("Fallback subprocess directorio usuario: %s", exc2)


def load_tokens() -> dict:
    ensure_directory(TOKENS_FILE)
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Error cargando tokens: %s", e)
    return {}


def save_tokens(tokens: dict) -> None:
    ensure_directory(TOKENS_FILE)
    try:
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(TOKENS_FILE, 0o644)
    except OSError as e:
        logger.error("Error guardando tokens: %s", e)
        raise
    jupyter_tokens_path = "/home/jovyan/.jupyter/tokens.json"
    try:
        ensure_directory(jupyter_tokens_path)
        with open(jupyter_tokens_path, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(jupyter_tokens_path, 0o644)
    except OSError as e:
        logger.debug(
            "No se escribió tokens en Jupyter (normal en contenedor auth solo): %s", e
        )


def generate_token(username: str) -> str:
    tokens = load_tokens()
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        "username": username,
        "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(days=30)).isoformat(),
    }
    save_tokens(tokens)
    return token


# --- Plantillas HTML (mismo aspecto Bootstrap que antes) ---

INDEX_HTML = """
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
    """

LOGIN_FAIL_HTML = """
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
            """

SESSION_EXPIRED_HTML = """
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
    """


@app.route("/")
def index():
    if "username" in session:
        return redirect("/lab")
    return render_template_string(INDEX_HTML)


@app.route("/login", methods=["POST"])
def login():
    try:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        logger.info("Intento de login LDAP: %s", username)

        if not ldap_auth.ldap_configured():
            logger.error("LDAP no configurado")
            return "Error de configuración del servidor (LDAP).", 503

        try:
            profile = ldap_auth.ldap_authenticate_and_profile(username, password)
        except ValueError:
            logger.info("Login LDAP rechazado: %s", username)
            return render_template_string(LOGIN_FAIL_HTML), 401
        except RuntimeError as exc:
            logger.exception("LDAP error: %s", exc)
            return f"Error de conexión con el directorio: {exc}", 503

        uname = profile["username"]
        session["username"] = uname
        session["is_admin"] = user_is_admin(uname)
        session.permanent = True
        ensure_user_workspace(uname)
        generate_token(uname)
        logger.info("Login LDAP OK: %s (admin=%s)", uname, session["is_admin"])
        return redirect("/lab")

    except Exception as e:
        logger.exception("Error en login: %s", e)
        return f"Error interno del servidor: {e}", 500


@app.route("/logout")
def logout():
    if "username" in session:
        logger.info("Logout: %s", session["username"])
        session.clear()
    return redirect("/pe-ctic/")


@app.route("/api/verify-session", methods=["GET"])
def verify_session():
    try:
        if "username" in session:
            response = app.response_class("", status=200)
            response.headers["X-User"] = session.get("username", "")
            return response
        return "", 401
    except Exception as e:
        logger.error("verify-session: %s", e)
        return "", 401


@app.route("/api/verify-token", methods=["POST"])
def verify_token():
    data = request.json or {}
    token = data.get("token", "")
    tokens = load_tokens()
    if token in tokens:
        token_info = tokens[token]
        expires = datetime.fromisoformat(token_info["expires"])
        if datetime.now() < expires:
            return jsonify({"valid": True, "username": token_info["username"]})
    return jsonify({"valid": False}), 401


@app.route("/api/users", methods=["GET"])
def list_users():
    """Ya no hay usuarios locales; la tabla admin queda vacía o solo informativa."""
    if "username" not in session or not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403
    return jsonify({"users": {}, "auth": "ldap"})


@app.route("/admin")
def admin_panel():
    if "username" not in session or not session.get("is_admin"):
        return redirect("/")
    with open("/app/admin.html", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/users", methods=["POST"])
def add_user():
    if "username" not in session or not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403
    return (
        jsonify(
            {
                "error": "Los usuarios se gestionan en Active Directory (LDAP). "
                "No se pueden crear cuentas desde este panel."
            }
        ),
        403,
    )


@app.route("/api/users/<username>", methods=["DELETE"])
def delete_user(username):
    if "username" not in session or not session.get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403
    _ = username
    return (
        jsonify(
            {
                "error": "Las cuentas son del directorio LDAP; no se eliminan desde aquí."
            }
        ),
        403,
    )


@app.route("/session-expired")
def session_expired():
    return render_template_string(SESSION_EXPIRED_HTML)


if __name__ == "__main__":
    ensure_directory(TOKENS_FILE)
    if not ldap_auth.ldap_configured():
        logger.warning(
            "LDAP_* no definidos; se usan valores por defecto (Castor / fundacionctic.org)."
        )
    logger.info("Servicio de autenticación PE-CTIC (LDAP) iniciado")
    app.run(host="0.0.0.0", port=5000, debug=True)

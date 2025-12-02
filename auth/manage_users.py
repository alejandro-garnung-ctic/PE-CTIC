#!/usr/bin/env python3
"""
Script para gestionar usuarios desde línea de comandos
"""
import sys
import os
import json
import hashlib
import argparse

USERS_FILE = '/app/users_data/users.json'

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Gestionar usuarios de PE-CTIC')
    parser.add_argument('action', choices=['add', 'remove', 'list', 'change-password'])
    parser.add_argument('--username', '-u', help='Nombre de usuario')
    parser.add_argument('--password', '-p', help='Contraseña')
    parser.add_argument('--admin', action='store_true', help='Usuario administrador')
    
    args = parser.parse_args()
    
    users = load_users()
    
    if args.action == 'add':
        if not args.username:
            print("Error: Se requiere --username")
            sys.exit(1)
        if not args.password:
            print("Error: Se requiere --password")
            sys.exit(1)
        users[args.username] = {
            'password': hash_password(args.password),
            'admin': args.admin,
            'created': __import__('datetime').datetime.now().isoformat()
        }
        save_users(users)
        
        # Crear directorio del usuario automáticamente
        # En el contenedor auth, el volumen users está montado en /app/users
        user_dir = f'/app/users/{args.username}'
        try:
            os.makedirs(user_dir, exist_ok=True)
            os.chmod(user_dir, 0o755)
            
            # Crear archivo BIENVENIDO.txt con mensaje personalizado
            welcome_file = os.path.join(user_dir, 'BIENVENIDO.txt')
            welcome_message = f"""¡Bienvenido/a, {args.username}!

Este es tu directorio personal en el entorno colaborativo PE-CTIC.

📁 Estructura del entorno:
  - shared/          : Recursos compartidos (datos, scripts, notebooks)
  - users/{args.username}/ : Tu directorio personal (aquí estás)

💡 Instrucciones rápidas:
  1. Crea tus notebooks y scripts en /shared/notebooks/ y /shared/scripts/
  2. Añade los encabezados pertinentes de los metadatados de cada notebook 
  3. Puedes meter datos compartidos en /shared/data/
  4. Visita la webapp (http://chomsky/pe-ctic/webapp/) para ver todo el repositorio
  5. Todos los usuarios pueden ver y colaborar en los directorios
  6. Usa tu directorio personal para guardar y usar lo que quieras

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
                welcome_message = f"""¡Bienvenido/a, {args.username}!

Este es tu directorio personal en el entorno colaborativo PE-CTIC.

📁 Estructura del entorno:
  - shared/          : Recursos compartidos (datos, scripts, notebooks)
  - users/{args.username}/ : Tu directorio personal (aquí estás)

💡 Instrucciones rápidas:
  1. Crea tus notebooks y scripts en /shared/notebooks/ y /shared/scripts/
  2. Añade los encabezados pertinentes de los metadatados de cada notebook 
  3. Puedes meter datos compartidos en /shared/data/
  4. Visita la webapp (http://chomsky/pe-ctic/webapp/) para ver todo el repositorio
  5. Todos los usuarios pueden ver y colaborar en los directorios
  6. Usa tu directorio personal para guardar y usar lo que quieras

PE-CTIC - Píldoras de Estadística de CTIC
"""
                with open(welcome_file, 'w', encoding='utf-8') as f:
                    f.write(welcome_message)
                subprocess.run(['chmod', '644', welcome_file], check=True)
                print(f"✓ Directorio creado (vía subprocess): {user_dir}")
                print(f"✓ Archivo BIENVENIDO.txt creado")
            except Exception as subprocess_error:
                print(f"⚠️ Error en subprocess: {subprocess_error}")
        
        print(f"Usuario '{args.username}' creado")
        if args.admin:
            print("  (Usuario administrador)")
    
    elif args.action == 'remove':
        if not args.username:
            print("Error: Se requiere --username")
            sys.exit(1)
        if args.username in users:
            del users[args.username]
            save_users(users)
            print(f"Usuario '{args.username}' eliminado")
        else:
            print(f"Usuario '{args.username}' no existe")
            sys.exit(1)
    
    elif args.action == 'list':
        if users:
            print("Usuarios:")
            for username, info in users.items():
                admin_str = " (admin)" if info.get('admin') else ""
                print(f"  - {username}{admin_str}")
        else:
            print("No hay usuarios")
    
    elif args.action == 'change-password':
        if not args.username:
            print("Error: Se requiere --username")
            sys.exit(1)
        if not args.password:
            print("Error: Se requiere --password")
            sys.exit(1)
        if args.username not in users:
            print(f"Usuario '{args.username}' no existe")
            sys.exit(1)
        users[args.username]['password'] = hash_password(args.password)
        save_users(users)
        print(f"Contraseña de '{args.username}' actualizada")

if __name__ == '__main__':
    main()

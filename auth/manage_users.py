#!/usr/bin/env python3
"""
Herramienta informativa (antes: usuarios locales con contraseña en JSON).

El acceso a PE-CTIC es por LDAP / Active Directory (misma configuración base
que EmilIA: variables LDAP_* y UPN). Las cuentas se gestionan en el directorio;
no se añaden usuarios desde este script.

Administradores del panel /admin: variable de entorno PE_CTIC_ADMIN_USERNAMES
(nombres cortos LDAP, separados por comas).

Ver auth/ldap_auth.py y docker-compose del proyecto.
"""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PE-CTIC: autenticación LDAP (sin gestión local de contraseñas)."
    )
    parser.add_argument(
        "legacy",
        nargs="*",
        help="Ignorado; use la documentación del README",
    )
    _ = parser.parse_args()

    print(
        "PE-CTIC usa LDAP (Active Directory). No hay usuarios/contraseñas en users.json.\n"
        "• Login: usuario y contraseña del directorio corporativo.\n"
        "• Admins (ruta /admin): PE_CTIC_ADMIN_USERNAMES en docker-compose.\n"
        "• LDAP: LDAP_SERVER_URI, LDAP_BASE_DN, LDAP_USER_UPN_SUFFIX (ver EmilIA / picture-uploader).\n",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

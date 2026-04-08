"""Autenticación LDAP / Active Directory (misma lógica que EmilIA picture-uploader)."""

from __future__ import annotations

import logging
import os
from typing import Any

from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPException
from ldap3.utils.conv import escape_filter_chars

logger = logging.getLogger(__name__)

_DEFAULT_LDAP_URI = "ldap://castor.fundacionctic.org:3268"
_DEFAULT_BASE_DN = "dc=fundacionctic,dc=org"
_DEFAULT_UPN_SUFFIX = "@fundacionctic.org"


def _env_or_default(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    stripped = raw.strip()
    return stripped if stripped else default


LDAP_SERVER_URI = _env_or_default("LDAP_SERVER_URI", _DEFAULT_LDAP_URI)
LDAP_BASE_DN = _env_or_default("LDAP_BASE_DN", _DEFAULT_BASE_DN)
LDAP_USER_UPN_SUFFIX = _env_or_default("LDAP_USER_UPN_SUFFIX", _DEFAULT_UPN_SUFFIX)
_sf = os.getenv("LDAP_USER_SEARCH_FILTER", "").strip()
LDAP_USER_SEARCH_FILTER = _sf if _sf else "(userPrincipalName={upn})"


def ldap_configured() -> bool:
    return bool(LDAP_SERVER_URI and LDAP_BASE_DN and LDAP_USER_UPN_SUFFIX)


def _entry_attr(entry: Any, name: str) -> str:
    if name not in entry:
        return ""
    attr = entry[name]
    if attr is None:
        return ""
    v = attr.value
    if v is None:
        return ""
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v).strip()


def ldap_authenticate_and_profile(username: str, password: str) -> dict[str, Any]:
    """Bind UPN + lectura de atributos (givenName, sn, mail, etc.)."""
    if not ldap_configured():
        raise RuntimeError(
            "LDAP no configurado (LDAP_SERVER_URI, LDAP_BASE_DN, LDAP_USER_UPN_SUFFIX)"
        )

    user_clean = username.strip()
    if not user_clean or not password:
        raise ValueError("Usuario y contraseña requeridos")

    upn = f"{user_clean}{LDAP_USER_UPN_SUFFIX}"
    filt = LDAP_USER_SEARCH_FILTER.format(
        username=escape_filter_chars(user_clean),
        upn=escape_filter_chars(upn),
    )

    server = Server(LDAP_SERVER_URI, get_info=ALL)
    try:
        conn = Connection(server, user=upn, password=password, auto_bind=True)
    except LDAPBindError as exc:
        raise ValueError("Credenciales incorrectas") from exc
    except LDAPException as exc:
        raise RuntimeError(f"LDAP: {exc}") from exc

    name = user_clean
    last_name = ""
    email = ""

    try:
        conn.search(
            LDAP_BASE_DN,
            filt,
            search_scope=SUBTREE,
            attributes=["givenName", "sn", "displayName", "mail", "cn"],
        )
        if conn.entries:
            entry = conn.entries[0]
            mail_v = _entry_attr(entry, "mail")
            cn_v = _entry_attr(entry, "cn")
            sn_v = _entry_attr(entry, "sn")
            display_v = _entry_attr(entry, "displayName")
            given = _entry_attr(entry, "givenName")
            logger.debug(
                "LDAP ok user=%s mail=%s cn=%s sn=%s displayName=%s givenName=%s",
                user_clean,
                mail_v,
                cn_v,
                sn_v,
                display_v,
                given,
            )
            if given or sn_v:
                name = given or user_clean
                last_name = sn_v
            else:
                disp = display_v or cn_v
                if disp:
                    parts = disp.split(None, 1)
                    name = parts[0]
                    last_name = parts[1] if len(parts) > 1 else ""
            email = mail_v
        else:
            logger.warning("LDAP bind OK pero sin entrada para el filtro: %s", user_clean)
    finally:
        conn.unbind()

    return {
        "username": user_clean,
        "name": name,
        "lastName": last_name,
        "email": email or "no email",
    }


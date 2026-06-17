import hashlib
import json
import os
import secrets

import streamlit as st


USER_STORE_FILE = os.path.join(os.path.dirname(__file__), "users.json")
PBKDF2_ITERATIONS = 120000

ROLE_LABELS = {
    "tecnico": "Técnico",
    "admin": "Administrador",
    "ingeniero_jefe": "Ingeniero en Jefe",
}

DEFAULT_USERS = [
    {
        "username": "tecnico1",
        "display_name": "Técnico de Planta",
        "role": "tecnico",
        "password": "Tecnico123!",
    },
    {
        "username": "admin",
        "display_name": "Administrador",
        "role": "admin",
        "password": "Admin123!",
    },
    {
        "username": "jefe",
        "display_name": "Ingeniero en Jefe",
        "role": "ingeniero_jefe",
        "password": "Jefe123!",
    },
]


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()


def _normalize_role(role):
    if role == "ingeniero":
        return "ingeniero_jefe"
    return role


def _serialize_user(user):
    salt = secrets.token_hex(16)
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "role": _normalize_role(user["role"]),
        "salt": salt,
        "password_hash": _hash_password(user["password"], salt),
        "active": True,
    }


def ensure_user_store():
    if os.path.exists(USER_STORE_FILE):
        return

    store = {
        "version": 1,
        "users": [_serialize_user(user) for user in DEFAULT_USERS],
    }
    with open(USER_STORE_FILE, "w", encoding="utf-8") as file:
        json.dump(store, file, indent=2, ensure_ascii=False)


def load_users():
    ensure_user_store()

    with open(USER_STORE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        users = data
    else:
        users = data.get("users", [])

    normalized_users = []
    for user in users:
        normalized_users.append(
            {
                "username": user.get("username", "").strip(),
                "display_name": user.get("display_name", user.get("name", "Usuario")).strip(),
                "role": _normalize_role(user.get("role", "tecnico")),
                "salt": user.get("salt", ""),
                "password_hash": user.get("password_hash", ""),
                "active": bool(user.get("active", True)),
            }
        )

    return normalized_users


def get_role_label(role):
    return ROLE_LABELS.get(role, role.replace("_", " ").title())


def authenticate(username, password):
    username = username.strip().lower()
    for user in load_users():
        if not user["active"]:
            continue
        if user["username"].lower() != username:
            continue
        if not user["salt"] or not user["password_hash"]:
            continue

        expected_hash = _hash_password(password, user["salt"])
        if secrets.compare_digest(expected_hash, user["password_hash"]):
            return {
                "username": user["username"],
                "display_name": user["display_name"],
                "role": user["role"],
            }

    return None


def ensure_auth_state():
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None


def logout():
    st.session_state.auth_user = None


def login_form(app_name="HidroMira"):
    st.markdown(f"## {app_name}")
    st.write("Ingresa con tu usuario y contraseña para continuar.")

    with st.form("auth_login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.auth_user = user
            st.rerun()
        st.error("Credenciales inválidas o usuario inactivo.")

    st.caption("La contraseña se almacena con hash local en users.json.")


def require_login(app_name="HidroMira"):
    ensure_auth_state()

    if st.session_state.auth_user:
        return st.session_state.auth_user

    login_form(app_name=app_name)
    st.stop()


def render_user_panel():
    ensure_auth_state()
    user = st.session_state.auth_user
    if not user:
        return

    with st.sidebar:
        st.markdown("### Sesión activa")
        st.write(user["display_name"])
        st.caption(f"Rol: {get_role_label(user['role'])}")
        if st.button("Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()


def has_role(user, allowed_roles):
    if not allowed_roles:
        return True
    return user and user.get("role") in allowed_roles


def require_role(user, allowed_roles, message=None):
    if has_role(user, allowed_roles):
        return True

    st.error(message or "No tienes permisos para acceder a esta sección.")
    st.stop()

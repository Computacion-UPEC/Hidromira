import hashlib
import json
import os
import secrets
import db

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
        "email": "ggeta13basantes@gmail.com",
        "password": "Tecnico123!",
    },
    {
        "username": "admin",
        "display_name": "Administrador",
        "role": "admin",
        "email": "ggeta13basantes@gmail.com",
        "password": "Admin123!",
    },
    {
        "username": "jefe",
        "display_name": "Ingeniero en Jefe",
        "role": "ingeniero_jefe",
        "email": "geovanny.basantesq@gmail.com",
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
        "email": user.get("email", "").strip(),
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
    return db.load_users()


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


import random
import string

def recuperar_password(username, email):
    username = username.strip().lower()
    email = email.strip().lower()

    # Importar iot_config en caliente para evitar problemas de importación circular
    try:
        import iot_config
        IOT_CONFIG_AVAILABLE = True
    except ImportError:
        iot_config = None
        IOT_CONFIG_AVAILABLE = False

    users = load_users()
    user_found = None
    for u in users:
        if u["username"].lower() == username and u["email"].lower() == email:
            user_found = u
            break

    if not user_found:
        return False, "Usuario o correo electrónico no coinciden."

    # Generar contraseña temporal
    caracteres = string.ascii_letters + string.digits + "!@#$"
    temp_pass = ''.join(random.choice(caracteres) for _ in range(8))

    # Hashear y actualizar
    salt = secrets.token_hex(16)
    user_found["salt"] = salt
    user_found["password_hash"] = _hash_password(temp_pass, salt)

    try:
        db.save_users(users)
    except Exception as e:
        return False, f"Error al actualizar la base de datos: {e}"

    # Enviar correo electrónico
    if not IOT_CONFIG_AVAILABLE or not getattr(iot_config, 'EMAIL_ENABLED', False):
        return True, f"🔑 (Modo pruebas/sin SMTP) Tu contraseña temporal es: **{temp_pass}**"

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = iot_config.EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = "🔑 [HidroMira] Recuperación de Contraseña"

        cuerpo_html = f"""
        <html>
        <body style='font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;'>
            <div style='max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 25px; border-top: 5px solid #2563eb;'>
                <h2 style='color: #2563eb;'>Recuperación de Contraseña - HidroMira</h2>
                <p>Hola <strong>{user_found['display_name']}</strong>,</p>
                <p>Se ha solicitado la restauración de tu contraseña para el panel HidroMira.</p>
                <p>Tu contraseña temporal de acceso es:</p>
                <div style='background-color: #f3f4f6; padding: 15px; border-radius: 5px; text-align: center; font-size: 20px; font-weight: bold; letter-spacing: 1px; color: #1e293b; margin: 20px 0;'>
                    {temp_pass}
                </div>
                <p style='color: #ef4444; font-weight: bold;'>Por favor, inicia sesión y cambia esta contraseña lo antes posible por seguridad.</p>
                <hr style='border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0;'>
                <p style='font-size: 12px; color: #6b7280; text-align: center;'>Sistema HidroMira - Control de Turbina</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(cuerpo_html, 'html'))

        server = smtplib.SMTP(iot_config.EMAIL_SMTP_SERVER, iot_config.EMAIL_SMTP_PORT)
        server.starttls()
        server.login(iot_config.EMAIL_FROM, iot_config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Se ha enviado una contraseña temporal a su correo electrónico."
    except Exception as e:
        return True, f"⚠️ Error de envío SMTP ({e}). Contraseña temporal: **{temp_pass}**"


def login_form(app_name="HidroMira"):
    st.markdown(f"## {app_name}")

    if "recovery_mode" not in st.session_state:
        st.session_state.recovery_mode = False

    if st.session_state.recovery_mode:
        st.subheader("🔑 Recuperar Contraseña")
        st.write("Ingresa tu usuario y el correo registrado para recibir una contraseña temporal.")
        
        with st.form("auth_recovery_form"):
            rec_username = st.text_input("Usuario")
            rec_email = st.text_input("Correo electrónico")
            submitted_rec = st.form_submit_button("Enviar contraseña temporal")
            
        if submitted_rec:
            if rec_username and rec_email:
                ok, msg = recuperar_password(rec_username, rec_email)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Por favor, completa todos los campos.")
                
        if st.button("Volver al Inicio de Sesión", use_container_width=True):
            st.session_state.recovery_mode = False
            st.rerun()
    else:
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

        if st.button("¿Olvidaste tu contraseña?", use_container_width=True):
            st.session_state.recovery_mode = True
            st.rerun()

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

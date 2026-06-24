import json
import secrets
import hashlib
import os
import sys

# Ruta al archivo users.json
USER_STORE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users.json")
PBKDF2_ITERATIONS = 120000

def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()

def main():
    print("🔑 REGENERADOR DE CONTRASEÑA DE ADMINISTRADOR - HIDROMIRA")
    print("="*60)
    
    # En entornos no interactivos
    if not sys.stdin.isatty():
        nueva_clave = "Admin123!"
        print(f"Entorno no interactivo detectado. Restableciendo contraseña por defecto: '{nueva_clave}'")
    else:
        nueva_clave = input("Ingresa la nueva contraseña para el usuario 'admin': ").strip()
        
    if not nueva_clave:
        print("❌ La contraseña no puede estar vacía.")
        return
        
    if not os.path.exists(USER_STORE_FILE):
        print(f"❌ No se encontró el archivo: {USER_STORE_FILE}")
        return
        
    try:
        with open(USER_STORE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            
        encontrado = False
        for user in data["users"]:
            if user["username"] == "admin":
                salt = secrets.token_hex(16)
                user["salt"] = salt
                user["password_hash"] = _hash_password(nueva_clave, salt)
                user["active"] = True
                encontrado = True
                break
                
        if encontrado:
            db_updated = False
            try:
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                import db
                if db.DB_ENABLED:
                    db.save_users(data["users"])
                    db_updated = True
            except Exception as e:
                print(f"Aviso: No se pudo actualizar en PostgreSQL: {e}")

            with open(USER_STORE_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            print(f"\nExito: Contraseña del usuario 'admin' actualizada exitosamente!")
            print(f"   Usuario: admin")
            print(f"   Contraseña: {nueva_clave}")
            if db_updated:
                print("   (Tambien se sincronizo correctamente en PostgreSQL)")
        else:
            print("❌ No se encontró el usuario 'admin' en el archivo users.json.")
            
    except Exception as e:
        print(f"❌ Error al actualizar el archivo: {e}")

if __name__ == "__main__":
    main()

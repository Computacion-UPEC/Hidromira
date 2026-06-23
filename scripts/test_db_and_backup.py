import sys
import os

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import auth

print("--- INICIANDO PRUEBAS DE BASE DE DATOS Y RESPALDOS ---")

# 1. Cargar usuarios
print("\n[1] Probando carga de usuarios...")
try:
    users = db.load_users()
    print(f"Exito. Total usuarios cargados: {len(users)}")
    for u in users:
        print(f"    - Usuario: {u['username']} | Correo: {u.get('email', 'Sin correo')}")
except Exception as e:
    print(f"Error al cargar usuarios: {e}")

# 2. Probar recuperación de contraseña
print("\n[2] Probando recuperación de contraseña (olvido de clave)...")
try:
    # Probar con datos correctos
    ok, msg = auth.recuperar_password("admin", "ggeta13basantes@gmail.com")
    if ok:
        print(f"Exito. {msg}")
    else:
        print(f"Fallo recuperacion: {msg}")
        
    # Probar con datos incorrectos
    ok_fail, msg_fail = auth.recuperar_password("admin", "correo_incorrecto@test.com")
    if not ok_fail:
        print(f"Exito en validacion de error: {msg_fail}")
    else:
        print(f"Fallo validacion de error: Acepto credenciales incorrectas.")
except Exception as e:
    print(f"Error en recuperacion de contrasena: {e}")

# 3. Probar respaldos automáticos/manuales
print("\n[3] Probando sistema de respaldo...")
try:
    ok, msg = db.ejecutar_respaldo("Test Manual Script")
    if ok:
        print(f"Exito. {msg}")
        # Listar directorio de backups
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
        if os.path.exists(backup_dir):
            files = os.listdir(backup_dir)
            print(f"    Archivos creados en backups/:")
            for f in files[-5:]:  # Mostrar los últimos 5
                print(f"      - {f}")
        else:
            print("El directorio de backups no fue creado.")
    else:
        print(f"Fallo el respaldo: {msg}")
except Exception as e:
    print(f"Error en respaldos: {e}")

print("\n--- PRUEBAS FINALIZADAS ---")

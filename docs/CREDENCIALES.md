# 🔑 CREDENCIALES DE ACCESO - HIDROMIRA

Este archivo documenta las credenciales de acceso por defecto para el sistema HidroMira y explica cómo regenerar la contraseña del usuario Administrador en caso de olvido o bloqueo.

---

## 📋 Usuarios y Contraseñas por Defecto

El sistema HidroMira cuenta con tres niveles de acceso preconfigurados en el archivo `users.json`:

| Rol | Usuario | Contraseña | Permisos |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin` | **`Admin123!`** | Acceso total y configuración de red/alertas |
| **Ingeniero en Jefe** | `jefe` | **`Jefe123!`** | Registro de mantenimientos e informes |
| **Técnico de Planta** | `tecnico1` | **`Tecnico123!`** | Monitoreo y control manual de actuadores |

---

## 🛠️ Cómo Regenerar/Cambiar la Contraseña de Administrador

Si cambiaste la contraseña de administrador y la olvidaste, puedes restablecerla ejecutando un script de Python que generará de forma segura el nuevo hash y la sal en `users.json`:

1. Abre tu terminal en la carpeta del proyecto.
2. Ejecuta el script de restablecimiento:
   ```powershell
   .\venv\Scripts\python.exe scripts\reset_admin.py
   ```
3. El script te solicitará que ingreses la nueva contraseña deseada.
4. Escríbela, presiona **Enter** y el archivo `users.json` se actualizará de inmediato de forma encriptada.

---

## 🛡️ Estructura de Seguridad (`users.json`)
Las contraseñas no se guardan en texto plano por seguridad. Se utiliza el algoritmo **PBKDF2 con hash SHA256** y una "sal" aleatoria única por cada usuario, tal como se implementa en el archivo `auth.py`. 

Si necesitas crear usuarios manualmente o desactivarlos, puedes hacerlo modificando la clave `"active": true/false` en dicho archivo.

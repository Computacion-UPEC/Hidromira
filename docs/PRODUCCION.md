# 🚀 Guía y Requisitos para Producción - HidroMira

Este documento resume el estado actual del proyecto HidroMira y los pasos requeridos para su puesta en marcha en un entorno de producción real y seguro.

---

## 📋 Estado Actual del Sistema

1. **Base de Datos con Fallback**: Se diseñó e implementó el adaptador `db.py` compatible con PostgreSQL. Por robustez, si la base de datos no está activa o tiene algún fallo de conexión, el sistema realiza un **fallback automático transparente** a los archivos JSON locales (`users.json`, `historical_data.json`, `maintenance_log.json`).
2. **Copias de Seguridad / Respaldos**:
   - Se implementó un sistema automático que genera respaldos **diarios** en segundo plano al iniciar la aplicación.
   - Se añadió una interfaz en la sección **Datos Técnicos y Mantenimiento** que permite a los operadores generar respaldos manuales inmediatos y visualizar el estado del último respaldo.
   - El sistema de respaldos guarda copias de todos los archivos JSON de configuración/datos y extrae un volcado completo estructurado de las tablas de PostgreSQL.
3. **Recuperación de Contraseñas**: Se integró en la pantalla de logeo la opción de recuperar contraseña mediante el envío automático de una clave temporal por correo electrónico a la dirección registrada de cada usuario.

---

## ⚠️ Lo que le falta al proyecto para producción

Para migrar de este entorno de desarrollo local a un servidor de producción de grado industrial, se deben implementar las siguientes mejoras:

### 1. 🔐 Seguridad y Gestión de Credenciales
- **Variables de Entorno**: Actualmente, las credenciales del servidor de base de datos (`DB_PASSWORD`) y del correo SMTP (`EMAIL_PASSWORD`) están escritas en texto plano en `iot_config.py`. En producción, estas deben cargarse a través de variables de entorno utilizando `os.environ` o un archivo `.env` excluido del control de versiones.
- **Protocolo HTTPS**: Toda la comunicación con el panel de Streamlit debe realizarse a través de HTTPS (SSL/TLS) para cifrar las contraseñas de inicio de sesión de los técnicos y administradores.
- **Forzar Cambio de Contraseña**: Al ingresar con una contraseña temporal generada por el sistema de recuperación, la interfaz debería forzar al usuario a ingresar una contraseña definitiva antes de operar la aplicación.

### 2. 🗄️ Base de Datos y Escalabilidad (PostgreSQL)
- **Conexión en Producción**: Cambiar la bandera `DB_ENABLED = True` en `iot_config.py` y configurar un servidor PostgreSQL dedicado (localmente o administrado en la nube como AWS RDS, Supabase, o DigitalOcean Databases).
- **Pool de Conexiones**: Actualmente, la aplicación abre y cierra conexiones por cada transacción. Para cargas elevadas o múltiples usuarios concurrentes en producción, se recomienda usar un pool de conexiones (como `psycopg2.pool.ThreadedConnectionPool` o SQLAlchemy) para optimizar el rendimiento.
- **Índices en Base de Datos**: Añadir un índice en la columna de marcas de tiempo (`ts`) de la tabla `historical_data` para agilizar las consultas del gráfico de análisis histórico cuando haya millones de lecturas.

### 3. 🌐 Despliegue e Infraestructura
- **Servidor Cloud**: Alojar la aplicación en un Servidor Virtual Privado (VPS) ejecutando Linux (Ubuntu Server).
- **Servicio Systemd**: Configurar la aplicación de Streamlit y el monitor en tiempo real como servicios de `systemd` para que se inicien automáticamente en caso de reinicio del servidor.
- **Proxy Inverso (Nginx)**: Utilizar Nginx como proxy inverso frente a Streamlit para manejar el tráfico web, gestionar los certificados SSL (vía Let's Encrypt) y optimizar el rendimiento.
- **Rotación de Logs**: El archivo `hidromira.log` crece indefinidamente. En producción, se debe configurar `RotatingFileHandler` en el logger de Python para limitar el tamaño de los logs y evitar que saturen el almacenamiento del servidor.

---

## 🛠️ Pasos para activar PostgreSQL en Producción

1. Instala el motor de PostgreSQL en tu servidor.
2. Crea una base de datos llamada `hidromira`.
3. Edita `iot_config.py` y actualiza las credenciales:
   ```python
   DB_ENABLED = True
   DB_HOST = "tuservidor-db.com"
   DB_PORT = 5432
   DB_NAME = "hidromira"
   DB_USER = "usuario_seguro"
   DB_PASSWORD = "password_super_seguro"
   ```
4. Al reiniciar la aplicación, `db.py` detectará las credenciales, creará el esquema de tablas automáticamente e importará los usuarios del archivo `users.json` local por primera y única vez.

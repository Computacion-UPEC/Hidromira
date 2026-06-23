import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("HidroMiraDB")

# Cargar configuración desde iot_config
try:
    import iot_config
    DB_ENABLED = getattr(iot_config, 'DB_ENABLED', False)
    DB_HOST = getattr(iot_config, 'DB_HOST', 'localhost')
    DB_PORT = getattr(iot_config, 'DB_PORT', 5432)
    DB_NAME = getattr(iot_config, 'DB_NAME', 'hidromira')
    DB_USER = getattr(iot_config, 'DB_USER', 'postgres')
    DB_PASSWORD = getattr(iot_config, 'DB_PASSWORD', '')
    IOT_CONFIG_AVAILABLE = True
except ImportError:
    DB_ENABLED = False
    IOT_CONFIG_AVAILABLE = False

def get_connection():
    if not DB_ENABLED:
        return None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=3
        )
        return conn
    except Exception as e:
        logger.warning(f"No se pudo conectar a PostgreSQL ({e}). Se usará el fallback a archivos JSON.")
        return None

def inicializar_tablas():
    conn = get_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            # Crear tabla users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    display_name VARCHAR(100),
                    role VARCHAR(50),
                    email VARCHAR(150),
                    salt VARCHAR(100),
                    password_hash VARCHAR(256),
                    active BOOLEAN DEFAULT TRUE
                );
            """)
            # Crear tabla historical_data
            cur.execute("""
                CREATE TABLE IF NOT EXISTS historical_data (
                    id SERIAL PRIMARY KEY,
                    vx DOUBLE PRECISION,
                    vy DOUBLE PRECISION,
                    vz DOUBLE PRECISION,
                    rms DOUBLE PRECISION,
                    zona VARCHAR(5),
                    ts TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Crear tabla maintenance_log
            cur.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_log (
                    id SERIAL PRIMARY KEY,
                    fecha DATE,
                    tipo VARCHAR(50),
                    descripcion TEXT,
                    tecnico VARCHAR(100)
                );
            """)
            conn.commit()
            logger.info("Tablas inicializadas correctamente en PostgreSQL.")
            
            # Sembrar usuarios iniciales si la tabla de usuarios está vacía
            cur.execute("SELECT COUNT(*) FROM users;")
            if cur.fetchone()[0] == 0:
                logger.info("Sembrando usuarios por defecto en PostgreSQL...")
                json_users = load_users_from_json()
                for user in json_users:
                    cur.execute("""
                        INSERT INTO users (username, display_name, role, email, salt, password_hash, active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username) DO NOTHING;
                    """, (
                        user['username'],
                        user['display_name'],
                        user['role'],
                        user.get('email', 'ggeta13basantes@gmail.com'),
                        user['salt'],
                        user['password_hash'],
                        user.get('active', True)
                    ))
                conn.commit()
    except Exception as e:
        logger.error(f"Error inicializando tablas en PostgreSQL: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- CARGA Y GUARDADO DE USUARIOS ---

def load_users_from_json():
    path = os.path.join(os.path.dirname(__file__), 'users.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            users = data.get("users", []) if isinstance(data, dict) else data
            return users
        except Exception as e:
            logger.error(f"Error leyendo users.json: {e}")
    return []

def save_users_to_json(users):
    path = os.path.join(os.path.dirname(__file__), 'users.json')
    try:
        store = {"version": 1, "users": users}
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(store, file, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error escribiendo users.json: {e}")
        return False

def load_users():
    conn = get_connection()
    if not conn:
        return load_users_from_json()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT username, display_name, role, email, salt, password_hash, active FROM users;")
            users = cur.fetchall()
            return [dict(u) for u in users]
    except Exception as e:
        logger.error(f"Error cargando usuarios de PostgreSQL: {e}. Usando fallback a JSON.")
        return load_users_from_json()
    finally:
        if conn:
            conn.close()

def save_users(users):
    # Guardamos localmente en JSON para consistencia de respaldo
    save_users_to_json(users)
    
    conn = get_connection()
    if not conn:
        return True
    try:
        with conn.cursor() as cur:
            for user in users:
                cur.execute("""
                    INSERT INTO users (username, display_name, role, email, salt, password_hash, active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO UPDATE 
                    SET display_name = EXCLUDED.display_name,
                        role = EXCLUDED.role,
                        email = EXCLUDED.email,
                        salt = EXCLUDED.salt,
                        password_hash = EXCLUDED.password_hash,
                        active = EXCLUDED.active;
                """, (
                    user['username'],
                    user['display_name'],
                    user['role'],
                    user.get('email', ''),
                    user['salt'],
                    user['password_hash'],
                    user.get('active', True)
                ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error guardando usuarios en PostgreSQL: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# --- CARGA Y GUARDADO DE DATOS HISTÓRICOS ---

def load_historical_data_from_json():
    path = os.path.join(os.path.dirname(__file__), 'historical_data.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_historical_data_to_json(readings):
    path = os.path.join(os.path.dirname(__file__), 'historical_data.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(readings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error guardando histórico en JSON: {e}")
        return False

def load_historical_data():
    conn = get_connection()
    if not conn:
        return load_historical_data_from_json()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT vx, vy, vz, rms, zona, ts FROM historical_data ORDER BY ts ASC;")
            readings = cur.fetchall()
            result = []
            for r in readings:
                result.append({
                    'vx': r['vx'],
                    'vy': r['vy'],
                    'vz': r['vz'],
                    'rms': r['rms'],
                    'zona': r['zona'],
                    'ts': r['ts'].isoformat()
                })
            return result
    except Exception as e:
        logger.error(f"Error cargando histórico de PostgreSQL: {e}. Usando fallback a JSON.")
        return load_historical_data_from_json()
    finally:
        if conn:
            conn.close()

def save_historical_data(readings):
    save_historical_data_to_json(readings)
    
    conn = get_connection()
    if not conn:
        return True
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE historical_data;")
            for r in readings:
                from datetime import datetime
                try:
                    # Remover Z si está presente para formatear correctamente con timezone
                    ts_str = r['ts'].replace('Z', '+00:00')
                    ts_val = datetime.fromisoformat(ts_str)
                except Exception:
                    ts_val = datetime.utcnow()
                cur.execute("""
                    INSERT INTO historical_data (vx, vy, vz, rms, zona, ts)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (r['vx'], r['vy'], r['vz'], r['rms'], r['zona'], ts_val))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error guardando histórico en PostgreSQL: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# --- CARGA Y GUARDADO DE BITÁCORA DE MANTENIMIENTO ---

def load_maintenance_log_from_json():
    path = os.path.join(os.path.dirname(__file__), 'maintenance_log.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_maintenance_log_to_json(logs):
    path = os.path.join(os.path.dirname(__file__), 'maintenance_log.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error escribiendo bitácora JSON: {e}")
        return False

def load_maintenance_log():
    conn = get_connection()
    if not conn:
        return load_maintenance_log_from_json()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT fecha, tipo, descripcion, tecnico FROM maintenance_log ORDER BY fecha DESC;")
            logs = cur.fetchall()
            result = []
            for l in logs:
                result.append({
                    'fecha': l['fecha'].isoformat() if hasattr(l['fecha'], 'isoformat') else str(l['fecha']),
                    'tipo': l['tipo'],
                    'descripcion': l['descripcion'],
                    'técnico': l['tecnico']
                })
            return result
    except Exception as e:
        logger.error(f"Error cargando bitácora de PostgreSQL: {e}. Usando fallback a JSON.")
        return load_maintenance_log_from_json()
    finally:
        if conn:
            conn.close()

def save_maintenance_log(logs):
    save_maintenance_log_to_json(logs)
    
    conn = get_connection()
    if not conn:
        return True
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE maintenance_log;")
            for l in logs:
                cur.execute("""
                    INSERT INTO maintenance_log (fecha, tipo, descripcion, tecnico)
                    VALUES (%s, %s, %s, %s);
                """, (l['fecha'], l['tipo'], l['descripcion'], l.get('técnico', l.get('tecnico', ''))))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error guardando bitácora en PostgreSQL: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# Inicializar tablas al importar si la DB está habilitada
if DB_ENABLED:
    inicializar_tablas()


def ejecutar_respaldo(tipo='Manual'):
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    
    if not os.path.exists(backup_dir):
        try:
            os.makedirs(backup_dir)
        except Exception as e:
            logger.error(f"No se pudo crear el directorio de respaldos: {e}")
            return False, f"Error al crear directorio: {e}"
            
    archivos_json = ['users.json', 'historical_data.json', 'maintenance_log.json', 'email_config.json', 'serial_config.json']
    respaldados_json = []
    
    # 1. Respaldar archivos JSON
    for filename in archivos_json:
        src = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, f"{filename.split('.')[0]}_{timestamp}.json")
            try:
                shutil.copy(src, dst)
                respaldados_json.append(filename)
            except Exception as e:
                logger.error(f"Error respaldando {filename}: {e}")
                
    # 2. Respaldar base de datos PostgreSQL (si está activa y conectada)
    db_backed_up = False
    conn = get_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Respaldar users
                cur.execute("SELECT * FROM users;")
                users_rows = cur.fetchall()
                with open(os.path.join(backup_dir, f"db_users_{timestamp}.json"), 'w', encoding='utf-8') as f:
                    json.dump([dict(r) for r in users_rows], f, indent=2, default=str)
                    
                # Respaldar historical_data
                cur.execute("SELECT * FROM historical_data;")
                history_rows = cur.fetchall()
                with open(os.path.join(backup_dir, f"db_historical_data_{timestamp}.json"), 'w', encoding='utf-8') as f:
                    json.dump([dict(r) for r in history_rows], f, indent=2, default=str)
                    
                # Respaldar maintenance_log
                cur.execute("SELECT * FROM maintenance_log;")
                maint_rows = cur.fetchall()
                with open(os.path.join(backup_dir, f"db_maintenance_log_{timestamp}.json"), 'w', encoding='utf-8') as f:
                    json.dump([dict(r) for r in maint_rows], f, indent=2, default=str)
                    
            db_backed_up = True
            logger.info("Respaldo de PostgreSQL realizado correctamente.")
        except Exception as e:
            logger.error(f"Error al respaldar base de datos PostgreSQL: {e}")
        finally:
            conn.close()
            
    # Guardar estado de último respaldo
    status_path = os.path.join(os.path.dirname(__file__), 'backup_status.json')
    try:
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump({
                'ultimo_respaldo': datetime.now().isoformat(),
                'tipo': tipo,
                'archivos_respaldados': respaldados_json,
                'postgresql_respaldado': db_backed_up
            }, f, indent=2)
    except Exception:
        pass
        
    msg = f"Respaldo completado ({tipo}). Archivos: {', '.join(respaldados_json)}"
    if db_backed_up:
        msg += " + Base de Datos (PostgreSQL)"
    return True, msg


# ============ CONFIGURACIÓN IoT ============

# ========== THINGSPEAK (Cloud Storage) ==========
# Obtén API keys gratis en: https://thingspeak.com/
THINGSPEAK_ENABLED = True  # ✅ ACTIVADO
THINGSPEAK_API_KEY = "LE2Y2ATBEJGXQPC9"  # Write API Key
THINGSPEAK_CHANNEL_ID = "3222160"  # Channel ID

# ========== TELEGRAM (Alertas) ==========
# Crea un bot con @BotFather en Telegram
TELEGRAM_ENABLED = False
TELEGRAM_BOT_TOKEN = "TU_BOT_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"  # Tu chat ID o grupo

# ========== MQTT (Protocolo IoT) ==========
MQTT_ENABLED = False
MQTT_BROKER = "broker.hivemq.com"  # Broker público gratuito
MQTT_PORT = 1883
MQTT_TOPIC = "hidromira/vibraciones"
MQTT_CLIENT_ID = "hidromira_sensor_1"

# ========== WEBHOOK (HTTP POST a tu servidor) ==========
WEBHOOK_ENABLED = False
WEBHOOK_URL = "https://tu-servidor.com/api/datos"

# ========== EMAIL (Alertas por correo) ==========
EMAIL_ENABLED = True  # ✅ ACTIVADO
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_FROM = "ggeta13basantes@gmail.com"  # ⚠️ CONFIGURA AQUÍ TU EMAIL
EMAIL_PASSWORD = "bdak yieq cwei rzxg"  # ⚠️ CONTRASEÑA DE APLICACIÓN (NO tu contraseña normal)
EMAIL_TO = ["ggeta13basantes@gmail.com", "geovanny.basantesq@gmail.com"]  # ⚠️ Email(s) para recibir alertas

# ========== CONFIGURACIÓN DE ALERTAS ==========
ALERT_ZONA_B = True   # Alertar en zona B (vigilancia)
ALERT_ZONA_C = True   # Alertar en zona C (corrección)
ALERT_ZONA_D = True   # Alertar en zona D (inaceptable)
ALERT_COOLDOWN = 300  # Segundos entre alertas repetidas (5 min)

# ========== CONFIGURACIÓN DE ACCESO REMOTO (NGROK) ==========
NGROK_URL = "https://3f33-190-15-129-108.ngrok-free.app/"

# ========== API REST ==========
API_ENABLED = True
API_PORT = 5000
API_HOST = "0.0.0.0"  # 0.0.0.0 para acceso externo

# ========== CONFIGURACIÓN DE PUERTOS SERIALES ==========
SENSOR_PORT_DEFAULT = 'COM8'
MOTOR_PORT_DEFAULT = 'COM3'

def load_serial_config():
    import os
    import json
    path = os.path.join(os.path.dirname(__file__), 'serial_config.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {
                    'sensor_port': config.get('sensor_port', SENSOR_PORT_DEFAULT),
                    'motor_port': config.get('motor_port', MOTOR_PORT_DEFAULT)
                }
        except Exception:
            pass
    return {'sensor_port': SENSOR_PORT_DEFAULT, 'motor_port': MOTOR_PORT_DEFAULT}

def save_serial_config(sensor_port, motor_port):
    import os
    import json
    path = os.path.join(os.path.dirname(__file__), 'serial_config.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'sensor_port': sensor_port,
                'motor_port': motor_port
            }, f, indent=2)
        return True
    except Exception:
        return False


# ========== CONFIGURACIÓN DE POSTGRESQL ==========
DB_ENABLED = False  # Cambiar a True para habilitar PostgreSQL
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "hidromira"
DB_USER = "postgres"
DB_PASSWORD = "tu_password_aqui"


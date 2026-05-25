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
MQTT_PORT = 8883
MQTT_TOPIC = "hidromira/vibraciones"
MQTT_CLIENT_ID = "hidromira_sensor_1"

# TLS 1.2 + certificados X.509 (recomendado para producción)
MQTT_TLS_ENABLED = True
MQTT_TLS_CA_CERT = ""  # Ruta al certificado CA raíz (obligatorio para validar el broker)
MQTT_TLS_CLIENT_CERT = ""  # Ruta al certificado cliente X.509
MQTT_TLS_CLIENT_KEY = ""  # Ruta a la clave privada del cliente
MQTT_TLS_INSECURE = False  # Mantener False para validar el certificado del servidor

# ========== WEBHOOK (HTTP POST a tu servidor) ==========
WEBHOOK_ENABLED = False
WEBHOOK_URL = "https://tu-servidor.com/api/datos"

# ========== EMAIL (Alertas por correo) ==========
EMAIL_ENABLED = True  # ✅ Activar alertas por correo
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_FROM = "ggeta13basantes@gmail.com"  # ⚠️ CONFIGURA AQUÍ TU EMAIL
EMAIL_PASSWORD = "bzxi kket xedb culk"  # ⚠️ CONTRASEÑA DE APLICACIÓN (NO tu contraseña normal)
EMAIL_TO = ["geovanny.basantesq@gmail.com"]  # ⚠️ Email(s) para recibir alertas

# ========== CONFIGURACIÓN DE ALERTAS ==========
ALERT_ZONA_B = True   # Alertar en zona B (vigilancia)
ALERT_ZONA_C = True   # Alertar en zona C (corrección)
ALERT_ZONA_D = True   # Alertar en zona D (inaceptable)
ALERT_COOLDOWN = 300  # Segundos entre alertas repetidas (5 min)

# ========== API REST ==========
API_ENABLED = True
API_PORT = 5000
API_HOST = "0.0.0.0"  # 0.0.0.0 para acceso externo

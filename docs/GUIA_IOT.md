# 🌐 HidroMira IoT - Guía de Configuración

## 📦 Instalación de Dependencias

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración IoT

Edita `iot_config.py` para activar los servicios que necesites:

### 1️⃣ ThingSpeak (Almacenamiento en la Nube - GRATIS)

**Paso 1**: Crear cuenta en https://thingspeak.com/

**Paso 2**: Crear un nuevo canal con 5 campos:
- Field 1: Velocidad X (mm/s)
- Field 2: Velocidad Y (mm/s)
- Field 3: Velocidad Z (mm/s)
- Field 4: RMS máximo (mm/s)
- Field 5: Zona ISO (65=A, 66=B, 67=C, 68=D)

**Paso 3**: Obtener Write API Key y Channel ID

**Paso 4**: En `iot_config.py`:
```python
THINGSPEAK_ENABLED = True
THINGSPEAK_API_KEY = "TU_WRITE_API_KEY"
THINGSPEAK_CHANNEL_ID = "TU_CHANNEL_ID"
```

**Visualizar datos**: https://thingspeak.com/channels/TU_CHANNEL_ID

---

### 2️⃣ Telegram (Alertas Instantáneas - GRATIS)

**Paso 1**: Habla con [@BotFather](https://t.me/BotFather) en Telegram

**Paso 2**: Envía `/newbot` y sigue las instrucciones

**Paso 3**: Copia el **Bot Token**

**Paso 4**: Obtén tu Chat ID:
- Habla con [@userinfobot](https://t.me/userinfobot)
- Copia tu **Chat ID**

**Paso 5**: En `iot_config.py`:
```python
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
TELEGRAM_CHAT_ID = "123456789"
```

**Recibirás alertas** cuando el sistema detecte Zona B, C o D

---

### 3️⃣ MQTT (Protocolo IoT Estándar - GRATIS)

**Uso con broker público**:
```python
MQTT_ENABLED = True
MQTT_BROKER = "broker.hivemq.com"  # Broker público gratuito
MQTT_PORT = 1883
MQTT_TOPIC = "hidromira/vibraciones"
```

**Suscribirse a los datos** (desde otro dispositivo):
```bash
mosquitto_sub -h broker.hivemq.com -t hidromira/vibraciones
```

**Brokers públicos alternativos**:
- `test.mosquitto.org`
- `broker.emqx.io`
- `mqtt.eclipseprojects.io`

---

### 4️⃣ Webhook (Integración con tu servidor)

**Paso 1**: Crea un endpoint en tu servidor que acepte POST JSON

**Paso 2**: En `iot_config.py`:
```python
WEBHOOK_ENABLED = True
WEBHOOK_URL = "https://tu-servidor.com/api/hidromira"
```

**Formato de datos enviados**:
```json
{
  "timestamp": "2026-01-07T20:00:00Z",
  "vx": 0.15,
  "vy": 0.12,
  "vz": 0.08,
  "rms": 0.13,
  "zona": "A",
  "rpm": 312
}
```

---

### 5️⃣ Email (Alertas por Correo)

**Para Gmail**:

**Paso 1**: Activar verificación en 2 pasos en tu cuenta Google

**Paso 2**: Ir a https://myaccount.google.com/apppasswords

**Paso 3**: Generar contraseña de aplicación

**Paso 4**: En `iot_config.py`:
```python
EMAIL_ENABLED = True
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_FROM = "tu_email@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"  # Contraseña de aplicación
EMAIL_TO = ["destinatario@ejemplo.com", "otro@ejemplo.com"]
```

---

## 🚀 API REST - Acceso Remoto a Datos

### Iniciar API

```bash
python api_rest.py
```

La API estará disponible en: `http://TU_IP:5000`

### Endpoints Disponibles

#### 1. **Información de la API**
```
GET http://localhost:5000/
```

#### 2. **Estado Actual**
```
GET http://localhost:5000/status
```

**Respuesta**:
```json
{
  "timestamp": "2026-01-07T20:00:00Z",
  "vx": 0.15,
  "vy": 0.12,
  "vz": 0.08,
  "total_lecturas": 1250
}
```

#### 3. **Últimas N Lecturas**
```
GET http://localhost:5000/datos?limit=100
```

#### 4. **Datos en Rango de Fechas**
```
GET http://localhost:5000/datos/rango?desde=2026-01-07T00:00:00Z&hasta=2026-01-07T23:59:59Z
```

#### 5. **Estadísticas**
```
GET http://localhost:5000/estadisticas
```

**Respuesta**:
```json
{
  "total_lecturas": 1250,
  "periodo": {
    "inicio": "2026-01-07T10:00:00Z",
    "fin": "2026-01-07T20:00:00Z"
  },
  "estadisticas": {
    "vx": {
      "promedio": 0.15,
      "max": 0.35,
      "min": 0.05,
      "std": 0.08
    },
    ...
  },
  "distribucion_zonas": {
    "A": 1200,
    "B": 40,
    "C": 8,
    "D": 2
  }
}
```

#### 6. **Alertas (Zona B/C/D)**
```
GET http://localhost:5000/alertas
```

---

## 🌍 Acceso desde Internet

### Opción 1: ngrok (Rápido y Fácil)

**Paso 1**: Descargar ngrok desde https://ngrok.com/

**Paso 2**: Ejecutar:
```bash
ngrok http 8503  # Para monitor en tiempo real
ngrok http 8502  # Para dashboard de análisis
ngrok http 5000  # Para API REST
```

**Paso 3**: ngrok te dará una URL pública temporal:
```
https://abc123.ngrok.io → http://localhost:8503
```

### Opción 2: No-IP / DynDNS (Permanente)

1. Crear cuenta en https://www.noip.com/
2. Crear hostname (ej: hidromira.ddns.net)
3. Configurar port forwarding en tu router:
   - Puerto 8503 → PC local puerto 8503
   - Puerto 8502 → PC local puerto 8502
   - Puerto 5000 → PC local puerto 5000

### Opción 3: Deploy en la Nube

**Streamlit Cloud** (GRATIS):
1. Subir código a GitHub
2. Ir a https://share.streamlit.io/
3. Conectar repositorio
4. Deploy automático

**Heroku** (API REST):
```bash
heroku create hidromira-api
git push heroku main
```

---

## 📱 Integración con Node-RED

**Paso 1**: Instalar Node-RED
```bash
npm install -g node-red
node-red
```

**Paso 2**: Abrir http://localhost:1880

**Paso 3**: Arrastrar nodo MQTT In

**Paso 4**: Configurar:
- Server: broker.hivemq.com
- Topic: hidromira/vibraciones

**Paso 5**: Conectar a nodos de procesamiento (dashboard, alertas, etc.)

---

## 📊 Dashboard de Ejemplo con ThingSpeak

Una vez configurado ThingSpeak, puedes crear visualizaciones:

1. Ir a tu canal en ThingSpeak
2. Clic en "Apps" → "MATLAB Visualizations"
3. Crear gráficos personalizados con MATLAB

**Ejemplo de código MATLAB para alerta**:
```matlab
% Leer último valor de RMS
data = thingSpeakRead(channelID, 'Fields', 4, 'NumPoints', 1);

if data > 0.75
    sendmail('tu_email@gmail.com', 'ALERTA ZONA D', 'Vibración crítica detectada');
end
```

---

## 🔒 Seguridad

### Para producción, asegúrate de:

1. **Cambiar contraseñas por defecto**
2. **Usar HTTPS** (no HTTP)
3. **Agregar autenticación** a la API:

```python
from flask import request

API_KEY = "tu_api_key_secreta"

@app.before_request
def verificar_api_key():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'No autorizado'}), 401
```

4. **Firewall**: Solo abrir puertos necesarios
5. **VPN**: Usar VPN para acceso remoto seguro

---

## 📞 Soporte

- **ThingSpeak**: https://www.mathworks.com/help/thingspeak/
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **MQTT**: https://mqtt.org/
- **Flask**: https://flask.palletsprojects.com/

---

## ✅ Checklist de Configuración

- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Configurar servicios IoT en `iot_config.py`
- [ ] Probar conexión al sensor COM3
- [ ] Iniciar monitor: `streamlit run monitor_realtime.py --server.port 8503`
- [ ] Iniciar API (opcional): `python api_rest.py`
- [ ] Verificar recepción de datos en ThingSpeak/Telegram
- [ ] Configurar acceso remoto (ngrok/No-IP)
- [ ] Documentar URLs públicas para acceso externo

¡Tu sistema ahora es completamente IoT! 🎉

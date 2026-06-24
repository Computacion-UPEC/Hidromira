import streamlit as st
import minimalmodbus
import serial
import plotly.graph_objects as go
from collections import deque
import time
import json
import os
from datetime import datetime
import numpy as np
from streamlit_autorefresh import st_autorefresh
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler("hidromira.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HidroMiraRealtime")

from auth import get_role_label, require_login, render_user_panel
import db

# Importar módulos IoT
try:
    import iot_config
    IOT_CONFIG_AVAILABLE = True
except Exception as e:
    logger.error(f"iot_config no disponible en monitor: {e}")
    IOT_CONFIG_AVAILABLE = False

@st.cache_resource
def get_iot_handler():
    try:
        if IOT_CONFIG_AVAILABLE:
            from iot_handler import IoTHandler
            return IoTHandler(vars(iot_config))
    except Exception as e:
        logger.error(f"Error inicializando IoTHandler en monitor: {e}")
        return None

iot_handler = get_iot_handler()
IOT_AVAILABLE = iot_handler is not None

st.set_page_config(page_title="HidroMira - Monitor Tiempo Real", layout="wide")

current_user = require_login(app_name="HidroMira - Monitor Tiempo Real")

# Registrar login en logs una sola vez por sesión
if 'login_logged' not in st.session_state:
    logger.info(f"[RT] Usuario autenticado: {current_user['username']} (Rol: {get_role_label(current_user['role'])})")
    st.session_state.login_logged = True

render_user_panel()

st.title("⚡ Monitoreo en Tiempo Real")
st.caption(f"Usuario: {current_user['display_name']} | Rol: {get_role_label(current_user['role'])}")

# Auto-refresh cada 500ms
count = st_autorefresh(interval=500, key="realtime_refresh")

# ============ INICIALIZACIÓN SESSION STATE ============

if 'buffer_x' not in st.session_state:
    st.session_state.buffer_x = deque([0]*50, maxlen=50)
if 'buffer_y' not in st.session_state:
    st.session_state.buffer_y = deque([0]*50, maxlen=50)
if 'buffer_z' not in st.session_state:
    st.session_state.buffer_z = deque([0]*50, maxlen=50)
if 'buffer_rpm' not in st.session_state:
    st.session_state.buffer_rpm = deque([0]*50, maxlen=50)
if 'all_readings' not in st.session_state:
    st.session_state.all_readings = []

# Variables para tracking IoT
if 'iot_envios_ok' not in st.session_state:
    st.session_state.iot_envios_ok = 0
if 'iot_envios_error' not in st.session_state:
    st.session_state.iot_envios_error = 0
if 'ultimo_envio_thingspeak' not in st.session_state:
    st.session_state.ultimo_envio_thingspeak = None

# Cargar configuración centralizada de puertos COM
if IOT_CONFIG_AVAILABLE and hasattr(iot_config, 'load_serial_config'):
    puertos_cfg = iot_config.load_serial_config()
else:
    puertos_cfg = {'sensor_port': 'COM8', 'motor_port': 'COM3'}

if 'sensor_port' not in st.session_state:
    st.session_state.sensor_port = puertos_cfg['sensor_port']

# ============ CONEXIÓN SENSOR ============

@st.cache_resource
def conectar(puerto):
    logger.info(f"[RT] Intentando conectar con el sensor ModBus WTVB01-485 en {puerto}...")
    try:
        sensor = minimalmodbus.Instrument(puerto, 80)
        sensor.serial.baudrate = 9600
        sensor.serial.bytesize = 8
        sensor.serial.parity = serial.PARITY_NONE
        sensor.serial.stopbits = 1
        sensor.serial.timeout = 1.0  # Aumentar timeout a 1 segundo
        sensor.mode = minimalmodbus.MODE_RTU  # Modo RTU
        sensor.clear_buffers_before_each_transaction = True  # Limpiar buffers
        
        # Test de conexión con múltiples intentos
        for intento in range(3):
            try:
                _ = sensor.read_register(58, functioncode=3)
                logger.info(f"[RT] ✅ Sensor ModBus conectado exitosamente en {puerto} (intento {intento + 1})")
                return sensor
            except Exception as e:
                if intento < 2:
                    logger.warning(f"[RT] Intento {intento + 1} de conexión ModBus fallido: {e}. Reintentando...")
                    time.sleep(0.5)
                    continue
                else:
                    raise e
        return sensor
    except Exception as e:
        logger.error(f"[RT] ❌ No se pudo conectar al sensor ModBus en {puerto}: {e}")
        return None

sensor = conectar(st.session_state.sensor_port)

# Mostrar estado de conexión
if sensor:
    st.success(f"✅ Sensor WTVB01-485 conectado en {st.session_state.sensor_port}")
else:
    st.error("❌ Sensor no disponible - Generando datos de demostración")
    st.warning(f"💡 Para usar el sensor real: Cierra otras apps que usen {st.session_state.sensor_port} y reinicia el monitor")

st.caption("")

# ============ FUNCIONES ============

def calcular_rms(buffer):
    if not buffer or len(buffer) == 0:
        return 0
    return np.sqrt(np.mean(np.array(buffer)**2))

def calcular_amplitud(buffer):
    if not buffer or len(buffer) == 0:
        return 0
    return max(buffer)

def calcular_rpm_correlacionado(rms_valor):
    rpm = rms_valor * 2400
    return min(rpm, 1200)

ZONA_A_MAX = 0.25
ZONA_B_MAX = 0.5
ZONA_C_MAX = 0.75

def clasificar_zona(velocidad):
    if velocidad <= ZONA_A_MAX:
        return "A", "#00c853"
    elif velocidad <= ZONA_B_MAX:
        return "B", "#ffd600"
    elif velocidad <= ZONA_C_MAX:
        return "C", "#ff9100"
    else:
        return "D", "#d50000"

# ============ LECTURA Y VISUALIZACIÓN ============

st.caption("🏭 Máquina: Grupo 1 (Soporte Rígido) | Norma ISO 20816-3 | Zona A ≤ 0.25 | B ≤ 0.5 | C ≤ 0.75 mm/s")

# Leer datos del sensor o generar demostración
sensor_ok = False
if sensor:
    try:
        # Leer con delay entre registros para evitar problemas de comunicación
        vx = sensor.read_register(58, functioncode=3, signed=True) / 100.0
        time.sleep(0.05)  # Pequeño delay entre lecturas
        vy = sensor.read_register(59, functioncode=3, signed=True) / 100.0
        time.sleep(0.05)
        vz = sensor.read_register(60, functioncode=3, signed=True) / 100.0
        sensor_ok = True
    except Exception as e:
        error_msg = str(e)
        # Solo mostrar error cada 10 lecturas para no saturar
        if len(st.session_state.all_readings) % 10 == 0:
            logger.error(f"[RT] Error de comunicación con el sensor ModBus: {error_msg[:80]}")
            st.error(f"⚠️ Error comunicación sensor: {error_msg[:80]}")
        # Usar datos de demostración
        vx = 0.15 + 0.05 * np.sin(time.time() * 0.5)
        vy = 0.12 + 0.04 * np.cos(time.time() * 0.5)
        vz = 0.08 + 0.03 * np.sin(time.time() * 0.7)
else:
    vx = 0.15 + 0.05 * np.sin(time.time() * 0.5)
    vy = 0.12 + 0.04 * np.cos(time.time() * 0.5)
    vz = 0.08 + 0.03 * np.sin(time.time() * 0.7)
    vy = 0.12 + 0.04 * np.cos(time.time() * 0.5)
    vz = 0.08 + 0.03 * np.sin(time.time() * 0.7)

# Agregar a buffers
st.session_state.buffer_x.append(vx)
st.session_state.buffer_y.append(vy)
st.session_state.buffer_z.append(vz)

# Agregar a histórico
rec = {'vx': vx, 'vy': vy, 'vz': vz, 'ts': datetime.utcnow().isoformat() + 'Z'}
st.session_state.all_readings.append(rec)

# Calcular valores antes de publicar IoT
vx_rms = calcular_rms(st.session_state.buffer_x)
vy_rms = calcular_rms(st.session_state.buffer_y)
vz_rms = calcular_rms(st.session_state.buffer_z)
vmax = max(vx_rms, vy_rms, vz_rms)
zona, color = clasificar_zona(vmax)
rpm = calcular_rpm_correlacionado(vmax)

# ========== PUBLICAR A IoT ==========
if IOT_AVAILABLE:
    try:
        # Cargar configuración de correo actualizada por app.py en caliente
        iot_handler.load_email_config()
        
        # Publicar datos cada lectura (ThingSpeak tiene límite de 1 envío cada 15 segundos)
        # Solo enviar cada 30 lecturas (aprox 15 segundos a 0.5s por lectura)
        if len(st.session_state.all_readings) % 30 == 0:
            # Enviar a ThingSpeak
            if iot_config.THINGSPEAK_ENABLED:
                logger.info(f"[RT] Publicando a ThingSpeak: vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}, rms={vmax:.3f}")
                resultado = iot_handler.enviar_thingspeak(vx, vy, vz, vmax, zona)
                if resultado:
                    logger.info("[RT] Envío a ThingSpeak exitoso.")
                    st.session_state.iot_envios_ok += 1
                    st.session_state.ultimo_envio_thingspeak = datetime.now()
                else:
                    logger.warning("[RT] Envío a ThingSpeak rechazado (tasa de límite superada o API key errónea).")
                    st.session_state.iot_envios_error += 1
        
        # Publicar a MQTT/Webhook cada lectura (sin rate limit)
        if iot_config.MQTT_ENABLED or iot_config.WEBHOOK_ENABLED:
            iot_handler.publicar_datos(vx, vy, vz, vmax, zona, rpm)
        
        # Verificar y enviar alertas si es necesario
        if iot_handler.verificar_alerta(zona, vmax):
            logger.critical(f"[RT] ⚠️ Alerta ISO 20816-3 Zona {zona} detectada con vmax={vmax:.3f}! Enviando avisos...")
            iot_handler.enviar_alerta_completa(zona, vmax, vx, vy, vz)
            logger.info("[RT] Alertas enviadas con éxito.")
    except Exception as e:
        logger.error(f"[RT] Error IoT: {e}")
        st.session_state.iot_envios_error += 1

# Guardar cada 50 lecturas usando el módulo db
if len(st.session_state.all_readings) % 50 == 0:
    try:
        db.save_historical_data(st.session_state.all_readings)
        logger.info(f"[RT] Histórico guardado automáticamente. Total registros: {len(st.session_state.all_readings)}")
    except Exception as e:
        logger.error(f"[RT] Error al guardar histórico: {e}")

col1, col2 = st.columns([1, 3])

# Agregar RPM al buffer
st.session_state.buffer_rpm.append(rpm)

col1.markdown(f"### 🚨 ESTADO ISO 20816-3")
col1.markdown(f"<div style='background-color:{color};padding:10px;border-radius:5px;text-align:center'>"
            f"<h2 style='color:white;margin:0'>ZONA {zona}</h2>"
            f"<p style='color:white;margin:5px 0'>{vmax:.2f} mm/s</p>"
            f"</div>", unsafe_allow_html=True)

col1.metric("⚙️ RPM", f"{rpm:.0f}", "1200 nominal")

if zona == "A":
    col1.success("✅ Funcionamiento Normal")
elif zona == "B":
    col1.warning("⚠️ Vigilancia Recomendada")
elif zona == "C":
    col1.error("🔴 Requiere Corrección")
else:
    col1.error("🚫 INACEPTABLE - Detener Máquina")

# Métricas
col1.markdown("---")
col1.caption("📈 X (Rojo)")
col1.metric("Valor", f"{vx:.2f} mm/s")
col1.metric("RMS", f"{vx_rms:.2f} mm/s")
col1.metric("Amplitud", f"{calcular_amplitud(st.session_state.buffer_x):.2f}")
zona_x, _ = clasificar_zona(vx_rms)
col1.caption(f"Zona: {zona_x}")

col1.markdown("---")
col1.caption("📈 Y (Verde)")
col1.metric("Valor", f"{vy:.2f} mm/s")
col1.metric("RMS", f"{vy_rms:.2f} mm/s")
col1.metric("Amplitud", f"{calcular_amplitud(st.session_state.buffer_y):.2f}")
zona_y, _ = clasificar_zona(vy_rms)
col1.caption(f"Zona: {zona_y}")

col1.markdown("---")
col1.caption("📈 Z (Azul)")
col1.metric("Valor", f"{vz:.2f} mm/s")
col1.metric("RMS", f"{vz_rms:.2f} mm/s")
col1.metric("Amplitud", f"{calcular_amplitud(st.session_state.buffer_z):.2f}")
zona_z, _ = clasificar_zona(vz_rms)
col1.caption(f"Zona: {zona_z}")

# Gráficas
fig = go.Figure()
fig.add_trace(go.Scatter(y=list(st.session_state.buffer_x), mode='lines+markers', 
                        line=dict(color='#ff6b6b', width=2), name='X'))
fig.add_trace(go.Scatter(y=list(st.session_state.buffer_y), mode='lines+markers', 
                        line=dict(color='#51cf66', width=2), name='Y'))
fig.add_trace(go.Scatter(y=list(st.session_state.buffer_z), mode='lines+markers', 
                        line=dict(color='#4dabf7', width=2), name='Z'))
# Escala Y dinámica con un mínimo de 3.0 para evitar oscilaciones de escala en reposo
max_y = max(
    max(list(st.session_state.buffer_x)) if st.session_state.buffer_x else 0,
    max(list(st.session_state.buffer_y)) if st.session_state.buffer_y else 0,
    max(list(st.session_state.buffer_z)) if st.session_state.buffer_z else 0,
    3.0
)
fig.update_layout(template="plotly_dark", height=400, yaxis=dict(range=[0, max_y * 1.15], title="Velocidad (mm/s)"))
col2.plotly_chart(fig, width='stretch')

st.markdown("---")
st.subheader("⚙️ Velocidad de Rotación (RPM)")
fig_rpm = go.Figure()
fig_rpm.add_trace(go.Scatter(y=list(st.session_state.buffer_rpm), mode='lines+markers',
                            line=dict(color='#ffd700', width=3), name='RPM',
                            fill='tozeroy'))
fig_rpm.add_hline(y=1200, line_dash="dash", line_color="green", annotation_text="RPM Nominal (1200)")
fig_rpm.update_layout(template="plotly_dark", height=350, 
                     yaxis=dict(range=[0, 1300], title="RPM"),
                     xaxis_title="Tiempo")
st.plotly_chart(fig_rpm, width='stretch')

# Indicador de fuente de datos e IoT
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if sensor_ok:
        st.success("📡 DATOS REALES DEL SENSOR")
    else:
        st.error("⚠️ DATOS DE DEMOSTRACIÓN")
        st.caption("Sensor no conectado")

with col2:
    if IOT_AVAILABLE and iot_config.THINGSPEAK_ENABLED:
        if st.session_state.ultimo_envio_thingspeak:
            tiempo_desde = (datetime.now() - st.session_state.ultimo_envio_thingspeak).seconds
            st.info(f"☁️ ThingSpeak: {tiempo_desde}s")
        else:
            st.info("☁️ ThingSpeak: Esperando...")
    else:
        st.error("☁️ ThingSpeak: OFF")

with col3:
    if IOT_AVAILABLE:
        st.metric("✅ Envíos OK", st.session_state.iot_envios_ok)
    else:
        st.metric("❌ Errores", st.session_state.iot_envios_error)

with col4:
    st.caption(f"🔄 {datetime.now().strftime('%H:%M:%S')} | {len(st.session_state.all_readings)} lecturas")

# Panel de debug IoT
if IOT_AVAILABLE and iot_config.THINGSPEAK_ENABLED:
    with st.expander("🔍 Debug ThingSpeak"):
        st.write(f"**Canal ID:** {iot_config.THINGSPEAK_CHANNEL_ID}")
        st.write(f"**API Key:** {iot_config.THINGSPEAK_API_KEY[:8]}...")
        st.write(f"**URL del canal:** https://thingspeak.com/channels/{iot_config.THINGSPEAK_CHANNEL_ID}")
        st.write(f"**Envíos exitosos:** {st.session_state.iot_envios_ok}")
        st.write(f"**Envíos fallidos:** {st.session_state.iot_envios_error}")
        if st.session_state.ultimo_envio_thingspeak:
            st.write(f"**Último envío:** {st.session_state.ultimo_envio_thingspeak.strftime('%H:%M:%S')}")
        st.caption("⚠️ ThingSpeak permite 1 envío cada 15 segundos (gratis)")


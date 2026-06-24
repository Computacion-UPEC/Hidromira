import streamlit as st
# pyrefly: ignore [missing-import]
import minimalmodbus
import plotly.graph_objects as go
from collections import deque
import time
import json
import os
from datetime import datetime, timedelta
import numpy as np
import serial
import serial.tools.list_ports
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
logger = logging.getLogger("HidroMiraApp")

from auth import get_role_label, require_login, render_user_panel, require_role
import db

# Importar módulos IoT
try:
    import iot_config
    IOT_CONFIG_AVAILABLE = True
except Exception as e:
    logger.error(f"iot_config no disponible: {e}")
    IOT_CONFIG_AVAILABLE = False

@st.cache_resource
def get_iot_handler():
    try:
        if IOT_CONFIG_AVAILABLE:
            from iot_handler import IoTHandler
            return IoTHandler(vars(iot_config))
    except Exception as e:
        logger.error(f"Error inicializando IoTHandler: {e}")
        return None

iot_handler = get_iot_handler()
IOT_AVAILABLE = iot_handler is not None

st.set_page_config(page_title="HidroMira IoT", layout="wide")

current_user = require_login(app_name="HidroMira - Panel de Operación e IoT")

# Registrar login en logs una sola vez por sesión
if 'login_logged' not in st.session_state:
    logger.info(f"Usuario autenticado: {current_user['username']} (Rol: {get_role_label(current_user['role'])})")
    st.session_state.login_logged = True

render_user_panel()

# ============ INICIALIZACIÓN SESSION STATE ============

# Buffers para tiempo real (máximo 50 puntos)
if 'buffer_x' not in st.session_state:
    st.session_state.buffer_x = deque([0]*50, maxlen=50)
if 'buffer_y' not in st.session_state:
    st.session_state.buffer_y = deque([0]*50, maxlen=50)
if 'buffer_z' not in st.session_state:
    st.session_state.buffer_z = deque([0]*50, maxlen=50)
if 'buffer_rpm' not in st.session_state:
    st.session_state.buffer_rpm = deque([0]*50, maxlen=50)

# Historial completo para análisis (SOLO para Tab 2, 3, 4)
if 'all_readings' not in st.session_state:
    st.session_state.all_readings = []  # Inicializar vacío, se carga cuando Tab 2 lo necesita

if 'json_loaded' not in st.session_state:
    st.session_state.json_loaded = False  # Bandera para cargar JSON solo una vez en Tab 2

# RPM actual correlacionado con vibraciones
if 'current_rpm' not in st.session_state:
    st.session_state.current_rpm = 0

if 'period_view' not in st.session_state:
    st.session_state.period_view = "Últimos 20s"

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0  # 0=Tab1, 1=Tab2, 2=Tab3, 3=Tab4

if 'last_tab1_refresh' not in st.session_state:
    st.session_state.last_tab1_refresh = time.time()

if 'tab1_needs_refresh' not in st.session_state:
    st.session_state.tab1_needs_refresh = False
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
    st.session_state.sensor_port = puertos_cfg.get('sensor_port', 'COM8')
if 'sensor_scale' not in st.session_state:
    st.session_state.sensor_scale = puertos_cfg.get('sensor_scale', 100.0)

# Estado del control del motor por serial
if 'motor_port' not in st.session_state:
    st.session_state.motor_port = puertos_cfg['motor_port']
if 'motor_connected' not in st.session_state:
    st.session_state.motor_connected = False
if 'motor_mode' not in st.session_state:
    st.session_state.motor_mode = 'Detenido'
if 'motor_response' not in st.session_state:
    st.session_state.motor_response = 'Sin comandos enviados'
if 'motor_speed' not in st.session_state:
    st.session_state.motor_speed = 255
if 'motor_serial' not in st.session_state:
    st.session_state.motor_serial = None
if 'servo_angle' not in st.session_state:
    st.session_state.servo_angle = 95

# El sensor solo se usa en monitor_realtime.py
# Esta app solo lee historical_data.json para análisis

def verificar_respaldo_automatico():
    import time
    import threading
    
    status_path = os.path.join(os.path.dirname(__file__), 'backup_status.json')
    last_backup = 0
    
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                status = json.load(f)
                dt = datetime.fromisoformat(status.get('ultimo_respaldo', ''))
                last_backup = dt.timestamp()
        except Exception:
            pass
            
    ahora = time.time()
    # Ejecutar respaldo automático diario (86400 segundos)
    if ahora - last_backup > 86400:
        logger.info("Iniciando respaldo automático diario de datos...")
        threading.Thread(target=db.ejecutar_respaldo, args=('Automático Diario',), daemon=True).start()

verificar_respaldo_automatico()

# ============ FUNCIONES DE CÁLCULO ============

def calcular_amplitud(buffer):
    if not buffer or len(buffer) == 0:
        return 0
    return max(buffer)

def calcular_pico_pico(buffer):
    if not buffer or len(buffer) == 0:
        return 0
    return max(buffer) - min(buffer)

def calcular_rms(buffer):
    if not buffer or len(buffer) == 0:
        return 0
    return np.sqrt(np.mean(np.array(buffer)**2))

def calcular_desv_std(buffer):
    if not buffer or len(buffer) == 0:
        return 0
    return np.std(buffer)

def calcular_rpm_correlacionado(rms_valor):
    """
    Calcula RPM correlacionado con vibraciones
    0 mm/s = 0 RPM (máquina parada)
    0.5 mm/s = ~1200 RPM (nominal)
    1.5 mm/s = ~1200 RPM (sin cambio, pues es el máximo operativo)
    """
    # Relación lineal: RPM = RMS * 2400 (así 0.5 → 1200)
    rpm = rms_valor * 2400
    # Limitar a rango operativo
    rpm = min(rpm, 1200)
    return rpm

# ============ NORMA ISO 20816-3 - GRUPO 1 ============
# Grupo 1: Máquinas pequeñas con soporte rígido
ZONA_A_MAX = 0.25  # Aceptable
ZONA_B_MAX = 0.5    # Aceptable con vigilancia
ZONA_C_MAX = 0.75   # Requiere corrección
# ZONA_D_MAX = inf   # Inaceptable

def clasificar_zona(velocidad):
    """Clasifica la velocidad según ISO 20816-3 Grupo 1"""
    if velocidad <= ZONA_A_MAX:
        return "A", "#00c853"  # Verde
    elif velocidad <= ZONA_B_MAX:
        return "B", "#ffd600"  # Amarillo
    elif velocidad <= ZONA_C_MAX:
        return "C", "#ff9100"  # Naranja
    else:
        return "D", "#d50000"  # Rojo

def detectar_anomalias(buffer, threshold_factor=2.0):
    """Detecta picos anormales (anomalías) en los datos"""
    if len(buffer) < 3:
        return []
    
    buffer_array = np.array(buffer)
    media = np.mean(buffer_array)
    desv = np.std(buffer_array)
    
    # Anomalía: valor > media + (threshold_factor * desv_std)
    anomalias = []
    for i, val in enumerate(buffer):
        if val > media + (threshold_factor * desv):
            anomalias.append((i, val))
    
    return anomalias

def save_historical_data():
    """Guardar datos históricos usando el módulo db"""
    try:
        db.save_historical_data(st.session_state.all_readings)
        logger.info(f"Guardado exitoso del histórico. Total registros: {len(st.session_state.all_readings)}")
    except Exception as e:
        logger.error(f"Error guardando datos históricos: {e}")


def obtener_puertos_serial_disponibles():
    return [port.device for port in serial.tools.list_ports.comports()]


def puerto_sensor_activo():
    if sensor and hasattr(sensor, 'serial'):
        return getattr(sensor.serial, 'port', None)
    return None


def conectar_motor_serial(puerto):
    motor_serial = st.session_state.get('motor_serial')

    if not puerto:
        st.session_state.motor_connected = False
        st.session_state.motor_response = 'Selecciona un puerto serial válido.'
        return False, st.session_state.motor_response

    sensor_port = puerto_sensor_activo()
    if sensor_port and puerto == sensor_port:
        st.session_state.motor_connected = False
        st.session_state.motor_response = f'El puerto {puerto} ya está ocupado por el sensor ModBus.'
        return False, st.session_state.motor_response

    if motor_serial and getattr(motor_serial, 'is_open', False):
        try:
            motor_serial.close()
        except Exception:
            pass

    try:
        motor_serial = serial.Serial(puerto, 9600, timeout=1.0, write_timeout=1.0)
        time.sleep(2.0)
        motor_serial.reset_input_buffer()
        motor_serial.reset_output_buffer()

        st.session_state.motor_serial = motor_serial
        st.session_state.motor_port = puerto
        st.session_state.motor_connected = True
        st.session_state.motor_mode = 'Conectado'
        st.session_state.motor_response = f'Conectado correctamente a {puerto}'
        return True, st.session_state.motor_response
    except Exception as e:
        st.session_state.motor_serial = None
        st.session_state.motor_connected = False
        st.session_state.motor_mode = 'Error'
        st.session_state.motor_response = f'No se pudo abrir {puerto}: {e}'
        return False, st.session_state.motor_response


def desconectar_motor_serial():
    motor_serial = st.session_state.get('motor_serial')
    if motor_serial and getattr(motor_serial, 'is_open', False):
        try:
            motor_serial.close()
        except Exception:
            pass

    st.session_state.motor_serial = None
    st.session_state.motor_connected = False
    st.session_state.motor_mode = 'Detenido'
    st.session_state.motor_response = 'Motor desconectado'
    return st.session_state.motor_response


def enviar_comando_motor(valor, modo):
    motor_serial = st.session_state.get('motor_serial')

    if not motor_serial or not getattr(motor_serial, 'is_open', False):
        st.session_state.motor_connected = False
        st.session_state.motor_response = 'El motor no está conectado.'
        return False, st.session_state.motor_response

    try:
        comando = f'M{valor}\n'
        motor_serial.write(comando.encode('utf-8'))
        motor_serial.flush()
        time.sleep(0.08)

        if motor_serial.in_waiting > 0:
            respuesta = motor_serial.readline().decode('utf-8', errors='ignore').strip()
        else:
            respuesta = 'Comando enviado sin respuesta directa'

        st.session_state.motor_speed = abs(int(valor))
        st.session_state.motor_mode = modo
        st.session_state.motor_response = respuesta
        return True, respuesta
    except Exception as e:
        st.session_state.motor_connected = False
        st.session_state.motor_mode = 'Error'
        st.session_state.motor_response = f'Error enviando comando al motor: {e}'
        try:
            motor_serial.close()
        except Exception:
            pass
        st.session_state.motor_serial = None
        return False, st.session_state.motor_response


def enviar_comando_servo(valor):
    motor_serial = st.session_state.get('motor_serial')

    if not motor_serial or not getattr(motor_serial, 'is_open', False):
        st.session_state.motor_connected = False
        st.session_state.motor_response = 'El dispositivo serial no está conectado.'
        return False, st.session_state.motor_response

    try:
        # Constreñir en el rango esperado de 10 a 100 grados
        valor_const = max(10, min(100, int(valor)))
        comando = f'S{valor_const}\n'
        motor_serial.write(comando.encode('utf-8'))
        motor_serial.flush()
        time.sleep(0.08)

        if motor_serial.in_waiting > 0:
            respuesta = motor_serial.readline().decode('utf-8', errors='ignore').strip()
        else:
            respuesta = 'Comando enviado sin respuesta directa'

        st.session_state.servo_angle = valor_const
        st.session_state.motor_response = respuesta
        return True, respuesta
    except Exception as e:
        st.session_state.motor_connected = False
        st.session_state.motor_response = f'Error enviando comando al servo: {e}'
        try:
            motor_serial.close()
        except Exception:
            pass
        st.session_state.motor_serial = None
        return False, st.session_state.motor_response


# ============ CONEXIÓN DEL SENSOR MODBUS ============
@st.cache_resource
def conectar(puerto):
    logger.info(f"Intentando conectar con el sensor ModBus WTVB01-485 en {puerto}...")
    try:
        sensor = minimalmodbus.Instrument(puerto, 80)
        sensor.serial.baudrate = 9600
        sensor.serial.bytesize = 8
        sensor.serial.parity = serial.PARITY_NONE
        sensor.serial.stopbits = 1
        sensor.serial.timeout = 1.0
        sensor.mode = minimalmodbus.MODE_RTU
        sensor.clear_buffers_before_each_transaction = True
        
        for intento in range(3):
            try:
                _ = sensor.read_register(58, functioncode=3)
                logger.info(f"✅ Sensor ModBus conectado exitosamente en {puerto} (intento {intento + 1})")
                return sensor
            except Exception as e:
                if intento < 2:
                    logger.warning(f"Intento {intento + 1} de conexión ModBus fallido: {e}. Reintentando...")
                    time.sleep(0.5)
                    continue
                else:
                    raise e
        return sensor
    except Exception as e:
        logger.error(f"❌ No se pudo conectar al sensor ModBus en {puerto}: {e}")
        return None

sensor = conectar(st.session_state.sensor_port)

# ============ MENÚ DE NAVEGACIÓN LATERAL (UNIFICACIÓN) ============
st.sidebar.title("🧭 Menú Principal")
opciones_menu = [
    "⚡ Monitoreo en Tiempo Real",
    "📊 Análisis Histórico",
    "🏭 Datos Técnicos y Mantenimiento",
    "⚙️ Rendimiento vs Vibraciones",
    "🔧 Control de Motor y Servo",
    "🪵 Consola de Registros (Logs)"
]

# Detectar parámetro de consulta en la URL para cambiar de pestaña automáticamente
menu_index = 0
try:
    if 'tab' in st.query_params:
        tab_param = st.query_params['tab']
        if tab_param == 'mantenimiento':
            menu_index = 2
        elif tab_param == 'control':
            menu_index = 4
except Exception as e:
    logger.error(f"Error leyendo parámetros de consulta: {e}")

page = st.sidebar.radio("Ir a la sección:", opciones_menu, index=menu_index)


if page == "⚡ Monitoreo en Tiempo Real":
    st.subheader("⚡ Monitoreo en Tiempo Real")
    
    # Auto-refresh cada 500ms
    count = st_autorefresh(interval=500, key="realtime_refresh")
    
    # Mostrar estado de conexión
    if sensor:
        st.success(f"✅ Sensor WTVB01-485 conectado en {st.session_state.sensor_port}")
    else:
        st.error("❌ Sensor no disponible - Generando datos de demostración")
        st.warning(f"💡 Para usar el sensor real: Cierra otras apps que usen {st.session_state.sensor_port} y reinicia el monitor")
        
    st.caption("🏭 Máquina: Grupo 1 (Soporte Rígido) | Norma ISO 20816-3 | Zona A ≤ 0.25 | B ≤ 0.5 | C ≤ 0.75 mm/s")
    
    # Leer datos del sensor o generar demostración
    sensor_ok = False
    if sensor:
        try:
            vx = sensor.read_register(58, functioncode=3, signed=True) / st.session_state.sensor_scale
            time.sleep(0.05)
            vy = sensor.read_register(59, functioncode=3, signed=True) / st.session_state.sensor_scale
            time.sleep(0.05)
            vz = sensor.read_register(60, functioncode=3, signed=True) / st.session_state.sensor_scale
            sensor_ok = True
        except Exception as e:
            error_msg = str(e)
            if len(st.session_state.all_readings) % 10 == 0:
                logger.error(f"Error comunicación sensor: {error_msg[:80]}")
                st.error(f"⚠️ Error comunicación sensor: {error_msg[:80]}")
            vx = 0.15 + 0.05 * np.sin(time.time() * 0.5)
            vy = 0.12 + 0.04 * np.cos(time.time() * 0.5)
            vz = 0.08 + 0.03 * np.sin(time.time() * 0.7)
    else:
        vx = 0.15 + 0.05 * np.sin(time.time() * 0.5)
        vy = 0.12 + 0.04 * np.cos(time.time() * 0.5)
        vz = 0.08 + 0.03 * np.sin(time.time() * 0.7)
        
    st.session_state.buffer_x.append(vx)
    st.session_state.buffer_y.append(vy)
    st.session_state.buffer_z.append(vz)
    
    rec = {'vx': vx, 'vy': vy, 'vz': vz, 'ts': datetime.utcnow().isoformat() + 'Z'}
    st.session_state.all_readings.append(rec)
    
    vx_rms = calcular_rms(st.session_state.buffer_x)
    vy_rms = calcular_rms(st.session_state.buffer_y)
    vz_rms = calcular_rms(st.session_state.buffer_z)
    vmax = max(vx_rms, vy_rms, vz_rms)
    zona, color = clasificar_zona(vmax)
    rpm = calcular_rpm_correlacionado(vmax)
    
    # ========== PUBLICAR A IoT ==========
    if IOT_AVAILABLE:
        try:
            if len(st.session_state.all_readings) % 30 == 0:
                if iot_config.THINGSPEAK_ENABLED:
                    logger.info(f"Publicando a ThingSpeak: vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}, rms={vmax:.3f}")
                    resultado = iot_handler.enviar_thingspeak(vx, vy, vz, vmax, zona)
                    if resultado:
                        st.session_state.iot_envios_ok += 1
                        st.session_state.ultimo_envio_thingspeak = datetime.now()
                    else:
                        st.session_state.iot_envios_error += 1
            if iot_config.MQTT_ENABLED or iot_config.WEBHOOK_ENABLED:
                iot_handler.publicar_datos(vx, vy, vz, vmax, zona, rpm)
            if iot_handler.verificar_alerta(zona, vmax):
                logger.critical(f"⚠️ Alerta ISO 20816-3 Zona {zona} detectada! Enviando avisos...")
                iot_handler.enviar_alerta_completa(zona, vmax, vx, vy, vz)
        except Exception as e:
            st.session_state.iot_envios_error += 1
            logger.error(f"Error IoT: {e}")
            
    # Guardar cada 50 lecturas
    if len(st.session_state.all_readings) % 50 == 0:
        save_historical_data()
        
    col1, col2 = st.columns([1, 3])
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
        
    # ========== CONTROL DE NOTIFICACIONES AUTOMÁTICAS (GMAIL & AZURE) ==========
    col1.markdown("---")
    col1.subheader("📧 Notificación Automática")
    
    # Cargar email institucional guardado de disco o usar geovanny.basantes@upec.edu.ec por defecto
    saved_email = ""
    if IOT_AVAILABLE and iot_handler.config.get('EMAIL_TO'):
        for em in iot_handler.config.get('EMAIL_TO'):
            if em not in iot_config.EMAIL_TO:
                saved_email = em
                break
                
    if 'email_institucional' not in st.session_state:
        st.session_state.email_institucional = saved_email if saved_email else 'geovanny.basantes@upec.edu.ec'
        
    # Campo para ingresar correo institucional de Azure
    email_institucional = col1.text_input(
        "Correo Institucional (Azure)",
        value=st.session_state.email_institucional,
        key='email_institucional_input'
    )
    st.session_state.email_institucional = email_institucional

    if 'email_notifications_enabled' not in st.session_state:
        st.session_state.email_notifications_enabled = iot_handler.config.get('EMAIL_ENABLED', False) if IOT_AVAILABLE else False
        
    # Sincronizar destinatarios y estado actual con el manejador de IoT
    if IOT_AVAILABLE:
        destinatarios = list(iot_config.EMAIL_TO)
        if email_institucional and "@" in email_institucional:
            if email_institucional not in destinatarios:
                destinatarios.append(email_institucional)
                
        # Guardar en disco si hay diferencias
        if (iot_handler.config.get('EMAIL_TO') != destinatarios or 
            iot_handler.config.get('EMAIL_ENABLED') != st.session_state.email_notifications_enabled):
            iot_handler.config['EMAIL_TO'] = destinatarios
            iot_handler.config['EMAIL_ENABLED'] = st.session_state.email_notifications_enabled
            iot_handler.save_email_config()
        
    if st.session_state.email_notifications_enabled:
        btn_label = "🔔 Desactivar Notificación Automática"
        col1.info("📧 Notificaciones: ACTIVADAS")
    else:
        btn_label = "🔕 Activar Notificación Automática"
        col1.warning("📧 Notificaciones: DESACTIVADAS")
        
    if col1.button(btn_label, use_container_width=True, key="gmail_notif_toggle"):
        if not IOT_AVAILABLE:
            st.error("El módulo IoT no está disponible.")
        else:
            # Invertir el estado
            nuevo_estado = not st.session_state.email_notifications_enabled
            st.session_state.email_notifications_enabled = nuevo_estado
            iot_handler.config['EMAIL_ENABLED'] = nuevo_estado
            
            # Asegurar que se sincronizan los destinatarios antes de mandar el correo de prueba
            destinatarios = list(iot_config.EMAIL_TO)
            if email_institucional and "@" in email_institucional:
                if email_institucional not in destinatarios:
                    destinatarios.append(email_institucional)
            iot_handler.config['EMAIL_TO'] = destinatarios
            
            if nuevo_estado:
                # Intentar enviar correo de prueba con el estado actual
                logger.info(f"Usuario activó notificaciones de correo. Enviando email de prueba a {destinatarios}...")
                with st.spinner("Enviando correo de prueba a Gmail y Azure..."):
                    asunto = f"📢 [HidroMira] Notificaciones de Estado Activadas"
                    cuerpo_html = f"""
                    <html>
                    <body style='font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;'>
                        <div style='max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 25px; border-top: 5px solid #10b981; box-shadow: 0 4px 10px rgba(0,0,0,0.1);'>
                            <h2 style='color: #10b981; text-align: center;'>⚡ Notificaciones HidroMira Activas</h2>
                            <p>Hola,</p>
                            <p>Has activado correctamente las notificaciones por correo para el monitoreo de vibraciones de la hidroturbina.</p>
                            <hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;'>
                            <h3 style='color: #1e293b;'>Estado Actual de la Máquina:</h3>
                            <table style='width: 100%; border-collapse: collapse; margin-top: 10px;'>
                                <tr>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: bold;'>Zona ISO 20816-3:</td>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; color: #ef4444; font-weight: bold;'>Zona {zona}</td>
                                </tr>
                                <tr>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: bold;'>Valor RMS Máximo:</td>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9;'>{vmax:.3f} mm/s</td>
                                </tr>
                                <tr>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: bold;'>Eje X:</td>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9;'>{vx:.3f} mm/s</td>
                                </tr>
                                <tr>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: bold;'>Eje Y:</td>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9;'>{vy:.3f} mm/s</td>
                                </tr>
                                <tr>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: bold;'>Eje Z:</td>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9;'>{vz:.3f} mm/s</td>
                                </tr>
                                <tr>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: bold;'>RPM:</td>
                                    <td style='padding: 8px; border-bottom: 1px solid #f1f5f9;'>{rpm:.0f} RPM</td>
                                </tr>
                            </table>
                            <p style='margin-top: 25px; font-size: 12px; color: #64748b; text-align: center;'>
                                Sistema HidroMira - Monitoreo Industrial en Tiempo Real
                            </p>
                        </div>
                    </body>
                    </html>
                    """
                    
                    enviado = iot_handler.enviar_email(asunto, cuerpo_html)
                    if enviado:
                        logger.info("Correo de prueba enviado correctamente.")
                        st.toast("✅ Correo de prueba enviado con éxito.", icon="📧")
                    else:
                        logger.error("Fallo al enviar correo de prueba (verificar credenciales de Gmail).")
                        st.toast("❌ Error al enviar correo. Verifica la clave en iot_config.py.", icon="⚠️")
                        # Restablecer estado a inactivo si falló el envío de prueba
                        st.session_state.email_notifications_enabled = False
                        iot_handler.config['EMAIL_ENABLED'] = False
            else:
                logger.info("Usuario desactivó las notificaciones de correo.")
                st.toast("🔕 Notificaciones desactivadas.", icon="🔌")
            st.rerun()
        
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
    
    st.markdown("---")
    col1_f, col2_f, col3_f, col4_f = st.columns(4)
    
    with col1_f:
        if sensor_ok:
            st.success("📡 DATOS REALES DEL SENSOR")
        else:
            st.error("⚠️ DATOS DE DEMOSTRACIÓN")
            st.caption("Sensor no conectado")
            
    with col2_f:
        if IOT_AVAILABLE and iot_config.THINGSPEAK_ENABLED:
            if st.session_state.ultimo_envio_thingspeak:
                tiempo_desde = (datetime.now() - st.session_state.ultimo_envio_thingspeak).seconds
                st.info(f"☁️ ThingSpeak: {tiempo_desde}s")
            else:
                st.info("☁️ ThingSpeak: Esperando...")
        else:
            st.error("☁️ ThingSpeak: OFF")
            
    with col3_f:
        if IOT_AVAILABLE:
            st.metric("✅ Envíos OK", st.session_state.iot_envios_ok)
        else:
            st.metric("❌ Errores", st.session_state.iot_envios_error)
            
    with col4_f:
        st.caption(f"🔄 {datetime.now().strftime('%H:%M:%S')} | {len(st.session_state.all_readings)} lecturas")

elif page == "📊 Análisis Histórico":
    st.subheader("Análisis Histórico - Diagnóstico ISO 20816-3")
    st.caption("🏭 Máquina: Grupo 1 (Soporte Rígido) | Zona A ≤ 0.25 | Zona B ≤ 0.5 | Zona C ≤ 0.75 | Zona D > 0.75 mm/s")
    
    # Cargar JSON solo UNA VEZ cuando Tab 1 se activa
    if not st.session_state.json_loaded:
        try:
            st.session_state.all_readings = db.load_historical_data()
        except Exception as e:
            logger.error(f"Error cargando histórico de base de datos: {e}")
        st.session_state.json_loaded = True
    
    # Selector de período
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Últimos 20s", width='stretch'):
            st.session_state.period_view = "Últimos 20s"
    with col2:
        if st.button("Último día", width='stretch'):
            st.session_state.period_view = "Último día"
    with col3:
        if st.button("Última semana", width='stretch'):
            st.session_state.period_view = "Última semana"
    with col4:
        if st.button("Último mes", width='stretch'):
            st.session_state.period_view = "Último mes"
    with col5:
        if st.button("Histórico completo", width='stretch'):
            st.session_state.period_view = "Histórico completo"
    
    # Selector de rango de fechas personalizado
    st.subheader("📅 Seleccionar período personalizado")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Desde:", key="start_date")
    with col2:
        end_date = st.date_input("Hasta:", key="end_date")
    
    # Filtrar datos según período
    now = datetime.utcnow()
    period = st.session_state.period_view
    
    if period == "Últimos 20s":
        filtered_readings = st.session_state.all_readings[-2000:] if len(st.session_state.all_readings) > 2000 else st.session_state.all_readings
    elif period == "Último día":
        start_time = now - timedelta(days=1)
        filtered_readings = []
        for r in st.session_state.all_readings:
            try:
                ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                ts_naive = ts.replace(tzinfo=None)
                if ts_naive >= start_time:
                    filtered_readings.append(r)
            except:
                pass
    elif period == "Última semana":
        start_time = now - timedelta(weeks=1)
        filtered_readings = []
        for r in st.session_state.all_readings:
            try:
                ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                ts_naive = ts.replace(tzinfo=None)
                if ts_naive >= start_time:
                    filtered_readings.append(r)
            except:
                pass
    elif period == "Último mes":
        start_time = now - timedelta(days=30)
        filtered_readings = []
        for r in st.session_state.all_readings:
            try:
                ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                ts_naive = ts.replace(tzinfo=None)
                if ts_naive >= start_time:
                    filtered_readings.append(r)
            except:
                pass
    else:  # Período personalizado o Histórico completo
        if start_date and end_date:
            filtered_readings = []
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            for r in st.session_state.all_readings:
                try:
                    ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                    ts_naive = ts.replace(tzinfo=None)
                    if start_dt <= ts_naive <= end_dt:
                        filtered_readings.append(r)
                except:
                    pass
        else:
            filtered_readings = st.session_state.all_readings
    
    st.info(f"📊 Mostrando {len(filtered_readings)} registros de {len(st.session_state.all_readings)} totales")
    
    if filtered_readings:
        # Extraer datos
        vx_vals = [r['vx'] for r in filtered_readings]
        vy_vals = [r['vy'] for r in filtered_readings]
        vz_vals = [r['vz'] for r in filtered_readings]
        
        timestamps = []
        for r in filtered_readings:
            try:
                ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                timestamps.append(ts)
            except:
                timestamps.append(None)
        
        # Formatear etiquetas
        if period == "Últimos 20s":
            x_labels = [ts.strftime("%H:%M:%S") if ts else "" for ts in timestamps]
        elif period == "Último día":
            x_labels = [ts.strftime("%H:%M") if ts else "" for ts in timestamps]
        elif period == "Última semana":
            x_labels = [ts.strftime("%a %H:%M") if ts else "" for ts in timestamps]
        else:
            x_labels = [ts.strftime("%Y-%m-%d") if ts else "" for ts in timestamps]
        
        # Crear gráficas
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("📊 Estadísticas")
            st.metric("Registros", len(filtered_readings))
            st.metric("Prom X (Horiz.)", f"{np.mean(vx_vals):.2f} mm/s")
            st.metric("Prom Y (Vert.)", f"{np.mean(vy_vals):.2f} mm/s")
            st.metric("Prom Z (Axial)", f"{np.mean(vz_vals):.2f} mm/s")
            st.metric("Max X (Horiz.)", f"{max(vx_vals):.2f} mm/s")
            st.metric("Max Y (Vert.)", f"{max(vy_vals):.2f} mm/s")
            st.metric("Max Z (Axial)", f"{max(vz_vals):.2f} mm/s")
        
        with col2:
            # Gráfica 1: X (Horizontal)
            fig_x = go.Figure(go.Scatter(
                x=x_labels if x_labels else list(range(len(vx_vals))),
                y=vx_vals,
                mode='lines+markers',
                line=dict(color='#ff6b6b', width=2),
                fill='tozeroy',
                name='X - Horizontal'
            ))
            max_x = max(vx_vals) if vx_vals else 0
            fig_x.update_layout(template="plotly_dark", height=350, 
                              yaxis=dict(range=[0, max(max_x, 3.0) * 1.15], title="Velocidad (mm/s)"),
                              title="Velocidad X (Horizontal)", xaxis_title="Tiempo")
            st.plotly_chart(fig_x, width='stretch')
        
        col1, col2 = st.columns([1, 2])
        with col2:
            # Gráfica 2: Y (Vertical)
            fig_y = go.Figure(go.Scatter(
                x=x_labels if x_labels else list(range(len(vy_vals))),
                y=vy_vals,
                mode='lines+markers',
                line=dict(color='#51cf66', width=2),
                fill='tozeroy',
                name='Y - Vertical'
            ))
            max_y = max(vy_vals) if vy_vals else 0
            fig_y.update_layout(template="plotly_dark", height=350, 
                              yaxis=dict(range=[0, max(max_y, 3.0) * 1.15], title="Velocidad (mm/s)"),
                              title="Velocidad Y (Vertical)", xaxis_title="Tiempo")
            st.plotly_chart(fig_y, width='stretch')
        
        col1, col2 = st.columns([1, 2])
        with col2:
            # Gráfica 3: Z (Axial)
            fig_z = go.Figure(go.Scatter(
                x=x_labels if x_labels else list(range(len(vz_vals))),
                y=vz_vals,
                mode='lines+markers',
                line=dict(color='#4dabf7', width=2),
                fill='tozeroy',
                name='Z - Axial'
            ))
            max_z = max(vz_vals) if vz_vals else 0
            fig_z.update_layout(template="plotly_dark", height=350, 
                              yaxis=dict(range=[0, max(max_z, 3.0) * 1.15], title="Velocidad (mm/s)"),
                              title="Velocidad Z (Axial)", xaxis_title="Tiempo")
            st.plotly_chart(fig_z, width='stretch')
    else:
        st.warning("📭 No hay datos para este período")
    
    # ========== GRÁFICAS ISO 20816-3 ==========
    st.markdown("---")
    st.subheader("🔬 Diagnóstico ISO 20816-3 (Grupo 1)")
    
    if filtered_readings and len(filtered_readings) > 0:
        vx_vals = [r['vx'] for r in filtered_readings]
        vy_vals = [r['vy'] for r in filtered_readings]
        vz_vals = [r['vz'] for r in filtered_readings]
        
        # Calcular RMS para cada eje
        rms_x = [np.sqrt(np.mean(np.array(vx_vals[:i+1])**2)) for i in range(len(vx_vals))]
        rms_y = [np.sqrt(np.mean(np.array(vy_vals[:i+1])**2)) for i in range(len(vy_vals))]
        rms_z = [np.sqrt(np.mean(np.array(vz_vals[:i+1])**2)) for i in range(len(vz_vals))]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfica ISO para X
            fig_iso_x = go.Figure()
            
            # Agregar zonas como áreas sombreadas
            fig_iso_x.add_hline(y=ZONA_A_MAX, line_dash="dash", line_color="green", annotation_text="Zona A/B")
            fig_iso_x.add_hline(y=ZONA_B_MAX, line_dash="dash", line_color="orange", annotation_text="Zona B/C")
            fig_iso_x.add_hline(y=ZONA_C_MAX, line_dash="dash", line_color="red", annotation_text="Zona C/D")
            
            fig_iso_x.add_vrect(x0=0, x1=len(rms_x), y0=0, y1=ZONA_A_MAX,
                              fillcolor="green", opacity=0.1, layer="below", line_width=0)
            fig_iso_x.add_vrect(x0=0, x1=len(rms_x), y0=ZONA_A_MAX, y1=ZONA_B_MAX,
                              fillcolor="yellow", opacity=0.1, layer="below", line_width=0)
            fig_iso_x.add_vrect(x0=0, x1=len(rms_x), y0=ZONA_B_MAX, y1=ZONA_C_MAX,
                              fillcolor="orange", opacity=0.1, layer="below", line_width=0)
            fig_iso_x.add_vrect(x0=0, x1=len(rms_x), y0=ZONA_C_MAX, y1=5,
                              fillcolor="red", opacity=0.1, layer="below", line_width=0)
            
            fig_iso_x.add_trace(go.Scatter(y=rms_x, mode='lines', name='RMS X',
                                          line=dict(color='#ff6b6b', width=3)))
            
            max_rms_x = max(rms_x) if rms_x else 0
            fig_iso_x.update_layout(
                template="plotly_dark", height=400, 
                yaxis=dict(range=[0, max(max_rms_x, 3.0) * 1.15], title="RMS (mm/s)"),
                title="Eje X - Diagrama ISO 20816-3",
                hovermode='x unified'
            )
            st.plotly_chart(fig_iso_x, width='stretch')
        
        with col2:
            # Gráfica ISO para Y
            fig_iso_y = go.Figure()
            
            fig_iso_y.add_hline(y=ZONA_A_MAX, line_dash="dash", line_color="green")
            fig_iso_y.add_hline(y=ZONA_B_MAX, line_dash="dash", line_color="orange")
            fig_iso_y.add_hline(y=ZONA_C_MAX, line_dash="dash", line_color="red")
            
            fig_iso_y.add_vrect(x0=0, x1=len(rms_y), y0=0, y1=ZONA_A_MAX,
                              fillcolor="green", opacity=0.1, layer="below", line_width=0)
            fig_iso_y.add_vrect(x0=0, x1=len(rms_y), y0=ZONA_A_MAX, y1=ZONA_B_MAX,
                              fillcolor="yellow", opacity=0.1, layer="below", line_width=0)
            fig_iso_y.add_vrect(x0=0, x1=len(rms_y), y0=ZONA_B_MAX, y1=ZONA_C_MAX,
                              fillcolor="orange", opacity=0.1, layer="below", line_width=0)
            fig_iso_y.add_vrect(x0=0, x1=len(rms_y), y0=ZONA_C_MAX, y1=5,
                              fillcolor="red", opacity=0.1, layer="below", line_width=0)
            
            fig_iso_y.add_trace(go.Scatter(y=rms_y, mode='lines', name='RMS Y',
                                          line=dict(color='#51cf66', width=3)))
            
            max_rms_y = max(rms_y) if rms_y else 0
            fig_iso_y.update_layout(
                template="plotly_dark", height=400,
                yaxis=dict(range=[0, max(max_rms_y, 3.0) * 1.15], title="RMS (mm/s)"),
                title="Eje Y - Diagrama ISO 20816-3",
                hovermode='x unified'
            )
            st.plotly_chart(fig_iso_y, width='stretch')
        
        # Gráfica Z
        col1, col2 = st.columns([1, 1])
        with col1:
            fig_iso_z = go.Figure()
            
            fig_iso_z.add_hline(y=ZONA_A_MAX, line_dash="dash", line_color="green")
            fig_iso_z.add_hline(y=ZONA_B_MAX, line_dash="dash", line_color="orange")
            fig_iso_z.add_hline(y=ZONA_C_MAX, line_dash="dash", line_color="red")
            
            fig_iso_z.add_vrect(x0=0, x1=len(rms_z), y0=0, y1=ZONA_A_MAX,
                              fillcolor="green", opacity=0.1, layer="below", line_width=0)
            fig_iso_z.add_vrect(x0=0, x1=len(rms_z), y0=ZONA_A_MAX, y1=ZONA_B_MAX,
                              fillcolor="yellow", opacity=0.1, layer="below", line_width=0)
            fig_iso_z.add_vrect(x0=0, x1=len(rms_z), y0=ZONA_B_MAX, y1=ZONA_C_MAX,
                              fillcolor="orange", opacity=0.1, layer="below", line_width=0)
            fig_iso_z.add_vrect(x0=0, x1=len(rms_z), y0=ZONA_C_MAX, y1=5,
                              fillcolor="red", opacity=0.1, layer="below", line_width=0)
            
            fig_iso_z.add_trace(go.Scatter(y=rms_z, mode='lines', name='RMS Z',
                                          line=dict(color='#4dabf7', width=3)))
            
            max_rms_z = max(rms_z) if rms_z else 0
            fig_iso_z.update_layout(
                template="plotly_dark", height=400,
                yaxis=dict(range=[0, max(max_rms_z, 3.0) * 1.15], title="RMS (mm/s)"),
                title="Eje Z - Diagrama ISO 20816-3",
                hovermode='x unified'
            )
            st.plotly_chart(fig_iso_z, width='stretch')
        
        # ========== DETECCIÓN DE ANOMALÍAS ==========
        st.markdown("---")
        st.subheader("🚨 Detección de Anomalías Periódicas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Anomalías Eje X**")
            anomalias_x = detectar_anomalias(vx_vals, threshold_factor=2.0)
            if anomalias_x:
                st.error(f"🔴 {len(anomalias_x)} anomalías detectadas")
                for idx, val in anomalias_x[:5]:  # Top 5
                    st.caption(f"Índice {idx}: {val:.2f} mm/s")
            else:
                st.success("✅ Sin anomalías")
        
        with col2:
            st.write("**Anomalías Eje Y**")
            anomalias_y = detectar_anomalias(vy_vals, threshold_factor=2.0)
            if anomalias_y:
                st.error(f"🔴 {len(anomalias_y)} anomalías detectadas")
                for idx, val in anomalias_y[:5]:
                    st.caption(f"Índice {idx}: {val:.2f} mm/s")
            else:
                st.success("✅ Sin anomalías")
        
        with col3:
            st.write("**Anomalías Eje Z**")
            anomalias_z = detectar_anomalias(vz_vals, threshold_factor=2.0)
            if anomalias_z:
                st.error(f"🔴 {len(anomalias_z)} anomalías detectadas")
                for idx, val in anomalias_z[:5]:
                    st.caption(f"Índice {idx}: {val:.2f} mm/s")
            else:
                st.success("✅ Sin anomalías")
        
        # Gráfica de anomalías
        fig_anomalias = go.Figure()
        fig_anomalias.add_trace(go.Scatter(y=vx_vals, mode='lines', name='X', line=dict(color='#ff6b6b')))
        fig_anomalias.add_trace(go.Scatter(y=vy_vals, mode='lines', name='Y', line=dict(color='#51cf66')))
        fig_anomalias.add_trace(go.Scatter(y=vz_vals, mode='lines', name='Z', line=dict(color='#4dabf7')))
        
        # Marcar anomalías
        for idx, val in anomalias_x:
            fig_anomalias.add_scatter(x=[idx], y=[val], mode='markers', 
                                     marker=dict(size=15, color='red', symbol='star'),
                                     name='Anomalía X', showlegend=False)
        for idx, val in anomalias_y:
            fig_anomalias.add_scatter(x=[idx], y=[val], mode='markers',
                                     marker=dict(size=15, color='darkred', symbol='diamond'),
                                     name='Anomalía Y', showlegend=False)
        
        max_anom = max(
            max(vx_vals) if vx_vals else 0,
            max(vy_vals) if vy_vals else 0,
            max(vz_vals) if vz_vals else 0,
            3.0
        )
        fig_anomalias.update_layout(
            template="plotly_dark", height=350,
            title="Detección de Anomalías Periódicas",
            yaxis=dict(range=[0, max_anom * 1.15], title="Velocidad (mm/s)"),
            hovermode='x unified'
        )
        st.plotly_chart(fig_anomalias, width='stretch')

        # ========== IMÁGENES DE REFERENCIA ==========
        st.markdown("---")
        st.subheader("🔍 Referencias de la Turbina Francis e ISO 20816-3")
        
        col1_img, col2_img = st.columns(2)
        with col1_img:
            turbina_img_path = os.path.join(os.path.dirname(__file__), 'hidromira-turbina.png')
            if os.path.exists(turbina_img_path):
                st.image(turbina_img_path, caption="Esquema Turbina Francis Hidromira", use_column_width=True)
                
        with col2_img:
            iso_img_path = os.path.join(os.path.dirname(__file__), 'images', 'iso20816.png')
            if os.path.exists(iso_img_path):
                st.image(iso_img_path, caption="Límites de Vibración según Norma ISO 20816-3", use_column_width=True)
                st.markdown("<p style='text-align: center; font-weight: bold; font-size: 15px;'>Hidromira pertenece a Grupo 1: Máquina Grande con Fundación Rígida</p>", unsafe_allow_html=True)

# ========== TAB 2: DATOS TÉCNICOS ==========

elif page == "🏭 Datos Técnicos y Mantenimiento":
    st.subheader("🏭 Datos Técnicos de la Hidroturbina")
    
    # Mostrar imagen de la turbina
    image_path = os.path.join(os.path.dirname(__file__), 'images', 'turbina.jpg')
    if os.path.exists(image_path):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image_path, use_column_width=True, caption="Turbina Francis - HidroMira")
    
    st.markdown("---")
    
    # Información técnica de la turbina
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Especificaciones de la Máquina")
        st.markdown("""
        **Proyecto:** HidroMira
        
        **Fabricante:** DELTA - DELFINI & CIA., S.A.
        
        **Tipo de Turbina:** Francis
        
        **Diámetro Rodete:** 465 mm
        
        **Velocidad de Rotación:** 1200 rpm
        
        **Grupo Normativo:** ISO 20816-3 Grupo 1
        
        **Tipo de Soporte:** Rígido
        
        **Diseñador:** Riccardo Delfini
        
        **Fecha de Diseño:** 06-may-11
        """)
    
    with col2:
        st.subheader("⚙️ Parámetros de Operación")
        st.markdown("""
        **Constante Gravitacional:** 9.81 m/s²
        
        **Caída Neta:** 77.6 m
        
        **Caudal Máximo:** 1.77 m³/s
        
        **Potencia Mecánica Máxima:** 1165.1 kW
        
        **Eficiencia Generador:** 96.5%
        
        **Eficiencia Transmisión:** 100%
        
        **Potencia Generada:** 1124.3 kW
        """)
    
    st.markdown("---")
    
    # Historial de mantenimiento
    st.subheader("🔧 Historial de Mantenimiento")

    can_edit_maintenance = current_user["role"] in {"admin", "ingeniero_jefe"}
    
    # Datos de mantenimiento (cargados de base de datos JSON persistente)
    if 'maintenance_log' not in st.session_state:
        try:
            st.session_state.maintenance_log = db.load_maintenance_log()
        except Exception as e:
            logger.error(f"Error al leer maintenance log: {e}")
            st.session_state.maintenance_log = []
            
        if not st.session_state.maintenance_log:
            st.session_state.maintenance_log = [
                {"fecha": "2024-12-15", "tipo": "Preventivo", "descripcion": "Limpieza general y lubricación", "técnico": "Carlos Rodríguez"},
                {"fecha": "2024-11-20", "tipo": "Correctivo", "descripcion": "Reemplazo de sello de eje", "técnico": "Juan Pérez"},
                {"fecha": "2024-10-10", "tipo": "Preventivo", "descripcion": "Inspección de álabes", "técnico": "María González"},
                {"fecha": "2024-09-05", "tipo": "Correctivo", "descripcion": "Ajuste de cojinetes", "técnico": "Carlos Rodríguez"},
                {"fecha": "2024-08-12", "tipo": "Preventivo", "descripcion": "Cambio de aceite del generador", "técnico": "Roberto Sánchez"},
            ]
    
    # Mostrar historial en tabla
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("**Últimos trabajos realizados:**")
        for i, mantenimiento in enumerate(st.session_state.maintenance_log):
            with st.expander(f"🔧 {mantenimiento['fecha']} - {mantenimiento['tipo']}"):
                st.write(f"**Descripción:** {mantenimiento['descripcion']}")
                st.write(f"**Técnico:** {mantenimiento['técnico']}")
    
    with col2:
        if can_edit_maintenance:
            if st.button("➕ Nuevo Registro"):
                st.session_state.show_new_maintenance = True
        else:
            st.info("Solo admin e ingeniero en jefe pueden registrar mantenimiento.")
    
    # Formulario para nuevo mantenimiento
    if st.session_state.get('show_new_maintenance', False):
        require_role(
            current_user,
            {"admin", "ingeniero_jefe"},
            message="Solo admin o ingeniero en jefe pueden registrar mantenimiento.",
        )
        st.markdown("---")
        st.subheader("📝 Registrar Nuevo Mantenimiento")
        
        col1, col2 = st.columns(2)
        with col1:
            new_fecha = st.date_input("Fecha del Mantenimiento")
            new_tipo = st.selectbox("Tipo de Mantenimiento", ["Preventivo", "Correctivo", "Emergencia"])
        
        with col2:
            new_tecnico = st.text_input("Técnico Responsable")
            new_descripcion = st.text_area("Descripción del Trabajo")
        
        if st.button("💾 Guardar Registro"):
            nuevo_registro = {
                "fecha": new_fecha.isoformat(),
                "tipo": new_tipo,
                "descripcion": new_descripcion,
                "técnico": new_tecnico
            }
            st.session_state.maintenance_log.insert(0, nuevo_registro)
            # Guardar en base de datos
            try:
                db.save_maintenance_log(st.session_state.maintenance_log)
                logger.info(f"Nuevo registro de mantenimiento guardado y persistido: [{new_tipo}] por {new_tecnico}. Descripción: {new_descripcion}")
            except Exception as e:
                logger.error(f"Error al guardar registro de mantenimiento: {e}")
            st.success("✅ Registro guardado exitosamente")
            st.session_state.show_new_maintenance = False
            st.rerun()
    
    st.markdown("---")
    
    # Próximos mantenimientos programados
    st.subheader("📅 Mantenimientos Programados")
    st.markdown("""
    | Fecha Programada | Tipo | Descripción |
    |---|---|---|
    | 2026-02-15 | Preventivo | Inspección anual completa |
    | 2026-03-20 | Preventivo | Limpieza de inyectores |
    | 2026-04-10 | Correctivo | Reemplazo de rodamientos (si es necesario) |
    | 2026-06-01 | Preventivo | Revisión de sistema de regulación |
    """)

    st.markdown("---")
    st.subheader("💾 Copias de Seguridad y Respaldos")
    st.write("Genera una copia de seguridad instantánea de la base de datos y los archivos del sistema.")
    
    col_back, col_info = st.columns([1, 2])
    with col_back:
        if st.button("🚀 Crear Respaldo Ahora", use_container_width=True):
            ok, msg = db.ejecutar_respaldo('Manual')
            if ok:
                st.success(msg)
            else:
                st.error(msg)
                
    with col_info:
        # Cargar último respaldo si existe
        status_path = os.path.join(os.path.dirname(__file__), 'backup_status.json')
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                st.info(f"📅 Último respaldo: {status.get('ultimo_respaldo', 'Nunca')} ({status.get('tipo', '')})")
            except:
                st.info("No se han detectado respaldos previos.")
        else:
            st.info("No se han detectado respaldos previos.")

# ========== TAB 3: RENDIMIENTO VS VIBRACIONES ==========

elif page == "⚙️ Rendimiento vs Vibraciones":
    st.subheader("⚙️ Análisis de Rendimiento vs Vibraciones")
    st.caption("Relación entre niveles de vibración (ISO 20816-3) y rendimiento de la turbina")
    
    # Función para calcular rendimiento en base a vibraciones
    def calcular_rendimiento(rms_valor):
        """
        Calcula rendimiento basado en RMS de vibraciones
        Zona A (0-1): 100-95% rendimiento
        Zona B (1-2): 95-80% rendimiento
        Zona C (2-3): 80-60% rendimiento
        Zona D (>3): <60% rendimiento (falla inminente)
        """
        if rms_valor <= ZONA_A_MAX:
            # Zona A: 100% a 95%
            return 100 - (rms_valor / ZONA_A_MAX) * 5
        elif rms_valor <= ZONA_B_MAX:
            # Zona B: 95% a 80%
            degradacion_b = ((rms_valor - ZONA_A_MAX) / (ZONA_B_MAX - ZONA_A_MAX)) * 15
            return 95 - degradacion_b
        elif rms_valor <= ZONA_C_MAX:
            # Zona C: 80% a 60%
            degradacion_c = ((rms_valor - ZONA_B_MAX) / (ZONA_C_MAX - ZONA_B_MAX)) * 20
            return 80 - degradacion_c
        else:
            # Zona D: <60%
            degradacion_d = ((rms_valor - ZONA_C_MAX) / ZONA_C_MAX) * 40
            return max(20, 60 - degradacion_d)
    
    if st.session_state.all_readings and len(st.session_state.all_readings) > 0:
        # Calcular RMS global
        all_vx = [r['vx'] for r in st.session_state.all_readings]
        all_vy = [r['vy'] for r in st.session_state.all_readings]
        all_vz = [r['vz'] for r in st.session_state.all_readings]
        
        rms_global_x = np.sqrt(np.mean(np.array(all_vx)**2))
        rms_global_y = np.sqrt(np.mean(np.array(all_vy)**2))
        rms_global_z = np.sqrt(np.mean(np.array(all_vz)**2))
        rms_global = max(rms_global_x, rms_global_y, rms_global_z)
        
        # Calcular rendimientos
        rendimiento_x = calcular_rendimiento(rms_global_x)
        rendimiento_y = calcular_rendimiento(rms_global_y)
        rendimiento_z = calcular_rendimiento(rms_global_z)
        rendimiento_promedio = np.mean([rendimiento_x, rendimiento_y, rendimiento_z])
        
        # Métricas de rendimiento
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Rendimiento Eje X", f"{rendimiento_x:.1f}%", 
                     delta=f"{rendimiento_x - 100:.1f}%" if rendimiento_x < 100 else "Normal")
        
        with col2:
            st.metric("Rendimiento Eje Y", f"{rendimiento_y:.1f}%",
                     delta=f"{rendimiento_y - 100:.1f}%" if rendimiento_y < 100 else "Normal")
        
        with col3:
            st.metric("Rendimiento Eje Z", f"{rendimiento_z:.1f}%",
                     delta=f"{rendimiento_z - 100:.1f}%" if rendimiento_z < 100 else "Normal")
        
        with col4:
            if rendimiento_promedio >= 95:
                st.success(f"Rendimiento Promedio: {rendimiento_promedio:.1f}%")
            elif rendimiento_promedio >= 80:
                st.warning(f"Rendimiento Promedio: {rendimiento_promedio:.1f}%")
            else:
                st.error(f"Rendimiento Promedio: {rendimiento_promedio:.1f}%")
        
        st.markdown("---")
        
        # Gráfica interactiva: Vibración vs Rendimiento
        col1, col2 = st.columns(2)
        
        with col1:
            # Crear curva teórica
            vibration_range = np.linspace(0, 1.5, 100)
            rendimiento_range = [calcular_rendimiento(v) for v in vibration_range]
            
            fig_relacion = go.Figure()
            
            # Agregar zonas ISO
            fig_relacion.add_vrect(x0=0, x1=ZONA_A_MAX, fillcolor="green", opacity=0.1, annotation_text="Zona A")
            fig_relacion.add_vrect(x0=ZONA_A_MAX, x1=ZONA_B_MAX, fillcolor="yellow", opacity=0.1, annotation_text="Zona B")
            fig_relacion.add_vrect(x0=ZONA_B_MAX, x1=ZONA_C_MAX, fillcolor="orange", opacity=0.1, annotation_text="Zona C")
            fig_relacion.add_vrect(x0=ZONA_C_MAX, x1=1.5, fillcolor="red", opacity=0.1, annotation_text="Zona D")
            
            # Línea de rendimiento
            fig_relacion.add_trace(go.Scatter(
                x=vibration_range, y=rendimiento_range,
                mode='lines', name='Rendimiento Teórico',
                line=dict(color='#4dabf7', width=3)
            ))
            
            # Puntos actuales
            fig_relacion.add_trace(go.Scatter(
                x=[rms_global_x, rms_global_y, rms_global_z],
                y=[rendimiento_x, rendimiento_y, rendimiento_z],
                mode='markers', name='Valores Actuales',
                marker=dict(size=12, color=['#ff6b6b', '#51cf66', '#4dabf7'])
            ))
            
            fig_relacion.update_layout(
                template="plotly_dark", height=400,
                xaxis=dict(title="RMS Vibración (mm/s)", range=[0, 1.5]),
                yaxis=dict(title="Rendimiento (%)", range=[0, 110]),
                title="Relación Vibración - Rendimiento",
                hovermode='x unified'
            )
            st.plotly_chart(fig_relacion, width='stretch')
        
        with col2:
            # Tabla de pérdida de rendimiento
            st.subheader("📉 Pérdida de Rendimiento por Zona")
            
            df_perdida = {
                "Zona": ["A", "B", "C", "D"],
                "Rango (mm/s)": ["0 - 0.25", "0.25 - 0.5", "0.5 - 0.75", "> 0.75"],
                "Rendimiento": ["95-100%", "80-95%", "60-80%", "< 60%"],
                "Pérdida": ["0-5%", "5-20%", "20-40%", "> 40%"],
                "Estado": ["✅ Normal", "⚠️ Vigilancia", "🔴 Corrección", "🚫 Inaceptable"]
            }
            
            st.dataframe(df_perdida, width='stretch', hide_index=True)
            
            st.markdown("---")
            st.subheader("💡 Recomendaciones")
            
            zona_actual, _ = clasificar_zona(rms_global)
            
            if zona_actual == "A":
                st.success("""
                ✅ **Máquina en Excelente Estado**
                - Rendimiento óptimo
                - Continuar monitoreo rutinario
                - Próximo mantenimiento preventivo: 6 meses
                """)
            elif zona_actual == "B":
                st.warning("""
                ⚠️ **Máquina Requiere Vigilancia**
                - Rendimiento degradado 5-20%
                - Aumentar frecuencia de monitoreo
                - Programar mantenimiento preventivo en 2-3 meses
                - Revisar cojinetes y alineación
                """)
            elif zona_actual == "C":
                st.error("""
                🔴 **Máquina Requiere Corrección Inmediata**
                - Rendimiento degradado 20-40%
                - Pérdidas económicas significativas
                - Inspección detallada recomendada
                - Programar mantenimiento correctivo urgente
                - Posibles causas: desbalance, falta de lubricación, grietas
                """)
            else:
                st.error("""
                🚫 **Estado Crítico - Falla Inminente**
                - Rendimiento < 60%
                - Riesgo de parada de emergencia
                - **DETENER OPERACIÓN INMEDIATAMENTE**
                - Inspección completa requerida
                - Reparación mayor necesaria
                """)
        
        st.markdown("---")
        
        # Gráfica histórica de rendimiento
        st.subheader("📈 Histórico de Rendimiento (Últimos 7 días)")
        
        # Calcular rendimiento diario si hay datos
        if len(st.session_state.all_readings) > 100:
            # Agrupar por día
            dias = {}
            for r in st.session_state.all_readings[-2000:]:  # Últimos 2000 registros
                try:
                    ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                    dia = ts.date()
                    if dia not in dias:
                        dias[dia] = {"vx": [], "vy": [], "vz": []}
                    dias[dia]["vx"].append(r['vx'])
                    dias[dia]["vy"].append(r['vy'])
                    dias[dia]["vz"].append(r['vz'])
                except:
                    pass
            
            if dias:
                fechas = sorted(dias.keys())
                rendimientos = []
                
                for fecha in fechas:
                    rms_x = np.sqrt(np.mean(np.array(dias[fecha]["vx"])**2))
                    rms_y = np.sqrt(np.mean(np.array(dias[fecha]["vy"])**2))
                    rms_z = np.sqrt(np.mean(np.array(dias[fecha]["vz"])**2))
                    rend = np.mean([calcular_rendimiento(rms_x), calcular_rendimiento(rms_y), calcular_rendimiento(rms_z)])
                    rendimientos.append(rend)
                
                fig_historico = go.Figure()
                fig_historico.add_trace(go.Scatter(
                    x=fechas, y=rendimientos,
                    mode='lines+markers',
                    name='Rendimiento Diario',
                    line=dict(color='#ffd700', width=3),
                    fill='tozeroy'
                ))
                
                # Líneas de referencia
                fig_historico.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Mínimo Aceptable")
                fig_historico.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="Alerta")
                fig_historico.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Crítico")
                
                fig_historico.update_layout(
                    template="plotly_dark", height=350,
                    xaxis_title="Fecha",
                    yaxis_title="Rendimiento (%)",
                    yaxis=dict(range=[0, 110]),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_historico, width='stretch')
    else:
        st.info("⏳ Esperando datos del sensor para calcular rendimiento...")

elif page == "🔧 Control de Motor y Servo":
    st.subheader("🔧 Control de Motor y Servo")
    st.caption("Panel serial para el motor L298N y Servomotor. Usa un puerto distinto al sensor ModBus si ambos dispositivos están conectados.")

    # Obtener puertos disponibles del sistema
    puertos_sistema = obtener_puertos_serial_disponibles()

    # Preparamos los puertos para el Sensor
    puertos_sensor = list(puertos_sistema)
    if st.session_state.sensor_port not in puertos_sensor:
        puertos_sensor = [st.session_state.sensor_port] + puertos_sensor
    try:
        indice_sensor = puertos_sensor.index(st.session_state.sensor_port)
    except ValueError:
        indice_sensor = 0

    # Preparamos los puertos para el Motor/Arduino
    puertos_motor = list(puertos_sistema)
    if not puertos_motor:
        puertos_motor = [st.session_state.motor_port]
    if st.session_state.motor_port not in puertos_motor:
        puertos_motor = [st.session_state.motor_port] + puertos_motor
    try:
        indice_motor = puertos_motor.index(st.session_state.motor_port)
    except ValueError:
        indice_motor = 0

    col_config, col_estado = st.columns([2, 1])

    with col_config:
        st.write("### ⚙️ Configuración de Puertos")
        
        # --- SECTOR SENSOR ---
        puerto_sensor_sel = st.selectbox(
            "Puerto serial del Sensor ModBus",
            puertos_sensor,
            index=indice_sensor,
            key="sensor_port_selector"
        )
        
        if puerto_sensor_sel != st.session_state.sensor_port:
            st.session_state.sensor_port = puerto_sensor_sel
            if IOT_CONFIG_AVAILABLE and hasattr(iot_config, 'save_serial_config'):
                iot_config.save_serial_config(st.session_state.sensor_port, st.session_state.motor_port, st.session_state.sensor_scale)
            st.toast(f"Puerto del sensor actualizado a {puerto_sensor_sel}. Reconectando...", icon="📡")
            st.rerun()
            
        # --- SECTOR ESCALA SENSOR ---
        escala_sensor_sel = st.selectbox(
            "Divisor de Escala del Sensor ModBus (Ajuste de Lectura)",
            [1.0, 10.0, 100.0],
            index=[1.0, 10.0, 100.0].index(st.session_state.sensor_scale) if st.session_state.sensor_scale in [1.0, 10.0, 100.0] else 2,
            key="sensor_scale_selector",
            help="1.0 = lectura directa (mm/s crudos). 10.0 = dividir para precisión decimal de décimas. 100.0 = dividir para precisión de centésimas."
        )
        
        if escala_sensor_sel != st.session_state.sensor_scale:
            st.session_state.sensor_scale = escala_sensor_sel
            if IOT_CONFIG_AVAILABLE and hasattr(iot_config, 'save_serial_config'):
                iot_config.save_serial_config(st.session_state.sensor_port, st.session_state.motor_port, st.session_state.sensor_scale)
            st.toast(f"Divisor de escala actualizado a {escala_sensor_sel}.", icon="📏")
            st.rerun()
            
        # --- SECTOR ARDUINO/MOTOR ---
        puerto_seleccionado = st.selectbox(
            "Puerto serial de Arduino (Motor/Servo)",
            puertos_motor,
            index=indice_motor,
            key="motor_port_selector",
        )
        
        if puerto_seleccionado != st.session_state.motor_port:
            st.session_state.motor_port = puerto_seleccionado
            if IOT_CONFIG_AVAILABLE and hasattr(iot_config, 'save_serial_config'):
                iot_config.save_serial_config(st.session_state.sensor_port, st.session_state.motor_port, st.session_state.sensor_scale)

        col_conectar, col_desconectar = st.columns(2)
        with col_conectar:
            if st.button("🔌 Conectar Arduino", use_container_width=True):
                ok, mensaje = conectar_motor_serial(puerto_seleccionado)
                if ok:
                    st.success(mensaje)
                else:
                    st.error(mensaje)

        with col_desconectar:
            if st.button("⛔ Desconectar Arduino", use_container_width=True):
                st.info(desconectar_motor_serial())

        st.markdown("---")

        # Tabs para organizar controles de Motor y Servo
        tab_motor, tab_servo = st.tabs(["⚡ Control del Motor", "📐 Control del Servo"])

        with tab_motor:
            st.write("**Acciones rápidas de dirección**")
            col_fwd, col_stop, col_rev = st.columns(3)
            with col_fwd:
                if st.button("⬆️ Adelante", use_container_width=True):
                    ok, mensaje = enviar_comando_motor(abs(int(st.session_state.motor_speed)), "Adelante")
                    if ok:
                        st.success(f"Motor adelante: {mensaje}")
                    else:
                        st.error(mensaje)

            with col_stop:
                if st.button("⏹️ Detener", use_container_width=True):
                    ok, mensaje = enviar_comando_motor(0, "Detenido")
                    if ok:
                        st.info(f"Motor detenido: {mensaje}")
                    else:
                        st.error(mensaje)

            with col_rev:
                if st.button("⬇️ Reversa", use_container_width=True):
                    ok, mensaje = enviar_comando_motor(-abs(int(st.session_state.motor_speed)), "Reversa")
                    if ok:
                        st.warning(f"Motor en reversa: {mensaje}")
                    else:
                        st.error(mensaje)

            st.markdown("---")
            velocidad = st.slider(
                "Velocidad PWM (Potencia)",
                min_value=0,
                max_value=255,
                value=int(st.session_state.motor_speed),
                step=5,
            )
            st.session_state.motor_speed = velocidad

            col_aplicar_fwd, col_aplicar_rev = st.columns(2)
            with col_aplicar_fwd:
                if st.button("Aplicar adelante", use_container_width=True):
                    ok, mensaje = enviar_comando_motor(abs(int(velocidad)), "Adelante")
                    if ok:
                        st.success(mensaje)
                    else:
                        st.error(mensaje)

            with col_aplicar_rev:
                if st.button("Aplicar reversa", use_container_width=True):
                    ok, mensaje = enviar_comando_motor(-abs(int(velocidad)), "Reversa")
                    if ok:
                        st.warning(mensaje)
                    else:
                        st.error(mensaje)

        with tab_servo:
            st.write("**Posiciones predefinidas (Rangos de tu código)**")
            col_min, col_init, col_max = st.columns(3)
            with col_min:
                if st.button("⏮️ Mínimo (10°)", use_container_width=True):
                    ok, mensaje = enviar_comando_servo(10)
                    if ok:
                        st.info(f"Servo a 10°: {mensaje}")
                    else:
                        st.error(mensaje)

            with col_init:
                if st.button("🔄 Inicial (95°)", use_container_width=True):
                    ok, mensaje = enviar_comando_servo(95)
                    if ok:
                        st.success(f"Servo a 95°: {mensaje}")
                    else:
                        st.error(mensaje)

            with col_max:
                if st.button("⏭️ Máximo (100°)", use_container_width=True):
                    ok, mensaje = enviar_comando_servo(100)
                    if ok:
                        st.warning(f"Servo a 100°: {mensaje}")
                    else:
                        st.error(mensaje)

            st.markdown("---")
            servo_val = st.slider(
                "Ángulo del Servomotor",
                min_value=10,
                max_value=100,
                value=int(st.session_state.servo_angle),
                step=1,
            )

            if st.button("Aplicar ángulo", use_container_width=True):
                ok, mensaje = enviar_comando_servo(servo_val)
                if ok:
                    st.success(mensaje)
                else:
                    st.error(mensaje)

    with col_estado:
        st.subheader("📊 Estado")
        st.metric("Conexión", "Activa" if st.session_state.motor_connected else "Inactiva")
        st.metric("Modo Motor", st.session_state.motor_mode)
        st.metric("Velocidad Motor", f"{st.session_state.motor_speed}")
        st.metric("Ángulo Servo", f"{st.session_state.servo_angle}°")
        st.caption(f"Puerto actual: {st.session_state.motor_port}")
        st.caption(f"Respuesta serial: {st.session_state.motor_response}")

    st.markdown("---")
    st.info(
        "Este panel envía comandos seriales con el formato M255 (motor adelante), M-255 (motor reversa), M0 (motor detener), "
        "y S10 a S100 (servo de 10° a 100°). Asegúrate de cargar el sketch compatible en tu Arduino."
    )

elif page == "🪵 Consola de Registros (Logs)":
    st.subheader("🪵 Consola de Registros de Operación (Logs)")
    st.caption("Lectura en tiempo real del archivo local `hidromira.log`.")
    
    if st.button("🔄 Refrescar Logs", use_container_width=True):
        st.rerun()
        
    log_path = "hidromira.log"
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            
            # Mostrar los últimos 150 registros
            show_lines = log_lines[-150:]
            
            log_text = ""
            for line in reversed(show_lines):
                if "[ERROR]" in line or "[CRITICAL]" in line:
                    log_text += f"🔴 {line}"
                elif "[WARNING]" in line:
                    log_text += f"🟡 {line}"
                elif "[INFO]" in line:
                    log_text += f"🟢 {line}"
                else:
                    log_text += f"⚪ {line}"
                    
            st.text_area("Eventos del Sistema", log_text, height=500)
            
            st.markdown("---")
            if st.button("🗑️ Limpiar Archivo de Logs", use_container_width=True):
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                logger.info("Archivo de logs limpiado manualmente por el usuario.")
                st.success("Archivo de logs vaciado.")
                st.rerun()
                
        except Exception as e:
            st.error(f"Error leyendo archivo de logs: {e}")
    else:
        st.info("Aún no se ha generado ningún registro de logs.")

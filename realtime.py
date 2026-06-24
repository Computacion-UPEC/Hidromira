import streamlit as st
import minimalmodbus
import plotly.graph_objects as go
from collections import deque
import time
import numpy as np

st.set_page_config(page_title="HidroMira IoT", layout="wide")
st.title("🌊 Monitoreo de Vibración Hidroeléctrica")

# 1. HISTORIAL DE DATOS
if 'buffer_x' not in st.session_state:
    st.session_state.buffer_x = deque([0]*50, maxlen=50)
if 'buffer_y' not in st.session_state:
    st.session_state.buffer_y = deque([0]*50, maxlen=50)
if 'buffer_z' not in st.session_state:
    st.session_state.buffer_z = deque([0]*50, maxlen=50)

# 2. CONEXIÓN (Lógica idéntica a tu código previo)
@st.cache_resource
def conectar():
    try:
        # Usamos COM3 y 0x50 porque es lo que WitMotion y tu código usan
        sensor = minimalmodbus.Instrument('COM3', 80) # 0x50 es 80 decimal
        sensor.serial.baudrate = 9600
        sensor.serial.timeout = 0.5
        return sensor
    except Exception as e:
        return None

sensor = conectar()
placeholder = st.empty()

# Funciones para calcular métricas
def calcular_amplitud(buffer):
    """Amplitud = máximo valor en el buffer"""
    if not buffer or len(buffer) == 0:
        return 0
    return max(buffer)

def calcular_pico_pico(buffer):
    """Pico a pico = máximo - mínimo"""
    if not buffer or len(buffer) == 0:
        return 0
    return max(buffer) - min(buffer)

def calcular_rms(buffer):
    """RMS = raíz cuadrada del promedio de valores al cuadrado"""
    if not buffer or len(buffer) == 0:
        return 0
    return np.sqrt(np.mean(np.array(buffer)**2))

def calcular_desv_std(buffer):
    """Desviación estándar = variabilidad de los datos"""
    if not buffer or len(buffer) == 0:
        return 0
    return np.std(buffer)


# 3. BUCLE DE LECTURA
if sensor:
    error_count = 0
    while True:
        try:
            # Leemos registros de velocidad X, Y, Z
            vx = sensor.read_register(58, functioncode=3, signed=True) / 100.0  # 0x3a = 58
            vy = sensor.read_register(59, functioncode=3, signed=True) / 100.0  # 0x3b = 59
            vz = sensor.read_register(60, functioncode=3, signed=True) / 100.0  # 0x3c = 60
            
            st.session_state.buffer_x.append(vx)
            st.session_state.buffer_y.append(vy)
            st.session_state.buffer_z.append(vz)
            
            error_count = 0  # Reset contador de errores

            with placeholder.container():
                col1, col2 = st.columns([1, 3])
                
                # Mostrar métricas en columna izquierda
                col1.subheader("X")
                col1.metric("Valor", f"{vx:.2f} mm/s")
                col1.metric("Amplitud", f"{calcular_amplitud(st.session_state.buffer_x):.2f}")
                col1.metric("RMS", f"{calcular_rms(st.session_state.buffer_x):.2f}")
                col1.metric("Pico-Pico", f"{calcular_pico_pico(st.session_state.buffer_x):.2f}")
                col1.metric("Desv. Std", f"{calcular_desv_std(st.session_state.buffer_x):.2f}")
                
                col1.markdown("---")
                col1.subheader("Y")
                col1.metric("Valor", f"{vy:.2f} mm/s")
                col1.metric("Amplitud", f"{calcular_amplitud(st.session_state.buffer_y):.2f}")
                col1.metric("RMS", f"{calcular_rms(st.session_state.buffer_y):.2f}")
                col1.metric("Pico-Pico", f"{calcular_pico_pico(st.session_state.buffer_y):.2f}")
                col1.metric("Desv. Std", f"{calcular_desv_std(st.session_state.buffer_y):.2f}")
                
                col1.markdown("---")
                col1.subheader("Z")
                col1.metric("Valor", f"{vz:.2f} mm/s")
                col1.metric("Amplitud", f"{calcular_amplitud(st.session_state.buffer_z):.2f}")
                col1.metric("RMS", f"{calcular_rms(st.session_state.buffer_z):.2f}")
                col1.metric("Pico-Pico", f"{calcular_pico_pico(st.session_state.buffer_z):.2f}")
                col1.metric("Desv. Std", f"{calcular_desv_std(st.session_state.buffer_z):.2f}")
                
                # Gráfica en columna derecha
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=list(st.session_state.buffer_x), mode='lines+markers', 
                                        line=dict(color='#ff6b6b', width=2), name='X'))
                fig.add_trace(go.Scatter(y=list(st.session_state.buffer_y), mode='lines+markers', 
                                        line=dict(color='#51cf66', width=2), name='Y'))
                fig.add_trace(go.Scatter(y=list(st.session_state.buffer_z), mode='lines+markers', 
                                        line=dict(color='#4dabf7', width=2), name='Z'))
                fig.update_layout(template="plotly_dark", height=400, yaxis=dict(range=[0, 5]))
                col2.plotly_chart(fig, width='stretch')
            
            time.sleep(0.5)
        except Exception as e:
            error_count += 1
            st.error(f"Error de lectura #{error_count}: {e}")
            time.sleep(2)
            
            # Reintentar reconexión después de 5 errores
            if error_count >= 5:
                st.warning("Intentando reconectar...")
                sensor = conectar()
                if sensor is None:
                    st.error("No se pudo reconectar. Cierra WitMotion y el Virtual Serial Port Kit.")
                    break
                error_count = 0
else:
    st.error("No se pudo abrir el COM3. WitMotion DEBE estar cerrado.")
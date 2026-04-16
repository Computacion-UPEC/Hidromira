import streamlit as st
import serial
import plotly.graph_objects as go
from collections import deque
import time
import json
import os
from datetime import datetime, timedelta
import threading
import queue
import streamlit.components.v1 as components
import struct

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

# Thread control event (do NOT use st.session_state inside background thread)
force_event = threading.Event()

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="HidroMira IoT", layout="wide")
st.title("🌊 HidroMira - Monitoreo de Vibración")

# Inicialización de historial de datos - SIN LÍMITE para análisis histórico
# Cargar datos históricos desde archivo
historical_data_path = os.path.join(os.path.dirname(__file__), 'historical_data.json')

if 'all_readings' not in st.session_state:
    # Intentar cargar datos históricos del archivo
    if os.path.exists(historical_data_path):
        try:
            with open(historical_data_path, 'r', encoding='utf-8') as f:
                st.session_state.all_readings = json.load(f)
        except Exception as e:
            print(f'Error cargando histórico: {e}', flush=True)
            st.session_state.all_readings = []
    else:
        st.session_state.all_readings = []

if 'historial_vx' not in st.session_state:
    st.session_state.historial_vx = deque([0]*50, maxlen=50)  # Para display rápido
if 'historial_vy' not in st.session_state:
    st.session_state.historial_vy = deque([0]*50, maxlen=50)
if 'historial_vz' not in st.session_state:
    st.session_state.historial_vz = deque([0]*50, maxlen=50)
if 'red_events' not in st.session_state:
    st.session_state.red_events = 0
if 'maintenance_queue' not in st.session_state:
    st.session_state.maintenance_queue = []
if 'force_fault' not in st.session_state:
    st.session_state.force_fault = False
if 'comm_errors' not in st.session_state:
    st.session_state.comm_errors = 0
if 'period_view' not in st.session_state:
    st.session_state.period_view = "Últimos 20s"
if 'latest' not in st.session_state:
    st.session_state['latest'] = {'vx': 0.0, 'vy': 0.0, 'vz': 0.0, 'ts': datetime.utcnow().isoformat() + 'Z'}
if 'loading_period' not in st.session_state:
    st.session_state.loading_period = False

# 2. INICIALIZACIÓN DEL SENSOR - PROTOCOLO NATIVO WITMOTIÓN (NO ModBus RTU)
def configurar_sensor():
    """Abre conexión serial SIN CACHE para permitir reconexión"""
    try:
        ser = serial.Serial(
            port='COM4',
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0,  # timeout más largo para lectura
            write_timeout=1.0
        )
        if not ser.is_open:
            ser.open()
        print(f'[SENSOR] COM4 abierto exitosamente', flush=True)
        return ser
    except Exception as e:
        print(f'[SENSOR] Error abriendo COM4: {e}', flush=True)
        return None


# Protocolo nativo WitMotion - Leer registros de velocidad
def read_witmotion_velocity(ser, device_addr=0x50):
    """
    Lee velocidad (Vx, Vy, Vz) del sensor WitMotion
    Registros: 0x3d=Vx, 0x3e=Vy, 0x3f=Vz
    """
    if ser is None or not ser.is_open:
        raise Exception("Puerto serial no está abierto")
    
    try:
        vx = read_register(ser, device_addr, 0x3d)
        vy = read_register(ser, device_addr, 0x3e)
        vz = read_register(ser, device_addr, 0x3f)
        return vx, vy, vz
    except Exception as e:
        raise Exception(f"Error leyendo velocidad: {e}")


def read_register(ser, device_addr, reg_addr):
    """
    Lee un registro de 16 bits del sensor WitMotion
    Frame: 0x55 0x51 <addr> <reg> <checksum>
    Respuesta: 0x55 0x51 <data_high> <data_low> <checksum>
    """
    if ser is None or not ser.is_open:
        raise Exception("Puerto no abierto")
    
    try:
        # Limpiar buffers
        ser.reset_input_buffer()
        time.sleep(0.05)
        
        # Construir comando de lectura
        cmd = bytes([0x55, 0x51, device_addr, reg_addr])
        checksum = (sum(cmd) & 0xFF)
        cmd += bytes([checksum])
        
        print(f'[SENSOR] TX: {cmd.hex()}', flush=True)
        ser.write(cmd)
        ser.flush()
        
        # Leer respuesta
        response = b''
        while len(response) < 5:
            chunk = ser.read(1)
            if not chunk:
                break
            response += chunk
        
        print(f'[SENSOR] RX: {response.hex()} (len={len(response)})', flush=True)
        
        if len(response) < 5:
            raise Exception(f"Respuesta incompleta: {response.hex()}")
        
        # Verificar header
        if response[0] != 0x55 or response[1] != 0x51:
            raise Exception(f"Header inválido: {response[:2].hex()}")
        
        # Extraer valor (bytes 3-4, big-endian signed)
        value_bytes = response[2:4]
        value_signed = struct.unpack('>h', value_bytes)[0]
        value_float = value_signed / 100.0
        
        print(f'[SENSOR] Reg 0x{reg_addr:02x} = {value_signed} -> {value_float} mm/s', flush=True)
        return value_float
        
    except Exception as e:
        raise Exception(f"read_register 0x{reg_addr:02x}: {e}")


# NO usar cache_resource - crear nueva instancia cada vez
sensor = None

# MQTT client resource
@st.cache_resource
def mqtt_client(broker, port):
    if mqtt is None:
        return None
    client = mqtt.Client()
    try:
        client.connect(broker, port, keepalive=60)
    except Exception:
        return None
    return client

def publish_mqtt(client, topic, payload):
    try:
        if client:
            client.publish(topic, json.dumps(payload))
    except Exception:
        pass

def save_historical_data():
    """Guardar datos históricos en archivo JSON"""
    try:
        with open(historical_data_path, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.all_readings, f, indent=2)
        print(f'[SAVE] Guardado {len(st.session_state.all_readings)} lecturas en histórico', flush=True)
    except Exception as e:
        print(f'[SAVE ERROR] {e}', flush=True)

# 3. INTERFAZ DE USUARIO
try:
    test_conn = configurar_sensor()
    has_sensor = test_conn is not None and test_conn.is_open
    if test_conn and test_conn.is_open:
        test_conn.close()
except:
    has_sensor = False

if has_sensor:
    st.sidebar.success("✅ Sensor WTVB01-485 Conectado")

    # Sidebar controls for IoT and sampling
    st.sidebar.subheader("Configuración")
    sampling_interval = st.sidebar.slider("Intervalo muestreo (s)", 0.0, 5.0, 0.2, 0.05)
    # Sensitivity thresholds (configurable) - rango 0..5
    st.sidebar.subheader("Umbrales de vibración (mm/s)")
    yellow_threshold = st.sidebar.slider("Umbral Amarillo (mm/s)", 0.0, 5.0, 1.0, 0.1)
    red_threshold = st.sidebar.slider("Umbral Rojo (mm/s)", 0.0, 5.0, 2.0, 0.1)
    # Ensure red >= yellow
    if red_threshold < yellow_threshold:
        red_threshold = yellow_threshold
    mqtt_enabled = st.sidebar.checkbox("Habilitar MQTT", value=False)
    mqtt_broker = st.sidebar.text_input("Broker MQTT", value="test.mosquitto.org")
    mqtt_port = st.sidebar.number_input("Puerto MQTT", value=1883)
    mqtt_topic = st.sidebar.text_input("Tópico MQTT", value="hidromira/telemetry")
    st.sidebar.markdown("---")
    if st.sidebar.button("Simular fallo / Programar mantenimiento"):
        force_event.set()
    if st.sidebar.button("Limpiar fallo"):
        force_event.clear()

    # Prepare MQTT client resource
    mqtt_cli = mqtt_client(mqtt_broker, int(mqtt_port)) if mqtt_enabled else None

    # Contenedores para actualizar datos
    # Placeholders para métricas (primera fila)
    col1, col2, col3 = st.columns(3)
    metrica_x = col1.empty()
    metrica_y = col2.empty()
    metrica_z = col3.empty()
    
    # Placeholder para estado general
    estado_placeholder = st.empty()
    
    # Placeholders para gráficas (lugares fijos)
    grafico_x = st.empty()
    grafico_y = st.empty()
    grafico_z = st.empty()

    # Paths
    registers_path = os.path.join(os.path.dirname(__file__), 'registers.json')

    # Unique key for the plot to avoid duplicate-key errors across reruns
    # (removed persistent plot key to avoid duplicate-key conflicts)

    # Initialize data_queue in session_state if not exists
    if 'data_queue' not in st.session_state:
        st.session_state['data_queue'] = queue.Queue()

    # Start a background thread to read the sensor continuously
    data_queue = st.session_state['data_queue']

    def background_reader(q):
        local_sensor = None
        backoff = 0.5
        consecutive_errors = 0
        print('[BG] Background reader started', flush=True)
        while True:
            try:
                if local_sensor is None or not local_sensor.is_open:
                    print('[BG] Abriendo conexión COM4...', flush=True)
                    local_sensor = configurar_sensor()
                    if local_sensor is None:
                        raise Exception('No se pudo abrir COM4')
                
                # Leer velocidad usando protocolo nativo WitMotion
                vx, vy, vz = read_witmotion_velocity(local_sensor, device_addr=0x50)
                print(f'[BG] Read: vx={vx:.2f}, vy={vy:.2f}, vz={vz:.2f}', flush=True)

                # Apply forced fault if requested (read module-level event)
                if force_event.is_set():
                    vx += 10.0

                rec = {'vx': vx, 'vy': vy, 'vz': vz, 'ts': datetime.utcnow().isoformat() + 'Z'}
                # Put the reading into the queue for the main thread to consume
                q.put_nowait(rec)
                
                # Publish telemetry (non-blocking)
                publish_mqtt(mqtt_cli, mqtt_topic, rec)

                # reset backoff and error counter on success
                backoff = 0.5
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                err_msg = str(e)
                print(f'[BG] Error #{consecutive_errors}: {err_msg}, backoff={backoff}s', flush=True)
                # store last error in queue
                try:
                    q.put_nowait({'error': err_msg, 'consecutive_errors': consecutive_errors})
                except Exception:
                    pass
                
                # Cerrar puerto y reconectar en siguiente intento
                try:
                    if local_sensor and local_sensor.is_open:
                        local_sensor.close()
                except:
                    pass
                local_sensor = None
                
                # Backoff exponencial pero más corto
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 3)  # Cap at 3s

            # Sleep según intervalo configurado
            time.sleep(max(0.01, sampling_interval))

    if 'data_thread' not in st.session_state:
        t = threading.Thread(target=background_reader, args=(data_queue,), daemon=True)
        t.start()
        st.session_state['data_thread'] = t

    # Diagnostics and control
    st.sidebar.subheader('Diagnóstico')
    st.sidebar.write('Sensor detectado:', bool(sensor))
    dt = st.session_state.get('data_thread')
    is_alive = False
    try:
        is_alive = dt.is_alive()
    except Exception:
        is_alive = False
    st.sidebar.write('Lector activo:', is_alive)
    dq = st.session_state.get('data_queue')
    try:
        qsize = dq.qsize() if dq else 0
    except Exception:
        qsize = 0
    st.sidebar.write('Tamaño cola:', qsize)
    st.sidebar.write('Último registro:', st.session_state.get('latest'))
    last_err = st.session_state.get('latest_error')
    if last_err:
        st.sidebar.error(f'Último error: {last_err}')
    else:
        st.sidebar.info('Sin errores')

    # Test sensor button
    if st.sidebar.button('Test Sensor (lectura única)'):
        try:
            test_sensor = configurar_sensor()
            if test_sensor and test_sensor.is_open:
                t_vx, t_vy, t_vz = read_witmotion_velocity(test_sensor, device_addr=0x50)
                st.sidebar.success(f'✅ Lectura exitosa: VX={t_vx:.2f}, VY={t_vy:.2f}, VZ={t_vz:.2f} mm/s')
                test_sensor.close()
            else:
                st.sidebar.error('❌ No se pudo abrir COM4')
        except Exception as e:
            st.sidebar.error(f'❌ Error: {str(e)[:100]}')

    if st.sidebar.button('Reiniciar lector'):
        # Remove and restart thread
        try:
            del st.session_state['data_thread']
        except Exception:
            pass
        t = threading.Thread(target=background_reader, args=(data_queue,), daemon=True)
        t.start()
        st.session_state['data_thread'] = t

    # UI: show latest values and plot (the reader updates session_state in background).
    # Drain queue produced by background thread and update session_state in main thread
    data_queue = st.session_state.get('data_queue')
    error = None
    write_counter = st.session_state.get('write_counter', 0)
    should_rerun = False
    data_loaded = False

    if data_queue:
        print(f'[UI] Checking queue, size={data_queue.qsize()}', flush=True)
        items_processed = 0
        last_valid_item = None  # Guardar el último item válido
        while not data_queue.empty():
            try:
                item = data_queue.get_nowait()
                items_processed += 1
                print(f'[UI] Got item {items_processed}: {item}', flush=True)
                if 'error' in item:
                    error = item['error']
                    # Solo mostrar errores si son varios consecutivos
                    if item.get('consecutive_errors', 0) > 2:
                        st.session_state['latest_error'] = error
                    continue
                # Guardar este item válido
                last_valid_item = item
                data_loaded = True
                # update latest and historial (para X, Y, Z)
                st.session_state['latest'] = item
                st.session_state.historial_vx.append(item['vx'])
                st.session_state.historial_vy.append(item['vy'])
                st.session_state.historial_vz.append(item['vz'])
                # AGREGAR A HISTÓRICO COMPLETO (sin límite)
                reading_record = {
                    'vx': item['vx'],
                    'vy': item['vy'],
                    'vz': item['vz'],
                    'ts': item['ts']
                }
                st.session_state.all_readings.append(reading_record)
                
                # Guardar histórico cada 50 lecturas
                if len(st.session_state.all_readings) % 50 == 0:
                    save_historical_data()
                
                should_rerun = True
                # persist every 10 samples
                write_counter += 1
                if write_counter >= 10:
                    rec = item.copy()
                    rec['status'] = {
                        'x': 'red' if rec['vx'] >= red_threshold else ('yellow' if rec['vx'] >= yellow_threshold else 'green'),
                        'y': 'red' if rec['vy'] >= red_threshold else ('yellow' if rec['vy'] >= yellow_threshold else 'green'),
                        'z': 'red' if rec['vz'] >= red_threshold else ('yellow' if rec['vz'] >= yellow_threshold else 'green')
                    }
                    try:
                        if os.path.exists(registers_path):
                            with open(registers_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                        else:
                            data = []
                        data.append(rec)
                        with open(registers_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2)
                    except Exception:
                        pass
                    write_counter = 0
            except queue.Empty:
                break
        st.session_state['write_counter'] = write_counter
        if items_processed > 0:
            print(f'[UI] Processed {items_processed} items, data_loaded={data_loaded}', flush=True)

    error = error or st.session_state.get('latest_error')

    # Obtener el latest más actual DESPUÉS de procesar la cola
    latest = st.session_state.get('latest', {'vx': 0.0, 'vy': 0.0, 'vz': 0.0, 'ts': datetime.utcnow().isoformat() + 'Z'})

    # Update metrics
    metrica_x.metric("Velocidad X", f"{latest['vx']:.2f} mm/s")
    metrica_y.metric("Velocidad Y", f"{latest['vy']:.2f} mm/s")
    metrica_z.metric("Velocidad Z", f"{latest['vz']:.2f} mm/s")

    # Single general status (computed from latest)
    def level(v, y_thr=yellow_threshold, r_thr=red_threshold):
        if v >= r_thr:
            return 'red'
        if v >= y_thr:
            return 'yellow'
        return 'green'

    sx = level(latest['vx'])
    sy = level(latest['vy'])
    sz = level(latest['vz'])
    statuses = {'x': sx, 'y': sy, 'z': sz}
    if 'red' in statuses.values():
        overall_status = 'red'
    elif 'yellow' in statuses.values():
        overall_status = 'yellow'
    else:
        overall_status = 'green'

    color_map = {'green': '#00c853', 'yellow': '#ffd600', 'red': '#d50000'}
    triggering_axes = [ax.upper() for ax, s in statuses.items() if s == overall_status]
    trigger_text = f" ({', '.join(triggering_axes)})" if triggering_axes else ''
    dot_html = f"<div style='width:18px;height:18px;border-radius:9px;background:{color_map[overall_status]};margin-right:8px'></div>"
    html = f"<b>Estado General</b><br><div style='display:flex;align-items:center'>{dot_html}{overall_status.upper()}{trigger_text}</div>"
    estado_placeholder.markdown(html, unsafe_allow_html=True)

    if error:
        st.sidebar.error(f"Error de lectura: {error}")

    # ===== PERIODO DE VISUALIZACIÓN =====
    st.sidebar.subheader("Período de Análisis")
    
    def on_period_change():
        """Callback cuando cambia el período - Fuerza rerun inmediato"""
        new_period = st.session_state.period_select
        if new_period != st.session_state.period_view:
            st.session_state.period_view = new_period
            st.session_state.loading_period = True  # Activar loading
            print(f'[UI] Período cambiado a: {new_period}', flush=True)
            st.rerun()
    
    period = st.sidebar.radio("Mostrar datos de:", 
        ["Últimos 20s", "Último día", "Última semana", "Histórico completo"],
        index=["Últimos 20s", "Último día", "Última semana", "Histórico completo"].index(st.session_state.period_view),
        key="period_select",
        on_change=on_period_change)
    
    st.session_state.period_view = period
    
    # Mostrar mensaje de carga si está procesando
    if st.session_state.loading_period:
        with st.spinner(f'🔄 Cargando datos de {period}...'):
            time.sleep(0.5)  # Simular pequeño delay para que se vea el spinner
        st.session_state.loading_period = False
    
    # Calcular rango de fechas según período
    now = datetime.utcnow()
    if period == "Últimos 20s":
        # Mostrar TODAS las vibraciones en tiempo real (sin filtro de tiempo)
        # Pero si hay muchas, solo los últimos 2000 puntos para performance
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
            except Exception as e:
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
            except Exception as e:
                pass
    else:  # Histórico completo
        filtered_readings = st.session_state.all_readings
    
    print(f'[UI] Período {period}: {len(filtered_readings)} datos de {len(st.session_state.all_readings)} totales', flush=True)
    
    # Si no hay datos filtrados, usar los últimos 50
    if not filtered_readings and st.session_state.all_readings:
        filtered_readings = st.session_state.all_readings[-50:]
    
    # Mostrar gráficas en FULL WIDTH (una por fila)
    
    # Extraer datos para las gráficas
    vx_vals = [r['vx'] for r in filtered_readings] if filtered_readings else []
    vy_vals = [r['vy'] for r in filtered_readings] if filtered_readings else []
    vz_vals = [r['vz'] for r in filtered_readings] if filtered_readings else []
    
    # Extraer timestamps y formatearlos según el período
    timestamps = []
    if filtered_readings:
        for r in filtered_readings:
            try:
                ts = datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                timestamps.append(ts)
            except:
                timestamps.append(None)
    
    # Formatear etiquetas del eje X según el período
    x_labels = []
    if period == "Últimos 20s":
        # Mostrar HH:MM:SS para últimos 20 segundos
        x_labels = [ts.strftime("%H:%M:%S") if ts else "" for ts in timestamps]
    elif period == "Último día":
        # Mostrar HH:MM para último día (24 horas)
        x_labels = [ts.strftime("%H:%M") if ts else "" for ts in timestamps]
    elif period == "Última semana":
        # Mostrar Día HH:MM para última semana
        x_labels = [ts.strftime("%a %H:%M") if ts else "" for ts in timestamps]
    else:  # Histórico completo
        # Mostrar YYYY-MM-DD para histórico completo
        x_labels = [ts.strftime("%Y-%m-%d") if ts else "" for ts in timestamps]
    
    # Función para encontrar picos (máximos locales)
    def find_peaks(values, threshold=0.5):
        if len(values) < 3:
            return []
        peaks = []
        for i in range(1, len(values)-1):
            if values[i] > threshold and values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(i)
        return peaks
    
    # Gráfica X
    try:
        peaks_x = find_peaks(vx_vals, threshold=1.0) if vx_vals else []
        fig_x = go.Figure(go.Scatter(
            x=x_labels if x_labels else list(range(len(vx_vals))),
            y=vx_vals,
            mode='lines+markers',
            line=dict(color='#ff6b6b', width=2),
            fill='tozeroy',
            name='Vx',
            hovertemplate='<b>Tiempo:</b> %{x}<br><b>Velocidad:</b> %{y:.2f} mm/s<extra></extra>'
        ))
        # Marcar picos
        if peaks_x:
            fig_x.add_scatter(
                x=[x_labels[i] if x_labels else i for i in peaks_x],
                y=[vx_vals[i] for i in peaks_x],
                mode='markers',
                marker=dict(size=10, color='yellow', symbol='star'),
                name='Picos',
                hovertemplate='<b>Pico en:</b> %{x}<br><b>Amplitud:</b> %{y:.2f} mm/s<extra></extra>'
            )
        fig_x.update_layout(
            template="plotly_dark",
            title="Onda de Velocidad X (mm/s)",
            xaxis=dict(
                title="Tiempo",
                rangeslider=dict(visible=True, thickness=0.05) if period == "Últimos 20s" else dict(visible=False)
            ),
            yaxis=dict(range=[0, 3], title="Velocidad (mm/s)"),
            height=400,
            margin=dict(l=50, r=20, t=40, b=80),
            hovermode='x unified'
        )
        st.plotly_chart(fig_x, width='stretch', key='graph_x')
    except Exception as e:
        print(f'[ERROR] Gráfica X: {e}', flush=True)
        st.warning(f'Error en gráfica X: {str(e)[:50]}')
    
    # Gráfica Y
    try:
        peaks_y = find_peaks(vy_vals, threshold=1.0) if vy_vals else []
        fig_y = go.Figure(go.Scatter(
            x=x_labels if x_labels else list(range(len(vy_vals))),
            y=vy_vals,
            mode='lines+markers',
            line=dict(color='#51cf66', width=2),
            fill='tozeroy',
            name='Vy',
            hovertemplate='<b>Tiempo:</b> %{x}<br><b>Velocidad:</b> %{y:.2f} mm/s<extra></extra>'
        ))
        # Marcar picos
        if peaks_y:
            fig_y.add_scatter(
                x=[x_labels[i] if x_labels else i for i in peaks_y],
                y=[vy_vals[i] for i in peaks_y],
                mode='markers',
                marker=dict(size=10, color='yellow', symbol='star'),
                name='Picos',
                hovertemplate='<b>Pico en:</b> %{x}<br><b>Amplitud:</b> %{y:.2f} mm/s<extra></extra>'
            )
        fig_y.update_layout(
            template="plotly_dark",
            title="Onda de Velocidad Y (mm/s)",
            xaxis=dict(
                title="Tiempo",
                rangeslider=dict(visible=True, thickness=0.05) if period == "Últimos 20s" else dict(visible=False)
            ),
            yaxis=dict(range=[0, 3], title="Velocidad (mm/s)"),
            height=400,
            margin=dict(l=50, r=20, t=40, b=80),
            hovermode='x unified'
        )
        st.plotly_chart(fig_y, width='stretch', key='graph_y')
    except Exception as e:
        print(f'[ERROR] Gráfica Y: {e}', flush=True)
        st.warning(f'Error en gráfica Y: {str(e)[:50]}')
    
    # Gráfica Z
    try:
        peaks_z = find_peaks(vz_vals, threshold=1.0) if vz_vals else []
        fig_z = go.Figure(go.Scatter(
            x=x_labels if x_labels else list(range(len(vz_vals))),
            y=vz_vals,
            mode='lines+markers',
            line=dict(color='#4dabf7', width=2),
            fill='tozeroy',
            name='Vz',
            hovertemplate='<b>Tiempo:</b> %{x}<br><b>Velocidad:</b> %{y:.2f} mm/s<extra></extra>'
        ))
        # Marcar picos
        if peaks_z:
            fig_z.add_scatter(
                x=[x_labels[i] if x_labels else i for i in peaks_z],
                y=[vz_vals[i] for i in peaks_z],
                mode='markers',
                marker=dict(size=10, color='yellow', symbol='star'),
                name='Picos',
                hovertemplate='<b>Pico en:</b> %{x}<br><b>Amplitud:</b> %{y:.2f} mm/s<extra></extra>'
            )
        fig_z.update_layout(
            template="plotly_dark",
            title="Onda de Velocidad Z (mm/s)",
            xaxis=dict(
                title="Tiempo",
                rangeslider=dict(visible=True, thickness=0.05) if period == "Últimos 20s" else dict(visible=False)
            ),
            yaxis=dict(range=[0, 3], title="Velocidad (mm/s)"),
            height=400,
            margin=dict(l=50, r=20, t=40, b=80),
            hovermode='x unified'
        )
        st.plotly_chart(fig_z, width='stretch', key='graph_z')
    except Exception as e:
        print(f'[ERROR] Gráfica Z: {e}', flush=True)
        st.warning(f'Error en gráfica Z: {str(e)[:50]}')

    # Rerun strategy: Solo refrescar en tiempo real (Últimos 20s)
    # Para períodos históricos, no necesita refrescarse constantemente
    auto_refresh = st.sidebar.checkbox('Auto-refresh UI (Últimos 20s)', value=True)
    
    # Simple: refrescar cada 1-2 segundos si estamos en tiempo real
    if auto_refresh and sampling_interval > 0 and st.session_state.period_view == "Últimos 20s":
        # Refrescas más suave: cada 1.5 segundos máximo
        print('[UI] Rerun en 1.5s (time real)', flush=True)
        time.sleep(1.5)
        st.rerun()

else:
    st.error("❌ No se pudo detectar el sensor en COM4.")
    st.info("Verifica que:\n1. El adaptador RS485 esté conectado\n2. COM4 sea el puerto correcto\n3. WitMotion esté cerrado")
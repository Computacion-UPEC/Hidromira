import streamlit as st
import minimalmodbus
import plotly.graph_objects as go
from collections import deque
import time
import json
import os
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="HidroMira IoT", layout="wide")
st.title("🌊 HidroMira - Monitoreo de Vibración")

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

# ============ NOTA: SENSOR NO NECESARIO EN APP.PY ============
# El sensor solo se usa en monitor_realtime.py
# Esta app solo lee historical_data.json para análisis

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
    """Guardar datos históricos en archivo JSON"""
    try:
        path = os.path.join(os.path.dirname(__file__), 'historical_data.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.all_readings, f, indent=2)
    except:
        pass

# ============ CREAR TABS (Solo Análisis, sin Monitoreo Tiempo Real) ============

tab1, tab2, tab3 = st.tabs(["📊 Análisis Histórico", "🏭 Datos Técnicos", "⚙️ Rendimiento vs Vibraciones"])

# Nota: Para Monitoreo en Tiempo Real, ejecutar: streamlit run monitor_realtime.py --server.port 8503

# ========== TAB 1: ANÁLISIS HISTÓRICO ==========

with tab1:
    st.subheader("Análisis Histórico - Diagnóstico ISO 20816-3")
    st.caption("🏭 Máquina: Grupo 1 (Soporte Rígido) | Zona A ≤ 0.25 | Zona B ≤ 0.5 | Zona C ≤ 0.75 | Zona D > 0.75 mm/s")
    
    # Cargar JSON solo UNA VEZ cuando Tab 1 se activa
    if not st.session_state.json_loaded:
        historical_path = os.path.join(os.path.dirname(__file__), 'historical_data.json')
        if os.path.exists(historical_path):
            try:
                with open(historical_path, 'r', encoding='utf-8') as f:
                    st.session_state.all_readings = json.load(f)
            except:
                pass
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
            fig_x.update_layout(template="plotly_dark", height=350, yaxis=dict(range=[0, 1.5]),
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
            fig_y.update_layout(template="plotly_dark", height=350, yaxis=dict(range=[0, 1.5]),
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
            fig_z.update_layout(template="plotly_dark", height=350, yaxis=dict(range=[0, 1.5]),
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
            
            fig_iso_x.update_layout(
                template="plotly_dark", height=400, 
                yaxis=dict(range=[0, 1.5], title="RMS (mm/s)"),
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
            
            fig_iso_y.update_layout(
                template="plotly_dark", height=400,
                yaxis=dict(range=[0, 1.5], title="RMS (mm/s)"),
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
            
            fig_iso_z.update_layout(
                template="plotly_dark", height=400,
                yaxis=dict(range=[0, 1.5], title="RMS (mm/s)"),
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
        
        fig_anomalias.update_layout(
            template="plotly_dark", height=350,
            title="Detección de Anomalías Periódicas",
            yaxis=dict(range=[0, 1.5], title="Velocidad (mm/s)"),
            hovermode='x unified'
        )
        st.plotly_chart(fig_anomalias, width='stretch')

# ========== TAB 2: DATOS TÉCNICOS ==========

with tab2:
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
    
    # Datos de mantenimiento (pueden editarse)
    if 'maintenance_log' not in st.session_state:
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
        if st.button("➕ Nuevo Registro"):
            st.session_state.show_new_maintenance = True
    
    # Formulario para nuevo mantenimiento
    if st.session_state.get('show_new_maintenance', False):
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

# ========== TAB 3: RENDIMIENTO VS VIBRACIONES ==========

with tab3:
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

# HidroMira - Sistema Separado de Monitoreo

## 📁 Estructura de Apps

### 1. **monitor_realtime.py** - Monitoreo en Tiempo Real ⚡
- Auto-refresh cada 0.5 segundos
- Lectura continua del sensor
- Visualización en tiempo real de vibraciones (X, Y, Z)
- RPM correlacionado
- Clasificación ISO 20816-3
- Guarda datos a `historical_data.json` cada 50 lecturas

### 2. **app.py** - Análisis y Gestión 📊
- **Tab 1**: Análisis Histórico (lee `historical_data.json`)
- **Tab 2**: Datos Técnicos (specs de turbina + mantenimiento)
- **Tab 3**: Rendimiento vs Vibraciones (análisis predictivo)

## 🚀 Cómo Ejecutar

### Opción 1: Dos Terminales Separados (RECOMENDADO)

**Terminal 1 - Monitor Tiempo Real:**
```bash
cd c:\Users\ggeta\Documents\HidroMira
C:/Users/ggeta/Documents/HidroMira/venv/Scripts/python.exe -m streamlit run monitor_realtime.py --server.port 8503
```
Abre: http://localhost:8503

**Terminal 2 - Panel de Análisis:**
```bash
cd c:\Users\ggeta\Documents\HidroMira
C:/Users/ggeta/Documents/HidroMira/venv/Scripts/python.exe -m streamlit run app.py --server.port 8502
```
Abre: http://localhost:8502

### Opción 2: Un Solo Terminal (Background)

```bash
cd c:\Users\ggeta\Documents\HidroMira
Start-Process powershell -ArgumentList "-NoExit", "-Command", "C:/Users/ggeta/Documents/HidroMira/venv/Scripts/python.exe -m streamlit run monitor_realtime.py --server.port 8503"
C:/Users/ggeta/Documents/HidroMira/venv/Scripts/python.exe -m streamlit run app.py --server.port 8502
```

## 📊 Flujo de Datos

```
Sensor COM3 (WTVB01-485)
    ↓
monitor_realtime.py (lee + visualiza en tiempo real)
    ↓
historical_data.json (guardado cada 50 lecturas)
    ↓
app.py (lee JSON + análisis histórico)
```

## ✅ Ventajas de la Separación

1. **Sin Interferencia**: El auto-refresh del monitor NO afecta las tabs de análisis
2. **Mejor Rendimiento**: Cada app es independiente
3. **Escalabilidad**: Se pueden correr en diferentes servidores
4. **Flexibilidad**: Puedes abrir solo el monitor o solo el análisis

## 🔧 Configuración

- **Sensor**: COM3, 9600 baud, address 80 (0x50)
- **Registros ModBus**: 0x3d (Vx), 0x3e (Vy), 0x3f (Vz)
- **Norma**: ISO 20816-3 Grupo 1
  - Zona A: ≤ 0.25 mm/s
  - Zona B: ≤ 0.5 mm/s
  - Zona C: ≤ 0.75 mm/s
  - Zona D: > 0.75 mm/s

## 📦 Dependencias

```
streamlit
streamlit-autorefresh  ← Nueva dependencia para auto-refresh
minimalmodbus
plotly
numpy
```

Instalar: `pip install streamlit-autorefresh`

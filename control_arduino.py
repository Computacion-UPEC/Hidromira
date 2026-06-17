import os
import sys
import time
import threading
import json
import serial
import serial.tools.list_ports
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Configuración por defecto
PORT_DEFAULT = 'COM3'
BAUDRATE = 9600

# Cerrar puertos residuales al iniciar para evitar PermissionError
def pre_cleanup(port):
    print(f"[Limpieza] Intentando liberar puerto {port} en caso de que esté ocupado...", flush=True)
    try:
        temp_ser = serial.Serial(port)
        temp_ser.close()
        print(f"[Limpieza] Puerto {port} liberado con éxito.", flush=True)
    except Exception as e:
        # Si da error de permiso, significa que ya hay un proceso usándolo
        print(f"[Limpieza] Info: No se pudo abrir/cerrar {port} directamente: {e}", flush=True)

pre_cleanup(PORT_DEFAULT)

# Cerrar puertos si ya existiera una conexión previa (para reinicios rápidos del script)
state = {
    'servo_angle': 90,
    'motor_speed': 0,
    'serial_connected': False,
    'simulation_mode': False,
    'port': PORT_DEFAULT,
    'logs': [],
    'arduino_response': 'Ninguna'
}

state_lock = threading.RLock()
ser = None

def log_message(msg):
    with state_lock:
        timestamp = time.strftime('%H:%M:%S')
        state['logs'].append(f"[{timestamp}] {msg}")
        if len(state['logs']) > 40:
            state['logs'].pop(0)

def connect_serial_port():
    global ser
    with state_lock:
        # Si ya está abierto, cerrarlo primero
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
            ser = None
        
        current_port = state['port']
        log_message(f"Intentando conectar a {current_port}...")
        
        # Verificar si el puerto existe
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if current_port not in ports:
            state['serial_connected'] = False
            state['simulation_mode'] = True
            log_message(f"Advertencia: {current_port} no está disponible físicamente. Activando MODO SIMULACIÓN.")
            log_message(f"Puertos disponibles encontrados: {', '.join(ports) if ports else 'Ninguno'}")
            return False
            
        try:
            # Abrir puerto serial con timeout para lecturas rápidas
            ser = serial.Serial(current_port, BAUDRATE, timeout=1.0, write_timeout=1.0)
            state['serial_connected'] = True
            state['simulation_mode'] = False
            log_message(f"Conexión exitosa con {current_port} a 9600 baudios.")
            
            # Esperar a que el Arduino se reinicie (típico de Arduino Uno tras abrir serial)
            time.sleep(2.0)
            
            # Limpiar búferes residuales
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Comprobar si hay respuesta inicial del Arduino
            if ser.in_waiting > 0:
                resp = ser.readline().decode('utf-8', errors='ignore').strip()
                state['arduino_response'] = resp
                log_message(f"Respuesta de Arduino: {resp}")
            else:
                log_message("Conectado, esperando comandos del usuario.")
            return True
        except Exception as e:
            ser = None
            state['serial_connected'] = False
            state['simulation_mode'] = True
            log_message(f"Error abriendo {current_port}: {e}. Activando MODO SIMULACIÓN.")
            return False

def send_serial_cmd(command):
    global ser
    log_message(f"TX (Enviado): {command.strip()}")
    
    with state_lock:
        is_sim = state['simulation_mode']
        is_conn = state['serial_connected']
        
    if is_sim or not is_conn or ser is None or not ser.is_open:
        log_message("RX (Simulación): ACK (Modo Simulación Activo)")
        return "Simulación: ACK"
        
    try:
        # Enviar el comando
        ser.write(command.encode('utf-8'))
        ser.flush()
        
        # Esperar brevemente respuesta del Arduino
        time.sleep(0.08)
        
        # Leer respuesta si existe
        if ser.in_waiting > 0:
            resp = ser.readline().decode('utf-8', errors='ignore').strip()
            with state_lock:
                state['arduino_response'] = resp
            log_message(f"RX (Recibido): {resp}")
            return resp
        else:
            log_message("RX: Sin respuesta directa del hardware (Comando enviado)")
            return "Comando Enviado"
    except Exception as e:
        log_message(f"Error escribiendo en puerto serial: {e}")
        with state_lock:
            state['serial_connected'] = False
            state['simulation_mode'] = True
            log_message("Cambiando automáticamente a MODO SIMULACIÓN debido a fallo de comunicación.")
        try:
            if ser:
                ser.close()
        except Exception:
            pass
        ser = None
        return "Error"

# ================= RUTA PRINCIPAL (WEB INTERFACE) =================
@app.route('/')
def home():
    # Obtener lista de puertos COM reales disponibles para mostrarlos en el frontend
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return render_template_string(HTML_TEMPLATE, ports=ports)

# ================= ENDPOINTS DE LA API =================
@app.route('/api/status', methods=['GET'])
def get_status():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    with state_lock:
        response_data = {
            'servo_angle': state['servo_angle'],
            'motor_speed': state['motor_speed'],
            'serial_connected': state['serial_connected'],
            'simulation_mode': state['simulation_mode'],
            'port': state['port'],
            'logs': state['logs'],
            'arduino_response': state['arduino_response'],
            'available_ports': ports
        }
    return jsonify(response_data)

@app.route('/api/servo', methods=['POST'])
def control_servo():
    data = request.get_json() or {}
    if 'angle' not in data:
        return jsonify({'status': 'error', 'message': 'Falta el parámetro "angle"'}), 400
        
    angle = int(data['angle'])
    if angle < 0 or angle > 180:
        return jsonify({'status': 'error', 'message': 'Ángulo fuera de rango (0-180)'}), 400
        
    with state_lock:
        state['servo_angle'] = angle
        
    # Enviar comando serial al Arduino
    arduino_resp = send_serial_cmd(f"S{angle}\n")
    return jsonify({'status': 'success', 'angle': angle, 'arduino_response': arduino_resp})

@app.route('/api/motor', methods=['POST'])
def control_motor():
    data = request.get_json() or {}
    if 'speed' not in data:
        return jsonify({'status': 'error', 'message': 'Falta el parámetro "speed"'}), 400
        
    speed = int(data['speed'])
    if speed < -255 or speed > 255:
        return jsonify({'status': 'error', 'message': 'Velocidad fuera de rango (-255 a 255)'}), 400
        
    with state_lock:
        state['motor_speed'] = speed
        
    # Enviar comando serial al Arduino
    arduino_resp = send_serial_cmd(f"M{speed}\n")
    return jsonify({'status': 'success', 'speed': speed, 'arduino_response': arduino_resp})

@app.route('/api/connect', methods=['POST'])
def connect_api():
    data = request.get_json() or {}
    port_to_connect = data.get('port', PORT_DEFAULT)
    
    with state_lock:
        state['port'] = port_to_connect
        
    success = connect_serial_port()
    return jsonify({
        'status': 'success' if success else 'simulation',
        'serial_connected': state['serial_connected'],
        'simulation_mode': state['simulation_mode'],
        'message': f"Conexión exitosa en {port_to_connect}" if success else "Iniciado en modo simulación"
    })

@app.route('/api/disconnect', methods=['POST'])
def disconnect_api():
    global ser
    with state_lock:
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
        ser = None
        state['serial_connected'] = False
        state['simulation_mode'] = True
        log_message("Desconectado del hardware manualmente. Modo simulación activado.")
        
    return jsonify({
        'status': 'success',
        'serial_connected': False,
        'simulation_mode': True
    })

# ================= DISEÑO FRONTIER WEB (CSS GLASSMORPHISM / PREMIUM) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HidroMira - Centro de Control Arduino</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.45);
            --border-glow: rgba(99, 102, 241, 0.2);
            --text-color: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-servo: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%);
            --accent-motor: linear-gradient(135deg, #10b981 0%, #059669 100%);
            --accent-danger: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            --shadow-primary: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
            --btn-hover-transform: translateY(-2px);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #0b0f19 100%);
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        header {
            padding: 24px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            background: rgba(11, 15, 25, 0.8);
            backdrop-filter: blur(10px);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-logo h1 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(to right, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: var(--accent-servo);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
        }

        .connection-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }

        .connection-badge .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .dot.connected {
            background-color: #10b981;
            box-shadow: 0 0 12px #10b981;
        }

        .dot.simulated {
            background-color: #f59e0b;
            box-shadow: 0 0 12px #f59e0b;
        }

        .dot.disconnected {
            background-color: #ef4444;
            box-shadow: 0 0 12px #ef4444;
        }

        .main-container {
            max-width: 1300px;
            width: 100%;
            margin: 0 auto;
            padding: 30px 20px;
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 25px;
            flex-grow: 1;
        }

        /* SIDEBAR DE CONFIGURACIÓN */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        .glass-card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 24px;
            box-shadow: var(--shadow-primary);
            transition: border-color 0.3s, box-shadow 0.3s;
        }

        .glass-card:hover {
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.6), 0 0 15px rgba(99, 102, 241, 0.05);
        }

        .card-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: 0.5px;
        }

        .card-title svg {
            width: 20px;
            height: 20px;
            fill: currentColor;
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .select-port {
            width: 100%;
            padding: 12px 16px;
            background: rgba(11, 15, 25, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            color: var(--text-color);
            font-size: 15px;
            outline: none;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .select-port:focus {
            border-color: #6366f1;
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.2);
        }

        .btn {
            width: 100%;
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            color: white;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn-primary {
            background: var(--accent-servo);
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }

        .btn-primary:hover {
            transform: var(--btn-hover-transform);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }

        .btn-danger {
            background: var(--accent-danger);
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
        }

        .btn-danger:hover {
            transform: var(--btn-hover-transform);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5);
        }

        /* CONSOLA DE LOGS */
        .logs-container {
            background: rgba(11, 15, 25, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 12px;
            height: 250px;
            overflow-y: auto;
            font-family: 'Courier New', Courier, monospace;
            font-size: 12px;
            color: #38bdf8;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .log-entry {
            line-height: 1.4;
            white-space: pre-wrap;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            padding-bottom: 4px;
        }

        /* MAIN CONTENT AREA */
        .control-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            align-items: start;
        }

        @media (max-width: 900px) {
            .main-container {
                grid-template-columns: 1fr;
            }
            .control-grid {
                grid-template-columns: 1fr;
            }
        }

        /* CARDS DE CONTROL DE SERVO Y MOTOR */
        .control-card {
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .servo-accent {
            border-top: 4px solid #6366f1;
        }

        .motor-accent {
            border-top: 4px solid #10b981;
        }

        .card-header-desc {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 20px;
            line-height: 1.4;
        }

        /* CONTROLES DEL SERVO */
        .servo-visual-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
            position: relative;
        }

        .servo-dial {
            width: 180px;
            height: 180px;
        }

        .servo-angle-text {
            position: absolute;
            font-size: 28px;
            font-weight: 700;
            color: var(--text-color);
            transform: translateY(20px);
        }

        .servo-needle {
            transform-origin: 90px 90px;
            transition: transform 0.6s cubic-bezier(0.19, 1, 0.22, 1);
        }

        .control-slider-container {
            margin: 25px 0 15px 0;
        }

        .slider-header {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 10px;
        }

        .angle-val {
            color: #6366f1;
            font-size: 16px;
            font-weight: 700;
        }

        .speed-val {
            color: #10b981;
            font-size: 16px;
            font-weight: 700;
        }

        .input-slider {
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.1);
            outline: none;
            -webkit-appearance: none;
            transition: all 0.3s;
        }

        .input-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #ffffff;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
            transition: transform 0.1s, background-color 0.3s;
        }

        .input-slider::-webkit-slider-thumb:hover {
            transform: scale(1.2);
        }

        .servo-slider::-webkit-slider-thumb {
            background: #6366f1;
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.6);
        }

        .motor-slider::-webkit-slider-thumb {
            background: #10b981;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
        }

        .preset-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin-top: 15px;
        }

        .preset-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 10px 4px;
            color: var(--text-color);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .preset-btn:hover {
            background: rgba(99, 102, 241, 0.15);
            border-color: #6366f1;
            color: white;
            transform: translateY(-1px);
        }

        /* CONTROLES DEL MOTOR L298N */
        .motor-visual-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin: 15px 0;
            min-height: 180px;
        }

        /* ANIMACIÓN MOTOR GIRATORIO */
        .motor-fan-wrapper {
            position: relative;
            width: 140px;
            height: 140px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 50%;
            border: 2px dashed rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.4);
        }

        .motor-fan {
            width: 100px;
            height: 100px;
            position: relative;
            transform-origin: center center;
            animation: spin 3s linear infinite;
            animation-play-state: paused;
        }

        /* Aspas de la Hélice */
        .fan-blade {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 16px;
            height: 48px;
            background: linear-gradient(to bottom, #10b981, #059669);
            border-radius: 8px;
            transform-origin: center top;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
        }

        .blade-1 { transform: translate(-50%, -100%) rotate(0deg); }
        .blade-2 { transform: translate(-50%, -100%) rotate(90deg); }
        .blade-3 { transform: translate(-50%, -100%) rotate(180deg); }
        .blade-4 { transform: translate(-50%, -100%) rotate(270deg); }

        .fan-center {
            position: absolute;
            width: 24px;
            height: 24px;
            background: #ffffff;
            border: 4px solid #111827;
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.4);
            z-index: 2;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .motor-btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }

        .motor-ctrl-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px;
            color: var(--text-color);
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
        }

        .motor-ctrl-btn.fwd:hover {
            background: rgba(16, 185, 129, 0.15);
            border-color: #10b981;
            color: #10b981;
        }

        .motor-ctrl-btn.rev:hover {
            background: rgba(245, 158, 11, 0.15);
            border-color: #f59e0b;
            color: #f59e0b;
        }

        .motor-ctrl-btn.stop {
            border-color: rgba(239, 68, 68, 0.3);
        }

        .motor-ctrl-btn.stop:hover {
            background: rgba(239, 68, 68, 0.2);
            border-color: #ef4444;
            color: #ef4444;
        }

        /* L298N PINS STATUS INDICATOR */
        .pin-status-deck {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .pin-pill {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .pin-pill .pin-name {
            font-size: 11px;
            color: var(--text-muted);
            font-weight: 600;
        }

        .pin-pill .pin-val {
            font-size: 13px;
            font-weight: 700;
        }

        .pin-pill.active {
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.05);
        }
        
        .pin-pill.active .pin-val {
            color: #10b981;
        }

        .arduino-echo {
            margin-top: 20px;
            padding: 12px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 14px;
        }

        .arduino-echo span {
            font-weight: 600;
            color: #a855f7;
        }

        footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 13px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: auto;
        }

        footer a {
            color: #6366f1;
            text-decoration: none;
        }
    </style>
</head>
<body>

    <header>
        <div class="header-logo">
            <div class="logo-icon">H</div>
            <div>
                <h1>HidroMira</h1>
                <p style="font-size: 11px; color: var(--text-muted);">Panel de Control Serial Arduino</p>
            </div>
        </div>
        
        <div class="connection-badge" id="conn-badge">
            <span class="dot disconnected" id="conn-dot"></span>
            <span id="conn-text">Desconectado</span>
        </div>
    </header>

    <div class="main-container">
        
        <!-- SIDEBAR DE CONFIGURACIÓN -->
        <div class="sidebar">
            
            <div class="glass-card">
                <h3 class="card-title">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H7c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.04-.42 1.99-1.07 2.75z"/></svg>
                    Conexión Serial
                </h3>
                
                <div class="form-group">
                    <label for="port-selector">Puerto COM (Arduino)</label>
                    <select id="port-selector" class="select-port">
                        {% for port in ports %}
                            <option value="{{ port }}" {% if port == 'COM3' %}selected{% endif %}>{{ port }}</option>
                        {% empty %}
                            <option value="COM3">COM3 (No detectado)</option>
                        {% endfor %}
                    </select>
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 20px;">
                    <button class="btn btn-primary" id="btn-connect" onclick="connectSerial()">Conectar</button>
                    <button class="btn btn-danger" id="btn-disconnect" onclick="disconnectSerial()" style="display:none;">Desconectar</button>
                </div>
            </div>

            <div class="glass-card" style="flex-grow: 1; display: flex; flex-direction: column;">
                <h3 class="card-title">
                    <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/></svg>
                    Consola Serial
                </h3>
                <div class="logs-container" id="logs-box">
                    <div class="log-entry">[INFO] Consola web iniciada. Presiona Conectar.</div>
                </div>
            </div>
            
        </div>

        <!-- AREA DE CONTROL PRINCIPAL -->
        <div class="control-grid">
            
            <!-- TARJETA DEL SERVO -->
            <div class="glass-card control-card servo-accent">
                <h3 class="card-title" style="color: #818cf8;">
                    <svg viewBox="0 0 24 24" style="fill: #818cf8;"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                    Servomotor
                </h3>
                <p class="card-header-desc">
                    Control de posición angular del servomotor en tiempo real a través del Pin Digital 10.
                </p>
                
                <div class="servo-visual-container">
                    <!-- Dial del Servo SVG -->
                    <svg class="servo-dial" viewBox="0 0 180 180">
                        <!-- Arco de fondo -->
                        <path d="M 20 120 A 70 70 0 0 1 160 120" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="12" stroke-linecap="round"/>
                        <!-- Marcadores -->
                        <line x1="20" y1="120" x2="30" y2="115" stroke="rgba(255,255,255,0.3)" stroke-width="2" />
                        <line x1="90" y1="50" x2="90" y2="60" stroke="rgba(255,255,255,0.3)" stroke-width="2" />
                        <line x1="160" y1="120" x2="150" y2="115" stroke="rgba(255,255,255,0.3)" stroke-width="2" />
                        
                        <!-- Aguja -->
                        <g class="servo-needle" id="servo-needle" transform="rotate(0, 90, 90)">
                            <polygon points="90,20 85,90 95,90" fill="#6366f1" />
                            <circle cx="90" cy="90" r="10" fill="#4f46e5" />
                        </g>
                    </svg>
                    <div class="servo-angle-text"><span id="servo-angle-display">90</span>°</div>
                </div>

                <div class="control-slider-container">
                    <div class="slider-header">
                        <span>Ajustar Ángulo</span>
                        <span class="angle-val"><span id="slider-angle-display">90</span>°</span>
                    </div>
                    <input type="range" id="servo-range" class="input-slider servo-slider" min="0" max="180" value="90" oninput="updateServoFromSlider(this.value)">
                </div>

                <div class="preset-grid">
                    <button class="preset-btn" onclick="setServoAngle(0)">0°</button>
                    <button class="preset-btn" onclick="setServoAngle(45)">45°</button>
                    <button class="preset-btn" onclick="setServoAngle(90)">90°</button>
                    <button class="preset-btn" onclick="setServoAngle(135)">135°</button>
                    <button class="preset-btn" onclick="setServoAngle(180)">180°</button>
                </div>
            </div>

            <!-- TARJETA DEL MOTOR L298N -->
            <div class="glass-card control-card motor-accent">
                <h3 class="card-title" style="color: #34d399;">
                    <svg viewBox="0 0 24 24" style="fill: #34d399;"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                    Motor DC (L298N)
                </h3>
                <p class="card-header-desc">
                    Control de velocidad PWM mediante el puente H L298N (ENA: Pin 6, IN1: Pin 9, IN2: Pin 7).
                </p>
                
                <div class="motor-visual-container">
                    <div class="motor-fan-wrapper">
                        <div class="motor-fan" id="motor-fan">
                            <div class="fan-blade blade-1"></div>
                            <div class="fan-blade blade-2"></div>
                            <div class="fan-blade blade-3"></div>
                            <div class="fan-blade blade-4"></div>
                            <div class="fan-center"></div>
                        </div>
                    </div>
                </div>

                <div class="control-slider-container">
                    <div class="slider-header">
                        <span>Velocidad & Dirección</span>
                        <span class="speed-val"><span id="slider-speed-display">0</span></span>
                    </div>
                    <input type="range" id="motor-range" class="input-slider motor-slider" min="-255" max="255" value="0" oninput="updateMotorFromSlider(this.value)">
                </div>

                <div class="motor-btn-group">
                    <button class="motor-ctrl-btn fwd" onclick="setMotorSpeed(200)">Adelante</button>
                    <button class="motor-ctrl-btn stop" onclick="setMotorSpeed(0)">Detener</button>
                    <button class="motor-ctrl-btn rev" onclick="setMotorSpeed(-200)">Reversa</button>
                </div>

                <div class="pin-status-deck">
                    <div class="pin-pill" id="pin-ena">
                        <span class="pin-name">ENA (Pin 6)</span>
                        <span class="pin-val" id="val-ena">0</span>
                    </div>
                    <div class="pin-pill" id="pin-in1">
                        <span class="pin-name">IN1 (Pin 9)</span>
                        <span class="pin-val" id="val-in1">LOW</span>
                    </div>
                    <div class="pin-pill" id="pin-in2">
                        <span class="pin-name">IN2 (Pin 7)</span>
                        <span class="pin-val" id="val-in2">LOW</span>
                    </div>
                </div>
            </div>
            
            <!-- CAJA COMPARTIDA ECOS ARDUINO -->
            <div class="glass-card" style="grid-column: 1 / -1;">
                <div class="arduino-echo">
                    Último eco del Arduino: <span id="arduino-response">Ninguna</span>
                </div>
            </div>

        </div>

    </div>

    <footer>
        <p>Desarrollado para <b>HidroMira</b>. Puerto Arduino por defecto: COM3</p>
    </footer>

    <!-- LOGIC / INTERACTIVITY SCRIPT -->
    <script>
        let updateTimeoutServo = null;
        let updateTimeoutMotor = null;

        // Iniciar chequeo periódico del estado del servidor
        setInterval(fetchStatus, 1500);
        fetchStatus();

        // Conectar al puerto serial seleccionado
        async function connectSerial() {
            const port = document.getElementById('port-selector').value;
            try {
                const response = await fetch('/api/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ port: port })
                });
                const data = await response.json();
                updateUIState(data);
                addLog(`Conectando al puerto ${port}...`);
            } catch (err) {
                console.error("Error conectando serial:", err);
                addLog("Error de conexión al servidor Flask.");
            }
        }

        // Desconectar manualmente
        async function disconnectSerial() {
            try {
                const response = await fetch('/api/disconnect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await response.json();
                updateUIState(data);
                addLog("Hardware desconectado manualmente.");
            } catch (err) {
                console.error("Error desconectando:", err);
            }
        }

        // Solicitar estado al servidor Flask
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateUIState(data);
            } catch (err) {
                console.warn("No se pudo obtener el estado actual del servidor Flask.");
            }
        }

        // Actualizar elementos de la interfaz de usuario
        function updateUIState(data) {
            // Actualizar badge de estado
            const dot = document.getElementById('conn-dot');
            const text = document.getElementById('conn-text');
            const btnConnect = document.getElementById('btn-connect');
            const btnDisconnect = document.getElementById('btn-disconnect');

            dot.className = "dot";
            if (data.serial_connected) {
                dot.classList.add('connected');
                text.innerText = `Conectado (${data.port})`;
                btnConnect.style.display = 'none';
                btnDisconnect.style.display = 'block';
            } else if (data.simulation_mode) {
                dot.classList.add('simulated');
                text.innerText = `Simulado (Fallo en ${data.port})`;
                btnConnect.style.display = 'block';
                btnDisconnect.style.display = 'none';
            } else {
                dot.classList.add('disconnected');
                text.innerText = "Desconectado";
                btnConnect.style.display = 'block';
                btnDisconnect.style.display = 'none';
            }

            // Actualizar Eco del Arduino
            document.getElementById('arduino-response').innerText = data.arduino_response || "Ninguna";

            // Actualizar Dial y Slider del Servo (solo si no se está arrastrando)
            if (!document.activeElement || document.activeElement.id !== 'servo-range') {
                document.getElementById('servo-range').value = data.servo_angle;
                updateServoVisuals(data.servo_angle);
            }

            // Actualizar Slider y animación del Motor (solo si no se está arrastrando)
            if (!document.activeElement || document.activeElement.id !== 'motor-range') {
                document.getElementById('motor-range').value = data.motor_speed;
                updateMotorVisuals(data.motor_speed);
            }

            // Actualizar Consola de Logs
            const logsBox = document.getElementById('logs-box');
            if (data.logs && data.logs.length > 0) {
                // Solo recargar si cambió la cantidad
                const currentLogCount = logsBox.children.length;
                if (currentLogCount !== data.logs.length) {
                    logsBox.innerHTML = '';
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.innerText = log;
                        logsBox.appendChild(div);
                    });
                    logsBox.scrollTop = logsBox.scrollHeight;
                }
            }
        }

        // Agregar log local en la consola
        function addLog(text) {
            const logsBox = document.getElementById('logs-box');
            const timestamp = new Date().toTimeString().split(' ')[0];
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerText = `[${timestamp}] [WEB] ${text}`;
            logsBox.appendChild(div);
            logsBox.scrollTop = logsBox.scrollHeight;
        }

        // Actualizar posición física de la aguja y texto
        function updateServoVisuals(angle) {
            document.getElementById('servo-angle-display').innerText = angle;
            document.getElementById('slider-angle-display').innerText = angle;
            
            // Mapear ángulo 0..180 a rotación de aguja -90deg a +90deg
            const rotation = angle - 90;
            const needle = document.getElementById('servo-needle');
            needle.style.transform = `rotate(${rotation}deg)`;
        }

        // Enviar ángulo de servo desde slider (Debounce)
        function updateServoFromSlider(val) {
            updateServoVisuals(val);
            clearTimeout(updateTimeoutServo);
            updateTimeoutServo = setTimeout(() => {
                sendServoAngle(val);
            }, 80);
        }

        // Enviar ángulo de servo (API POST)
        async function sendServoAngle(angle) {
            try {
                const response = await fetch('/api/servo', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ angle: parseInt(angle) })
                });
                const resData = await response.json();
                document.getElementById('arduino-response').innerText = resData.arduino_response || "Comando enviado";
            } catch (err) {
                console.error("Error enviando ángulo servo:", err);
            }
        }

        // Ajustar ángulo con presets
        function setServoAngle(angle) {
            document.getElementById('servo-range').value = angle;
            updateServoVisuals(angle);
            sendServoAngle(angle);
        }

        // Actualizar visuales del motor (hélice y pines L298N)
        function updateMotorVisuals(speed) {
            document.getElementById('slider-speed-display').innerText = speed;
            
            const fan = document.getElementById('motor-fan');
            const pinEna = document.getElementById('pin-ena');
            const pinIn1 = document.getElementById('pin-in1');
            const pinIn2 = document.getElementById('pin-in2');
            
            const valEna = document.getElementById('val-ena');
            const valIn1 = document.getElementById('val-in1');
            const valIn2 = document.getElementById('val-in2');

            // Determinar sentido y activar pines L298N
            if (speed == 0) {
                // Apagado
                fan.style.animationPlayState = 'paused';
                
                pinEna.classList.remove('active');
                pinIn1.classList.remove('active');
                pinIn2.classList.remove('active');
                
                valEna.innerText = "0";
                valIn1.innerText = "LOW";
                valIn2.innerText = "LOW";
            } else {
                fan.style.animationPlayState = 'running';
                
                // Controlar la velocidad de rotación en base a la magnitud
                const absSpeed = Math.abs(speed);
                // Mapeo: speed=255 -> 0.3s (rápido), speed=50 -> 2.5s (lento)
                const duration = Math.max(0.2, (255 - absSpeed) / 80 + 0.3);
                fan.style.animationDuration = `${duration}s`;
                
                // Control de dirección en la animación
                if (speed > 0) {
                    fan.style.animationDirection = 'normal';
                    
                    pinEna.classList.add('active');
                    pinIn1.classList.add('active');
                    pinIn2.classList.remove('active');
                    
                    valEna.innerText = absSpeed;
                    valIn1.innerText = "HIGH";
                    valIn2.innerText = "LOW";
                } else {
                    fan.style.animationDirection = 'reverse';
                    
                    pinEna.classList.add('active');
                    pinIn1.classList.remove('active');
                    pinIn2.classList.add('active');
                    
                    valEna.innerText = absSpeed;
                    valIn1.innerText = "LOW";
                    valIn2.innerText = "HIGH";
                }
            }
        }

        // Controlar motor desde Slider (Debounce)
        function updateMotorFromSlider(val) {
            updateMotorVisuals(val);
            clearTimeout(updateTimeoutMotor);
            updateTimeoutMotor = setTimeout(() => {
                sendMotorSpeed(val);
            }, 80);
        }

        // Enviar velocidad de motor (API POST)
        async function sendMotorSpeed(speed) {
            try {
                const response = await fetch('/api/motor', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ speed: parseInt(speed) })
                });
                const resData = await response.json();
                document.getElementById('arduino-response').innerText = resData.arduino_response || "Comando enviado";
            } catch (err) {
                console.error("Error enviando velocidad motor:", err);
            }
        }

        // Ajustar velocidad con botones rápidos
        function setMotorSpeed(speed) {
            document.getElementById('motor-range').value = speed;
            updateMotorVisuals(speed);
            sendMotorSpeed(speed);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("DEBUG: Entrando en __main__", flush=True)
    # Intentar conexión inicial en puerto COM3
    print("DEBUG: Llamando a connect_serial_port()", flush=True)
    connect_serial_port()
    print("DEBUG: connect_serial_port() finalizado", flush=True)
    
    # Iniciar Flask en puerto 5000 (abierto a red local si se desea con host='0.0.0.0')
    port_flask = 5000
    print(f"\n[SERVIDOR] Iniciando servidor web de HidroMira en http://localhost:{port_flask}\n", flush=True)
    try:
        print("DEBUG: Ejecutando app.run()...", flush=True)
        app.run(host='0.0.0.0', port=port_flask, debug=False)
    except Exception as e:
        print(f"DEBUG: Error en app.run(): {e}", flush=True)

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Permitir acceso desde cualquier origen

# Ruta al archivo de datos
DATA_FILE = os.path.join(os.path.dirname(__file__), 'historical_data.json')

def cargar_datos():
    """Cargar datos del archivo JSON"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except:
        return []

@app.route('/')
def home():
    """Endpoint raíz con información de la API"""
    return jsonify({
        'nombre': 'HidroMira IoT API',
        'version': '1.0',
        'descripcion': 'API REST para monitoreo de vibraciones',
        'endpoints': {
            '/': 'Información de la API',
            '/status': 'Estado actual del sistema',
            '/datos': 'Últimas N lecturas (query: limit=N)',
            '/datos/rango': 'Lecturas en rango de fechas (query: desde=ISO8601&hasta=ISO8601)',
            '/estadisticas': 'Estadísticas generales',
            '/alertas': 'Lecturas en zona B, C o D'
        }
    })

@app.route('/status')
def status():
    """Estado actual del sistema"""
    datos = cargar_datos()
    if not datos:
        return jsonify({'error': 'No hay datos disponibles'}), 404
    
    ultimo = datos[-1]
    return jsonify({
        'timestamp': ultimo.get('ts'),
        'vx': ultimo.get('vx'),
        'vy': ultimo.get('vy'),
        'vz': ultimo.get('vz'),
        'total_lecturas': len(datos)
    })

@app.route('/datos')
def datos():
    """Obtener últimas N lecturas"""
    limit = request.args.get('limit', default=100, type=int)
    datos = cargar_datos()
    
    if not datos:
        return jsonify({'error': 'No hay datos disponibles'}), 404
    
    return jsonify({
        'total': len(datos),
        'limite': limit,
        'datos': datos[-limit:]
    })

@app.route('/datos/rango')
def datos_rango():
    """Obtener datos en rango de fechas"""
    desde_str = request.args.get('desde')
    hasta_str = request.args.get('hasta')
    
    if not desde_str or not hasta_str:
        return jsonify({'error': 'Se requieren parámetros desde y hasta (formato ISO8601)'}), 400
    
    try:
        desde = datetime.fromisoformat(desde_str.replace('Z', '+00:00'))
        hasta = datetime.fromisoformat(hasta_str.replace('Z', '+00:00'))
    except:
        return jsonify({'error': 'Formato de fecha inválido. Use ISO8601 (ej: 2026-01-07T12:00:00Z)'}), 400
    
    datos = cargar_datos()
    datos_filtrados = []
    
    for d in datos:
        try:
            ts = datetime.fromisoformat(d['ts'].replace('Z', '+00:00'))
            if desde <= ts <= hasta:
                datos_filtrados.append(d)
        except:
            continue
    
    return jsonify({
        'desde': desde_str,
        'hasta': hasta_str,
        'total': len(datos_filtrados),
        'datos': datos_filtrados
    })

@app.route('/estadisticas')
def estadisticas():
    """Estadísticas generales del sistema"""
    datos = cargar_datos()
    
    if not datos:
        return jsonify({'error': 'No hay datos disponibles'}), 404
    
    import numpy as np
    
    vx_vals = [d['vx'] for d in datos if 'vx' in d]
    vy_vals = [d['vy'] for d in datos if 'vy' in d]
    vz_vals = [d['vz'] for d in datos if 'vz' in d]
    
    def clasificar_zona(v):
        if v <= 0.25:
            return 'A'
        elif v <= 0.5:
            return 'B'
        elif v <= 0.75:
            return 'C'
        else:
            return 'D'
    
    zonas = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for vx, vy, vz in zip(vx_vals, vy_vals, vz_vals):
        vmax = max(vx, vy, vz)
        zona = clasificar_zona(vmax)
        zonas[zona] += 1
    
    return jsonify({
        'total_lecturas': len(datos),
        'periodo': {
            'inicio': datos[0]['ts'] if datos else None,
            'fin': datos[-1]['ts'] if datos else None
        },
        'estadisticas': {
            'vx': {
                'promedio': float(np.mean(vx_vals)) if vx_vals else 0,
                'max': float(np.max(vx_vals)) if vx_vals else 0,
                'min': float(np.min(vx_vals)) if vx_vals else 0,
                'std': float(np.std(vx_vals)) if vx_vals else 0
            },
            'vy': {
                'promedio': float(np.mean(vy_vals)) if vy_vals else 0,
                'max': float(np.max(vy_vals)) if vy_vals else 0,
                'min': float(np.min(vy_vals)) if vy_vals else 0,
                'std': float(np.std(vy_vals)) if vy_vals else 0
            },
            'vz': {
                'promedio': float(np.mean(vz_vals)) if vz_vals else 0,
                'max': float(np.max(vz_vals)) if vz_vals else 0,
                'min': float(np.min(vz_vals)) if vz_vals else 0,
                'std': float(np.std(vz_vals)) if vz_vals else 0
            }
        },
        'distribucion_zonas': zonas
    })

@app.route('/alertas')
def alertas():
    """Obtener lecturas que requieren atención (Zona B, C, D)"""
    datos = cargar_datos()
    
    if not datos:
        return jsonify({'error': 'No hay datos disponibles'}), 404
    
    def clasificar_zona(v):
        if v <= 0.25:
            return 'A'
        elif v <= 0.5:
            return 'B'
        elif v <= 0.75:
            return 'C'
        else:
            return 'D'
    
    alertas = []
    for d in datos:
        vx = d.get('vx', 0)
        vy = d.get('vy', 0)
        vz = d.get('vz', 0)
        vmax = max(vx, vy, vz)
        zona = clasificar_zona(vmax)
        
        if zona in ['B', 'C', 'D']:
            alertas.append({
                'timestamp': d['ts'],
                'zona': zona,
                'vmax': vmax,
                'vx': vx,
                'vy': vy,
                'vz': vz
            })
    
    return jsonify({
        'total_alertas': len(alertas),
        'alertas': alertas[-50:]  # Últimas 50
    })

if __name__ == '__main__':
    import iot_config
    app.run(
        host=iot_config.API_HOST,
        port=iot_config.API_PORT,
        debug=False
    )

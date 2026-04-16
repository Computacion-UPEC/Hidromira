import json
import os
from datetime import datetime, timedelta
import random
import math

# Generar datos desde hace 6 meses
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=180)  # 6 meses

all_readings = []

# Fechas de mantenimiento cada 4 meses en el período de 6 meses
# Mantenimiento 1: hace 4 meses
maintenance_dates = [
    start_date + timedelta(days=120),  # Después de 4 meses
]

# Generador de vibraciones con aumento gradual y reseteo en mantenimiento
base_vibration = 0.2
max_vibration_before_maintenance = 1.8

current_date = start_date
reading_count = 0

while current_date < end_date:
    # Calcular progreso hacia el próximo mantenimiento
    days_since_start = (current_date - start_date).days
    days_since_last_maintenance = 0
    
    # Encontrar cuántos días hace desde el último mantenimiento
    for maint_date in maintenance_dates:
        if current_date >= maint_date:
            days_since_last_maintenance = (current_date - maint_date).days
    
    # Si no hay mantenimiento aplicado, usar días desde el inicio
    if days_since_last_maintenance == 0 and current_date >= start_date:
        days_since_last_maintenance = days_since_start
    
    # Progresión de vibraciones: aumentan gradualmente
    # Después de mantenimiento: vibración baja
    # Conforme pasan días: vibración aumenta
    progress_to_maintenance = min(1.0, days_since_last_maintenance / 120.0)  # 120 días para llegar al máximo
    
    # Vibración base que aumenta con el tiempo
    vx_base = base_vibration + (max_vibration_before_maintenance - base_vibration) * progress_to_maintenance
    vy_base = base_vibration + (max_vibration_before_maintenance - base_vibration) * progress_to_maintenance * 0.8
    vz_base = base_vibration + (max_vibration_before_maintenance - base_vibration) * progress_to_maintenance * 0.9
    
    # Añadir ruido variabilidad realista
    vx = vx_base + random.gauss(0, 0.05)
    vy = vy_base + random.gauss(0, 0.04)
    vz = vz_base + random.gauss(0, 0.045)
    
    # Asegurar valores positivos y dentro de rango
    vx = max(0.0, min(2.5, vx))
    vy = max(0.0, min(2.5, vy))
    vz = max(0.0, min(2.5, vz))
    
    # Crear lectura
    reading = {
        'vx': round(vx, 2),
        'vy': round(vy, 2),
        'vz': round(vz, 2),
        'ts': current_date.isoformat() + 'Z'
    }
    
    all_readings.append(reading)
    reading_count += 1
    
    # Incrementar 1 minuto para próxima lectura
    current_date += timedelta(minutes=1)

# Guardar en historical_data.json
output_path = os.path.join(os.path.dirname(__file__), 'historical_data.json')

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_readings, f, indent=2)
    print(f'✅ Generados {len(all_readings)} lecturas')
    print(f'📅 Período: {start_date.strftime("%Y-%m-%d")} → {end_date.strftime("%Y-%m-%d")}')
    print(f'🔧 Mantenimiento cada 4 meses')
    print(f'💾 Guardado en: {output_path}')
except Exception as e:
    print(f'❌ Error al guardar: {e}')

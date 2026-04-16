import json
import os
from datetime import datetime, timedelta
import random

# Configuración
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime.utcnow()
MAINTENANCE_INTERVAL_DAYS = 120  # ~4 meses
BASE_VIBRATION = 0.15  # mm/s inicial
VIBRATION_INCREASE_PER_DAY = 0.008  # Incremento diario natural
VIBRATION_POST_MAINTENANCE = 0.20  # Vibración después de mantenimiento
VIBRATION_NOISE = 0.08  # Ruido aleatorio ±
SAMPLING_INTERVAL = 5  # segundos entre muestras
SAMPLES_PER_DAY = (24 * 3600) // SAMPLING_INTERVAL  # ~17280 muestras/día

print("Generando datos históricos desde 2022-01-01...")
print(f"Intervalo de mantenimiento: {MAINTENANCE_INTERVAL_DAYS} días")
print(f"Incremento diario de vibración: {VIBRATION_INCREASE_PER_DAY:.4f} mm/s")

all_readings = []
current_date = START_DATE
maintenance_counter = 0
days_since_maintenance = 0

while current_date <= END_DATE:
    # Calcular la vibración base para hoy
    days_from_start = (current_date - START_DATE).days
    maintenance_number = days_from_start // MAINTENANCE_INTERVAL_DAYS
    days_since_maintenance = days_from_start % MAINTENANCE_INTERVAL_DAYS
    
    # Vibración aumenta gradualmente
    # Después de cada mantenimiento, comienza baja y sube
    base_vib = VIBRATION_POST_MAINTENANCE + (VIBRATION_INCREASE_PER_DAY * days_since_maintenance)
    
    # Agregar algunas muestras para este día
    for sample in range(SAMPLES_PER_DAY):
        timestamp = current_date + timedelta(seconds=sample * SAMPLING_INTERVAL)
        
        if timestamp > END_DATE:
            break
        
        # Agregar ruido aleatorio a cada componente
        vx = max(0.0, base_vib + random.uniform(-VIBRATION_NOISE, VIBRATION_NOISE))
        vy = max(0.0, base_vib + random.uniform(-VIBRATION_NOISE, VIBRATION_NOISE))
        vz = max(0.0, base_vib + random.uniform(-VIBRATION_NOISE, VIBRATION_NOISE))
        
        # Ocasionalmente agregar picos (anomalías)
        if random.random() < 0.002:  # 0.2% de probabilidad
            pico_factor = random.uniform(1.5, 3.0)
            vx *= pico_factor
        if random.random() < 0.002:
            pico_factor = random.uniform(1.5, 3.0)
            vy *= pico_factor
        if random.random() < 0.002:
            pico_factor = random.uniform(1.5, 3.0)
            vz *= pico_factor
        
        reading = {
            'vx': round(vx, 2),
            'vy': round(vy, 2),
            'vz': round(vz, 2),
            'ts': timestamp.isoformat() + 'Z'
        }
        all_readings.append(reading)
    
    current_date += timedelta(days=1)
    
    # Mostrar progreso cada mes
    if (current_date - START_DATE).days % 30 == 0:
        print(f"  {current_date.strftime('%Y-%m-%d')}: {len(all_readings)} lecturas generadas")

print(f"\nTotal de lecturas generadas: {len(all_readings)}")

# Guardar en archivo
output_path = os.path.join(os.path.dirname(__file__), 'historical_data.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_readings, f, indent=2)

print(f"✅ Datos guardados en: {output_path}")
print(f"\nResumen:")
print(f"  Período: {START_DATE.date()} a {END_DATE.date()}")
print(f"  Días totales: {(END_DATE - START_DATE).days}")
print(f"  Ciclos de mantenimiento: {(END_DATE - START_DATE).days // MAINTENANCE_INTERVAL_DAYS + 1}")
print(f"  Primeras 3 lecturas:")
for i in range(min(3, len(all_readings))):
    r = all_readings[i]
    print(f"    {r['ts']}: vx={r['vx']}, vy={r['vy']}, vz={r['vz']}")
print(f"  Últimas 3 lecturas:")
for i in range(max(0, len(all_readings)-3), len(all_readings)):
    r = all_readings[i]
    print(f"    {r['ts']}: vx={r['vx']}, vy={r['vy']}, vz={r['vz']}")

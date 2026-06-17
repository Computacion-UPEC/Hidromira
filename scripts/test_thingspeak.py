"""
Script de prueba para ThingSpeak
Envía un dato de prueba para verificar la conexión
"""
import sys
import os
# Añadir la carpeta raíz al path para poder importar iot_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import iot_config

print("=" * 60)
print("🧪 TEST DE CONEXIÓN THINGSPEAK")
print("=" * 60)

# Verificar configuración
print(f"\n📋 Configuración:")
print(f"   Habilitado: {iot_config.THINGSPEAK_ENABLED}")
print(f"   API Key: {iot_config.THINGSPEAK_API_KEY}")
print(f"   Channel ID: {iot_config.THINGSPEAK_CHANNEL_ID}")

if not iot_config.THINGSPEAK_ENABLED:
    print("\n❌ ThingSpeak está deshabilitado en iot_config.py")
    print("   Cambia THINGSPEAK_ENABLED = True")
    exit(1)

# Enviar datos de prueba
print(f"\n📤 Enviando datos de prueba...")

url = "https://api.thingspeak.com/update"
payload = {
    'api_key': iot_config.THINGSPEAK_API_KEY,
    'field1': 0.15,  # Vx
    'field2': 0.12,  # Vy
    'field3': 0.08,  # Vz
    'field4': 0.13,  # RMS
    'field5': 65     # Zona A (ASCII)
}

print(f"   URL: {url}")
print(f"   Datos: vx=0.15, vy=0.12, vz=0.08, rms=0.13, zona=A")

try:
    response = requests.post(url, data=payload, timeout=10)
    
    print(f"\n📥 Respuesta:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Body: {response.text}")
    
    if response.status_code == 200:
        entry_id = response.text.strip()
        if entry_id != '0':
            print(f"\n✅ ¡ÉXITO! Entry ID: {entry_id}")
            print(f"\n🌐 Ver datos en:")
            print(f"   https://thingspeak.com/channels/{iot_config.THINGSPEAK_CHANNEL_ID}")
            print(f"   https://thingspeak.com/channels/{iot_config.THINGSPEAK_CHANNEL_ID}/charts/1")
        else:
            print(f"\n❌ ThingSpeak rechazó los datos (Entry ID = 0)")
            print(f"\n🔍 Posibles causas:")
            print(f"   1. API Key incorrecta")
            print(f"   2. Rate limit (solo 1 envío cada 15 segundos)")
            print(f"   3. Canal no existe o está deshabilitado")
            print(f"\n💡 Soluciones:")
            print(f"   1. Verifica el Write API Key en https://thingspeak.com/channels/{iot_config.THINGSPEAK_CHANNEL_ID}/api_keys")
            print(f"   2. Espera 15 segundos y vuelve a intentar")
            print(f"   3. Verifica que el canal exista en tu cuenta")
    else:
        print(f"\n❌ Error HTTP {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error de conexión: {e}")
    print(f"\n🔍 Posibles causas:")
    print(f"   1. Sin conexión a internet")
    print(f"   2. Firewall bloqueando conexiones")
    print(f"   3. ThingSpeak no disponible")

print("\n" + "=" * 60)
print("Presiona Enter para salir...")
input()

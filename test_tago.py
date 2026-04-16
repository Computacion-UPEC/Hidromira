import paho.mqtt.client as mqtt
import json
import time

# Usa el Token que viste en tu pantalla (5d6440c7...)
TOKEN = "5d6440c7-12f8-4125-b303-46007ee07b4b" 
BROKER = "mqtt.tago.io"

client = mqtt.Client()
client.username_pw_set("Token", TOKEN)

# PRUEBA ESTO: Si el puerto 1883 falla, el 8883 con TLS suele arreglarlo
client.tls_set() 
client.connect(BROKER, 8883)

print("📡 Enviando pulso de vida a TagoIO...")

while True:
    payload = [{
        "variable": "vibracion",
        "value": 25.5,
        "unit": "mm/s"
    }]
    
    result = client.publish("tago/data/post", json.dumps(payload))
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print("✅ Mensaje aceptado por el Broker")
    else:
        print("❌ Error de red: El mensaje no salió de tu PC")
        
    time.sleep(5)
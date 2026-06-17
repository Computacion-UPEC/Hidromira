"""
Script de diagnóstico para sensor ModBus WTVB01-485
Prueba diferentes configuraciones para encontrar la correcta
"""
import minimalmodbus
import time
import serial.tools.list_ports

print("=" * 70)
print("🔍 DIAGNÓSTICO DE SENSOR MODBUS WTVB01-485")
print("=" * 70)

# 1. Listar puertos disponibles
print("\n📋 Puertos COM disponibles:")
puertos = serial.tools.list_ports.comports()
if puertos:
    for puerto in puertos:
        print(f"   • {puerto.device}: {puerto.description}")
else:
    print("   ❌ No se encontraron puertos COM")

# 2. Configuraciones a probar
configuraciones = [
    {'puerto': 'COM8', 'direccion': 80, 'baudrate': 9600, 'timeout': 1.0},
    {'puerto': 'COM8', 'direccion': 1, 'baudrate': 9600, 'timeout': 1.0},
    {'puerto': 'COM8', 'direccion': 80, 'baudrate': 19200, 'timeout': 1.0},
]

print("\n🧪 Probando configuraciones...\n")

for idx, config in enumerate(configuraciones, 1):
    print(f"Prueba {idx}/{len(configuraciones)}: {config['puerto']} @ {config['baudrate']} baud, Dir={config['direccion']}")
    
    try:
        # Crear instrumento
        sensor = minimalmodbus.Instrument(config['puerto'], config['direccion'])
        sensor.serial.baudrate = config['baudrate']
        sensor.serial.bytesize = 8
        sensor.serial.parity = minimalmodbus.serial.PARITY_NONE
        sensor.serial.stopbits = 1
        sensor.serial.timeout = config['timeout']
        sensor.mode = minimalmodbus.MODE_RTU
        sensor.clear_buffers_before_each_transaction = True
        
        # Intentar leer registros
        print(f"   Intentando leer registro 0x3D (61)...")
        vx = sensor.read_register(61, functioncode=3, signed=True)
        print(f"   ✅ Registro 61: {vx} (raw) = {vx/100.0:.3f} mm/s")
        
        time.sleep(0.1)
        
        print(f"   Intentando leer registro 0x3E (62)...")
        vy = sensor.read_register(62, functioncode=3, signed=True)
        print(f"   ✅ Registro 62: {vy} (raw) = {vy/100.0:.3f} mm/s")
        
        time.sleep(0.1)
        
        print(f"   Intentando leer registro 0x3F (63)...")
        vz = sensor.read_register(63, functioncode=3, signed=True)
        print(f"   ✅ Registro 63: {vz} (raw) = {vz/100.0:.3f} mm/s")
        
        print(f"\n   🎉 ¡CONFIGURACIÓN CORRECTA ENCONTRADA!")
        print(f"   Puerto: {config['puerto']}")
        print(f"   Dirección ModBus: {config['direccion']} (0x{config['direccion']:02X})")
        print(f"   Baudrate: {config['baudrate']}")
        print(f"   Timeout: {config['timeout']}s")
        print(f"\n   Valores leídos:")
        print(f"   Vx = {vx/100.0:.3f} mm/s")
        print(f"   Vy = {vy/100.0:.3f} mm/s")
        print(f"   Vz = {vz/100.0:.3f} mm/s")
        
        sensor.serial.close()
        break
        
    except Exception as e:
        error_str = str(e)
        if "PermissionError" in error_str:
            print(f"   ❌ Error: Puerto en uso por otra aplicación")
        elif "FileNotFoundError" in error_str:
            print(f"   ❌ Error: Puerto no existe")
        elif "No communication" in error_str:
            print(f"   ❌ Error: Sin respuesta del sensor")
        elif "Timeout" in error_str:
            print(f"   ❌ Error: Timeout (sin respuesta)")
        else:
            print(f"   ❌ Error: {error_str[:60]}")
        
        try:
            sensor.serial.close()
        except:
            pass
    
    print()

print("=" * 70)
print("\n💡 RECOMENDACIONES:")
print("\n1. Verifica que el sensor esté encendido")
print("2. Verifica el cable RS485 (A → A+, B → B-)")
print("3. Cierra otras aplicaciones usando COM8")
print("4. Verifica la dirección ModBus del sensor (0x50 = 80 decimal)")
print("5. Si nada funciona, intenta con software WitMotion oficial")
print("\n📚 Documentación WTVB01-485:")
print("   - Dirección por defecto: 0x50 (80)")
print("   - Baudrate por defecto: 9600")
print("   - Registros: 0x3D (Vx), 0x3E (Vy), 0x3F (Vz)")
print("   - Valores en centésimas (dividir por 100)")

print("\n" + "=" * 70)
print("Presiona Enter para salir...")
input()

"""
Script simple para probar comunicación con sensor WTVB01-485
Sin Streamlit - solo lectura directa del puerto COM8
"""
import minimalmodbus
import serial
import time

print("🔧 PRUEBA SIMPLE DEL SENSOR WTVB01-485")
print("="*60)
print("\n📋 Configuración:")
print("   Puerto: COM8")
print("   Dirección ModBus: 80 (0x50)")
print("   Baudrate: 9600")
print("   Registros: 0x3A (Vx), 0x3B (Vy), 0x3C (Vz)")
print("\n🔌 Conectando al sensor...")

try:
    # Configurar sensor
    sensor = minimalmodbus.Instrument('COM8', 80)
    sensor.serial.baudrate = 9600
    sensor.serial.bytesize = 8
    sensor.serial.parity = serial.PARITY_NONE
    sensor.serial.stopbits = 1
    sensor.serial.timeout = 1.0
    sensor.mode = minimalmodbus.MODE_RTU
    sensor.clear_buffers_before_each_transaction = True
    
    print("✅ Puerto COM8 abierto correctamente")
    print("\n📊 Intentando leer registros...")
    
    # Intentar leer registro de prueba
    print("   - Probando registro 0x3A (58 decimal - Vx)...")
    vx_raw = sensor.read_register(58, functioncode=3, signed=True)
    vx = vx_raw / 100.0
    print(f"   ✅ Vx raw: {vx_raw} → {vx:.3f} mm/s")
    
    time.sleep(0.1)
    
    print("   - Probando registro 0x3B (59 decimal - Vy)...")
    vy_raw = sensor.read_register(59, functioncode=3, signed=True)
    vy = vy_raw / 100.0
    print(f"   ✅ Vy raw: {vy_raw} → {vy:.3f} mm/s")
    
    time.sleep(0.1)
    
    print("   - Probando registro 0x3C (60 decimal - Vz)...")
    vz_raw = sensor.read_register(60, functioncode=3, signed=True)
    vz = vz_raw / 100.0
    print(f"   ✅ Vz raw: {vz_raw} → {vz:.3f} mm/s")
    
    print("\n" + "="*60)
    print("🎉 ÉXITO - SENSOR FUNCIONANDO CORRECTAMENTE")
    print("="*60)
    print(f"\n📈 Valores de vibración:")
    print(f"   Vx: {vx:.3f} mm/s")
    print(f"   Vy: {vy:.3f} mm/s")
    print(f"   Vz: {vz:.3f} mm/s")
    
    # Calcular RMS
    vmax = max(abs(vx), abs(vy), abs(vz))
    print(f"   RMS (máximo): {vmax:.3f} mm/s")
    
    # Clasificación ISO 20816-3
    if vmax <= 0.25:
        zona = "A (Normal)"
    elif vmax <= 0.5:
        zona = "B (Vigilancia)"
    elif vmax <= 0.75:
        zona = "C (Corrección)"
    else:
        zona = "D (Inaceptable)"
    
    print(f"   Zona ISO 20816-3: {zona}")
    print("\n✅ El sensor está listo para usarse en el monitor en tiempo real")

except minimalmodbus.NoResponseError:
    print("\n❌ ERROR: No hay respuesta del sensor")
    print("\n🔍 Posibles causas:")
    print("   1. Dirección ModBus incorrecta (actual: 80)")
    print("      → Prueba con dirección 1: Modifica línea 20 a: sensor = minimalmodbus.Instrument('COM8', 1)")
    print("   2. Baudrate incorrecto (actual: 9600)")
    print("      → Prueba con 19200: Modifica línea 21 a: sensor.serial.baudrate = 19200")
    print("   3. Sensor apagado o desconectado")
    print("   4. Cable RS485 mal conectado (A con A, B con B)")
    print("   5. Sensor requiere configuración previa con software WitMotion")

except serial.SerialException as e:
    print(f"\n❌ ERROR DE PUERTO SERIAL: {e}")
    print("\n🔍 Posibles causas:")
    print("   1. COM8 ocupado por otra aplicación")
    print("      → Cierra Streamlit monitor si está corriendo")
    print("   2. Puerto COM incorrecto")
    print("      → Verifica en Administrador de Dispositivos")

except Exception as e:
    print(f"\n❌ ERROR INESPERADO: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
    print("\n📝 Detalles técnicos para depuración:")
    import traceback
    traceback.print_exc()

finally:
    print("\n👋 Prueba finalizada")
    input("Presiona Enter para salir...")

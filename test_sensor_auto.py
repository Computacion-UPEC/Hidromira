"""
Prueba automática de todas las configuraciones comunes del sensor WTVB01-485
Prueba múltiples combinaciones de dirección, baudrate y función ModBus
"""
import minimalmodbus
import serial
import time

print("🔧 PRUEBA AUTOMÁTICA DEL SENSOR WTVB01-485")
print("="*70)

# Configuraciones a probar
direcciones = [1, 80, 50]  # Direcciones ModBus comunes
baudrates = [9600, 19200, 115200]  # Baudrates comunes en WitMotion
registros = [61, 0, 1]  # Registros a probar (61=0x3D, 0=primer registro, 1=segundo)
funciones = [3, 4]  # Función 3 = Holding Registers, Función 4 = Input Registers

configuraciones_probadas = 0
configuracion_exitosa = None

print(f"\n📋 Probando {len(direcciones)} direcciones × {len(baudrates)} baudrates × {len(funciones)} funciones")
print(f"   Total: {len(direcciones) * len(baudrates) * len(funciones)} configuraciones\n")

for direccion in direcciones:
    for baudrate in baudrates:
        for funcion in funciones:
            configuraciones_probadas += 1
            
            config_nombre = f"Dir:{direccion} | {baudrate} baud | Func:{funcion}"
            print(f"[{configuraciones_probadas:2d}] Probando: {config_nombre}... ", end='', flush=True)
            
            try:
                # Configurar sensor
                sensor = minimalmodbus.Instrument('COM3', direccion)
                sensor.serial.baudrate = baudrate
                sensor.serial.bytesize = 8
                sensor.serial.parity = serial.PARITY_NONE
                sensor.serial.stopbits = 1
                sensor.serial.timeout = 0.5  # Timeout corto para pruebas rápidas
                sensor.mode = minimalmodbus.MODE_RTU
                sensor.clear_buffers_before_each_transaction = True
                
                # Intentar leer primer registro (61 = Vx en sensor configurado)
                valor = sensor.read_register(61, functioncode=funcion, signed=True)
                
                # Si llegamos aquí, ¡funcionó!
                print("✅ ¡ÉXITO!")
                configuracion_exitosa = {
                    'direccion': direccion,
                    'baudrate': baudrate,
                    'funcion': funcion,
                    'valor_raw': valor,
                    'valor_mm_s': valor / 100.0
                }
                
                print("\n" + "="*70)
                print("🎉 CONFIGURACIÓN ENCONTRADA")
                print("="*70)
                print(f"   Dirección ModBus: {direccion}")
                print(f"   Baudrate: {baudrate}")
                print(f"   Función ModBus: {funcion}")
                print(f"   Registro 61 (Vx): {valor} raw → {valor/100.0:.3f} mm/s")
                
                # Probar leer los 3 ejes
                print(f"\n📊 Leyendo todos los ejes...")
                try:
                    vx = sensor.read_register(61, functioncode=funcion, signed=True) / 100.0
                    time.sleep(0.05)
                    vy = sensor.read_register(62, functioncode=funcion, signed=True) / 100.0
                    time.sleep(0.05)
                    vz = sensor.read_register(63, functioncode=funcion, signed=True) / 100.0
                    
                    print(f"   Vx: {vx:.3f} mm/s")
                    print(f"   Vy: {vy:.3f} mm/s")
                    print(f"   Vz: {vz:.3f} mm/s")
                    print(f"   RMS: {max(abs(vx), abs(vy), abs(vz)):.3f} mm/s")
                    
                except Exception as e:
                    print(f"   ⚠️ Error leyendo ejes Y/Z: {e}")
                
                break
                
            except minimalmodbus.NoResponseError:
                print("❌ Sin respuesta")
            except minimalmodbus.InvalidResponseError:
                print("❌ Respuesta inválida")
            except serial.SerialException as e:
                print(f"❌ Error puerto: {e}")
            except Exception as e:
                print(f"❌ Error: {type(e).__name__}")
            
            finally:
                # Cerrar puerto antes de siguiente prueba
                try:
                    if 'sensor' in locals():
                        sensor.serial.close()
                except:
                    pass
                time.sleep(0.1)  # Pequeña pausa entre pruebas
        
        if configuracion_exitosa:
            break
    if configuracion_exitosa:
        break

print("\n" + "="*70)

if configuracion_exitosa:
    print("✅ SENSOR FUNCIONANDO - Actualiza monitor_realtime.py con:")
    print("="*70)
    print(f"\nCambia línea ~80-81:")
    print(f"   sensor = minimalmodbus.Instrument('COM3', {configuracion_exitosa['direccion']})")
    print(f"   sensor.serial.baudrate = {configuracion_exitosa['baudrate']}")
    print(f"\nCambia líneas de lectura (~125-130):")
    print(f"   vx = sensor.read_register(61, functioncode={configuracion_exitosa['funcion']}, signed=True) / 100.0")
    print(f"   vy = sensor.read_register(62, functioncode={configuracion_exitosa['funcion']}, signed=True) / 100.0")
    print(f"   vz = sensor.read_register(63, functioncode={configuracion_exitosa['funcion']}, signed=True) / 100.0")
    
else:
    print("❌ NINGUNA CONFIGURACIÓN FUNCIONÓ")
    print("="*70)
    print("\n🔍 Verifica:")
    print("   1. ✅ Sensor encendido")
    print("   2. ✅ Cable RS485 conectado correctamente:")
    print("      • Terminal A del sensor → Terminal A del adaptador")
    print("      • Terminal B del sensor → Terminal B del adaptador")
    print("   3. ✅ Adaptador USB-RS485 conectado a COM3")
    print("   4. ⚠️ Sensor puede requerir configuración con software WitMotion")
    print("      • Descarga: https://wit-motion.yuque.com/wumwnr/ltst94")
    print("      • Configura dirección ModBus y baudrate")
    print("\n💡 Prueba también con direcciones personalizadas si configuraste el sensor")

print("\n👋 Prueba finalizada")
input("Presiona Enter para salir...")

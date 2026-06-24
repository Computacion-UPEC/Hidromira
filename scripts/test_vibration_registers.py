import minimalmodbus
import serial
import time
import json
import os

# Cargar config
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import iot_config
    puertos = iot_config.load_serial_config()
    port = puertos.get('sensor_port', 'COM8')
except Exception as e:
    print(f"Error cargando config, usando COM8: {e}")
    port = 'COM8'

print(f"Probando sensor en puerto: {port}")

try:
    sensor = minimalmodbus.Instrument(port, 80)
    sensor.serial.baudrate = 9600
    sensor.serial.bytesize = 8
    sensor.serial.parity = serial.PARITY_NONE
    sensor.serial.stopbits = 1
    sensor.serial.timeout = 1.0
    sensor.mode = minimalmodbus.MODE_RTU
    sensor.clear_buffers_before_each_transaction = True

    print("\n--- LECTURA DE REGISTROS 58, 59, 60 (Velocidad sugerida) ---")
    try:
        vx_58 = sensor.read_register(58, functioncode=3, signed=True)
        print(f"Reg 58 (VX) raw: {vx_58}")
    except Exception as e:
        print(f"Reg 58 error: {e}")
        vx_58 = None

    time.sleep(0.1)
    try:
        vy_59 = sensor.read_register(59, functioncode=3, signed=True)
        print(f"Reg 59 (VY) raw: {vy_59}")
    except Exception as e:
        print(f"Reg 59 error: {e}")
        vy_59 = None

    time.sleep(0.1)
    try:
        vz_60 = sensor.read_register(60, functioncode=3, signed=True)
        print(f"Reg 60 (VZ) raw: {vz_60}")
    except Exception as e:
        print(f"Reg 60 error: {e}")
        vz_60 = None

    print("\n--- LECTURA DE REGISTROS 61, 62, 63 (Ángulo/Vibración actual) ---")
    try:
        vx_61 = sensor.read_register(61, functioncode=3, signed=True)
        print(f"Reg 61 raw: {vx_61}")
    except Exception as e:
        print(f"Reg 61 error: {e}")
        vx_61 = None

    time.sleep(0.1)
    try:
        vy_62 = sensor.read_register(62, functioncode=3, signed=True)
        print(f"Reg 62 raw: {vy_62}")
    except Exception as e:
        print(f"Reg 62 error: {e}")
        vy_62 = None

    time.sleep(0.1)
    try:
        vz_63 = sensor.read_register(63, functioncode=3, signed=True)
        print(f"Reg 63 raw: {vz_63}")
    except Exception as e:
        print(f"Reg 63 error: {e}")
        vz_63 = None

    sensor.serial.close()

except Exception as e:
    print(f"Error de conexión: {e}")

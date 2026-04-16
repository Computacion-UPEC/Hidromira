"""
Script para cerrar todas las conexiones al puerto COM3
"""
import serial
import serial.tools.list_ports
import time

print("🔧 Cerrando todas las conexiones a COM3...\n")

try:
    # Intentar abrir y cerrar COM3 varias veces
    for intento in range(3):
        try:
            puerto = serial.Serial('COM3', 9600, timeout=0.5)
            print(f"✅ Intento {intento + 1}: Puerto COM3 abierto")
            puerto.close()
            print(f"✅ Intento {intento + 1}: Puerto COM3 cerrado")
            time.sleep(0.5)
        except Exception as e:
            if "PermissionError" in str(e):
                print(f"❌ Intento {intento + 1}: Puerto en uso por otra aplicación")
            elif "FileNotFoundError" in str(e):
                print(f"❌ Intento {intento + 1}: Puerto no existe")
            else:
                print(f"❌ Intento {intento + 1}: {str(e)[:60]}")
        
        time.sleep(0.5)
    
    print("\n✅ Proceso completado")
    print("\n💡 Si COM3 sigue ocupado:")
    print("   1. Cierra el monitor de Streamlit (Ctrl+C)")
    print("   2. Espera 5 segundos")
    print("   3. Ejecuta este script de nuevo")
    print("   4. Inicia el monitor de nuevo")
    
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\nPresiona Enter para salir...")
input()

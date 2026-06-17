"""
Verificación básica de hardware - Lista puertos COM disponibles
"""
import serial.tools.list_ports

print("🔌 PUERTOS COM DISPONIBLES")
print("="*70)

puertos = list(serial.tools.list_ports.comports())

if not puertos:
    print("❌ No se encontraron puertos COM")
else:
    print(f"\n✅ Se encontraron {len(puertos)} puerto(s):\n")
    for puerto in puertos:
        print(f"   Puerto: {puerto.device}")
        print(f"   Nombre: {puerto.description}")
        print(f"   Hardware ID: {puerto.hwid}")
        print(f"   Fabricante: {puerto.manufacturer or 'N/A'}")
        print(f"   Producto: {puerto.product or 'N/A'}")
        print(f"   Serial: {puerto.serial_number or 'N/A'}")
        print("-"*70)

print("\n🔍 DIAGNÓSTICO DEL SENSOR WTVB01-485:")
print("-"*70)

# Buscar específicamente el adaptador CH340
ch340_encontrado = False
for puerto in puertos:
    if 'CH340' in puerto.description or 'CH340' in puerto.hwid:
        ch340_encontrado = True
        print(f"✅ Adaptador USB-RS485 (CH340) encontrado en {puerto.device}")
        print(f"   Este debería ser el sensor WTVB01-485")
        break

if not ch340_encontrado:
    print("❌ No se encontró adaptador CH340")
    print("\n⚠️ PROBLEMA: El sensor no está conectado o el driver no está instalado")
    print("\n🔧 SOLUCIONES:")
    print("   1. Conecta el sensor al puerto USB")
    print("   2. Instala driver CH340:")
    print("      https://www.wch.cn/downloads/CH341SER_EXE.html")
    print("   3. Reinicia la computadora después de instalar el driver")

print("\n📝 INFORMACIÓN SOBRE EL SENSOR WTVB01-485:")
print("-"*70)
print("Este sensor requiere:")
print("   • Conexión RS485 con adaptador USB-RS485")
print("   • Alimentación (generalmente 5V-12V DC)")
print("   • Configuración inicial con software WitMotion (opcional)")
print("   • Cable con conexiones A-A y B-B (no cruzado)")

print("\n🔌 VERIFICACIÓN DE CONEXIONES:")
print("-"*70)
print("Verifica que:")
print("   [ ] Cable USB conectado a la PC")
print("   [ ] LED en el sensor está encendido/parpadeando")
print("   [ ] Cable RS485 conectado:")
print("       • Terminal A del sensor → Terminal A+ del adaptador")
print("       • Terminal B del sensor → Terminal B- del adaptador")
print("   [ ] Sensor alimentado correctamente (5V-12V)")
print("   [ ] Adaptador USB reconocido en Administrador de Dispositivos")

print("\n💡 PRÓXIMOS PASOS:")
print("-"*70)
if ch340_encontrado:
    print("1. Verifica que el LED del sensor esté encendido")
    print("2. Verifica las conexiones A/B del cable RS485")
    print("3. Puede necesitar configuración con software WitMotion:")
    print("   https://wit-motion.yuque.com/wumwnr/ltst94")
    print("4. Configura dirección ModBus y baudrate en el software")
else:
    print("1. Conecta el sensor al puerto USB")
    print("2. Instala driver CH340 si es necesario")
    print("3. Vuelve a ejecutar este script")

input("\nPresiona Enter para salir...")

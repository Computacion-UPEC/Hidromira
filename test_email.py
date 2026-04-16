"""
Script para probar alertas por Gmail
Verifica configuración y envía email de prueba
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import sys

print("📧 PRUEBA DE ALERTAS POR GMAIL")
print("="*70)

# Importar configuración
try:
    import iot_config
    print("✅ Archivo iot_config.py cargado correctamente")
except Exception as e:
    print(f"❌ Error al cargar iot_config.py: {e}")
    input("Presiona Enter para salir...")
    sys.exit(1)

# Verificar configuración
print("\n📋 VERIFICACIÓN DE CONFIGURACIÓN:")
print("-"*70)

if not iot_config.EMAIL_ENABLED:
    print("❌ EMAIL_ENABLED = False")
    print("   Cambia a: EMAIL_ENABLED = True en iot_config.py")
    input("Presiona Enter para salir...")
    sys.exit(1)
else:
    print("✅ EMAIL_ENABLED = True")

print(f"📧 EMAIL_FROM: {iot_config.EMAIL_FROM}")
if "TU_EMAIL" in iot_config.EMAIL_FROM.upper() or "@" not in iot_config.EMAIL_FROM:
    print("   ⚠️ Debes configurar tu email real de Gmail")
    print("   Ejemplo: juan.perez@gmail.com")
    input("Presiona Enter para salir...")
    sys.exit(1)

print(f"🔑 EMAIL_PASSWORD: {'*' * len(iot_config.EMAIL_PASSWORD)}")
if "TU_CONTRASEÑA" in iot_config.EMAIL_PASSWORD.upper() or len(iot_config.EMAIL_PASSWORD) < 10:
    print("   ⚠️ Debes configurar tu contraseña de aplicación de Gmail")
    print("   NO uses tu contraseña normal - genera una contraseña de aplicación:")
    print("   https://myaccount.google.com/apppasswords")
    input("Presiona Enter para salir...")
    sys.exit(1)

print(f"📬 EMAIL_TO: {iot_config.EMAIL_TO}")
if any("ejemplo" in email.lower() or "TU_EMAIL" in email.upper() for email in iot_config.EMAIL_TO):
    print("   ⚠️ Debes configurar emails reales para recibir alertas")
    input("Presiona Enter para salir...")
    sys.exit(1)

print(f"🌐 SMTP_SERVER: {iot_config.EMAIL_SMTP_SERVER}:{iot_config.EMAIL_SMTP_PORT}")

print("\n✅ Configuración básica correcta")

# Intentar enviar email de prueba
print("\n📤 ENVIANDO EMAIL DE PRUEBA...")
print("-"*70)

try:
    # Crear mensaje
    msg = MIMEMultipart()
    msg['From'] = iot_config.EMAIL_FROM
    msg['To'] = ', '.join(iot_config.EMAIL_TO)
    msg['Subject'] = "✅ Prueba HidroMira - Sistema de Alertas"
    
    # Cuerpo HTML
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #00c853; margin-bottom: 20px;">✅ Sistema de Alertas Configurado Correctamente</h2>
            
            <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; border-left: 4px solid #00c853; margin-bottom: 20px;">
                <p style="margin: 0;"><strong>🎉 ¡Email de prueba exitoso!</strong></p>
            </div>
            
            <h3 style="color: #333; margin-top: 20px;">📊 Información del Sistema</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Sistema:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">HidroMira IoT Monitor</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Fecha:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{timestamp}</td>
                </tr>
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Servidor SMTP:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{iot_config.EMAIL_SMTP_SERVER}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Desde:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{iot_config.EMAIL_FROM}</td>
                </tr>
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Para:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{', '.join(iot_config.EMAIL_TO)}</td>
                </tr>
            </table>
            
            <h3 style="color: #333; margin-top: 30px;">⚠️ Tipos de Alertas Configuradas</h3>
            <ul style="line-height: 1.8;">
                <li><strong>Zona B (Amarillo):</strong> {'✅ Activa' if iot_config.ALERT_ZONA_B else '❌ Desactivada'} - Vigilancia (> 0.25 mm/s)</li>
                <li><strong>Zona C (Naranja):</strong> {'✅ Activa' if iot_config.ALERT_ZONA_C else '❌ Desactivada'} - Corrección necesaria (> 0.5 mm/s)</li>
                <li><strong>Zona D (Rojo):</strong> {'✅ Activa' if iot_config.ALERT_ZONA_D else '❌ Desactivada'} - Inaceptable (> 0.75 mm/s)</li>
            </ul>
            
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3; margin-top: 20px;">
                <p style="margin: 0;"><strong>💡 Información:</strong></p>
                <p style="margin: 10px 0 0 0;">El sistema enviará alertas automáticamente cuando la vibración supere los límites configurados. Tiempo entre alertas: {iot_config.ALERT_COOLDOWN // 60} minutos.</p>
            </div>
            
            <p style="margin-top: 30px; color: #666; font-size: 12px; text-align: center;">
                Este es un email automático del sistema de monitoreo HidroMira.<br>
                No responder a este mensaje.
            </p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html'))
    
    print("1/4 Creando mensaje HTML... ✅")
    
    # Conectar al servidor SMTP
    print(f"2/4 Conectando a {iot_config.EMAIL_SMTP_SERVER}:{iot_config.EMAIL_SMTP_PORT}... ", end='', flush=True)
    server = smtplib.SMTP(iot_config.EMAIL_SMTP_SERVER, iot_config.EMAIL_SMTP_PORT)
    print("✅")
    
    # Iniciar TLS
    print("3/4 Iniciando cifrado TLS... ", end='', flush=True)
    server.starttls()
    print("✅")
    
    # Login
    print("4/4 Autenticando con Gmail... ", end='', flush=True)
    server.login(iot_config.EMAIL_FROM, iot_config.EMAIL_PASSWORD)
    print("✅")
    
    # Enviar
    print("📤 Enviando email... ", end='', flush=True)
    server.send_message(msg)
    print("✅")
    
    server.quit()
    
    print("\n" + "="*70)
    print("🎉 ¡ÉXITO! EMAIL ENVIADO CORRECTAMENTE")
    print("="*70)
    print(f"\n✅ Revisa tu bandeja de entrada: {iot_config.EMAIL_TO[0]}")
    print("   (Si no lo ves, revisa SPAM/Promociones)")
    print("\n💡 El sistema ahora enviará alertas automáticamente cuando:")
    print("   • Vibración entre en Zona B (> 0.25 mm/s) - Vigilancia")
    print("   • Vibración entre en Zona C (> 0.5 mm/s) - Corrección")
    print("   • Vibración entre en Zona D (> 0.75 mm/s) - Inaceptable")
    print(f"\n⏱️ Tiempo entre alertas repetidas: {iot_config.ALERT_COOLDOWN // 60} minutos")
    print("\n✅ El monitor en tiempo real ya tiene alertas por email habilitadas")

except smtplib.SMTPAuthenticationError:
    print("\n" + "="*70)
    print("❌ ERROR DE AUTENTICACIÓN")
    print("="*70)
    print("\n🔍 PROBLEMA: Gmail rechazó tu usuario/contraseña")
    print("\n✅ SOLUCIÓN:")
    print("   1. Verifica que EMAIL_FROM sea correcto:")
    print(f"      Actual: {iot_config.EMAIL_FROM}")
    print("   2. Usa una CONTRASEÑA DE APLICACIÓN (NO tu contraseña normal):")
    print("      • Ve a: https://myaccount.google.com/apppasswords")
    print("      • Crea una nueva para 'HidroMira'")
    print("      • Copia la contraseña de 16 caracteres")
    print("      • Actualiza EMAIL_PASSWORD en iot_config.py")
    print("   3. Asegúrate de tener verificación en 2 pasos habilitada:")
    print("      https://myaccount.google.com/security")

except smtplib.SMTPException as e:
    print(f"\n❌ ERROR SMTP: {e}")
    print("\n🔍 Verifica tu configuración de Gmail")

except Exception as e:
    print(f"\n❌ ERROR INESPERADO: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
    print("\n📝 Detalles para depuración:")
    import traceback
    traceback.print_exc()

input("\n👋 Presiona Enter para salir...")

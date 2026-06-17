import sys
import os
import time

# Asegurar que la raíz esté en el path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iot_handler import IoTHandler
import iot_config

class MockIoTHandler(IoTHandler):
    def __init__(self, config):
        super().__init__(config)
        self.sent_emails = []
        
    def enviar_email(self, asunto, mensaje):
        print(f"\n[EMAIL] [Mock Email Enviado]")
        # Limpiar asunto de emojis para evitar fallos de impresión en Windows
        asunto_limpio = asunto.replace("✅", "[OK]").replace("⚠️", "[WARN]").replace("🔴", "[HIGH]").replace("🚫", "[CRIT]")
        print(f"   Asunto: {asunto_limpio}")
        print(f"   Destinatarios: {self.config.get('EMAIL_TO')}")
        # Obtener la línea del emoji/título en el mensaje HTML, quitando emojis
        lineas = [l.strip() for l in mensaje.strip().splitlines() if l.strip()]
        linea_interes = lineas[0] if lineas else ""
        linea_interes_limpia = linea_interes.replace("✅", "[OK]").replace("⚠️", "[WARN]").replace("🔴", "[HIGH]").replace("🚫", "[CRIT]")
        print(f"   Mensaje (resumido): {linea_interes_limpia}")
        self.sent_emails.append((asunto, mensaje))
        return True

def run_test():
    config = vars(iot_config).copy()
    config['EMAIL_ENABLED'] = True
    config['ALERT_COOLDOWN'] = 5  # Cooldown corto de 5 segundos para pruebas
    config['ALERT_ZONA_B'] = True
    config['ALERT_ZONA_C'] = True
    config['ALERT_ZONA_D'] = True
    
    handler = MockIoTHandler(config)
    
    print("=== INICIANDO PRUEBA DE LÓGICA DE ALERTAS POR ZONA ===")
    
    # 1. Primera lectura en Zona A: No debe enviar alerta.
    print("\n--- Lectura 1: Zona A (Funcionamiento normal) ---")
    should_alert = handler.verificar_alerta('A', 0.15)
    print(f"¿Debe alertar?: {should_alert}")
    assert not should_alert, "Error: No debería alertar en Zona A en la primera lectura"
    
    # 2. Cambio a Zona B: Debe alertar inmediatamente (bypass cooldown).
    print("\n--- Lectura 2: Cambio a Zona B (Vigilancia) ---")
    should_alert = handler.verificar_alerta('B', 0.85)
    print(f"¿Debe alertar?: {should_alert}")
    if should_alert:
        handler.enviar_alerta_completa('B', 0.85, 0.8, 0.4, 0.3)
    assert should_alert, "Error: Debería alertar al cambiar a Zona B"
    assert len(handler.sent_emails) == 1, "Error: Debe haberse enviado 1 email"
    
    # 3. Lectura repetida en Zona B (antes del cooldown de 5s): No debe enviar alerta.
    print("\n--- Lectura 3: Misma Zona B (Sin expirar cooldown) ---")
    should_alert = handler.verificar_alerta('B', 0.90)
    print(f"¿Debe alertar?: {should_alert}")
    assert not should_alert, "Error: No debería alertar en la misma zona antes de expirar cooldown"
    
    # 4. Cambio a Zona C: Debe alertar inmediatamente (bypass cooldown).
    print("\n--- Lectura 4: Cambio a Zona C (Corrección urgente) ---")
    should_alert = handler.verificar_alerta('C', 1.95)
    print(f"¿Debe alertar?: {should_alert}")
    if should_alert:
        handler.enviar_alerta_completa('C', 1.95, 1.8, 0.9, 0.5)
    assert should_alert, "Error: Debería alertar inmediatamente al cambiar a Zona C"
    assert len(handler.sent_emails) == 2, "Error: Debe haberse enviado un segundo email"
    
    # 5. Cambio a Zona A (Restauración): Debe alertar inmediatamente.
    print("\n--- Lectura 5: Cambio a Zona A (Restauración) ---")
    should_alert = handler.verificar_alerta('A', 0.18)
    print(f"¿Debe alertar?: {should_alert}")
    if should_alert:
        handler.enviar_alerta_completa('A', 0.18, 0.1, 0.1, 0.08)
    assert should_alert, "Error: Debería alertar al restaurar a Zona A"
    assert len(handler.sent_emails) == 3, "Error: Debe haberse enviado un email de restauración"
    assert "RESTAURACIÓN" in handler.sent_emails[-1][0], "Error: El asunto debe indicar restauración"
    
    # 6. Lectura repetida en Zona A: No debe alertar.
    print("\n--- Lectura 6: Mismo estado Zona A ---")
    should_alert = handler.verificar_alerta('A', 0.15)
    print(f"¿Debe alertar?: {should_alert}")
    assert not should_alert, "Error: No debería alertar en Zona A repetidamente"
    
    # 7. Cambio a Zona B: Debe alertar inmediatamente.
    print("\n--- Lectura 7: Cambio de Zona A a B ---")
    should_alert = handler.verificar_alerta('B', 0.88)
    print(f"¿Debe alertar?: {should_alert}")
    if should_alert:
        handler.enviar_alerta_completa('B', 0.88, 0.8, 0.4, 0.3)
    assert should_alert, "Error: Debería alertar al cambiar a Zona B"
    assert len(handler.sent_emails) == 4, "Error: Debe haberse enviado el cuarto email"
    
    # 8. Esperar a que pase el cooldown (5s) en la misma zona B: Debe volver a alertar.
    print("\n--- Lectura 8: Esperar 6 segundos en la misma Zona B (Cooldown expirado) ---")
    print("Esperando 6 segundos...")
    time.sleep(6)
    should_alert = handler.verificar_alerta('B', 0.92)
    print(f"¿Debe alertar?: {should_alert}")
    if should_alert:
        handler.enviar_alerta_completa('B', 0.92, 0.85, 0.42, 0.31)
    assert should_alert, "Error: Debería alertar tras expirar el cooldown en la misma zona"
    assert len(handler.sent_emails) == 5, "Error: Debe haberse enviado el quinto email"
    
    print("\n[SUCCESS] TODAS LAS PRUEBAS DE LÓGICA PASARON EXITOSAMENTE!")

if __name__ == '__main__':
    run_test()

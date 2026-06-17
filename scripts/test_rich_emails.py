"""
Script para probar el envío de correos premium/enriquecidos (HTML + Imagen Inline + ngrok)
Envía un correo de prueba simulando Zona C a los destinatarios configurados.
"""
import sys
import os
import time

# Añadir la carpeta raíz al path para poder importar iot_config e iot_handler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iot_handler import IoTHandler
import iot_config

def main():
    print("[EMAIL] PRUEBA DE CORREOS ENRIQUECIDOS (HTML + IMAGEN + NGROK)")
    print("="*70)
    
    # Forzar habilitación para pruebas
    config = vars(iot_config).copy()
    config['EMAIL_ENABLED'] = True
    config['ALERT_ZONA_C'] = True
    
    print("[INFO] Inicializando IoTHandler con los parámetros de iot_config.py...")
    handler = IoTHandler(config)
    
    # Simular una lectura en Zona C (Vibración alta)
    zona = 'C'
    vmax = 0.685
    vx, vy, vz = 0.450, 0.685, 0.310
    
    print(f"\n[INFO] Simulando Alerta en ZONA {zona}...")
    print(f"       Parámetros: vmax={vmax} mm/s (vx={vx}, vy={vy}, vz={vz})")
    print(f"       Destinatarios: {config.get('EMAIL_TO')}")
    
    # Disparar alerta completa (esto ejecutará la lógica con la imagen y los botones)
    print("\n[SEND] Enviando alerta enriquecida en segundo plano...")
    print("       (Espera unos segundos para validar la salida en consola)...")
    
    success = handler.enviar_alerta_completa(zona, vmax, vx, vy, vz)
    
    if success:
        print("\n[OK] Solicitud de envío asíncrono completada con éxito.")
        print("     Esperando 8 segundos para que el hilo asíncrono complete el envío SMTP...")
        time.sleep(8)
        print("     Envío finalizado. Revisa las bandejas de entrada de tus correos (incluyendo SPAM/Promociones).")
    else:
        print("\n[ERROR] Falló la solicitud de envío de alerta.")
        
    print("\n" + "="*70)
    print("Proceso finalizado.")

if __name__ == '__main__':
    main()

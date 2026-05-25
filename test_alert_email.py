"""
Prueba directa de alertas por email usando la misma lógica del monitor.

Uso:
  .\venv\Scripts\python.exe test_alert_email.py --zona B
  .\venv\Scripts\python.exe test_alert_email.py --zona D
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime


def cargar_handler():
    try:
        import iot_config
        from iot_handler import IoTHandler
    except Exception as exc:
        print(f"❌ No se pudo cargar la configuración o el manejador: {exc}")
        sys.exit(1)

    return iot_config, IoTHandler(vars(iot_config))


def validar_config(iot_config):
    errores = []

    if not iot_config.EMAIL_ENABLED:
        errores.append("EMAIL_ENABLED debe estar en True")
    if not iot_config.EMAIL_FROM or "@" not in iot_config.EMAIL_FROM:
        errores.append("EMAIL_FROM no parece válido")
    if not iot_config.EMAIL_PASSWORD or len(iot_config.EMAIL_PASSWORD.strip()) < 10:
        errores.append("EMAIL_PASSWORD no parece una contraseña de aplicación válida")
    if not iot_config.EMAIL_TO:
        errores.append("EMAIL_TO no tiene destinatarios")

    return errores


def main():
    parser = argparse.ArgumentParser(description="Enviar una alerta de prueba por email.")
    parser.add_argument(
        "--zona",
        choices=["B", "D"],
        default="B",
        help="Tipo de alerta a enviar: B = amarilla, D = roja",
    )
    args = parser.parse_args()

    iot_config, handler = cargar_handler()

    errores = validar_config(iot_config)
    if errores:
        print("❌ Configuración incompleta:")
        for error in errores:
            print(f"  - {error}")
        sys.exit(1)

    if args.zona == "B":
        zona = "B"
        vmax = 0.38
        vx, vy, vz = 0.40, 0.36, 0.33
        titulo = "Alerta AMARILLA de prueba"
    else:
        zona = "D"
        vmax = 1.25
        vx, vy, vz = 1.35, 1.22, 1.18
        titulo = "Alerta ROJA de prueba"

    print("📧 Enviando prueba de alerta por email")
    print(f"   Tipo: {titulo}")
    print(f"   Destino: {', '.join(iot_config.EMAIL_TO)}")
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    enviado = handler.enviar_alerta_completa(zona, vmax, vx, vy, vz)
    if enviado:
        print("✅ Alerta enviada correctamente")
        print("Revisa tu bandeja de entrada y SPAM")
    else:
        print("❌ No se pudo enviar la alerta")
        sys.exit(1)


if __name__ == "__main__":
    main()

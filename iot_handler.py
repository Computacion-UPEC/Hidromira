import requests
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger("HidroMiraIoT")

class IoTHandler:
    def __init__(self, config):
        self.config = config
        self.last_alert_time = {}
        self.mqtt_client = None
        self.last_zone = None
        
        # Cargar configuración persistente de email (para sincronización entre apps)
        self.load_email_config()
        
        # Inicializar MQTT si está habilitado
        if config.get('MQTT_ENABLED', False):
            self._init_mqtt()
    
    def _init_mqtt(self):
        """Inicializar cliente MQTT"""
        try:
            self.mqtt_client = mqtt.Client(self.config['MQTT_CLIENT_ID'])
            self.mqtt_client.connect(
                self.config['MQTT_BROKER'],
                self.config['MQTT_PORT'],
                60
            )
            self.mqtt_client.loop_start()
            logger.info(f"✅ MQTT conectado a {self.config['MQTT_BROKER']}")
        except Exception as e:
            logger.error(f"❌ Error MQTT: {e}")
            self.mqtt_client = None
            
    def load_email_config(self):
        """Cargar configuración compartida de notificaciones"""
        try:
            import os
            path = os.path.join(os.path.dirname(__file__), 'email_config.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.config['EMAIL_ENABLED'] = saved.get('EMAIL_ENABLED', self.config.get('EMAIL_ENABLED', False))
                    self.config['EMAIL_TO'] = saved.get('EMAIL_TO', self.config.get('EMAIL_TO', []))
                    logger.info(f"📧 Configuración de correo cargada de disco: {saved}")
        except Exception as e:
            logger.error(f"❌ Error al cargar configuración de correo: {e}")

    def save_email_config(self):
        """Guardar configuración compartida de notificaciones en disco"""
        try:
            import os
            path = os.path.join(os.path.dirname(__file__), 'email_config.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'EMAIL_ENABLED': self.config.get('EMAIL_ENABLED', False),
                    'EMAIL_TO': self.config.get('EMAIL_TO', [])
                }, f, indent=2)
            logger.info("💾 Configuración de correo guardada en disco")
        except Exception as e:
            logger.error(f"❌ Error al guardar configuración de correo: {e}")
    
    def enviar_thingspeak(self, vx, vy, vz, rms, zona):
        """Enviar datos a ThingSpeak"""
        if not self.config.get('THINGSPEAK_ENABLED', False):
            return False
        
        try:
            url = f"https://api.thingspeak.com/update"
            payload = {
                'api_key': self.config['THINGSPEAK_API_KEY'],
                'field1': round(vx, 4),
                'field2': round(vy, 4),
                'field3': round(vz, 4),
                'field4': round(rms, 4),
                'field5': ord(zona)  # A=65, B=66, C=67, D=68
            }
            logger.info(f"📤 Enviando a ThingSpeak: vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}, rms={rms:.3f}, zona={zona}")
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                entry_id = response.text.strip()
                if entry_id != '0':
                    logger.info(f"✅ ThingSpeak OK - Entry ID: {entry_id}")
                    return True
                else:
                    logger.warning(f"❌ ThingSpeak rechazó datos (rate limit o API key incorrecta)")
                    return False
            else:
                logger.error(f"❌ ThingSpeak error: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error ThingSpeak: {e}")
            return False
    
    def enviar_telegram(self, mensaje):
        """Enviar mensaje de alerta por Telegram"""
        if not self.config.get('TELEGRAM_ENABLED', False):
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            payload = {
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': mensaje,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error Telegram: {e}")
            return False
    
    def enviar_mqtt(self, topic, data):
        """Publicar datos en MQTT"""
        if not self.config.get('MQTT_ENABLED', False) or not self.mqtt_client:
            return False
        
        try:
            payload = json.dumps(data)
            self.mqtt_client.publish(topic, payload)
            return True
        except Exception as e:
            logger.error(f"Error MQTT publish: {e}")
            return False
    
    def enviar_webhook(self, data):
        """Enviar datos a webhook HTTP"""
        if not self.config.get('WEBHOOK_ENABLED', False):
            return False
        
        try:
            response = requests.post(
                self.config['WEBHOOK_URL'],
                json=data,
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error Webhook: {e}")
            return False
    
    def enviar_email(self, asunto, mensaje, image_path=None):
        """Enviar email de alerta en un hilo secundario para evitar bloquear la UI"""
        if not self.config.get('EMAIL_ENABLED', False):
            return False
        
        import threading
        
        def _enviar_async():
            try:
                destinatarios = self.config['EMAIL_TO']
                logger.info(f"📧 Iniciando envío de correo asíncrono a: {destinatarios}...")
                
                if image_path:
                    # Usar related para poder incrustar imágenes inline (Content-ID)
                    msg = MIMEMultipart('related')
                else:
                    msg = MIMEMultipart()
                    
                msg['From'] = self.config['EMAIL_FROM']
                msg['To'] = ', '.join(destinatarios)
                msg['Subject'] = asunto
                
                if image_path:
                    # Crear parte alternative para HTML
                    msg_alternative = MIMEMultipart('alternative')
                    msg.attach(msg_alternative)
                    msg_html = MIMEText(mensaje, 'html')
                    msg_alternative.attach(msg_html)
                    
                    # Adjuntar imagen
                    from email.mime.image import MIMEImage
                    import os
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                        img = MIMEImage(img_data)
                        img.add_header('Content-ID', '<iso20816>')
                        img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                        msg.attach(img)
                        logger.info(f"🖼️ Imagen inline adjuntada: {image_path}")
                    else:
                        logger.warning(f"⚠️ Imagen no encontrada en: {image_path}")
                else:
                    msg.attach(MIMEText(mensaje, 'html'))
                
                server = smtplib.SMTP(
                    self.config['EMAIL_SMTP_SERVER'],
                    self.config['EMAIL_SMTP_PORT']
                )
                server.starttls()
                server.login(self.config['EMAIL_FROM'], self.config['EMAIL_PASSWORD'])
                server.send_message(msg)
                server.quit()
                logger.info(f"✅ Correo enviado con éxito a {destinatarios}!")
            except Exception as e:
                logger.error(f"❌ Error al enviar email en segundo plano: {e}")
                
        # Lanzar el hilo asíncrono sin bloquear la UI
        threading.Thread(target=_enviar_async, daemon=True).start()
        return True
    
    def verificar_alerta(self, zona, vmax):
        """Verificar si se debe enviar alerta o si cambió de zona"""
        # Inicializar last_zone si no existe (por si acaso no se llamó al constructor modificado)
        if not hasattr(self, 'last_zone'):
            self.last_zone = None

        ahora = time.time()
        
        # Caso 1: Primera lectura (inicialización)
        if self.last_zone is None:
            self.last_zone = zona
            if zona != 'A':
                # Comprobar si la alerta para la zona está habilitada
                if zona == 'B' and not self.config.get('ALERT_ZONA_B', False):
                    return False
                if zona == 'C' and not self.config.get('ALERT_ZONA_C', False):
                    return False
                if zona == 'D' and not self.config.get('ALERT_ZONA_D', False):
                    return False
                self.last_alert_time[zona] = ahora
                return True
            return False
            
        # Caso 2: Cambio de zona detectado (Bypass de Cooldown)
        if zona != self.last_zone:
            antigua_zona = self.last_zone
            self.last_zone = zona  # Actualizar siempre la zona actual
            
            if zona == 'A':
                # Si veníamos de una zona de alerta (B, C, o D), enviar restauración
                if antigua_zona in ['B', 'C', 'D']:
                    self.last_alert_time[zona] = ahora
                    return True
                return False
            else:
                # Comprobar si la alerta para la nueva zona está habilitada
                if zona == 'B' and not self.config.get('ALERT_ZONA_B', False):
                    return False
                if zona == 'C' and not self.config.get('ALERT_ZONA_C', False):
                    return False
                if zona == 'D' and not self.config.get('ALERT_ZONA_D', False):
                    return False
                self.last_alert_time[zona] = ahora
                return True

        # Caso 3: Mismo estado (zona == self.last_zone)
        if zona == 'A':
            return False

        # Verificar si la zona requiere alerta
        if zona == 'B' and not self.config.get('ALERT_ZONA_B', False):
            return False
        if zona == 'C' and not self.config.get('ALERT_ZONA_C', False):
            return False
        if zona == 'D' and not self.config.get('ALERT_ZONA_D', False):
            return False

        # Verificar cooldown
        if zona in self.last_alert_time:
            if ahora - self.last_alert_time[zona] < self.config.get('ALERT_COOLDOWN', 300):
                return False  # Aún en cooldown
        
        self.last_alert_time[zona] = ahora
        return True
    
    def enviar_alerta_completa(self, zona, vmax, vx, vy, vz):
        """Enviar alerta por todos los canales configurados"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determinar nivel de urgencia y formato
        if zona == 'D':
            emoji = "🚫"
            nivel = "CRÍTICO"
            accion = "DETENER MÁQUINA INMEDIATAMENTE"
            titulo_seccion = "ALERTA ISO 20816-3"
            subject = f"ALERTA {nivel}: Zona {zona} - {vmax:.3f} mm/s"
            header_color = "#d32f2f"  # Rojo
            bg_color = "#ffebee"
            text_color = "#c62828"
        elif zona == 'C':
            emoji = "🔴"
            nivel = "ALTA"
            accion = "Requiere corrección urgente"
            titulo_seccion = "ALERTA ISO 20816-3"
            subject = f"ALERTA {nivel}: Zona {zona} - {vmax:.3f} mm/s"
            header_color = "#f57c00"  # Naranja
            bg_color = "#fff3e0"
            text_color = "#ef6c00"
        elif zona == 'B':
            emoji = "⚠️"
            nivel = "MEDIA"
            accion = "Vigilancia recomendada"
            titulo_seccion = "ALERTA ISO 20816-3"
            subject = f"ALERTA {nivel}: Zona {zona} - {vmax:.3f} mm/s"
            header_color = "#fbc02d"  # Amarillo
            bg_color = "#fffde7"
            text_color = "#f57f17"
        elif zona == 'A':
            emoji = "✅"
            nivel = "RESTAURACIÓN"
            accion = "Máquina operando en niveles normales de vibración"
            titulo_seccion = "ESTADO ISO 20816-3"
            subject = f"RESTAURACIÓN: Zona {zona} - {vmax:.3f} mm/s (Funcionamiento Normal)"
            header_color = "#388e3c"  # Verde
            bg_color = "#e8f5e9"
            text_color = "#2e7d32"
        else:
            return
        
        # Obtener URL dinámica de ngrok
        ngrok_url = None
        try:
            import requests
            response = requests.get("http://localhost:4040/api/tunnels", timeout=1.0)
            if response.status_code == 200:
                tunnels = response.json().get('tunnels', [])
                for tunnel in tunnels:
                    if tunnel.get('proto') == 'https':
                        ngrok_url = tunnel.get('public_url')
                        break
        except Exception:
            pass
            
        if not ngrok_url:
            # Fallback al NGROK_URL configurado en iot_config.py o al de producción del usuario
            ngrok_url = self.config.get('NGROK_URL', 'https://3f33-190-15-129-108.ngrok-free.app').rstrip('/')
            
        # Generar botón según la categoría
        if zona in ['B', 'C']:
            boton_accion = f"""
            <a href="{ngrok_url}/?tab=mantenimiento" style="display: inline-block; padding: 12px 24px; color: white; background-color: #f57c00; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; font-size: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">📅 Programar Parada Programada</a>
            """
        elif zona == 'D':
            boton_accion = f"""
            <a href="{ngrok_url}/?tab=control" style="display: inline-block; padding: 12px 24px; color: white; background-color: #d32f2f; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; font-size: 16px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">🚨 Parada de Emergencia</a>
            """
        else: # 'A'
            boton_accion = f"""
            <a href="{ngrok_url}" style="display: inline-block; padding: 12px 24px; color: white; background-color: #388e3c; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; font-size: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">📊 Ver Monitoreo en Tiempo Real</a>
            """

        # Ruta de la imagen iso20816.png
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, 'images', 'iso20816.png')

        # Mensaje para Telegram (texto plano formateado)
        mensaje_telegram = f"""
{emoji} <b>{titulo_seccion}</b> {emoji}

<b>Nivel:</b> {nivel}
<b>Zona:</b> {zona}
<b>Velocidad máxima:</b> {vmax:.3f} mm/s

<b>Detalles:</b>
• Eje X: {vx:.3f} mm/s
• Eje Y: {vy:.3f} mm/s
• Eje Z: {vz:.3f} mm/s

<b>Acción:</b> {accion}

<i>Fecha: {timestamp}</i>
        """

        # Mensaje HTML premium para email
        mensaje_html = f"""
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f4f6f9; color: #333; margin: 0;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-top: 6px solid {header_color};">
        <h2 style="color: {header_color}; margin-top: 0; margin-bottom: 20px; font-size: 24px; text-align: center;">{emoji} {titulo_seccion} {emoji}</h2>
        
        <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; border-left: 4px solid {header_color}; margin-bottom: 25px; text-align: center;">
            <p style="margin: 0; font-size: 16px; color: {text_color}; font-weight: bold;">Sistema de Alertas Configurado Correctamente</p>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #555;">Notificación de Cambio de Categoría de Vibraciones</p>
        </div>
        
        <h3 style="color: #444; border-bottom: 2px solid #eaeaea; padding-bottom: 8px; margin-bottom: 15px; font-size: 18px;">📊 Información del Sistema</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 14px;">
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; width: 40%; color: #555;">Sistema:</td>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #111;">HidroMira IoT Monitor</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #555;">Fecha:</td>
                <td style="padding: 12px; border: 1px solid #e0e0e0; color: #111;">{timestamp}</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #555;">Zona / Estado:</td>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: {header_color};">Zona {zona} ({nivel})</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #555;">Velocidad Máxima:</td>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #111;">{vmax:.3f} mm/s</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #555;">Detalles Ejes (X, Y, Z):</td>
                <td style="padding: 12px; border: 1px solid #e0e0e0; color: #333;">X: {vx:.3f} | Y: {vy:.3f} | Z: {vz:.3f} mm/s</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: #555;">Acción Recomendada:</td>
                <td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: bold; color: {header_color};">{accion}</td>
            </tr>
        </table>

        <!-- Tabla con la imagen de los niveles de la norma ISO -->
        <h3 style="color: #444; border-bottom: 2px solid #eaeaea; padding-bottom: 8px; margin-bottom: 15px; font-size: 18px;">📈 Tabla de Referencia ISO 20816-3</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px; text-align: center;">
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background-color: #fff; text-align: center;">
                    <img src="cid:iso20816" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 4px;" alt="Norma ISO 20816-3">
                </td>
            </tr>
        </table>

        <!-- Botón de acción dinámica (ngrok) -->
        <div style="text-align: center; margin-top: 15px; margin-bottom: 25px;">
            {boton_accion}
        </div>
        
        <p style="margin-top: 30px; color: #777; font-size: 12px; text-align: center; border-top: 1px solid #eaeaea; padding-top: 15px; line-height: 1.5;">
            Este es un correo automático generado por el sistema de monitoreo de vibraciones HidroMira.<br>
            <strong>Dirección pública ngrok activa:</strong> <a href="{ngrok_url}" style="color: #2196f3; font-weight: bold; text-decoration: none;">{ngrok_url}</a>
        </p>
    </div>
</body>
</html>
        """
        
        # Enviar por Telegram
        if self.config.get('TELEGRAM_ENABLED', False):
            self.enviar_telegram(mensaje_telegram.replace('<b>', '*').replace('</b>', '*').replace('<i>', '_').replace('</i>', '_'))
        
        # Enviar por Email (adjuntando la imagen ISO)
        if self.config.get('EMAIL_ENABLED', False):
            self.enviar_email(subject, mensaje_html, image_path=image_path)
        
        return True
    
    def publicar_datos(self, vx, vy, vz, rms, zona, rpm):
        """Publicar datos en todos los servicios IoT configurados"""
        timestamp = datetime.now().isoformat()
        
        data = {
            'timestamp': timestamp,
            'vx': vx,
            'vy': vy,
            'vz': vz,
            'rms': rms,
            'zona': zona,
            'rpm': rpm
        }
        
        # ThingSpeak
        if self.config.get('THINGSPEAK_ENABLED', False):
            self.enviar_thingspeak(vx, vy, vz, rms, zona)
        
        # MQTT
        if self.config.get('MQTT_ENABLED', False):
            self.enviar_mqtt(self.config.get('MQTT_TOPIC', 'hidromira/vibraciones'), data)
        
        # Webhook
        if self.config.get('WEBHOOK_ENABLED', False):
            self.enviar_webhook(data)
    
    def cleanup(self):
        """Limpiar recursos"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

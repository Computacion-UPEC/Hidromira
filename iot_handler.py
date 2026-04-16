import requests
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class IoTHandler:
    def __init__(self, config):
        self.config = config
        self.last_alert_time = {}
        self.mqtt_client = None
        
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
            print(f"✅ MQTT conectado a {self.config['MQTT_BROKER']}")
        except Exception as e:
            print(f"❌ Error MQTT: {e}")
            self.mqtt_client = None
    
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
            print(f"📤 Enviando a ThingSpeak: vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}, rms={rms:.3f}, zona={zona}")
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                entry_id = response.text.strip()
                if entry_id != '0':
                    print(f"✅ ThingSpeak OK - Entry ID: {entry_id}")
                    return True
                else:
                    print(f"❌ ThingSpeak rechazó datos (rate limit o API key incorrecta)")
                    return False
            else:
                print(f"❌ ThingSpeak error: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error ThingSpeak: {e}")
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
            print(f"Error Telegram: {e}")
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
            print(f"Error MQTT publish: {e}")
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
            print(f"Error Webhook: {e}")
            return False
    
    def enviar_email(self, asunto, mensaje):
        """Enviar email de alerta"""
        if not self.config.get('EMAIL_ENABLED', False):
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['EMAIL_FROM']
            msg['To'] = ', '.join(self.config['EMAIL_TO'])
            msg['Subject'] = asunto
            
            msg.attach(MIMEText(mensaje, 'html'))
            
            server = smtplib.SMTP(
                self.config['EMAIL_SMTP_SERVER'],
                self.config['EMAIL_SMTP_PORT']
            )
            server.starttls()
            server.login(self.config['EMAIL_FROM'], self.config['EMAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Error Email: {e}")
            return False
    
    def verificar_alerta(self, zona, vmax):
        """Verificar si se debe enviar alerta"""
        # Verificar cooldown
        ahora = time.time()
        if zona in self.last_alert_time:
            if ahora - self.last_alert_time[zona] < self.config.get('ALERT_COOLDOWN', 300):
                return False  # Aún en cooldown
        
        # Verificar si la zona requiere alerta
        if zona == 'B' and not self.config.get('ALERT_ZONA_B', False):
            return False
        if zona == 'C' and not self.config.get('ALERT_ZONA_C', False):
            return False
        if zona == 'D' and not self.config.get('ALERT_ZONA_D', False):
            return False
        
        self.last_alert_time[zona] = ahora
        return True
    
    def enviar_alerta_completa(self, zona, vmax, vx, vy, vz):
        """Enviar alerta por todos los canales configurados"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determinar nivel de urgencia
        if zona == 'D':
            emoji = "🚫"
            nivel = "CRÍTICO"
            accion = "DETENER MÁQUINA INMEDIATAMENTE"
        elif zona == 'C':
            emoji = "🔴"
            nivel = "ALTA"
            accion = "Requiere corrección urgente"
        elif zona == 'B':
            emoji = "⚠️"
            nivel = "MEDIA"
            accion = "Vigilancia recomendada"
        else:
            return  # No alertar en zona A
        
        # Mensaje para Telegram/Email
        mensaje = f"""
{emoji} <b>ALERTA ISO 20816-3</b> {emoji}

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
        
        # Enviar por Telegram
        if self.config.get('TELEGRAM_ENABLED', False):
            self.enviar_telegram(mensaje.replace('<b>', '*').replace('</b>', '*').replace('<i>', '_').replace('</i>', '_'))
        
        # Enviar por Email
        if self.config.get('EMAIL_ENABLED', False):
            self.enviar_email(
                f"ALERTA {nivel}: Zona {zona} - {vmax:.3f} mm/s",
                mensaje
            )
        
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

# 📧 CONFIGURACIÓN DE ALERTAS POR GMAIL

## ✅ Gmail está HABILITADO en el sistema

Las alertas por email se enviarán cuando la vibración entre en:
- **Zona B** (Amarillo): Vigilancia (> 0.25 mm/s)
- **Zona C** (Naranja): Corrección necesaria (> 0.5 mm/s)
- **Zona D** (Rojo): Inaceptable (> 0.75 mm/s)

**Cooldown**: 5 minutos entre alertas repetidas para evitar spam.

---

## 🔧 CONFIGURACIÓN PASO A PASO

### 1. Crear Contraseña de Aplicación en Gmail

Gmail **NO permite usar tu contraseña normal** por seguridad. Debes crear una "Contraseña de Aplicación":

#### Paso 1: Habilitar verificación en 2 pasos
1. Ve a: https://myaccount.google.com/security
2. En "Acceso a Google", selecciona **"Verificación en 2 pasos"**
3. Sigue los pasos para habilitarla (necesitas tu teléfono)

#### Paso 2: Generar contraseña de aplicación
1. Una vez habilitada la verificación en 2 pasos, ve a:
   https://myaccount.google.com/apppasswords
2. En "Nombre de la aplicación", escribe: **HidroMira Monitor**
3. Haz clic en **"Crear"**
4. Gmail generará una contraseña de 16 caracteres (ejemplo: `abcd efgh ijkl mnop`)
5. **COPIA ESTA CONTRASEÑA** (la necesitarás en el siguiente paso)

### 2. Configurar iot_config.py

Abre el archivo: `iot_config.py`

Busca la sección **EMAIL** (líneas 27-32) y completa:

```python
# ========== EMAIL (Alertas por correo) ==========
EMAIL_ENABLED = True  # ✅ YA ESTÁ ACTIVADO
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_FROM = "tu_email@gmail.com"  # ← TU EMAIL DE GMAIL
EMAIL_PASSWORD = "abcd efgh ijkl mnop"  # ← CONTRASEÑA DE APLICACIÓN (16 caracteres)
EMAIL_TO = ["tu_email@gmail.com"]  # ← EMAIL(S) PARA RECIBIR ALERTAS
```

**Ejemplo real:**
```python
EMAIL_FROM = "juan.perez@gmail.com"
EMAIL_PASSWORD = "xmpl abcd 1234 efgh"  # La que generaste en paso anterior
EMAIL_TO = ["juan.perez@gmail.com", "supervisor@empresa.com"]  # Puedes poner varios
```

### 3. Guardar y Reiniciar Monitor

1. **Guarda** el archivo `iot_config.py`
2. **Detén** el monitor (Ctrl+C en la terminal de Streamlit)
3. **Reinicia** el monitor:
   ```powershell
   streamlit run monitor_realtime.py --server.port 8503
   ```

---

## 📬 FORMATO DE ALERTAS POR EMAIL

Las alertas incluirán:

**Asunto:**
```
⚠️ ALERTA ZONA C - Vibración Alta en HidroMira
```

**Cuerpo del email (HTML):**
```html
🚨 ALERTA DE VIBRACIÓN

━━━━━━━━━━━━━━━━━━━━━━
📊 ESTADO: ZONA C (Naranja)
⚠️ NIVEL: Alto
🎯 ACCIÓN: Programar corrección en próximo mantenimiento
━━━━━━━━━━━━━━━━━━━━━━

📈 VALORES ACTUALES:
   • Vx: 0.42 mm/s
   • Vy: 0.53 mm/s
   • Vz: 0.38 mm/s
   • RMS: 0.53 mm/s

⏰ Timestamp: 2026-01-07 20:45:23

🏭 Norma: ISO 20816-3 Grupo 1
   Zona A: ≤ 0.25 mm/s (Normal)
   Zona B: ≤ 0.5 mm/s (Vigilancia)
   Zona C: ≤ 0.75 mm/s (Corrección) ← ACTUAL
   Zona D: > 0.75 mm/s (Inaceptable)
```

---

## 🧪 PROBAR ALERTAS

Para probar que funciona, puedes:

1. **Método rápido** - Ejecuta el script de prueba:
   ```powershell
   python test_email.py
   ```

2. **En el monitor** - Las alertas se envían automáticamente cuando:
   - Vibración > 0.25 mm/s (Zona B) con datos reales
   - Sistema detecta cambio de zona

---

## 🔍 SOLUCIÓN DE PROBLEMAS

### Error: "Username and Password not accepted"
- ✅ Verifica que EMAIL_FROM sea tu email completo (@gmail.com)
- ✅ Verifica que EMAIL_PASSWORD sea la contraseña de aplicación (16 caracteres)
- ✅ **NO uses tu contraseña normal de Gmail**
- ✅ Asegúrate de haber habilitado verificación en 2 pasos

### Error: "SMTPAuthenticationError"
- La contraseña de aplicación es incorrecta
- Genera una nueva en: https://myaccount.google.com/apppasswords

### Error: "Connection refused"
- Verifica tu conexión a internet
- Gmail puede estar bloqueado en tu red (firewall corporativo)

### No llegan emails
- ✅ Revisa la carpeta de SPAM
- ✅ Agrega EMAIL_FROM a tus contactos
- ✅ Verifica que EMAIL_TO esté correcto

### Error: "Application-specific password required"
- Tu cuenta Gmail **requiere** contraseña de aplicación
- No puedes usar la contraseña normal
- Sigue el paso 1 arriba para crearla

---

## 🔐 SEGURIDAD

- ✅ La contraseña de aplicación solo funciona para HidroMira
- ✅ No da acceso completo a tu cuenta Gmail
- ✅ Puedes revocarla en cualquier momento desde: https://myaccount.google.com/apppasswords
- ⚠️ **NO compartas** el archivo `iot_config.py` con la contraseña

---

## 📊 CONFIGURACIÓN AVANZADA

### Enviar a múltiples destinatarios:
```python
EMAIL_TO = [
    "operador@empresa.com",
    "supervisor@empresa.com",
    "mantenimiento@empresa.com"
]
```

### Cambiar cooldown (tiempo entre alertas):
```python
ALERT_COOLDOWN = 180  # 3 minutos (más frecuente)
ALERT_COOLDOWN = 600  # 10 minutos (menos frecuente)
```

### Desactivar alertas de zona B:
```python
ALERT_ZONA_B = False  # Solo alertar en C y D
ALERT_ZONA_C = True
ALERT_ZONA_D = True
```

---

## ✅ ESTADO ACTUAL

- **ThingSpeak**: ✅ Activo (cloud storage cada 15s)
- **REST API**: ✅ Activo (puerto 5000)
- **Email Gmail**: ✅ Habilitado (requiere configuración)
- **Telegram**: ❌ Deshabilitado (BotFather no responde)
- **MQTT**: ⚙️ Disponible (deshabilitado)
- **Webhook**: ⚙️ Disponible (deshabilitado)

---

## 🆘 AYUDA

Si tienes problemas, ejecuta:
```powershell
python test_email.py
```

El script mostrará exactamente dónde está el error.

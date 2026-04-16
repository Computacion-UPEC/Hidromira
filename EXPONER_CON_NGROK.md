# 🌐 EXPONER HIDROMIRA A INTERNET CON NGROK

## ¿Qué es ngrok?

**ngrok** crea un túnel seguro HTTPS desde internet hacia tu aplicación local. Perfecto para:
- ✅ Acceder al monitor desde cualquier lugar
- ✅ Integrar la API REST con otros sistemas
- ✅ Recibir webhooks de servicios externos
- ✅ Compartir el dashboard con tu equipo

---

## 🚀 INSTALACIÓN DE NGROK

### Opción 1: Descarga directa (Recomendado)

1. **Descarga ngrok:**
   - Ve a: https://ngrok.com/download
   - Descarga la versión para Windows
   - Extrae `ngrok.exe` a `C:\ngrok\` (o cualquier carpeta)

2. **Crea cuenta gratis** (opcional pero recomendado):
   - Regístrate en: https://dashboard.ngrok.com/signup
   - Obtendrás un authtoken para túneles persistentes

3. **Configura authtoken** (si creaste cuenta):
   ```powershell
   C:\ngrok\ngrok.exe config add-authtoken TU_TOKEN_AQUI
   ```

### Opción 2: Con Chocolatey

Si tienes Chocolatey instalado:
```powershell
choco install ngrok
```

### Opción 3: Con Scoop

Si tienes Scoop:
```powershell
scoop install ngrok
```

---

## 📡 EXPONER EL MONITOR STREAMLIT (Puerto 8503)

### Paso 1: Inicia el monitor (si no está corriendo)

```powershell
streamlit run monitor_realtime.py --server.port 8503
```

### Paso 2: En otra terminal, inicia ngrok

```powershell
C:\ngrok\ngrok.exe http 8503
```

**Salida esperada:**
```
Session Status                online
Account                       TuCuenta (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:8503

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### Paso 3: Accede desde internet

**URL pública:** `https://abc123.ngrok.io` (la que te muestre ngrok)

Puedes abrir esta URL desde:
- ✅ Tu celular
- ✅ Otra computadora
- ✅ Red externa (fuera de tu oficina)
- ✅ Compartir con colegas

---

## 🔌 EXPONER LA API REST (Puerto 5000)

### Paso 1: Inicia la API (si no está corriendo)

```powershell
python api_rest.py
```

### Paso 2: En otra terminal, expone el puerto 5000

```powershell
C:\ngrok\ngrok.exe http 5000
```

**URL pública:** `https://xyz456.ngrok.io`

### Endpoints disponibles:

1. **GET** `/api/estado` - Estado actual del sistema
   ```
   https://xyz456.ngrok.io/api/estado
   ```

2. **GET** `/api/datos` - Últimas lecturas
   ```
   https://xyz456.ngrok.io/api/datos
   ```

3. **GET** `/api/historico` - Histórico completo
   ```
   https://xyz456.ngrok.io/api/historico
   ```

4. **GET** `/api/estadisticas` - Estadísticas
   ```
   https://xyz456.ngrok.io/api/estadisticas
   ```

5. **POST** `/api/alerta` - Registrar alerta
   ```
   https://xyz456.ngrok.io/api/alerta
   ```

6. **GET** `/api/salud` - Health check
   ```
   https://xyz456.ngrok.io/api/salud
   ```

---

## 🎯 CONFIGURACIÓN AVANZADA

### Túnel con dominio personalizado (Plan Paid)

```powershell
ngrok http 8503 --domain=hidromira.ngrok.io
```

### Túnel con autenticación básica

```powershell
ngrok http 8503 --basic-auth="usuario:contraseña"
```

### Túnel con IP whitelisting (Plan Paid)

```powershell
ngrok http 8503 --cidr-allow="1.2.3.4/32"
```

### Ver panel de inspección ngrok

Abre en tu navegador: http://127.0.0.1:4040

Verás:
- ✅ Todas las peticiones HTTP
- ✅ Headers completos
- ✅ Respuestas
- ✅ Tiempos de respuesta
- ✅ Replay de peticiones

---

## 🔄 EXPONER AMBOS PUERTOS SIMULTÁNEAMENTE

### Método 1: Con archivo de configuración

**Crea** `ngrok.yml` en `C:\Users\ggeta\AppData\Local\ngrok\`:

```yaml
version: "2"
authtoken: TU_AUTHTOKEN_AQUI

tunnels:
  monitor:
    proto: http
    addr: 8503
    inspect: true
  
  api:
    proto: http
    addr: 5000
    inspect: true
```

**Inicia ambos túneles:**
```powershell
ngrok start --all
```

### Método 2: Dos terminales separadas

**Terminal 1:**
```powershell
ngrok http 8503
```

**Terminal 2:**
```powershell
ngrok http 5000
```

---

## 📱 USO CON WEBHOOK (Para IoT)

Si quieres recibir datos desde servicios externos:

**1. Configura webhook en iot_config.py:**
```python
WEBHOOK_ENABLED = True
WEBHOOK_URL = "https://tu-servidor.com/recibir"
```

**2. Expón tu servidor local que reciba webhooks:**
```powershell
ngrok http 3000
```

**3. Usa la URL de ngrok en servicios externos:**
- ThingSpeak React
- IFTTT
- Zapier
- Servicios personalizados

---

## 🔐 SEGURIDAD

### ⚠️ Consideraciones importantes:

1. **URLs temporales**: Las URLs gratuitas cambian cada vez que reinicias ngrok
   - Solución: Cuenta Pro ($10/mes) con dominio fijo

2. **Exposición pública**: Tu monitor es accesible desde internet
   - Solución: Usa autenticación básica o IP whitelisting

3. **Límites plan gratuito**:
   - 1 proceso ngrok simultáneo
   - 40 conexiones/min
   - URLs aleatorias

4. **Datos sensibles**: No expongas contraseñas en el monitor
   - Ya protegido: Las contraseñas en iot_config no se muestran en el UI

### ✅ Mejores prácticas:

```powershell
# Con autenticación
ngrok http 8503 --basic-auth="admin:HidroMira2026!"

# Solo ciertas IPs
ngrok http 8503 --cidr-allow="200.10.20.30/32"

# Con región específica
ngrok http 8503 --region=sa  # Sudamérica (menos latencia)
```

---

## 🎨 INTERFAZ WEB DE NGROK

Mientras ngrok corre, puedes ver estadísticas en:

**http://localhost:4040**

Funciones útiles:
- 📊 Ver todas las peticiones en tiempo real
- 🔄 Replay peticiones (volver a enviar)
- 📝 Inspeccionar headers y body
- ⏱️ Medir tiempos de respuesta
- 🔍 Buscar peticiones específicas

---

## 🚀 SCRIPTS DE INICIO RÁPIDO

### Script: `iniciar_hidromira_publico.ps1`

```powershell
# Inicia todo el stack HidroMira con exposición pública

# Terminal 1: Monitor Streamlit
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\ggeta\Documents\HidroMira; .\venv\Scripts\Activate.ps1; streamlit run monitor_realtime.py --server.port 8503"

# Esperar 5 segundos
Start-Sleep -Seconds 5

# Terminal 2: API REST
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\ggeta\Documents\HidroMira; .\venv\Scripts\Activate.ps1; python api_rest.py"

# Esperar 3 segundos
Start-Sleep -Seconds 3

# Terminal 3: ngrok para monitor
Start-Process powershell -ArgumentList "-NoExit", "-Command", "C:\ngrok\ngrok.exe http 8503"

# Terminal 4: ngrok para API (si tienes plan Pro)
# Start-Process powershell -ArgumentList "-NoExit", "-Command", "C:\ngrok\ngrok.exe http 5000"

Write-Host "✅ HidroMira iniciado y expuesto públicamente"
Write-Host "📱 Accede al monitor desde la URL que muestra ngrok"
```

---

## 📊 EJEMPLO DE USO COMPLETO

### 1. Inicia servicios locales

```powershell
# Terminal 1
streamlit run monitor_realtime.py --server.port 8503

# Terminal 2 (opcional)
python api_rest.py
```

### 2. Expón con ngrok

```powershell
# Terminal 3
ngrok http 8503
```

### 3. Comparte la URL

Ngrok te dará algo como:
```
https://f2a3b4c5d6e7.ngrok.io
```

Comparte esa URL con:
- 👨‍💼 Supervisor
- 👷 Equipo de mantenimiento
- 📱 Tu teléfono móvil
- 💻 Otro sistema que consuma la API

### 4. Accede desde cualquier lugar

Abre la URL en cualquier navegador:
- ✅ Verás el monitor en tiempo real
- ✅ Gráficos actualizándose cada 500ms
- ✅ Alertas ISO 20816-3
- ✅ Estadísticas ThingSpeak

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: "ngrok not found"
```powershell
# Usa ruta completa
C:\ngrok\ngrok.exe http 8503
```

### Error: "Account limit exceeded"
- Cierra otros túneles ngrok activos
- Plan gratuito: solo 1 túnel simultáneo
- Upgrade a plan Pro si necesitas múltiples túneles

### Túnel muy lento
```powershell
# Usa región más cercana
ngrok http 8503 --region=sa  # Sudamérica
ngrok http 8503 --region=us  # USA
ngrok http 8503 --region=eu  # Europa
```

### URL cambia cada vez
- Solución: Cuenta Pro con dominio reservado
- Alternativa: Actualiza URL en tus integraciones cada vez

---

## 💡 ALTERNATIVAS A NGROK

Si necesitas algo diferente:

1. **LocalTunnel** (Gratis, open source)
   ```powershell
   npm install -g localtunnel
   lt --port 8503
   ```

2. **Cloudflare Tunnel** (Gratis, sin límites)
   ```powershell
   cloudflared tunnel --url http://localhost:8503
   ```

3. **Serveo** (Solo SSH)
   ```bash
   ssh -R 80:localhost:8503 serveo.net
   ```

---

## ✅ CHECKLIST DE DESPLIEGUE PÚBLICO

Antes de compartir tu URL:

- [ ] Monitor Streamlit corriendo en 8503
- [ ] Datos actualizándose correctamente
- [ ] ThingSpeak recibiendo datos
- [ ] Email alertas configurado (opcional)
- [ ] ngrok iniciado y túnel activo
- [ ] URL pública funcionando
- [ ] Autenticación configurada (si es necesario)
- [ ] IP whitelisting (si es necesario)
- [ ] URL compartida con equipo

---

## 📞 SOPORTE

**Ngrok Docs:** https://ngrok.com/docs
**Ngrok Dashboard:** https://dashboard.ngrok.com/
**Planes:** https://ngrok.com/pricing

**Plan Gratis incluye:**
- ✅ 1 túnel online simultáneo
- ✅ 40 conexiones/min
- ✅ HTTPS
- ✅ Panel de inspección

**Plan Pro ($10/mes) incluye:**
- ✅ 3 túneles simultáneos
- ✅ Dominios personalizados
- ✅ IP whitelisting
- ✅ Autenticación básica
- ✅ URLs persistentes

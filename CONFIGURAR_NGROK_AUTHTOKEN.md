# 🔑 CONFIGURAR NGROK - SOLUCIÓN RÁPIDA

## ❌ Error: "authentication failed: Usage of ngrok requires a verified account"

Este error significa que ngrok necesita que configures tu authtoken.

---

## ✅ SOLUCIÓN EN 3 PASOS

### PASO 1: Crea cuenta gratuita (1 minuto)

Ve a: **https://dashboard.ngrok.com/signup**

Opciones para registrarte:
- GitHub (recomendado - 1 clic)
- Google
- Email

✅ **Es GRATIS** - no necesitas tarjeta de crédito

---

### PASO 2: Obtén tu authtoken

Después de registrarte, ngrok te redirige a:
**https://dashboard.ngrok.com/get-started/your-authtoken**

Verás algo como:
```
Your Authtoken
2aBcDeF3gHiJkLmNoPqRsTuVwXyZ_4aBcDeFgHiJkLmNoPqRs
```

📋 **COPIA ese token** (clic en el botón "Copy")

---

### PASO 3: Configura el authtoken en tu computadora

Abre PowerShell en HidroMira y ejecuta:

```powershell
ngrok config add-authtoken TU_TOKEN_AQUI
```

**Ejemplo real:**
```powershell
ngrok config add-authtoken 2aBcDeF3gHiJkLmNoPqRsTuVwXyZ_4aBcDeFgHiJkLmNoPqRs
```

✅ Salida esperada:
```
Authtoken saved to configuration file: C:\Users\ggeta\.ngrok2\ngrok.yml
```

---

## 🚀 AHORA SÍ - EXPÓN EL MONITOR

Una vez configurado el authtoken, ejecuta:

```powershell
ngrok http 8503
```

✅ Funcionará y verás:
```
Session Status                online
Account                       Tu Nombre (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://abc123.ngrok.io -> http://localhost:8503
```

---

## 📱 USA LA URL PÚBLICA

La URL que te muestre (ejemplo: `https://abc123.ngrok.io`) es tu monitor accesible desde:
- ✅ Tu celular
- ✅ Cualquier computadora
- ✅ Fuera de tu red
- ✅ Compartir con equipo

---

## 🔍 COMANDOS ÚTILES

### Ver configuración actual:
```powershell
ngrok config check
```

### Ver archivo de configuración:
```powershell
notepad C:\Users\ggeta\.ngrok2\ngrok.yml
```

### Panel web de inspección (mientras ngrok corre):
Abre en navegador: **http://localhost:4040**

---

## ⚡ SCRIPT AUTOMATIZADO

Una vez configurado el authtoken, usa el script PowerShell:

```powershell
.\exponer_ngrok.ps1
```

O manualmente:
```powershell
# Monitor Streamlit
ngrok http 8503

# API REST (en otra terminal)
ngrok http 5000
```

---

## 💡 PLAN GRATUITO INCLUYE

✅ 1 túnel online simultáneo
✅ 40 conexiones/min
✅ URLs HTTPS automáticas
✅ Panel de inspección
✅ Permanente (no expira)

⚠️ Limitaciones:
- URLs aleatorias (cambian al reiniciar)
- 1 solo túnel a la vez

**Plan Pro ($10/mes):**
- 3 túneles simultáneos
- Dominios personalizados fijos
- IP whitelisting
- Más conexiones/min

---

## 🆘 PROBLEMAS COMUNES

### "command not found: ngrok"
Usa ruta completa:
```powershell
C:\ngrok\ngrok.exe config add-authtoken TU_TOKEN
C:\ngrok\ngrok.exe http 8503
```

### "invalid authtoken"
- Verifica que copiaste el token completo
- No incluyas espacios ni comillas
- El token tiene ~40 caracteres

### "tunnel already exists"
Ya tienes un túnel corriendo:
- Cierra otras ventanas de ngrok (Ctrl+C)
- Verifica con: `tasklist | findstr ngrok`
- Matar proceso: `taskkill /F /IM ngrok.exe`

---

## ✅ RESUMEN

1. **Regístrate**: https://dashboard.ngrok.com/signup
2. **Copia token**: https://dashboard.ngrok.com/get-started/your-authtoken
3. **Configura**: `ngrok config add-authtoken TU_TOKEN`
4. **Ejecuta**: `ngrok http 8503`
5. **Comparte URL**: La que te muestre ngrok

¡Listo! Tu monitor estará disponible públicamente.

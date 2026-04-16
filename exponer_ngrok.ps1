# Script para exponer HidroMira a internet con ngrok
# Requiere: ngrok instalado en C:\ngrok\ngrok.exe (o ajustar ruta)

Write-Host "🌐 EXPONIENDO HIDROMIRA A INTERNET CON NGROK" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 69) -ForegroundColor Gray
Write-Host ""

# Verificar si ngrok está instalado
$ngrokPaths = @(
    "C:\ngrok\ngrok.exe",
    "C:\Program Files\ngrok\ngrok.exe",
    "$env:USERPROFILE\Downloads\ngrok.exe",
    "ngrok.exe"  # En PATH
)

$ngrokPath = $null
foreach ($path in $ngrokPaths) {
    if (Test-Path $path -ErrorAction SilentlyContinue) {
        $ngrokPath = $path
        break
    }
}

if (-not $ngrokPath) {
    # Intentar ejecutar ngrok desde PATH
    try {
        $null = Get-Command ngrok -ErrorAction Stop
        $ngrokPath = "ngrok"
    } catch {
        Write-Host "❌ ngrok no encontrado" -ForegroundColor Red
        Write-Host ""
        Write-Host "📥 Descarga ngrok desde: https://ngrok.com/download" -ForegroundColor Yellow
        Write-Host "   1. Descarga ngrok para Windows"
        Write-Host "   2. Extrae ngrok.exe a C:\ngrok\"
        Write-Host "   3. Ejecuta este script nuevamente"
        Write-Host ""
        pause
        exit 1
    }
}

Write-Host "✅ ngrok encontrado en: $ngrokPath" -ForegroundColor Green
Write-Host ""

# Preguntar qué exponer
Write-Host "🎯 ¿Qué deseas exponer?" -ForegroundColor Cyan
Write-Host "   1. Monitor Streamlit (Puerto 8503) [RECOMENDADO]"
Write-Host "   2. API REST (Puerto 5000)"
Write-Host "   3. Ambos (requiere cuenta Pro)"
Write-Host ""

$opcion = Read-Host "Selecciona opción (1/2/3)"

switch ($opcion) {
    "1" {
        $puerto = 8503
        $servicio = "Monitor Streamlit"
        $comando = "streamlit run monitor_realtime.py --server.port 8503"
    }
    "2" {
        $puerto = 5000
        $servicio = "API REST"
        $comando = "python api_rest.py"
    }
    "3" {
        Write-Host "⚠️ Exponer ambos requiere cuenta ngrok Pro" -ForegroundColor Yellow
        Write-Host "   Exponiendo solo Monitor por ahora..." -ForegroundColor Yellow
        $puerto = 8503
        $servicio = "Monitor Streamlit"
        $comando = "streamlit run monitor_realtime.py --server.port 8503"
    }
    default {
        Write-Host "❌ Opción inválida" -ForegroundColor Red
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "📡 Exponiendo: $servicio (Puerto $puerto)" -ForegroundColor Cyan
Write-Host ""

# Verificar si el servicio está corriendo
$servicioActivo = $false
try {
    $test = Invoke-WebRequest -Uri "http://localhost:$puerto" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
    $servicioActivo = $true
} catch {
    $servicioActivo = $false
}

if (-not $servicioActivo) {
    Write-Host "⚠️ El servicio no está corriendo en puerto $puerto" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "¿Quieres que lo inicie automáticamente? (S/N): " -NoNewline -ForegroundColor Yellow
    $respuesta = Read-Host
    
    if ($respuesta -eq "S" -or $respuesta -eq "s") {
        Write-Host ""
        Write-Host "🚀 Iniciando $servicio..." -ForegroundColor Cyan
        
        # Activar venv y ejecutar comando
        $scriptBlock = {
            param($dir, $cmd)
            Set-Location $dir
            & "$dir\venv\Scripts\Activate.ps1"
            Invoke-Expression $cmd
        }
        
        $dirActual = Get-Location
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {Set-Location '$dirActual'; & '.\venv\Scripts\Activate.ps1'; $comando}"
        
        Write-Host "⏳ Esperando 8 segundos a que el servicio inicie..." -ForegroundColor Yellow
        Start-Sleep -Seconds 8
    } else {
        Write-Host ""
        Write-Host "❌ Inicia manualmente el servicio antes de continuar:" -ForegroundColor Red
        Write-Host "   $comando" -ForegroundColor White
        Write-Host ""
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "✅ Servicio detectado en puerto $puerto" -ForegroundColor Green
Write-Host ""

# Preguntar por autenticación
Write-Host "🔐 ¿Quieres proteger con autenticación básica? (S/N): " -NoNewline -ForegroundColor Cyan
$auth = Read-Host

$authParam = ""
if ($auth -eq "S" -or $auth -eq "s") {
    Write-Host ""
    $usuario = Read-Host "Usuario"
    $password = Read-Host "Contraseña" -AsSecureString
    $passwordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
    $authParam = "--basic-auth=`"$usuario`:$passwordPlain`""
}

Write-Host ""
Write-Host "🌍 Iniciando túnel ngrok..." -ForegroundColor Cyan
Write-Host "-" -NoNewline; Write-Host ("-" * 69) -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️ IMPORTANTE:" -ForegroundColor Yellow
Write-Host "   • La URL pública aparecerá en la siguiente ventana"
Write-Host "   • Formato: https://XXXXXXXX.ngrok.io"
Write-Host "   • Comparte esa URL para acceso remoto"
Write-Host "   • Panel de inspección: http://localhost:4040"
Write-Host ""
Write-Host "🛑 Para detener: Presiona Ctrl+C en la ventana de ngrok" -ForegroundColor Yellow
Write-Host ""

# Construir comando
$ngrokCmd = "http $puerto $authParam"

Write-Host "🚀 Ejecutando: $ngrokPath $ngrokCmd" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Accede desde cualquier dispositivo usando la URL de ngrok" -ForegroundColor Cyan
Write-Host ""

# Esperar 2 segundos antes de ejecutar
Start-Sleep -Seconds 2

# Ejecutar ngrok
try {
    if ($authParam) {
        & $ngrokPath http $puerto $authParam
    } else {
        & $ngrokPath http $puerto
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error al iniciar ngrok: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Intenta manualmente:" -ForegroundColor Yellow
    Write-Host "   $ngrokPath http $puerto" -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "👋 Túnel cerrado" -ForegroundColor Yellow
pause

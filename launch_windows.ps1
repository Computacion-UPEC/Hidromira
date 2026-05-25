<#
launch_windows.ps1
Script to create/activate a venv, install requirements if needed,
and launch API + Streamlit apps in separate PowerShell windows on Windows.

Usage: Run this script from the project root (where this file is):
    powershell -ExecutionPolicy Bypass -File .\launch_windows.ps1
#>

param(
    [string]$venvDir = "venv",
    [string]$pythonExeRel = "$venvDir\Scripts\python.exe",
    [string]$ports = "api:5000,app:8502,monitor:8503,web:8501"
)

Set-StrictMode -Version Latest

function Write-Ok($m){ Write-Host $m -ForegroundColor Green }
function Write-Warn($m){ Write-Host $m -ForegroundColor Yellow }
function Write-Err($m){ Write-Host $m -ForegroundColor Red }

$cwd = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Set-Location $cwd

Write-Host "Proyecto: $cwd"

# 1) Crear venv si no existe
if (-not (Test-Path -Path $venvDir)) {
    Write-Host "Creando entorno virtual en .\$venvDir..."
    python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { Write-Err "Fallo al crear venv"; exit 1 }
    Write-Ok "venv creado"
} else {
    Write-Ok "venv ya existe"
}

# 2) Rutas
$pythonExe = Join-Path $cwd $pythonExeRel
if (-not (Test-Path $pythonExe)) {
    Write-Warn "No se encontró $pythonExe. Intentando usar 'python' del sistema."
    $pythonExe = "python"
}

# 3) Instalar requirements si pip detecta que falta streamlit
try {
    & $pythonExe -m pip show streamlit > $null 2>&1
    $streamlitMissing = $LASTEXITCODE -ne 0
} catch {
    $streamlitMissing = $true
}

if ($streamlitMissing) {
    Write-Host "Instalando dependencias desde requirements.txt (esto puede tardar)..."
    & $pythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Err "Fallo al instalar dependencias"; exit 1 }
    Write-Ok "Dependencias instaladas"
} else {
    Write-Ok "Dependencias ya instaladas (streamlit presente)"
}

# 4) Función para abrir nueva PowerShell y ejecutar un comando
function Start-NewWindow($title, $command) {
    $psCommand = "Start-Process powershell -ArgumentList '-NoExit','-Command','$command' -WindowStyle Normal"
    Write-Host "Lanzando: $title"
    Invoke-Expression $psCommand
}

# 5) Leer puertos (opcional)
$map = @{}
foreach ($entry in $ports.Split(',')){
    $parts = $entry.Split(':')
    if ($parts.Count -eq 2) { $map[$parts[0]] = $parts[1] }
}

# 6) Comandos a lanzar
if ($map.ContainsKey('api')) { $apiPort = $map['api'] } else { $apiPort = 5000 }
if ($map.ContainsKey('app')) { $appPort = $map['app'] } else { $appPort = 8502 }
if ($map.ContainsKey('monitor')) { $monitorPort = $map['monitor'] } else { $monitorPort = 8503 }
if ($map.ContainsKey('web')) { $webPort = $map['web'] } else { $webPort = 8501 }

# API via uvicorn
$apiCmd = "$pythonExe -m uvicorn api_rest:app --host 0.0.0.0 --port $apiPort"
Start-NewWindow 'API REST' $apiCmd

# Streamlit apps
$appCmd = "$pythonExe -m streamlit run app.py --server.port $appPort"
Start-NewWindow 'App Análisis' $appCmd

$monitorCmd = "$pythonExe -m streamlit run monitor_realtime.py --server.port $monitorPort"
Start-NewWindow 'Monitor RT' $monitorCmd

$webCmd = "$pythonExe -m streamlit run web_hidro_pro.py --server.port $webPort"
Start-NewWindow 'Web Pro' $webCmd

Write-Ok "Todos los procesos fueron lanzados en nuevas ventanas PowerShell." 
Write-Host "Si alguna ventana muestra error, revisa los logs y los puertos COM configurados en los scripts." 

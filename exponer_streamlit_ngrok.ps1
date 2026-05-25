param(
    [string]$AppFile = "monitor_realtime.py",
    [int]$Port = 8503,
    [string]$NgrokPath = "ngrok"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Set-Location $projectRoot

function Resolve-PythonExe {
    $venvPython = Join-Path $projectRoot 'venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return 'python'
}

function Resolve-NgrokPath {
    param([string]$Candidate)

    $paths = @(
        $Candidate,
        'C:\ngrok\ngrok.exe',
        'C:\Program Files\ngrok\ngrok.exe'
    )

    foreach ($path in $paths) {
        if (-not [string]::IsNullOrWhiteSpace($path) -and (Test-Path $path)) {
            return $path
        }
    }

    $command = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "No se encontró ngrok. Instálalo o ajusta -NgrokPath."
}

$pythonExe = Resolve-PythonExe
$ngrokExe = Resolve-NgrokPath -Candidate $NgrokPath

Write-Host "Proyecto: $projectRoot" -ForegroundColor Cyan
Write-Host "Python:   $pythonExe" -ForegroundColor Cyan
Write-Host "ngrok:    $ngrokExe" -ForegroundColor Cyan
Write-Host "App:      $AppFile" -ForegroundColor Cyan
Write-Host "Puerto:   $Port" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $projectRoot $AppFile))) {
    throw "No existe el archivo $AppFile en $projectRoot"
}

$streamlitCmd = "$pythonExe -m streamlit run `"$AppFile`" --server.port $Port"
Start-Process powershell -ArgumentList @('-NoExit', '-Command', "Set-Location '$projectRoot'; $streamlitCmd")

Start-Sleep -Seconds 4

Write-Host "Iniciando ngrok..." -ForegroundColor Green
Write-Host "Panel local: http://127.0.0.1:4040" -ForegroundColor Yellow
Write-Host "URL publica: la mostrara ngrok en esta ventana" -ForegroundColor Yellow

& $ngrokExe http $Port

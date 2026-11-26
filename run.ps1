param([string]$PythonPath = "")

$ErrorActionPreference = "Stop"
if (-not $PythonPath) {
    $PythonPath = "C:\Users\Siddhi Joshi\AppData\Local\Python\bin\python.exe"
    if (-not (Test-Path $PythonPath)) { $PythonPath = "python" }
}

$PythonMinor = [int](& $PythonPath -c "import sys; print(sys.version_info.minor)")
$Requirements = "requirements.txt"
$VenvDirectory = ".venv-full"
if ($PythonMinor -gt 12) {
    $Requirements = "requirements-lite.txt"
    $VenvDirectory = ".venv"
    Write-Warning "Python 3.13+ does not yet have the widest ML package support. Starting MeetMind in demo mode. Use Python 3.11/3.12 or Docker for faster-whisper and Kokoro."
}
$InstallMarker = Join-Path $VenvDirectory ".installed"

if (-not (Test-Path $VenvDirectory)) {
    & $PythonPath -m venv $VenvDirectory
}

$VenvPython = Join-Path $PWD "$VenvDirectory\Scripts\python.exe"
if (-not (Test-Path $InstallMarker)) {
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r $Requirements
    New-Item -ItemType File -Path $InstallMarker -Force | Out-Null
}

& $VenvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


# serve.ps1 - Launcher for Qualix AI Decoupled FastAPI + Streamlit App

$PythonPath = "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $PythonPath)) {
    $wherePython = Get-Command python -ErrorAction SilentlyContinue
    if ($wherePython) {
        $PythonPath = $wherePython.Source
    } else {
        Write-Error "Python 3.11 was not found at $PythonPath or in system PATH. Please ensure Python is installed."
        Exit 1
    }
}

Write-Host "Using Python at: $PythonPath"

# 1. Kill any existing processes holding port 8000 or 8080
Write-Host "Checking for existing processes on ports 8000 and 8080..."
$proc8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($proc8000) {
    Write-Host "Stopping process $proc8000 holding port 8000..."
    Stop-Process -Id $proc8000 -Force -ErrorAction SilentlyContinue
}
$proc8080 = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($proc8080) {
    Write-Host "Stopping process $proc8080 holding port 8080..."
    Stop-Process -Id $proc8080 -Force -ErrorAction SilentlyContinue
}

# 2. Create Virtual Environment if not exists
$VenvPath = Join-Path (Get-Location) ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating Python Virtual Environment at $VenvPath..."
    & $PythonPath -m venv .venv
}

# 3. Install/Upgrade dependencies
$PipPath = Join-Path $VenvPath "Scripts\pip.exe"
Write-Host "Installing/Upgrading requirements from requirements.txt..."
& $PipPath install --upgrade pip
& $PipPath install -r requirements.txt

# 4. Launch unified runner script
Write-Host "Starting Qualix AI Platform..."
& "$VenvPath\Scripts\python.exe" run.py

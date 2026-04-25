param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$backendLog = Join-Path $projectRoot "backend-uvicorn.log"
$backendErrLog = Join-Path $projectRoot "backend-uvicorn.err.log"
$frontendLog = Join-Path $projectRoot "frontend\frontend-vite.log"
$frontendErrLog = Join-Path $projectRoot "frontend\frontend-vite.err.log"

function Stop-PortProcess {
    param([int]$Port)

    $pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($pidValue in $pids) {
        if ($pidValue) {
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-Backend {
    if (-not (Test-Path $pythonExe)) {
        throw "Python virtual environment not found at $pythonExe"
    }

    Stop-PortProcess -Port 8000
    $backendArgs = @("-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8000")
    $backendProcess = Start-Process -FilePath $pythonExe `
        -ArgumentList $backendArgs `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendErrLog `
        -PassThru

    Write-Host "Backend started on http://127.0.0.1:8000 (PID $($backendProcess.Id))"
}

function Start-Frontend {
    Stop-PortProcess -Port 5173
    $frontendDir = Join-Path $projectRoot "frontend"
    $frontendArgs = @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173")
    $frontendProcess = Start-Process -FilePath "npm.cmd" `
        -ArgumentList $frontendArgs `
        -WorkingDirectory $frontendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $frontendLog `
        -RedirectStandardError $frontendErrLog `
        -PassThru

    Write-Host "Frontend started on http://127.0.0.1:5173 (PID $($frontendProcess.Id))"
}

if (-not $FrontendOnly) {
    Start-Backend
}

if (-not $BackendOnly) {
    Start-Frontend
}

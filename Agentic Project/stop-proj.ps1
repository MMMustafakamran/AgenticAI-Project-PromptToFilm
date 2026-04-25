$ErrorActionPreference = "Stop"

function Stop-PortProcess {
    param([int]$Port)

    $pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    if (-not $pids) {
        Write-Host "No listening process found on port $Port"
        return
    }

    foreach ($pidValue in $pids) {
        if ($pidValue) {
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped PID $pidValue on port $Port"
        }
    }
}

Stop-PortProcess -Port 8000
Stop-PortProcess -Port 5173

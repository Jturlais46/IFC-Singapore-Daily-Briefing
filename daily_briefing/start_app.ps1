$ErrorActionPreference = "Stop"

try {
    Write-Host "Starting IFC Daily Briefing Tool..." -ForegroundColor Cyan

    # Determine Python executable
    $PYTHON = "python"
    if (!(Get-Command "python" -ErrorAction SilentlyContinue)) {
        if (Get-Command "py" -ErrorAction SilentlyContinue) {
            $PYTHON = "py"
            Write-Host "Using 'py' launcher..." -ForegroundColor DarkGray
        }
        else {
            throw "Python is not installed or not in your PATH. Please install Python 3.10+ and check 'Add to PATH'."
        }
    }

    # 1. Kill anything on port 8000
    $procIdsOnPort = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $procIdsOnPort) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "Killed process $procId on port 8000" -ForegroundColor DarkGray
        } catch {}
    }

    # 2. Kill orphan python/uvicorn processes associated with this app
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*main:app*" } | ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "Killed orphan uvicorn process $($_.ProcessId)" -ForegroundColor DarkGray
        } catch {}
    }
    # -----------------------------------------------

    # Check if requirements installed (simple check)
    if (!(Get-Command "uvicorn" -ErrorAction SilentlyContinue)) {
        Write-Host "First run detected. Installing dependencies..." -ForegroundColor Yellow
        & $PYTHON -m pip install -r requirements.txt
        & $PYTHON -m playwright install chromium chrome
    }

    # Navigate to backend
    Set-Location "$PSScriptRoot\backend"

    Write-Host "`n--- SELF-HEALING GUARDRAIL ACTIVE ---" -ForegroundColor Green
    Write-Host "Monitoring server at http://127.0.0.1:8000/health" -ForegroundColor Cyan
    Write-Host "The server will automatically restart if it crashes or hangs." -ForegroundColor Gray
    
    $failureCount = 0
    $maxFailures = 2 # Restart after 2 missed health checks (20 seconds)

    while ($true) {
        # Check if port 8000 is listening
        $isListening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
        
        if (!$isListening) {
            Write-Host "Server port 8000 is not active. Starting server..." -ForegroundColor Yellow
            Start-Process -FilePath $PYTHON -ArgumentList "-m uvicorn main:app --reload --host 127.0.0.1 --port 8000" -WindowStyle Hidden
            Start-Sleep -Seconds 12 # Give it time to bind and warm up AI
        }

        # Health Check
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                # Success
                if ($failureCount -gt 0) { Write-Host "Server recovered!" -ForegroundColor Green }
                $failureCount = 0
            } else {
                throw "Bad status code: $($resp.StatusCode)"
            }
        }
        catch {
            $failureCount++
            Write-Host "Health check failed ($failureCount/$maxFailures): $($_.Exception.Message)" -ForegroundColor Red
            
            if ($failureCount -ge $maxFailures) {
                Write-Host "Server is unhealthy. Performing Hard Restart..." -ForegroundColor Red
                
                # Hard Cleanup
                $procIdsToKill = @()
                $procIdsToKill += Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
                $procIdsToKill += Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
                    try { $_.CommandLine -like "*uvicorn*" } catch { $false }
                } | Select-Object -ExpandProperty Id
                
                foreach ($id in ($procIdsToKill | Select-Object -Unique)) {
                    if ($id) {
                        try { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } catch {}
                    }
                }
                
                $failureCount = 0
                Start-Sleep -Seconds 2
            }
        }

        Start-Sleep -Seconds 10
    }
}
catch {
    Write-Host "AN ERROR OCCURRED IN GUARDRAIL:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    Write-Host "`n"
    Read-Host "Monitoring stopped. Press Enter to exit..."
}

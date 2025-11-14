# Restart Dashboard Script
# Kills existing dashboard process and starts a new one in background

Write-Host "Stopping any existing dashboard processes..." -ForegroundColor Yellow

# Kill any running Python processes (dashboard)
Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*start_dashboard.py*" 
} | Stop-Process -Force

Start-Sleep -Seconds 2

Write-Host "Starting dashboard in background..." -ForegroundColor Green

# Start dashboard in a new PowerShell window that stays open
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\venv\Scripts\python.exe start_dashboard.py"

Write-Host "Dashboard started! Check the new PowerShell window for output." -ForegroundColor Cyan
Write-Host "Dashboard should be available at: http://localhost:8000" -ForegroundColor Green

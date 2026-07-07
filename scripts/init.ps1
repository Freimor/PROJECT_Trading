# PROJECT Trading — первичная настройка (Windows PowerShell)
# Запуск: .\scripts\init.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== PROJECT Trading — init ===" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — edit N8N_PASSWORD before production use."
}

Write-Host "Starting Docker services..."
docker compose up -d --build

Write-Host "Waiting for db-api..."
$retries = 30
for ($i = 0; $i -lt $retries; $i++) {
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2
        if ($r.status -eq "ok") { break }
    } catch { Start-Sleep -Seconds 2 }
}

Write-Host "DB health: $(Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress)"

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. docker exec -it trading-ollama ollama pull qwen3.5:9b"
Write-Host "  2. Open http://localhost:5678 and import workflows from n8n_automation/workflows/shared/"
Write-Host "  3. Set Error Workflow to shared-global-error-handler"
Write-Host "  4. Activate shared-health-check"
Write-Host "  6. Smoke test: docker exec trading-db-api python smoke_test.py"

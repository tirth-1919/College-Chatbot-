[CmdletBinding()]
param(
    [string]$StartupScript = './user.py',
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$healthUrl = "http://localhost:$Port/health"
$startupPath = Join-Path $ProjectRoot $StartupScript
function Test-Healthy {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
        return $r.StatusCode -ge 200 -and $r.StatusCode -lt 300
    }
    catch { return $false }
}

if (-not (Test-Path $startupPath)) {
    Write-Error "Existing user startup script was not found: $startupPath"
    exit 1
}

if (-not (Test-Healthy)) {
    Write-Host '[AIT_STARTING] Starting the existing AIT application startup mechanism...' -ForegroundColor Cyan
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error 'Python was not found on PATH. Start the existing user application manually with: python user.py'
        exit 1
    }
    $appProcess = Start-Process -FilePath $python.Source -ArgumentList @($startupPath) -WorkingDirectory $ProjectRoot -PassThru
    $deadline = (Get-Date).AddMinutes(2)
    while ((Get-Date) -lt $deadline -and -not (Test-Healthy)) {
        if ($appProcess.HasExited) {
            Write-Error "The existing startup script exited with code $($appProcess.ExitCode) before the health endpoint became ready."
            exit 1
        }
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Healthy)) {
        Write-Error "AIT server did not become healthy at $healthUrl within two minutes."
        exit 1
    }
}
else {
    Write-Host '[AIT_SERVER_RUNNING] Reusing the healthy existing AIT server; no duplicate backend started.' -ForegroundColor Green
}

Write-Host '[AIT_READY] Starting optional ngrok access...' -ForegroundColor Green
try {
    & (Join-Path $ProjectRoot 'start-ngrok.ps1') -Port $Port
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    if ($appProcess -and -not $appProcess.HasExited) {
        Write-Host 'Stopping the AIT process started by start-public.ps1...' -ForegroundColor Yellow
        Stop-Process -Id $appProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

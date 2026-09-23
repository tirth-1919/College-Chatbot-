[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$LocalHost = 'localhost',
    [string]$NgrokDomain = $env:NGROK_DOMAIN
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalUrl = "http://$LocalHost`:$Port"
$HealthUrl = "$LocalUrl/health"

function Write-Status([string]$Code, [string]$Message, [ConsoleColor]$Color = [ConsoleColor]::Gray) {
    Write-Host "[$Code] $Message" -ForegroundColor $Color
}

function Test-AitHealth {
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
    } catch {
        return $false
    }
}

function Get-NgrokCommand {
    $command = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $commonPaths = @(
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\ngrok.exe",
        "$env:ProgramFiles\ngrok\ngrok.exe",
        "$env:ChocolateyInstall\bin\ngrok.exe"
    )
    foreach ($path in $commonPaths) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    return $null
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host 'AIT AI ASSISTANT - NGROK PUBLIC ACCESS' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "AIT LOCAL:    $LocalUrl"
Write-Host "AIT HEALTH:   $HealthUrl"
Write-Host ''

$NgrokExe = Get-NgrokCommand
if (-not $NgrokExe) {
    Write-Status 'NGROK_NOT_INSTALLED' 'ngrok was not found on PATH.' Red
    Write-Host 'Install the official agent with:' -ForegroundColor Yellow
    Write-Host '  winget install ngrok -s msstore' -ForegroundColor Yellow
    Write-Host 'Then authenticate once with:' -ForegroundColor Yellow
    Write-Host '  ngrok config add-authtoken "<YOUR_AUTHTOKEN>"' -ForegroundColor Yellow
    exit 1
}

Write-Status 'NGROK_INSTALLED' "Using $NgrokExe" Green
if (-not (Test-AitHealth)) {
    Write-Status 'AIT_SERVER_NOT_RUNNING' "No healthy AIT server responded at $HealthUrl." Red
    Write-Host 'Start the existing AIT application first, then run this script again.' -ForegroundColor Yellow
    Write-Host 'This script will not launch a duplicate backend.' -ForegroundColor Yellow
    exit 1
}
Write-Status 'AIT_SERVER_RUNNING' 'The local AIT health endpoint is responding.' Green
$ConfigCheck = & $NgrokExe config check 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status 'NGROK_NOT_AUTHENTICATED' 'ngrok configuration is missing or invalid.' Red
    Write-Host (($ConfigCheck | Out-String).Trim()) -ForegroundColor Yellow
    Write-Host 'Authenticate with: ngrok config add-authtoken "<YOUR_AUTHTOKEN>"' -ForegroundColor Yellow
    exit 1
}

$arguments = @('http', "$Port", '--log=stdout')
if ($NgrokDomain) { $arguments += @('--domain', $NgrokDomain) }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $NgrokExe
$psi.Arguments = ($arguments | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
$psi.WorkingDirectory = $ProjectRoot
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
try {
    [void]$process.Start()
    $publicUrl = $null
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline -and -not $process.HasExited) {
        Start-Sleep -Milliseconds 500
        try {
            $tunnels = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -UseBasicParsing -TimeoutSec 2
            $publicUrl = @($tunnels.tunnels | Where-Object { $_.public_url -like 'https://*' } | Select-Object -First 1 -ExpandProperty public_url)
            if ($publicUrl) { break }
        } catch { }
    }

    if ($process.HasExited) {
        $safeError = (($process.StandardError.ReadToEnd() + "`n" + $process.StandardOutput.ReadToEnd()).Trim())
        Write-Status 'NGROK_FAILED' $(if ($safeError) { $safeError } else { 'ngrok exited before creating a tunnel.' }) Red
        exit 1
    }

    if ($publicUrl) {
        Write-Status 'NGROK_STARTED' 'Tunnel is running.' Green
        Write-Host ''
        Write-Host '============================================================' -ForegroundColor Green
        Write-Host 'AIT LOCAL:   ' -NoNewline; Write-Host $LocalUrl -ForegroundColor White
        Write-Host 'AIT HEALTH:  ' -NoNewline; Write-Host $HealthUrl -ForegroundColor White
        Write-Host 'AIT PUBLIC:  ' -NoNewline; Write-Host $publicUrl -ForegroundColor Green
        Write-Host 'PUBLIC HEALTH:' -NoNewline; Write-Host "$publicUrl/health" -ForegroundColor Green
        Write-Host '============================================================' -ForegroundColor Green
    } else {
        Write-Status 'NGROK_STARTED' 'Tunnel is running, but its HTTPS URL could not be detected automatically.' Yellow
        Write-Host 'Open http://127.0.0.1:4040/status or inspect the ngrok dashboard for the URL.' -ForegroundColor Yellow
    }

    Write-Host 'Press Ctrl+C to stop the tunnel.' -ForegroundColor Yellow
    while (-not $process.HasExited) {
        Start-Sleep -Seconds 1
        if (-not $publicUrl) {
            try { $publicUrl = @((Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels').tunnels | Where-Object { $_.public_url -like 'https://*' } | Select-Object -First 1 -ExpandProperty public_url) } catch { }
        }
    }
} finally {
    if ($process -and -not $process.HasExited) { $process.Kill() }
    if ($process) { $process.Dispose() }
}

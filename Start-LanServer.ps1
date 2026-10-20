<#
.SYNOPSIS
    Secure LAN Chat & File Sharing — Windows 11 PowerShell Launcher
.DESCRIPTION
    Launches the production single-origin server, inspects local network IP addresses,
    and checks Windows Firewall status for inbound port 8000.
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host " SECURE LAN CHAT & FILE SHARING — Windows 11 PowerShell Launcher" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python installation
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "[OK] Python detected: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python was not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

# 2. Check compiled frontend dist
$distPath = Join-Path $ScriptDir "frontend\dist\index.html"
if (-not (Test-Path $distPath)) {
    Write-Host "[INFO] frontend/dist/index.html not found. Building frontend..." -ForegroundColor Yellow
    Push-Location (Join-Path $ScriptDir "frontend")
    try {
        & npm run build
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[OK] Production frontend bundle verified at frontend/dist" -ForegroundColor Green
}

# 3. Check Windows Firewall rule for Port 8000
try {
    $existingRules = Get-NetFirewallRule -DisplayName "*Secure LAN Chat*" -ErrorAction SilentlyContinue
    if ($existingRules) {
        Write-Host "[OK] Windows Firewall rule detected for Secure LAN Chat." -ForegroundColor Green
    } else {
        Write-Host "[NOTICE] No dedicated Windows Firewall rule found for port $Port." -ForegroundColor Yellow
        Write-Host "If second devices cannot connect, run this in an Administrator PowerShell window:" -ForegroundColor Gray
        Write-Host "New-NetFirewallRule -DisplayName 'Secure LAN Chat' -Direction Inbound -LocalPort $Port -Protocol TCP -Action Allow -Profile Private" -ForegroundColor White
    }
} catch {
    # Non-elevated PowerShell may fail to query firewall rules; non-fatal
    Write-Host "[INFO] Firewall rule query skipped (run as Admin if diagnosing network connection)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Starting server on $HostAddress`:$Port..." -ForegroundColor Cyan
Write-Host ""

$env:HOST = $HostAddress
$env:PORT = $Port.ToString()

try {
    & python run_server.py
} catch {
    Write-Host "`nServer terminated: $_" -ForegroundColor Yellow
}

# ============================================================================
#  AphidZ — START (one click).  Run as Administrator.
#  - redirects api-rejoin.pebletz.xyz -> 127.0.0.1 (hosts)
#  - launches the local auth/heartbeat emulator on :443
#  - prints the inject steps
# ============================================================================
$ErrorActionPreference = "Stop"

# self-elevate
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$hosts = "$env:WINDIR\System32\drivers\etc\hosts"
$line  = "127.0.0.1 api-rejoin.pebletz.xyz"

# 1. hosts redirect (idempotent)
$cur = Get-Content $hosts -ErrorAction SilentlyContinue
if ($cur -notmatch "api-rejoin\.pebletz\.xyz") {
    Add-Content $hosts "`r`n# AphidZ emulator`r`n$line"
    Write-Host "[+] hosts: added  $line" -ForegroundColor Green
} else {
    Write-Host "[=] hosts: api-rejoin.pebletz.xyz already redirected" -ForegroundColor DarkGray
}
ipconfig /flushdns | Out-Null

# 2. find python
$py = $null
foreach ($c in @('python','python3','py')) {
    $p = (Get-Command $c -ErrorAction SilentlyContinue)
    if ($p) { $py = $p.Source; break }
}
if (-not $py) { Write-Host "ERROR: Python not found on PATH." -ForegroundColor Red; Read-Host "Enter"; exit 1 }

# 3. launch emulator in its own window
$emu = Join-Path $here "emulator.py"
Write-Host "[+] starting emulator ($py)" -ForegroundColor Green
Start-Process $py -ArgumentList "`"$emu`"" -WorkingDirectory $here

Start-Sleep -Milliseconds 800
Write-Host ""
Write-Host "  ===== READY =====" -ForegroundColor Cyan
Write-Host "  Emulator running in its own window (keep it open)." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Now, in order:" -ForegroundColor Yellow
Write-Host "   1. Launch PixelWorlds with  -force-d3d11"
Write-Host "   2. Inject  WinHttpRelax.dll      (from Downloads)"
Write-Host "   3. Inject  AphidZ_CLEAN.dll      (from Downloads - the CLEAN one)"
Write-Host "   4. In AphidZ login, type anything as the key and log in"
Write-Host "   5. Toggle fly / features"
Write-Host ""
Write-Host "  The emulator window logs every request (start/heartbeat/command)." -ForegroundColor DarkGray
Write-Host "  When done, run  STOP_AphidZ.ps1  to remove the hosts redirect." -ForegroundColor DarkGray
Write-Host ""
Read-Host "Press Enter to close this window (emulator keeps running)"

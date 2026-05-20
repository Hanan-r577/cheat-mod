# ============================================================================
#  AphidZ — STOP / cleanup.  Run as Administrator.
#  Removes the hosts redirect and stops the emulator.
# ============================================================================
$ErrorActionPreference = "SilentlyContinue"

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$hosts = "$env:WINDIR\System32\drivers\etc\hosts"
$lines = Get-Content $hosts
$keep  = $lines | Where-Object { $_ -notmatch "api-rejoin\.pebletz\.xyz" -and $_ -notmatch "^# AphidZ emulator$" }
Set-Content -Path $hosts -Value $keep -Encoding ASCII
ipconfig /flushdns | Out-Null
Write-Host "[+] hosts: api-rejoin.pebletz.xyz redirect removed" -ForegroundColor Green

# stop the emulator (python process serving on :443 from our folder)
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='python3.exe' OR Name='py.exe'" |
    Where-Object { $_.CommandLine -match "emulator\.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host "[+] emulator stopped (PID $($_.ProcessId))" -ForegroundColor Green }

Write-Host ""
Write-Host "  AphidZ traffic now goes to the real server again." -ForegroundColor Cyan
Read-Host "Press Enter"

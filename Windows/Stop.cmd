@echo off
REM Open the Windows folder, then double-click this file to stop the local app.
cd /d "%~dp0.."
echo Stopping Due Diligence Workstation...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo Done. Port 8765 should be free.
if not defined GITHUB_ACTIONS pause

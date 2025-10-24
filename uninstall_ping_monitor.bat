@echo on
setlocal
schtasks /Delete /TN "PingMonitor (UserTray)" /F >nul 2>&1
rmdir /S /Q "%LOCALAPPDATA%\PingMonitor" 2>nul
echo [✓] Uninstalled.
pause
endlocal

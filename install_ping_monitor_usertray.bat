@echo on
setlocal
set "APPNAME=PingMonitor (UserTray)"
set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"

:: Stable local install folder
set "TARGET=%LOCALAPPDATA%\PingMonitor"
if not exist "%TARGET%" mkdir "%TARGET%"

echo [+] Copying files to "%TARGET%"...
copy /Y "%SRC%\ping_monitor.exe" "%TARGET%" >nul
copy /Y "%SRC%\config.json"     "%TARGET%" >nul
if exist "%SRC%\icon.ico" copy /Y "%SRC%\icon.ico" "%TARGET%" >nul

echo [+] Creating/Updating user logon task (tray visible)...
schtasks /Create ^
  /TN "%APPNAME%" ^
  /TR "\"%TARGET%\ping_monitor.exe\"" ^
  /SC ONLOGON ^
  /RL HIGHEST ^
  /F || (echo [!] Failed. Run this installer as Administrator. & pause & exit /b 1)

schtasks /Run /TN "%APPNAME%"
echo [✓] Installed (UserTray). Tray icon will appear in this user session after sign‑in.
pause
endlocal

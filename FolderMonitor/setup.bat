@echo off
set TASK_NAME=FolderMonitor
set TASK_PATH=%~dp0

echo Creating repeating task "%TASK_NAME%" (every 15 minutes)...
schtasks /create /f /sc minute /mo 15 /tn "%TASK_NAME%" /tr "wscript.exe \"%TASK_PATH%run_app.vbs\"" /rl HIGHEST

echo Creating startup task "%TASK_NAME% - Startup" (run once at boot)...
schtasks /create /f /sc onstart /tn "%TASK_NAME% - Startup" /tr "wscript.exe \"%TASK_PATH%run_app.vbs\"" /rl HIGHEST

echo Running "%TASK_NAME%" once now for testing...
wscript.exe "%TASK_PATH%run_app.vbs"

echo.
echo Installed. It will run at startup and every 15 minutes, even after reboot.
pause

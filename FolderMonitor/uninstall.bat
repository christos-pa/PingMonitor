@echo off
set TASK_NAME=FolderMonitor

echo Removing tasks...
schtasks /delete /f /tn "%TASK_NAME%"
schtasks /delete /f /tn "%TASK_NAME% - Startup"

echo Uninstalled.
pause

@echo off
REM launch_all.bat - calls the PowerShell launcher to start API + dashboards

SET PS_SCRIPT=launch_windows.ps1

REM Use PowerShell to run the script with bypassed execution policy
powershell -ExecutionPolicy Bypass -File "%~dp0%PS_SCRIPT%"

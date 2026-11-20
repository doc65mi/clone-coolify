@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-local.ps1" -OpenBrowser
if errorlevel 1 pause

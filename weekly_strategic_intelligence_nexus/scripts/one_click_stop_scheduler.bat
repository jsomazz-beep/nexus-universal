@echo off
setlocal
cd /d "%~dp0.."

echo Parando scheduler...
docker compose stop weekly-reporter-scheduler
if errorlevel 1 (
  echo Falha ao parar o scheduler.
  pause
  exit /b 1
)

echo Scheduler parado.
pause

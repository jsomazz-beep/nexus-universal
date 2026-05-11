@echo off
setlocal
cd /d "%~dp0.."

echo [1/2] Verificando Docker...
docker --version >nul 2>&1
if errorlevel 1 (
  echo Docker nao encontrado. Instale o Docker Desktop e tente novamente.
  pause
  exit /b 1
)

echo [2/2] Iniciando scheduler em background...
docker compose up -d --build weekly-reporter-scheduler
if errorlevel 1 (
  echo Falha ao iniciar o scheduler.
  pause
  exit /b 1
)

echo Scheduler iniciado com sucesso.
echo Use scripts\one_click_logs.bat para acompanhar logs.
pause

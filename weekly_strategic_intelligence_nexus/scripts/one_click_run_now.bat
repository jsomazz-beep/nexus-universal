@echo off
setlocal
cd /d "%~dp0.."

where docker >nul 2>&1
if %errorlevel% neq 0 (
  echo Docker nao encontrado no PATH.
  echo Use scripts\one_click_run_now_local.bat para executar sem Docker.
  pause
  exit /b 1
)

echo Executando rodada manual agora...
docker compose run --rm weekly-reporter
if errorlevel 1 (
  echo Execucao manual falhou.
  pause
  exit /b 1
)

echo Execucao manual concluida.
start "" "%cd%\output"
pause

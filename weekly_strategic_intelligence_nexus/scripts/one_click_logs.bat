@echo off
setlocal
cd /d "%~dp0.."

echo Mostrando logs do scheduler (Ctrl+C para sair)...
docker compose logs -f weekly-reporter-scheduler

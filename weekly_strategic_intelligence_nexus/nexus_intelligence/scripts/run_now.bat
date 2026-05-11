@echo off
cd /d "%~dp0.."
if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
if not exist ".env" copy .env.example .env
echo.
echo  Nexus Intelligence - Execucao direta (CLI)
echo.
set PYTHONPATH=src
python -m nexus.pipeline_cli %*
pause

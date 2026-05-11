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
echo  Nexus Intelligence - WebApp
echo  Abrindo em http://127.0.0.1:8788
echo.
python src\webapp.py
pause

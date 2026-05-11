@echo off
cd /d "%~dp0.."
if not exist ".venv" (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
pip install -r requirements.txt --quiet
echo Dependencias instaladas com sucesso.
pause

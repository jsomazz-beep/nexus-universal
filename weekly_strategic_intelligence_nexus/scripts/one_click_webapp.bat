@echo off
setlocal
cd /d "%~dp0.."

echo Iniciando Strategic Intelligence Reporter WebApp...

if not exist "config\config.yaml" (
  if exist "config\config.example.yaml" (
    copy /Y "config\config.example.yaml" "config\config.yaml" >nul
  ) else (
    echo config\config.example.yaml nao encontrado.
    pause
    exit /b 1
  )
)

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
  ) else (
    echo .env.example nao encontrado.
    pause
    exit /b 1
  )
)

if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if %errorlevel%==0 (
    py -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 (
    echo Falha ao criar .venv.
    pause
    exit /b 1
  )
  set "PYEXE=.venv\Scripts\python.exe"
)

%PYEXE% -m pip install -r requirements.txt >nul
if errorlevel 1 (
  echo Falha ao instalar dependencias.
  pause
  exit /b 1
)

echo WebApp embarcado disponivel em: http://127.0.0.1:8787
%PYEXE% src/run_embedded_webapp.py

pause

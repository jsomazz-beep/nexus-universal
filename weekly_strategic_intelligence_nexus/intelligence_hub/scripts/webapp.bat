@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0.."

echo.
echo  +--------------------------------------------------+
echo  ^|  Intelligence Hub v2.0 - Web App                 ^|
echo  ^|  Abrindo em http://127.0.0.1:8787               ^|
echo  +--------------------------------------------------+
echo.

:: ── Config e .env ──────────────────────────────────────────────────────
if not exist "config\config.yaml" (
  if exist "config\config.example.yaml" (
    echo [setup] Criando config\config.yaml...
    copy /Y "config\config.example.yaml" "config\config.yaml" >nul
  )
)
if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
  )
)

:: ── Localiza Python ────────────────────────────────────────────────────
if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
  goto :install
)

echo [setup] Procurando Python...
set "BASEPY="
where py >nul 2>&1
if %errorlevel%==0 ( set "BASEPY=py" & goto :found_py )
where python >nul 2>&1
if %errorlevel%==0 ( set "BASEPY=python" & goto :found_py )
where python3 >nul 2>&1
if %errorlevel%==0 ( set "BASEPY=python3" & goto :found_py )

echo [ERRO] Python nao encontrado. Instale Python 3.10+ em https://python.org
pause & exit /b 1

:found_py
echo [setup] Criando ambiente virtual .venv com %BASEPY%...
%BASEPY% -m venv .venv
if errorlevel 1 ( echo [ERRO] Falha ao criar .venv. & pause & exit /b 1 )
set "PYEXE=.venv\Scripts\python.exe"

:install
echo [setup] Instalando/verificando dependencias...
"%PYEXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [AVISO] Alguma dependencia pode ter falhado. Continuando...
)

echo.
echo [OK] Iniciando servidor web em http://127.0.0.1:8787
echo      Pressione Ctrl+C para parar.
echo.

"%PYEXE%" src\webapp.py --host 127.0.0.1 --port 8787
if errorlevel 1 (
  echo.
  echo [ERRO] O servidor encerrou com erro. Verifique a mensagem acima.
)

pause

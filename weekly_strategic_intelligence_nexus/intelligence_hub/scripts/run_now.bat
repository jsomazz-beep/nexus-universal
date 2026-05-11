@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0.."

echo.
echo  +--------------------------------------------------+
echo  ^|  Intelligence Hub v2.0 - Executar Agora          ^|
echo  +--------------------------------------------------+
echo.

:: ── Config e .env ──────────────────────────────────────────────────────
if not exist "config\config.yaml" (
  if exist "config\config.example.yaml" (
    echo [setup] Criando config\config.yaml a partir do exemplo...
    copy /Y "config\config.example.yaml" "config\config.yaml" >nul
  ) else (
    echo [ERRO] config\config.example.yaml nao encontrado.
    pause & exit /b 1
  )
)

if not exist ".env" (
  if exist ".env.example" (
    echo [setup] Criando .env a partir do exemplo...
    copy /Y ".env.example" ".env" >nul
  )
)

:: ── Localiza Python ────────────────────────────────────────────────────
if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
  goto :run
)

echo [setup] Ambiente virtual nao encontrado. Procurando Python...

set "BASEPY="
where py >nul 2>&1
if %errorlevel%==0 ( set "BASEPY=py" & goto :found_py )
where python >nul 2>&1
if %errorlevel%==0 ( set "BASEPY=python" & goto :found_py )
where python3 >nul 2>&1
if %errorlevel%==0 ( set "BASEPY=python3" & goto :found_py )

echo [ERRO] Python nao encontrado no PATH.
echo        Instale Python 3.10+ em https://python.org e tente novamente.
pause & exit /b 1

:found_py
echo [setup] Python encontrado: %BASEPY%
echo [setup] Criando ambiente virtual .venv...
%BASEPY% -m venv .venv
if errorlevel 1 (
  echo [ERRO] Falha ao criar .venv. Verifique sua instalacao de Python.
  pause & exit /b 1
)
set "PYEXE=.venv\Scripts\python.exe"

:run
echo [setup] Instalando/verificando dependencias...
"%PYEXE%" -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo [AVISO] Algumas dependencias podem nao ter instalado corretamente.
  echo         Continuando mesmo assim...
)

echo.
echo [OK] Iniciando coleta de noticias...
echo.

"%PYEXE%" src\main.py --config config\config.yaml --env-file .env --open %*

if errorlevel 1 (
  echo.
  echo [ERRO] A execucao falhou. Verifique o log acima.
  pause & exit /b 1
)

echo.
echo [OK] Concluido! O relatorio foi aberto no navegador.
pause

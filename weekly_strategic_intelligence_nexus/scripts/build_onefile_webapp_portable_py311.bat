@echo off
setlocal
cd /d "%~dp0.."

set "APP_NAME=StrategicIntelligenceWebApp"
set "OUT_EXE=dist\%APP_NAME%.exe"
set "VENV_DIR=.venv311_portable"
set "PYEXE=%VENV_DIR%\Scripts\python.exe"
set "ROOT=%cd%"

echo ================================================
echo Build portavel (.exe) com Python oficial 3.11
echo ================================================
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python Launcher ^(py^) nao encontrado.
  echo Instale Python oficial 3.11 x64 de https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

py -3.11 -V >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python 3.11 nao encontrado no launcher ^(py -3.11^).
  echo Instale Python oficial 3.11 x64 e tente novamente.
  pause
  exit /b 1
)

echo Encerrando instancia anterior do app ^(se aberta^)...
taskkill /F /IM "%APP_NAME%.exe" >nul 2>&1
ping -n 2 127.0.0.1 >nul

if exist "%OUT_EXE%" (
  echo Removendo executavel antigo...
  powershell -NoProfile -Command "try { Remove-Item -LiteralPath '%OUT_EXE%' -Force -ErrorAction Stop } catch { exit 1 }"
  if errorlevel 1 (
    echo ERRO: Nao foi possivel remover %OUT_EXE%.
    echo Feche o app, pause o OneDrive para esta pasta e rode novamente.
    pause
    exit /b 1
  )
)

if not exist "%PYEXE%" (
  echo Criando ambiente virtual dedicado em %VENV_DIR%...
  py -3.11 -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo ERRO: Falha ao criar venv com Python 3.11.
    pause
    exit /b 1
  )
)

echo Atualizando ferramentas base...
"%PYEXE%" -m pip install --upgrade pip setuptools wheel >nul
if errorlevel 1 (
  echo ERRO: Falha ao atualizar pip/setuptools/wheel.
  pause
  exit /b 1
)

echo Instalando dependencias do projeto...
"%PYEXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERRO: Falha ao instalar requirements.txt.
  pause
  exit /b 1
)

echo Instalando PyInstaller...
"%PYEXE%" -m pip install pyinstaller
if errorlevel 1 (
  echo ERRO: Falha ao instalar PyInstaller.
  pause
  exit /b 1
)

echo Gerando executavel...
set "PYTHONNOUSERSITE=1"
"%PYEXE%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --paths src ^
  --name %APP_NAME% ^
  --distpath dist ^
  --workpath build\py311 ^
  --specpath build\py311 ^
  --add-data "%ROOT%\src\news_reporter\templates;news_reporter\templates" ^
  --add-data "%ROOT%\config\config.example.yaml;config" ^
  --add-data "%ROOT%\.env.example;." ^
  packaged_webapp_launcher.py

if errorlevel 1 (
  echo ERRO: Build falhou.
  pause
  exit /b 1
)

if not exist "%OUT_EXE%" (
  echo ERRO: Build terminou sem gerar %OUT_EXE%.
  pause
  exit /b 1
)

echo.
echo Build concluido com sucesso.
echo Executavel: %OUT_EXE%
echo.
pause

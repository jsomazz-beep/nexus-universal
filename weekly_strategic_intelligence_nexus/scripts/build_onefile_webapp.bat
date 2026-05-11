@echo off
setlocal
cd /d "%~dp0.."

echo Gerando executavel unico (one-file) do WebApp...
set "APP_NAME=StrategicIntelligenceWebApp"
set "OUT_EXE=dist\%APP_NAME%.exe"

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

%PYEXE% -m pip install pyinstaller >nul
if errorlevel 1 (
  echo Falha ao instalar pyinstaller.
  pause
  exit /b 1
)

echo Encerrando instancia anterior do app (se aberta)...
taskkill /F /IM "%APP_NAME%.exe" >nul 2>&1
ping -n 2 127.0.0.1 >nul

if exist "%OUT_EXE%" (
  echo Limpando executavel anterior...
  powershell -NoProfile -Command "try { Remove-Item -LiteralPath '%OUT_EXE%' -Force -ErrorAction Stop } catch { exit 1 }"
  if errorlevel 1 (
    echo Nao foi possivel substituir %OUT_EXE% - arquivo em uso ou bloqueado.
    echo Feche o app e pause sincronizacao do OneDrive para esta pasta, depois rode novamente.
    pause
    exit /b 1
  )
)

%PYEXE% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --paths src ^
  --name %APP_NAME% ^
  --add-data "src\news_reporter\templates;news_reporter\templates" ^
  --add-data "config\config.example.yaml;config" ^
  --add-data ".env.example;." ^
  packaged_webapp_launcher.py

if errorlevel 1 (
  echo Build falhou.
  pause
  exit /b 1
)

echo Build concluido.
echo Executavel: dist\StrategicIntelligenceWebApp.exe
pause

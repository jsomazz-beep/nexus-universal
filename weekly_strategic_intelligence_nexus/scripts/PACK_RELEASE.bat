@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

set "PROJECT_NAME=weekly_news_reporter"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "DIST_DIR=%cd%\dist"
set "STAGE_DIR=%DIST_DIR%\%PROJECT_NAME%_release_%STAMP%"
set "ZIP_PATH=%DIST_DIR%\%PROJECT_NAME%_release_%STAMP%.zip"

echo Criando pacote de release limpo...

if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

robocopy "%cd%" "%STAGE_DIR%" /E /NFL /NDL /NJH /NJS /NC /NS ^
 /XD ".git" ".venv" "node_modules" "logs" "output" "data" "dist" "__pycache__" ^
 /XF ".env" "*.pyc" "*.pyo" "*.pyd"

if %ERRORLEVEL% GEQ 8 (
  echo Falha ao copiar arquivos para staging.
  pause
  exit /b 1
)

for /r "%STAGE_DIR%" %%D in (__pycache__) do rmdir /s /q "%%D" >nul 2>&1

echo Gerando ZIP: %ZIP_PATH%
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGE_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"
if errorlevel 1 (
  echo Falha ao gerar arquivo ZIP.
  pause
  exit /b 1
)

echo.
echo Pacote gerado com sucesso:
echo %ZIP_PATH%
echo.
echo Conteudo excluido automaticamente: .env, logs, output, data, .venv, caches.

pause

@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

echo.
echo  +--------------------------------------------------+
echo  ^|  Intelligence Hub v2.0 - Build Executavel        ^|
echo  ^|  Gera: dist\IntelligenceHub.exe                  ^|
echo  +--------------------------------------------------+
echo.

:: Localiza Python / venv
if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
  echo [OK] Usando .venv
) else (
  where python >nul 2>&1
  if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Execute scripts\setup.bat primeiro.
    pause
    exit /b 1
  )
  set "PYEXE=python"
  echo [OK] Usando Python do sistema
)

:: Instala dependencias + PyInstaller
echo.
echo [1/4] Instalando dependencias e PyInstaller...
"%PYEXE%" -m pip install -r requirements.txt pyinstaller --quiet
if %errorlevel% neq 0 (
  echo [AVISO] Alguma dependencia pode ter falhado. Continuando...
)

:: Garante .env.example
if not exist ".env.example" (
  echo # Chaves de API opcionais > .env.example
  echo GUARDIAN_API_KEY= >> .env.example
  echo NYTIMES_API_KEY= >> .env.example
  echo NEWSAPI_KEY= >> .env.example
)

:: Encerra processo anterior se estiver rodando
echo [2/4] Limpando builds anteriores...
taskkill /F /IM IntelligenceHub.exe >nul 2>&1
timeout /t 2 /nobreak >nul

if exist "dist\IntelligenceHub.exe" del /Q "dist\IntelligenceHub.exe"
if exist "dist\IntelligenceHub.exe" (
  echo [ERRO] Nao foi possivel apagar o exe anterior. Feche-o manualmente e tente de novo.
  pause
  exit /b 1
)
if exist "build\pyinstaller" rmdir /S /Q "build\pyinstaller"

:: Compila o executavel (comando numa unica linha para evitar problemas de continuacao)
echo [3/4] Compilando executavel (pode levar 3-8 minutos)...
echo       Aguarde, PyInstaller empacotando todas as dependencias...
echo.

"%PYEXE%" -m PyInstaller intelligence_hub.spec --distpath dist --workpath build\pyinstaller --noconfirm --log-level WARN

if %errorlevel% neq 0 (
  echo.
  echo [ERRO] Build falhou. Tente rodar com --log-level INFO para mais detalhes.
  pause
  exit /b 1
)

:: Verifica resultado
echo [4/4] Verificando resultado...
if not exist "dist\IntelligenceHub.exe" (
  echo [ERRO] dist\IntelligenceHub.exe nao foi gerado.
  pause
  exit /b 1
)

for %%F in ("dist\IntelligenceHub.exe") do set "EXE_SIZE=%%~zF"
set /a EXE_MB=!EXE_SIZE! / 1048576

echo.
echo  +--------------------------------------------------+
echo  ^|  BUILD CONCLUIDO COM SUCESSO!                    ^|
echo  ^|                                                  ^|
echo  ^|  Arquivo : dist\IntelligenceHub.exe              ^|
echo  ^|  Tamanho : ~!EXE_MB! MB                              ^|
echo  ^|                                                  ^|
echo  ^|  Para usar em outro PC:                          ^|
echo  ^|  1. Copie IntelligenceHub.exe para qualquer      ^|
echo  ^|     pasta no PC destino                          ^|
echo  ^|  2. Execute com duplo clique                     ^|
echo  ^|  3. Aguarde ~10s na primeira execucao            ^|
echo  ^|  4. Acesse http://127.0.0.1:8787                 ^|
echo  +--------------------------------------------------+
echo.

set /p TEST=Testar o executavel agora? (s/n):
if /i "!TEST!"=="s" (
  echo Iniciando IntelligenceHub.exe...
  start "" "dist\IntelligenceHub.exe"
)

pause

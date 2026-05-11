@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

echo Executando rodada manual (setup automatico + execucao)...

if not exist "config\config.yaml" (
  if exist "config\config.example.yaml" (
    echo Criando config\config.yaml a partir de config.example.yaml...
    copy /Y "config\config.example.yaml" "config\config.yaml" >nul
  ) else (
    echo Arquivo config\config.example.yaml nao encontrado.
    pause
    exit /b 1
  )
)

if not exist ".env" (
  if exist ".env.example" (
    echo Criando .env a partir de .env.example...
    copy /Y ".env.example" ".env" >nul
  ) else (
    echo Arquivo .env.example nao encontrado.
    pause
    exit /b 1
  )
)

set "BASEPY="
if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if %errorlevel%==0 (
    set "BASEPY=py"
  ) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
      set "BASEPY=python"
    )
  )

  if not defined BASEPY (
    echo Python nao encontrado. Instale Python 3.11+ e tente novamente.
    pause
    exit /b 1
  )

  echo Criando ambiente virtual .venv...
  %BASEPY% -m venv .venv
  if errorlevel 1 (
    echo Falha ao criar .venv.
    pause
    exit /b 1
  )

  set "PYEXE=.venv\Scripts\python.exe"
)

echo Verificando dependencias (requirements.txt)...
%PYEXE% -m pip install -r requirements.txt >nul
if errorlevel 1 (
  echo Falha ao instalar dependencias.
  pause
  exit /b 1
)

set "STATUS=KEEP"
set "KEYWORDS_SELECTION=__KEEP__"
set "MAXNEWS_SELECTION=__KEEP__"
set "THEME_SELECTION=__KEEP__"
set "SELECTION_FILE=%TEMP%\weekly_si_popup_%RANDOM%_%RANDOM%.txt"

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\select_keywords_popup.ps1" -ResultFile "%SELECTION_FILE%" >nul

if exist "%SELECTION_FILE%" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%SELECTION_FILE%") do (
    if /I "%%A"=="STATUS" set "STATUS=%%B"
    if /I "%%A"=="KEYWORDS" set "KEYWORDS_SELECTION=%%B"
    if /I "%%A"=="MAXNEWS" set "MAXNEWS_SELECTION=%%B"
    if /I "%%A"=="THEME" set "THEME_SELECTION=%%B"
  )
  del /q "%SELECTION_FILE%" >nul 2>&1
) else (
  echo Falha ao ler selecao do popup. Mantendo parametros padrao.
)

if /I "%STATUS%"=="CANCEL" (
  echo Operacao cancelada pelo usuario.
  pause
  exit /b 0
)

if /I "%MAXNEWS_SELECTION%"=="__KEEP__" (
  set "MAXNEWS_DISPLAY=config"
) else (
  set "MAXNEWS_DISPLAY=%MAXNEWS_SELECTION%"
)
if /I "%THEME_SELECTION%"=="__KEEP__" (
  set "THEME_DISPLAY=config"
) else (
  set "THEME_DISPLAY=%THEME_SELECTION%"
)

echo Parametros aplicados:
echo   STATUS=%STATUS%
echo   KEYWORDS=%KEYWORDS_SELECTION%
echo   MAXNEWS=%MAXNEWS_DISPLAY%
echo   THEME=%THEME_DISPLAY%

set "CMD=%PYEXE% src/main.py --config config/config.yaml --env-file .env"

set "NEWS_PRIORITY_KEYWORDS="
set "NEWS_MAX_NEWS="
set "NEWS_REPORT_THEME="
if /I not "%KEYWORDS_SELECTION%"=="__KEEP__" if not "%KEYWORDS_SELECTION%"=="" (
  set "NEWS_PRIORITY_KEYWORDS=%KEYWORDS_SELECTION%"
)
if /I not "%MAXNEWS_SELECTION%"=="__KEEP__" if not "%MAXNEWS_SELECTION%"=="" (
  set "NEWS_MAX_NEWS=%MAXNEWS_SELECTION%"
)
if /I not "%THEME_SELECTION%"=="__KEEP__" if not "%THEME_SELECTION%"=="" (
  set "NEWS_REPORT_THEME=%THEME_SELECTION%"
)

echo Rodando gerador de noticias...
call !CMD!
if errorlevel 1 (
  echo Execucao manual falhou.
  pause
  exit /b 1
)

echo Execucao manual concluida.

set "LATEST_HTML="
for /f "delims=" %%F in ('dir /b /o-d "%cd%\output\weekly_report_*.html" 2^>nul') do (
  if not defined LATEST_HTML set "LATEST_HTML=%%F"
)

if defined LATEST_HTML (
  echo Abrindo HTML mais recente: %LATEST_HTML%
  start "" "%cd%\output\%LATEST_HTML%"
) else (
  echo Nenhum HTML encontrado. Abrindo pasta de saida...
  start "" "%cd%\output"
)

pause

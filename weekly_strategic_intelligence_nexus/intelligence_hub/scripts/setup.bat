@echo off
chcp 65001 >nul
title Intelligence Hub — Setup
cd /d "%~dp0.."

echo.
echo  ^|  Intelligence Hub v2.0 — Setup inicial
echo  ^|
echo  ^|  Este script cria o ambiente virtual e instala dependências.
echo.

python -m venv .venv
if errorlevel 1 (
    echo  [ERRO] Python não encontrado. Instale Python 3.10+ em https://python.org
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install -r requirements.txt

echo.
echo  Copiando arquivos de configuração...
if not exist "config\config.yaml" (
    copy config\config.example.yaml config\config.yaml
    echo  ^| config\config.yaml criado.
)
if not exist ".env" (
    copy .env.example .env
    echo  ^| .env criado.
)

echo.
echo  ====================================================
echo   Setup concluído!
echo.
echo   Próximos passos:
echo   1. Edite config\config.yaml com suas palavras-chave
echo   2. Edite .env e adicione chaves de API (opcional)
echo   3. Execute scripts\run_now.bat OU scripts\webapp.bat
echo  ====================================================
echo.
pause

@echo off
title LAY_SCORE BOT
cd /d "%~dp0"

echo.
echo ==========================================
echo   LAY_SCORE BOT - Iniciando...
echo ==========================================
echo.

:: Verifica se .env existe
if not exist .env (
    echo.
    echo ❌ ERRO: Arquivo .env nao encontrado!
    echo.
    echo Para configurar:
    echo   1. Copie .env.example para .env
    echo   2. Abra .env no editor de texto
    echo   3. Preencha com suas credenciais
    echo.
    pause
    exit /b 1
)

echo ✓ Arquivo .env encontrado
echo.

:: Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python nao encontrado!
    echo Instale Python de https://python.org e tente novamente.
    pause
    exit /b 1
)

:: Instala dependencias se necessario
echo Instalando dependencias...
pip install telethon gspread oauth2client pandas requests python-dotenv -q

echo.
echo ✓ Iniciando bot... (mantenha esta janela aberta)
echo.

python layscore_local.py

echo.
echo Bot encerrado.
pause

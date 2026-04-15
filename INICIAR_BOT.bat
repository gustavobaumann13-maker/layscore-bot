@echo off
title LAY_SCORE BOT
cd /d "%~dp0"

echo.
echo ==========================================
echo   LAY_SCORE BOT - Iniciando...
echo ==========================================
echo.

:: Carrega variaveis de ambiente do arquivo .env
echo Carregando configuracoes do .env...
if exist .env (
    for /f "delims== tokens=1,*" %%a in (.env) do (
        if not "%%a"=="" if not "%%a:~0,1%%"=="#" (
            set %%a=%%b
        )
    )
    echo ✓ Variaveis de ambiente carregadas
) else (
    echo ❌ ERRO: Arquivo .env nao encontrado!
    echo.
    echo Criar arquivo .env:
    echo 1. Copie .env.example para .env
    echo 2. Preencha com suas credenciais
    echo.
    pause
    exit /b 1
)

:: Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale Python e tente novamente.
    pause
    exit /b 1
)

:: Instala dependencias se necessario
echo Verificando dependencias...
pip install telethon gspread oauth2client pandas requests python-dotenv -q

echo.
echo Iniciando bot... (mantenha esta janela aberta)
echo.

python layscore_local.py

echo.
echo Bot encerrado.
pause

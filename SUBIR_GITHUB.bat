@echo off
chcp 65001 > nul
title SUBIR PROJETO PARA GITHUB
color 0A

echo.
echo ======================================
echo   LAY_SCORE BOT - GITHUB UPLOAD
echo ======================================
echo.

REM Configura Git
echo [1/6] Configurando identidade Git...
git config --global user.email "gustavobaumann13@gmail.com"
git config --global user.name "Gustavo Baumann"
if errorlevel 1 (
    echo ❌ Erro ao configurar Git
    pause
    exit /b 1
)
echo ✓ Identidade configurada

REM Inicializa repositório
echo [2/6] Inicializando repositório...
git init
if errorlevel 1 (
    echo ❌ Erro ao inicializar
    pause
    exit /b 1
)
echo ✓ Repositório inicializado

REM Adiciona todos os arquivos
echo [3/6] Adicionando arquivos...
git add .
if errorlevel 1 (
    echo ❌ Erro ao adicionar arquivos
    pause
    exit /b 1
)
echo ✓ Arquivos adicionados

REM Faz commit
echo [4/6] Criando commit...
git commit -m "Initial commit: LAY_SCORE Bot com Dashboard"
if errorlevel 1 (
    echo ⚠️  Aviso ao fazer commit (pode ser normal)
)
echo ✓ Commit criado

REM Configura branch main
echo [5/6] Configurando branch main...
git branch -M main
if errorlevel 1 (
    echo ❌ Erro ao configurar branch
    pause
    exit /b 1
)
echo ✓ Branch configurada

REM Adiciona remote origin
echo [6/6] Conectando ao GitHub...
git remote add origin https://github.com/gustavobaumann13-maker/layscore-bot.git
if errorlevel 1 (
    echo ⚠️  Remote pode já existir (normal)
    git remote set-url origin https://github.com/gustavobaumann13-maker/layscore-bot.git
)
echo ✓ Conectado ao GitHub

REM Faz push
echo.
echo 🚀 Fazendo PUSH para GitHub...
echo (Pode pedir login do GitHub - use seu token ou SSH)
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo ❌ ERRO ao fazer push
    echo Possível causa: autenticação do GitHub
    echo.
    echo Se pedir autenticação:
    echo 1. Use seu GitHub username: gustavobaumann13-maker
    echo 2. Use um Personal Access Token (não senha)
    echo 3. Gere em: https://github.com/settings/tokens
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo ✅ SUCESSO!
echo ======================================
echo.
echo Seu projeto está no GitHub:
echo https://github.com/gustavobaumann13-maker/layscore-bot
echo.
echo Próximos passos:
echo 1. Abra https://app.netlify.com
echo 2. Clique em "Add new site" → "Import existing project"
echo 3. Escolha GitHub e selecione "layscore-bot"
echo.
pause

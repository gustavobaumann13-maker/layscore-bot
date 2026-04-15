@echo off
title LAY_SCORE BOT - Instalando...
color 0A
echo.
echo  ================================================
echo    LAY_SCORE BOT - Instalador
echo  ================================================
echo.
echo  Instalando dependencias Python...
echo.

pip install telethon gspread oauth2client pandas requests --no-cache-dir --quiet

echo.
echo  ================================================
echo    Dependencias instaladas! Iniciando bot...
echo  ================================================
echo.
echo  Deixe essa janela aberta. O bot vai atualizar
echo  a planilha a cada 5 minutos automaticamente.
echo.
echo  Para parar: feche essa janela ou pressione Ctrl+C
echo  ================================================
echo.

python layscore_local.py

pause

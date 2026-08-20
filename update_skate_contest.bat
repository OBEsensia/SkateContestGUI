@echo off
title Update Skate Contest System
color 0B

echo ===================================================
echo       SKATE CONTEST - AUTO UPDATE TOOL
echo ===================================================
echo.

:: Verification de la presence de Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH de cette machine.
    echo Veuillez installer Python (3.9 ou superieur) pour executer la mise a jour.
    echo.
    pause
    exit /b 1
)

:: Lancement du script de mise a jour
python update.py

echo.
echo ===================================================
echo Appuyez sur une touche pour fermer cette fenetre...
pause >nul

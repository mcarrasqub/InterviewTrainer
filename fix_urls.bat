@echo off
title Lumo - Arreglar URLs
color 0A

echo.
echo ========================================
echo    🔧 ARREGLANDO CONFIGURACIÓN
echo ========================================
echo.

:: Activar entorno virtual
call lumo_env\Scripts\activate.bat

echo [1/3] Verificando archivos...
if not exist "interview_trainer\api_urls.py" (
    echo ❌ ERROR: Archivo api_urls.py no encontrado
    pause
    exit /b 1
)

echo ✅ Archivos encontrados

echo.
echo [2/3] Aplicando migraciones...
python manage.py makemigrations interview_trainer
python manage.py migrate

echo.
echo [3/3] Verificando configuración...
python manage.py check

if errorlevel 1 (
    echo ❌ Error en la verificación
    pause
    exit /b 1
)

echo.
echo ✅ Configuración arreglada exitosamente
echo.
echo 🚀 Ahora puedes ejecutar: python manage.py runserver
echo.
pause

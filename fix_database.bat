@echo off
title Lumo - Reparar Base de Datos
color 0C

echo.
echo ========================================
echo    🔧 REPARANDO BASE DE DATOS
echo ========================================
echo.

:: Verificar entorno virtual
if not exist "lumo_env\Scripts\activate.bat" (
    echo ❌ ERROR: Entorno virtual no encontrado
    echo Ejecuta primero: setup_windows.bat
    pause
    exit /b 1
)

:: Activar entorno virtual
call lumo_env\Scripts\activate.bat

echo [1/4] Eliminando migraciones anteriores (si existen)...
del /q interview_trainer\migrations\0*.py 2>nul

echo.
echo [2/4] Creando nuevas migraciones...
python manage.py makemigrations interview_trainer

echo.
echo [3/4] Aplicando migraciones a la base de datos...
python manage.py migrate

echo.
echo [4/4] Verificando que las tablas se crearon correctamente...
python manage.py shell -c "from interview_trainer.models import UserProfile; print('✅ Tablas creadas correctamente')"

if errorlevel 1 (
    echo ❌ Error verificando las tablas
    echo.
    echo SOLUCIÓN ALTERNATIVA:
    echo 1. Elimina el archivo db.sqlite3
    echo 2. Ejecuta este script nuevamente
    pause
    exit /b 1
)

echo.
echo ✅ Base de datos reparada exitosamente
echo.
echo 🚀 Ahora puedes ejecutar: run.bat
echo.
pause

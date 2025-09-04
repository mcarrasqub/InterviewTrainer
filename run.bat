@echo off
title Lumo Interview Trainer - Servidor
color 0A

echo.
echo ========================================
echo    🚀 LUMO INTERVIEW TRAINER
echo    Iniciando servidor de desarrollo...
echo ========================================
echo.

:: Verificar si el entorno virtual existe
if not exist "lumo_env\Scripts\activate.bat" (
    echo ❌ ERROR: Entorno virtual no encontrado
    echo.
    echo Ejecuta primero: setup_windows.bat
    echo.
    pause
    exit /b 1
)

:: Activar entorno virtual
call lumo_env\Scripts\activate.bat

:: Verificar si manage.py existe
if not exist "manage.py" (
    echo ❌ ERROR: manage.py no encontrado
    echo.
    echo Asegurate de estar en la carpeta correcta del proyecto
    echo.
    pause
    exit /b 1
)

:: Aplicar migraciones pendientes
echo 🔄 Verificando migraciones...
python manage.py makemigrations --dry-run --verbosity=0 > nul 2>&1
if not errorlevel 1 (
    echo 📝 Aplicando migraciones pendientes...
    python manage.py makemigrations
    python manage.py migrate
)

:: Recopilar archivos estáticos
echo 📁 Recopilando archivos estáticos...
python manage.py collectstatic --noinput --clear > nul 2>&1

echo.
echo ✅ Servidor listo para iniciar
echo.
echo 🌐 URL del servidor: http://127.0.0.1:8000
echo 🛑 Para detener: Presiona Ctrl+C
echo.
echo ========================================
echo.

:: Iniciar servidor
python manage.py runserver

echo.
echo 👋 Servidor detenido
pause

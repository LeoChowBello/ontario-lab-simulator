@echo off
echo.
echo ============================================
echo  Ontario Lab Mocklab - Universal Installer
echo ============================================
echo.

echo Step 1: Starting Docker containers...
echo   - OpenEMR database (MySQL)
echo   - OpenEMR web application
echo   - Lab simulator
echo.

docker-compose -f docker-compose-8.0.x.yml up -d

if %errorlevel% neq 0 (
    echo ERROR: Docker Compose failed. Make sure Docker is running.
    pause
    exit /b 1
)

echo.
echo Waiting 60 seconds for services to initialize...
timeout /t 60 /nobreak

echo.
echo Step 2: Configuring database and installing tests...
echo.

python3 ontario_lab_turnkey.py --install

if %errorlevel% neq 0 (
    echo ERROR: Installation failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  ✅ Installation Complete!
echo ============================================
echo.
echo OpenEMR:  http://localhost:8082
echo Mocklab:  http://localhost:5001
echo Login:    admin / pass
echo.
echo Everything is running automatically.
pause

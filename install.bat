@echo off
setlocal

echo.
echo ============================================
echo  Ontario Lab Mocklab - Universal Installer
echo ============================================
echo.

set MODE=%ONTARIO_LAB_MODE%
if "%MODE%"=="" (
    if not "%OPENEMR_ROOT%"=="" set MODE=host
    if not "%OPENEMR_SITES%"=="" set MODE=host
    if not "%OPENEMR_SQLCONF%"=="" set MODE=host
)
if "%MODE%"=="" set MODE=docker

if /I "%MODE%"=="host" goto host
if exist docker-compose-8.0.x.yml goto docker

goto host

:docker
echo Step 1: Cleaning up old containers...
docker-compose -f docker-compose-8.0.x.yml down -v 2>nul

echo Step 2: Starting Docker containers...
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
echo Step 3: Configuring database and installing tests...
echo.

docker-compose -f docker-compose-8.0.x.yml exec -T mocklab python3 /app/ontario_lab_turnkey.py --install

if %errorlevel% neq 0 (
    echo ERROR: Installation failed.
    pause
    exit /b 1
)

goto done

:host
echo Running host-based installation...
echo.
python3 ontario_lab_turnkey.py --install

if %errorlevel% neq 0 (
    echo ERROR: Installation failed.
    pause
    exit /b 1
)

goto done

:done
echo.
echo ============================================
echo  ✅ Installation Complete!
echo ============================================
echo.
echo Your healthcare IT lab is now running.
echo.
echo NEXT STEPS:
echo ============================================
echo.
echo 1. OPEN YOUR BROWSER
echo    Go to: http://YOUR.IP.ADDRESS:8082
echo.
echo 2. LOGIN
echo    Username: admin
echo    Password: pass
echo.
echo 3. CREATE A TEST PATIENT
echo    - Click "Patients" menu
echo    - Click "+ New Patient"
echo    - Fill in: John, Doe, DOB: 01/01/1990
echo    - Click "Save Patient"
echo.
echo 4. CREATE A LAB ORDER
echo    - Click the patient name
echo    - Click "Orders" or "New Order"
echo    - Search for: 3016-3 (TSH test)
echo    - Click "Save Order"
echo.
echo 5. WATCH THE MAGIC
echo    - Wait 10-15 seconds
echo    - Refresh your browser
echo    - See the result appear automatically!
echo.
echo THAT'S IT! You just used HL7 messaging like hospitals do.
echo.
echo For more help, see: INSTALL.md
echo.
pause

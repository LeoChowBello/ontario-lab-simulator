@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo.
echo ============================================
echo  Ontario Lab Simulator - Student Installer
echo ============================================
echo.
echo This installer will walk you through setup step by step.
echo If this is your first time using OpenEMR, that is completely normal.
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
echo Step 1 of 4: Checking your setup
echo.
echo   Detected mode: docker
echo   This will start the bundled Docker lab.
echo   Compose file: docker-compose-8.0.x.yml
echo.
echo What will happen next:
echo   1. OpenEMR will be prepared for the student lab workflow
echo   2. Sample lab tests will be added
echo   3. The lab order form will be softened for teaching use
echo   4. You will get a short first-login walkthrough
echo.
set /p CONTINUE=Press Enter when you are ready to continue.

echo.
echo Step 2 of 4: Cleaning up any old containers...
docker-compose -f docker-compose-8.0.x.yml down -v 2>nul

echo Step 3 of 4: Starting the Docker lab...
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
echo Step 4 of 4: Waiting for OpenEMR to finish starting...
echo   This usually takes about one minute.
echo.
timeout /t 60 /nobreak >nul

echo.
echo Configuring the student lab...
echo.
docker-compose -f docker-compose-8.0.x.yml exec -T mocklab python3 /app/ontario_lab_turnkey.py --install

if %errorlevel% neq 0 (
    echo ERROR: Installation failed.
    pause
    exit /b 1
)

goto done

:host
echo Step 1 of 4: Checking your setup
echo.
echo   Detected mode: host
echo   This will connect to OpenEMR already installed on the server.
echo.
if not "%OPENEMR_ROOT%"=="" echo   OPENEMR_ROOT detected.
if not "%OPENEMR_SITES%"=="" echo   OPENEMR_SITES detected.
if not "%OPENEMR_SQLCONF%"=="" echo   OPENEMR_SQLCONF detected.
echo.
echo What will happen next:
echo   1. OpenEMR will be prepared for the student lab workflow
echo   2. Sample lab tests will be added
echo   3. The lab order form will be softened for teaching use
echo   4. You will get a short first-login walkthrough
echo.
set /p CONTINUE=Press Enter when you are ready to continue.

echo.
echo Step 2 of 4: Preparing your existing OpenEMR install...
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
echo  Installation Complete
echo ============================================
echo.
echo Now let's do the first student login together.
echo.
echo 1. Open your browser
echo    Go to: http://YOUR.IP.ADDRESS:8082
echo.
echo 2. Sign in
echo    Username: admin
echo    Password: pass
echo.
echo 3. Find the patient area
echo    Look for Patients in the left menu
echo.
echo 4. Create a test patient
echo    First name: John
echo    Last name: Doe
echo    Date of birth: 01/01/1990
echo.
echo 5. Create a lab order
echo    Search for: 3016-3
echo    That is the TSH test
echo.
echo 6. Wait a few seconds
echo    Then refresh the page and look for the result
echo.
echo If your menus look slightly different, that is okay.
echo OpenEMR versions and themes can vary a little.
echo.
echo For more help, see: INSTALL.md
echo.
pause

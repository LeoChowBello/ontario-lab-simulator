#!/bin/bash

set -e

echo ""
echo "============================================"
echo "  Ontario Lab Simulator - Student Installer"
echo "============================================"
echo ""
echo "This installer will walk you through setup step by step."
echo "If this is your first time using OpenEMR, that is completely normal."
echo ""

pause_for_student() {
    local prompt="$1"
    echo ""
    read -r -p "$prompt" _
}

check_path() {
    local label="$1"
    local path="$2"
    if [ -e "$path" ]; then
        echo "  ✓ $label found"
    else
        echo "  - $label not checked"
    fi
}

MODE="${ONTARIO_LAB_MODE:-}"
if [ -z "$MODE" ] && { [ -n "$OPENEMR_ROOT" ] || [ -n "$OPENEMR_SITES" ] || [ -n "$OPENEMR_SQLCONF" ]; }; then
    MODE="host"
fi
if [ -z "$MODE" ]; then
    MODE="docker"
fi

COMPOSE_FILE="${ONTARIO_LAB_COMPOSE:-docker-compose-8.0.x.yml}"

echo "Step 1 of 4: Checking your setup"
echo ""
echo "  Detected mode: $MODE"
if [ "$MODE" = "host" ]; then
    echo "  This will connect to OpenEMR already installed on the server."
    [ -n "$OPENEMR_ROOT" ] && check_path "OPENEMR_ROOT" "$OPENEMR_ROOT"
    [ -n "$OPENEMR_SITES" ] && check_path "OPENEMR_SITES" "$OPENEMR_SITES"
    [ -n "$OPENEMR_SQLCONF" ] && check_path "OPENEMR_SQLCONF" "$OPENEMR_SQLCONF"
else
    echo "  This will start the bundled Docker lab."
    check_path "Compose file" "$COMPOSE_FILE"
fi

echo ""
echo "What will happen next:"
echo "  1. OpenEMR will be prepared for the student lab workflow"
echo "  2. Sample lab tests will be added"
echo "  3. The lab order form will be softened for teaching use"
echo "  4. You will get a short first-login walkthrough"
echo ""
pause_for_student "Press Enter when you are ready to continue."

if [ "$MODE" = "host" ]; then
    echo ""
    echo "Step 2 of 4: Preparing your existing OpenEMR install"
    echo ""
    python3 ontario_lab_turnkey.py --install
else
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "ERROR: $COMPOSE_FILE not found. Set ONTARIO_LAB_MODE=host for a host install."
        exit 1
    fi

    echo ""
    echo "Step 2 of 4: Starting the Docker lab"
    echo ""
    echo "  - OpenEMR database (MySQL)"
    echo "  - OpenEMR web application"
    echo "  - Lab simulator"
    echo ""
    docker-compose -f "$COMPOSE_FILE" up -d

    echo ""
    echo "Step 3 of 4: Waiting for OpenEMR to finish starting"
    echo ""
    echo "  This usually takes about one minute."
    echo "  While you wait, get your browser ready."
    echo ""
    sleep 60

    echo ""
    echo "Step 4 of 4: Configuring the student lab"
    echo ""
    docker-compose -f "$COMPOSE_FILE" exec -T mocklab python3 /app/ontario_lab_turnkey.py --install
fi

echo ""
echo "============================================"
echo "  Installation Complete"
echo "============================================"
echo ""
echo "Now let's do the first student login together."
echo ""
echo "1. Open your browser"
echo "   Go to: http://YOUR.IP.ADDRESS:8082"
echo ""
echo "2. Sign in"
echo "   Username: admin"
echo "   Password: pass"
echo ""
echo "3. Find the patient area"
echo "   Look for Patients in the left menu"
echo ""
echo "4. Create a test patient"
echo "   First name: John"
echo "   Last name: Doe"
echo "   Date of birth: 01/01/1990"
echo ""
echo "5. Create a lab order"
echo "   Search for: 3016-3"
echo "   That is the TSH test"
echo ""
echo "6. Wait a few seconds"
echo "   Then refresh the page and look for the result"
echo ""
echo "If your menus look slightly different, that is okay."
echo "OpenEMR versions and themes can vary a little."
echo ""
echo "For more help, see: INSTALL.md"
echo ""
pause_for_student "Press Enter to finish."

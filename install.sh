#!/bin/bash

set -e

echo ""
echo "============================================"
echo "  Ontario Lab Mocklab - Universal Installer"
echo "============================================"
echo ""

MODE="${ONTARIO_LAB_MODE:-docker}"
COMPOSE_FILE="${ONTARIO_LAB_COMPOSE:-docker-compose-8.0.x.yml}"

if [ "$MODE" = "host" ]; then
    echo "Running host-based installation..."
    echo ""
    python3 ontario_lab_turnkey.py --install
else
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "ERROR: $COMPOSE_FILE not found. Set ONTARIO_LAB_MODE=host for a host install."
        exit 1
    fi

    echo "Step 1: Starting Docker containers..."
    echo "   - OpenEMR database (MySQL)"
    echo "   - OpenEMR web application"
    echo "   - Lab simulator"
    echo ""

    docker-compose -f "$COMPOSE_FILE" up -d

    if [ $? -ne 0 ]; then
        echo "ERROR: Docker Compose failed. Make sure Docker is running."
        exit 1
    fi

    echo ""
    echo "Waiting 60 seconds for services to initialize..."
    sleep 60

    echo ""
    echo "Step 2: Configuring database and installing tests..."
    echo ""

    docker-compose -f "$COMPOSE_FILE" exec -T mocklab python3 /app/ontario_lab_turnkey.py --install

    if [ $? -ne 0 ]; then
        echo "ERROR: Installation failed."
        exit 1
    fi
fi

echo ""
echo "============================================"
echo "  ✅ Installation Complete!"
echo "============================================"
echo ""
echo "Your healthcare IT lab is now running."
echo ""
echo "NEXT STEPS:"
echo "============================================"
echo ""
echo "1. OPEN YOUR BROWSER"
echo "   Go to: http://YOUR.IP.ADDRESS:8082"
echo ""
echo "2. LOGIN"
echo "   Username: admin"
echo "   Password: pass"
echo ""
echo "3. CREATE A TEST PATIENT"
echo "   - Click 'Patients' menu"
echo "   - Click '+ New Patient'"
echo "   - Fill in: John, Doe, DOB: 01/01/1990"
echo "   - Click 'Save Patient'"
echo ""
echo "4. CREATE A LAB ORDER"
echo "   - Click the patient name"
echo "   - Click 'Orders' or 'New Order'"
echo "   - Search for: 3016-3 (TSH test)"
echo "   - Click 'Save Order'"
echo ""
echo "5. WATCH THE MAGIC"
echo "   - Wait 10-15 seconds"
echo "   - Refresh your browser"
echo "   - See the result appear automatically!"
echo ""
echo "THAT'S IT! You just used HL7 messaging like hospitals do."
echo ""
echo "For more help, see: INSTALL.md"
echo ""

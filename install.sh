#!/bin/bash

echo ""
echo "============================================"
echo "  Ontario Lab Mocklab - Universal Installer"
echo "============================================"
echo ""

echo "Step 1: Starting Docker containers..."
echo "   - OpenEMR database (MySQL)"
echo "   - OpenEMR web application"
echo "   - Lab simulator"
echo ""

docker-compose -f docker-compose-8.0.x.yml up -d

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

python3 ontario_lab_turnkey.py --install

if [ $? -ne 0 ]; then
    echo "ERROR: Installation failed."
    exit 1
fi

echo ""
echo "============================================"
echo "  ✅ Installation Complete!"
echo "============================================"
echo ""
echo "OpenEMR:  http://localhost:8082"
echo "Mocklab:  http://localhost:5001"
echo "Login:    admin / pass"
echo ""
echo "Everything is running automatically."

# Installation Guide - Ontario Lab Simulator v1.0

## Before You Start

**Requirements:**
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- ~5 GB disk space
- Internet connection (first run only)

**Not required:**
- Python (included in Docker)
- Database knowledge
- HL7 experience
- Any configuration

## Windows Installation

### Step 1: Download
Clone or download this repository.

### Step 2: Run Installer
1. Open File Explorer
2. Navigate to the `ontario-lab-sim` folder
3. **Double-click `install.bat`**

A console window opens. You'll see:
```
============================================
 Ontario Lab Simulator - Installer
============================================

Step 1: Starting Docker containers...
   [Progress messages...]

Waiting 60 seconds for services to initialize...
⏳ 60... 59... 58...

Step 2: Configuring database...
✅ Installation Complete!

OpenEMR:  http://localhost:8082
Login:    admin / pass

Press any key to exit...
```

### Step 3: Done!
Press any key. The console closes. Everything is running in the background.

### Step 4: Open Browser
Go to: `http://192.168.2.X:8082`

(Replace X with your computer's IP address - ask your instructor if unsure)

---

## Linux / Mac Installation

### Step 1: Download
Clone or download this repository.

### Step 2: Make Script Executable
```bash
chmod +x install.sh
```

### Step 3: Run Installer
```bash
./install.sh
```

You'll see progress messages:
```
============================================
 Ontario Lab Simulator - Installer
============================================

Starting Docker containers...
[Progress...]

Configuring database...
✅ Installation Complete!

OpenEMR:  http://YOUR.IP.ADDRESS:8082
Login:    admin / pass
```

### Step 4: Open Browser
Go to: `http://192.168.2.X:8082`

---

## First Time Using OpenEMR?

### Login
- **Username:** admin
- **Password:** pass
- Click **Login**

### Create a Test Patient
1. Click **Patients** (left menu)
2. Click **+ New Patient** (or similar)
3. Fill in:
   - First Name: John
   - Last Name: Doe
   - Date of Birth: 01/01/1990
4. Click **Save Patient**

### Create a Lab Order
1. Click patient **John Doe**
2. Click **Orders** (left menu)
3. Click **+ New Order** (or **New Procedure Order**)
4. In the search box, type: `3016-3`
5. Select **TSH** from the list
6. Fill in any required fields:
   - Date Collected: (today's date)
   - Billing Type: select any option
7. Click **Save Order** or **Submit**

### Watch the Magic
Wait 10-15 seconds. The order goes through:
1. OpenEMR writes to `/edi/orders/`
2. Mocklab reads it
3. Mocklab generates a realistic result
4. Result imported automatically
5. Appears in John Doe's chart

You can:
- **Refresh the page** to see the result
- **Click on the patient** to see it in their chart
- **Look for "Lab Results"** or **"Orders"** section

---

## Available Lab Tests

You can order any of these:

| Test Name | Code |
|-----------|------|
| WBC (White Blood Cell) | 6690-2 |
| Hemoglobin | 718-7 |
| Glucose (Fasting) | 1558-6 |
| TSH (Thyroid) | 3016-3 |
| Total Cholesterol | 2093-3 |
| Hemoglobin A1c | 4548-4 |

Just type the code or test name when creating an order.

---

## Understanding What's Happening

### The HL7 Workflow

**Order Message (ORM^O01):**
```
OpenEMR → HL7 Message → /edi/orders/0001.txt → Mocklab reads it
```

**Result Message (ORU^R01):**
```
Mocklab → HL7 Message → /edi/inbox/RES_0001.txt → Auto-importer reads it
```

**Result Imported:**
```
Auto-importer → Database → OpenEMR UI → Patient's chart
```

This is exactly how hospitals do it in real life!

---

## Troubleshooting

### "Docker command not found"
**Solution:** Install Docker Desktop or Docker Engine
- Windows/Mac: https://www.docker.com/products/docker-desktop
- Linux: `sudo apt install docker.io docker-compose`

### "Can't connect to localhost:8082"
**Solution:** Use your actual IP address
- Run: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
- Look for IP like: 192.168.2.X
- Go to: `http://192.168.2.X:8082`

### "Installation hangs"
**Solution:** Check Docker is running
- Open Docker Desktop app (Windows/Mac)
- Or run: `sudo systemctl start docker` (Linux)
- Restart: `docker-compose down` then run installer again

### "Port 8082 already in use"
**Solution:** Use a different port
1. Edit `docker-compose-8.0.x.yml`
2. Find: `8082:80`
3. Change to: `8083:80` (or any unused port)
4. Restart: `docker-compose down && docker-compose up -d`

### "I don't see the result after waiting"
**Solution:** Try these steps
1. Wait another 15 seconds
2. Refresh browser (Ctrl+R or Cmd+R)
3. Try creating another order to test
4. Check Docker is still running: `docker ps`

### "I see validation errors when creating an order"
**This is normal.** The system accepts orders even with blank fields.
Just fill in what you can and click Save.

### "Still stuck?"
Run this to check system status:
```bash
docker-compose ps
```

You should see three containers, all "Up":
- openemr-8x-1
- openemr-8x-mysql-1
- mocklab-1

If any show "Exit" or "Error", run:
```bash
docker-compose logs openemr-8x-1
```

---

## Next Steps (For Instructors)

### Modify Test Results
Edit `ontario_lab_turnkey.py`, line 55-60, to change normal ranges.

### Add More Lab Tests
Edit line 54-61 in `ontario_lab_turnkey.py` to add more LOINC codes.

### Generate Abnormal Results
Modify line 262 to force abnormal values for teaching scenarios.

### Inspect HL7 Messages
Check inside `/edi/orders/` and `/edi/inbox/` to see actual HL7 messages.

---

## What to Tell Students

1. **"Just double-click install.bat, wait 60 seconds, then open the browser."**
2. **"Create a patient, create an order, wait 15 seconds."**
3. **"The result appears automatically. That's HL7 in action."**
4. **"If something doesn't work, tell me - nothing you do will break it."**

---

## System Stops After Restart?

Run:
```bash
docker-compose up -d
```

Services restart automatically and reconnect to existing database.

---

**Questions?** Contact your instructor.

**Ontario Lab Simulator - Teaching Real Healthcare IT.** 🧪

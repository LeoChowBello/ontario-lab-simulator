# Ontario Lab Simulator v1.0

**Complete HL7 lab integration system for OpenEMR. One-click installation. No errors. No configuration.**

Students create lab orders in OpenEMR. Results appear automatically in their charts in 15 seconds.

## ✅ Installation (60 seconds)

### Windows
```
Double-click: install.bat
```

### Linux / Mac
```
./install.sh
```

Everything starts automatically. When complete, open your browser.

## 🚀 Quick Start

1. Go to: `http://192.168.2.X:8082` (use your computer's IP address)
2. Login: `admin / pass`
3. Create a patient
4. Create a lab order (e.g., TSH: `3016-3`)
5. Wait 15 seconds
6. **Result appears in patient chart** ✓

## 📚 What You're Learning

- **HL7 v2.3** - Real healthcare messaging standards
- **ORM^O01** - Lab order messages
- **ORU^R01** - Lab result messages
- **EDI** - Electronic data exchange
- **Real workflow** - How hospitals integrate labs with EMRs

## 🔧 Architecture

```
OpenEMR          MySQL         Mocklab
(order UI)  ←→  (database) ←→  (simulator)
  :8082          :3306           :5001
```

**Workflow:**
1. You create order in OpenEMR
2. HL7 message written to `/edi/orders/`
3. Mocklab reads it, generates result
4. HL7 result written to `/edi/inbox/`
5. Result auto-imported to database
6. Appears in patient chart

All automatic. Zero manual steps.

## 📖 Full Guide

See [INSTALL.md](INSTALL.md) for detailed setup and troubleshooting.

## ✨ What's Included

- OpenEMR 8.0.1 (containerized)
- MySQL database
- Mocklab HL7 simulator
- Auto-result importer
- 6 lab tests pre-configured (WBC, Hemoglobin, Glucose, TSH, Cholesterol, A1c)

## 🧪 Test the System

1. Create patient "John Doe"
2. Order "TSH" (code: 3016-3)
3. Fill in the form, click Save
4. Wait 15 seconds
5. Refresh the page
6. See result: "TSH: 2.5 mIU/L"

Done! You've just experienced a real healthcare IT workflow.

## 📞 Troubleshooting

**Containers not starting?**
- Make sure Docker is running
- Check: `docker ps`

**Can't see the result?**
- Wait 15 seconds (sometimes takes longer)
- Refresh browser page
- Check container logs: `docker logs openemr-8x-1`

**Port 8082 already in use?**
- Edit `docker-compose-8.0.x.yml`
- Change `8082:80` to `8083:80`
- Restart: `docker-compose up -d`

See [INSTALL.md](INSTALL.md) for more help.

---

**Ontario Lab Simulator - Teaching Healthcare IT.** 🧪

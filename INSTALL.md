# Installation Guide

## What is supported

This installer supports two real deployment styles:

- Docker-based OpenEMR 7.0.2+ using the bundled compose stack
- Host-based OpenEMR on Ubuntu EC2, where OpenEMR is already installed on the server

## Before you start

For Docker installs:

- Docker Desktop or Docker Engine
- Docker Compose
- About 5 GB of free disk space

For host installs:

- Python 3
- PyMySQL (`pip install pymysql`)
- Read access to the OpenEMR root or `sqlconf.php`

## Docker installation

1. Clone or download this repository.
2. Open a terminal in the repository folder.
3. Run the installer:

```bash
./install.sh
```

On Windows, double-click `install.bat`.

What happens next:

- The OpenEMR and simulator containers start
- The installer waits for the services to become ready
- The simulator container configures the OpenEMR database and order form
- The simulator starts watching the EDI folders

## Host installation on Ubuntu EC2

If OpenEMR is already installed on the server, run the simulator in host mode.

Example:

```bash
export ONTARIO_LAB_MODE=host
export OPENEMR_ROOT=/var/www/localhost/htdocs/openemr
python3 ontario_lab_turnkey.py --install
```

If your OpenEMR install lives somewhere else, you can point the simulator at:

- `OPENEMR_ROOT`
- `OPENEMR_SITES`
- `OPENEMR_SQLCONF`

Only one of those needs to be correct.

## After installation

- Log into OpenEMR with the student account for the environment
- Create a patient
- Create a lab order using one of the sample LOINC codes
- Wait a few seconds and refresh the chart
- The result should appear automatically

## What the installer changes

- Creates `orders` and `inbox` EDI folders
- Adds a lab provider record
- Adds the sample test catalog
- Relaxes the lab order form validation used in the teaching workflow

## If something goes wrong

- Make sure the OpenEMR path you provided really exists
- Make sure `sqlconf.php` is readable
- Make sure the OpenEMR database is reachable from the machine running the simulator
- For Docker installs, confirm the compose file is in the repository folder and Docker is running

## Common paths on Ubuntu

If you do not know where OpenEMR is installed, try one of these:

- `/var/www/localhost/htdocs/openemr`
- `/var/www/html/openemr`
- `/var/www/openemr`

## Summary

The goal is not "any OpenEMR ever". The goal is:

- OpenEMR 7.0.2+
- Docker sandbox installs
- Ubuntu EC2 host installs
- Minimal environment-specific tweaking

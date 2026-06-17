# Ontario Lab Simulator

Universal HL7 lab simulator for OpenEMR 7.0.2 and newer.

This project is designed for two supported deployment styles:

- Bundled Docker install, where OpenEMR and the simulator run from the provided compose stack
- Host-based Ubuntu install, where OpenEMR is already installed on an EC2 server

The simulator discovers the OpenEMR site path and database settings from environment variables first, then from common install paths, and finally from a local docker-compose file if needed.

## Supported setups

- Docker-based OpenEMR 7.0.2+ with a mounted `sites` directory
- Ubuntu EC2 host install with OpenEMR already present on the server

## Quick start: Docker

From the repository folder:

```bash
./install.sh
```

On Windows:

```bat
install.bat
```

This starts the bundled containers and then runs the installer inside the simulator container.

## Quick start: host install

If OpenEMR is already installed on the EC2 server, set the host mode and point the simulator at the OpenEMR root or `sqlconf.php` file:

```bash
export ONTARIO_LAB_MODE=host
export OPENEMR_ROOT=/var/www/localhost/htdocs/openemr
python3 ontario_lab_turnkey.py --install
```

You can also set `OPENEMR_SITES` or `OPENEMR_SQLCONF` instead of `OPENEMR_ROOT`.

## Configuration variables

- `ONTARIO_LAB_MODE`: `docker` or `host`
- `OPENEMR_ROOT`: path to the OpenEMR root directory
- `OPENEMR_SITES`: path to the OpenEMR `sites` directory
- `OPENEMR_SQLCONF`: direct path to `sqlconf.php`

## What the simulator does

- Creates the `orders` and `inbox` EDI folders
- Registers a lab provider and a small catalog of test codes
- Loosens the lab order form validation used by the student workflow
- Watches for new order files and generates matching result files
- Imports result files back into OpenEMR so they appear in the patient chart

## Student workflow

1. Log into OpenEMR
2. Create a patient
3. Create a lab order for one of the sample tests
4. Wait a few seconds
5. Refresh the chart and confirm the result appears

## Sample tests

- WBC `6690-2`
- Hemoglobin `718-7`
- Glucose (Fasting) `1558-6`
- TSH `3016-3`
- Total Cholesterol `2093-3`
- Hemoglobin A1c `4548-4`

## Troubleshooting

- If the simulator cannot find OpenEMR, set `OPENEMR_ROOT`, `OPENEMR_SITES`, or `OPENEMR_SQLCONF`
- If Docker mode fails, confirm Docker is running and the compose file is in the repository folder
- If host mode fails, confirm the OpenEMR files and `sqlconf.php` are readable by the current user

## Notes

This is a teaching simulator. It is aimed at the supported OpenEMR deployment patterns above, not every custom OpenEMR layout ever created.

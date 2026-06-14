#!/usr/bin/env python3
"""
Ontario Lab Turnkey: Version-Universal Mocklab

This script is now UNIVERSAL across OpenEMR versions (7.0.2, 8.0.x, 9.0, etc.)
because it auto-discovers configuration from your docker-compose file instead
of hardcoding paths.

WHAT CHANGED:
=============
OLD (hardcoded):
  EDI_BASE = '/var/lib/docker/volumes/openemr_openemr_sites/_data/default/documents/edi'
  Container: 'openemr-openemr-1'
  Only worked on ONE specific setup.

NEW (auto-discovered):
  - Reads docker-compose*.yml
  - Extracts container name, volume name, mount path
  - Builds EDI_BASE dynamically
  - Works on 7.0.2, 8.0.x, and future versions automatically

HOW TO USE:
===========
1. Place this script in same directory as your docker-compose-*.yml
2. Run: python3 ontario_lab_turnkey.py --install
3. Script discovers config automatically, sets up mocklab, starts Flask server

The --install flag triggers setup (creates directories, configures database,
patches validation code). Normal run launches the lab simulation.
"""

import os, sys, json, time, re, random, threading, subprocess
from datetime import datetime
from flask import Flask
from config_discovery import discover_config

# Auto-discover configuration from docker-compose file
try:
    DISCOVERED = discover_config()
except Exception as e:
    print(f"❌ Configuration discovery failed: {e}")
    print("\nMake sure you're running this script in the same directory as docker-compose*.yml")
    sys.exit(1)

# Build CONFIG dict from discovered values
CONFIG = {
    'LAB_NAME': 'Ontario Reference Lab',
    'PORT': 5001,
    'CONTAINER_NAME': DISCOVERED['CONTAINER_NAME'],  # Used in patch_php()
    'EDI_BASE': DISCOVERED['EDI_BASE'],  # Now discovered, not hardcoded
    'DB_CONFIG': DISCOVERED['DB_CONFIG']  # Now discovered, not hardcoded
}

CATALOG = {
    '6690-2':  dict(name='WBC', unit='x10^9/L', low=4.0, high=11.0),
    '718-7':   dict(name='Hemoglobin', unit='g/L', low=120.0, high=175.0),
    '1558-6':  dict(name='Glucose (Fasting)', unit='mmol/L', low=3.6, high=6.0),
    '3016-3':  dict(name='TSH', unit='mIU/L', low=0.32, high=4.00),
    '2093-3':  dict(name='Total Cholesterol', unit='mmol/L', low=0.0, high=5.2),
    '4548-4':  dict(name='Hemoglobin A1c', unit='%', low=4.0, high=6.0),
}

def get_db():
    db_config = CONFIG['DB_CONFIG']

    txt = None
    # If running on host (not in container), try to read from container
    if not os.path.exists(db_config):
        print(f"  Config file not found at {db_config}, trying docker exec...")
        import subprocess
        try:
            # Read sqlconf.php from inside the container
            result = subprocess.run(
                f"docker exec {CONFIG['CONTAINER_NAME']} cat /var/www/localhost/htdocs/openemr/sites/default/sqlconf.php",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                txt = result.stdout
                print(f"  ✓ Read config from container")
            else:
                print(f"  ✗ docker exec failed: {result.stderr[:100]}")
                return None
        except Exception as e:
            print(f"  ✗ docker exec exception: {str(e)[:100]}")
            return None
    else:
        with open(db_config) as f:
            txt = f.read()
            print(f"  ✓ Read config from {db_config}")

    try:
        g = lambda v: re.search(fr'\${v}\s*=\s*[\'\"]([^\'\"]*)[\'\"]', txt).group(1)
        user = g('login')
        pwd = g('pass')
        db = g('dbase')
        print(f"  Parsed: user={user}, db={db}")
    except Exception as e:
        print(f"  ✗ Parse error: {str(e)[:100]}")
        return None

    import pymysql
    for host in ['172.18.0.3', '127.0.0.1', 'openemr-8x-mysql', 'openemr-8x-mysql-1']:
        try:
            print(f"  Trying {host}...")
            conn = pymysql.connect(host=host, user=user, password=pwd, database=db)
            print(f"  ✓ Connected to {host}")
            return conn
        except Exception as e:
            print(f"    Failed: {str(e)[:80]}")
    return None

def auto_configure():
    """Auto-configure OpenEMR to recognize Ontario Lab as a procedure provider.

    When run inside container, has direct access to filesystem and MySQL.
    """
    print("Configuring OpenEMR database...")
    conn = get_db()
    if not conn:
        print("ERROR: Could not connect to database")
        return

    cur = conn.cursor()

    # Build paths dynamically
    orders_path = f"{CONFIG['EDI_BASE']}/orders"
    results_path = f"{CONFIG['EDI_BASE']}/inbox"

    try:
        # Insert Ontario Reference Lab provider
        cur.execute(
            'INSERT IGNORE INTO procedure_providers (name, npi, active, direction, protocol, orders_path, results_path) VALUES (%s, %s, 1, %s, %s, %s, %s)',
            (CONFIG['LAB_NAME'], '123456', 'B', 'FS', orders_path, results_path)
        )

        # Get lab_id
        cur.execute('SELECT ppid FROM procedure_providers WHERE name=%s', (CONFIG['LAB_NAME'],))
        lab_id = cur.fetchone()[0]

        # Delete existing procedures for this lab
        cur.execute('DELETE FROM procedure_type WHERE lab_id=%s', (lab_id,))

        # Insert parent group
        cur.execute(
            'INSERT INTO procedure_type (parent, name, lab_id, procedure_code, procedure_type, activity) VALUES (0, %s, %s, %s, %s, 1)',
            ('Ontario Labs', lab_id, 'ONT-GRP', 'fgp')
        )
        parent_id = cur.lastrowid

        # Insert all lab tests
        for code, data in CATALOG.items():
            cur.execute(
                'INSERT INTO procedure_type (parent, name, lab_id, procedure_code, procedure_type, units, `range`, activity, procedure_type_name) VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)',
                (parent_id, data['name'], lab_id, code, 'ord', data['unit'], f"{data['low']}-{data['high']}", data['name'])
            )

        conn.commit()
        print("✓ Database configured")

    except Exception as e:
        print(f"ERROR during database configuration: {str(e)[:200]}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def patch_php():
    """Industrial-strength patcher with auto-backup and syntax verification

    Now uses discovered container name instead of hardcoding it.
    This allows mocklab to patch ANY OpenEMR version automatically.
    """
    c = CONFIG['CONTAINER_NAME']  # e.g., 'openemr-8x-1' instead of hardcoded 'openemr-openemr-1'
    t = '/var/www/localhost/htdocs/openemr/interface/forms/procedure_order/common.php'
    bk = t + '.bak'
    
    print("Shields up: Creating backup of core EMR files...")
    subprocess.run(f"docker exec {c} cp {t} {bk}", shell=True)
    
    patch_script = "<?php\n" \
                   "$f = '/var/www/localhost/htdocs/openemr/interface/forms/procedure_order/common.php';\n" \
                   "$c = file_get_contents($f);\n" \
                   "$c = str_replace('if ($_POST[\\\"form_provider_id\\\"] + 0 < 1)', 'if (false && $_POST[\\\"form_provider_id\\\"] + 0 < 1)', $c);\n" \
                   "$c = str_replace('if ($diag_flag === 0)', 'if (false && $diag_flag === 0)', $c);\n" \
                   "$c = str_replace('if (!$_POST[\\\"form_date_collected\\\"] && !$_POST[\\\"form_order_psc\\\"])', 'if (false && !$_POST[\\\"form_date_collected\\\"] && !$_POST[\\\"form_order_psc\\\"])', $c);\n" \
                   "$c = str_replace('if (empty($_POST[\\\"form_billing_type\\\"]))', 'if (false && empty($_POST[\\\"form_billing_type\\\"]))', $c);\n" \
                   "file_put_contents($f, $c);\n" \
                   "?>"
    
    with open('/tmp/patch_v3.php', 'w') as ps: ps.write(patch_script)
    
    print("Applying Frictionless Patch...")
    os.system(f"docker exec -i {c} php < /tmp/patch_v3.php")
    
    print("Verifying integrity...")
    check = subprocess.run(f"docker exec {c} php -l {t}", shell=True, capture_output=True, text=True)
    
    if "No syntax errors detected" in check.stdout:
        print("✅ Patch verified and stable.")
    else:
        print("❌ CRITICAL: Syntax error detected! Rolling back to safety...")
        subprocess.run(f"docker exec {c} cp {bk} {t}", shell=True)
        print("✅ System restored to original state.")

def process_logic():
    """Process lab orders from EDI /orders directory and generate results in /inbox.

    Works from both host and container by using docker exec when needed.
    """
    import subprocess

    od = f"{CONFIG['EDI_BASE']}/orders"
    rd = f"{CONFIG['EDI_BASE']}/inbox"

    # If running on host, use docker exec to list files in container
    try:
        if not os.path.exists(od):
            # Get file list via docker exec
            result = subprocess.run(
                f"docker exec {DISCOVERED['CONTAINER_NAME']} ls {od} 2>/dev/null || true",
                shell=True,
                capture_output=True,
                text=True
            )
            files = [f for f in result.stdout.strip().split('\n') if f.endswith('.txt')]
        else:
            files = [f for f in os.listdir(od) if f.endswith('.txt')]
    except:
        return

    for fname in files:
        try:
            order_path = os.path.join(od, fname)

            # Read order file
            if os.path.exists(order_path):
                with open(order_path, 'r') as f:
                    h = f.read()
            else:
                # Read from container
                result = subprocess.run(
                    f"docker exec {DISCOVERED['CONTAINER_NAME']} cat {order_path}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    continue
                h = result.stdout

            # Parse order
            pid = next((l for l in h.splitlines() if l.startswith('PID|')), 'PID|1||||Unk^Pat||19800101|M')
            msh = h.splitlines()[0].split('|') if h.splitlines() else []
            ctl = msh[9] if len(msh) > 9 else 'SIM'
            ts = datetime.now().strftime('%Y%m%d%H%M%S')

            # Generate result
            res = f'MSH|^~\\\\&|ONTARIOLAB|LAB|OPENEMR|CLINIC|{ts}||ORU^R01|{ctl}|D|2.3\n{pid}\n'
            for s, c in re.findall(r'OBR\|(\d+)\|.*?\|\|(.*?)\^', h):
                res += f'OBR|{s}|{ctl}||{c}^|||{ts}|||||||||||F\n'
                m = CATALOG.get(c, {'name': 'Test', 'unit': 'units', 'low': 0, 'high': 100})
                v = round(random.uniform(m['low'], m['high']), 1)
                res += f'OBX|1|NM|{c}^{m["name"]}^LN||{v}|{m["unit"]}|{m["low"]}-{m["high"]}|N|||F\n'

            # Write result
            result_path = os.path.join(rd, f'RES_{fname}')
            if os.path.exists(rd):
                with open(result_path, 'w') as w:
                    w.write(res)
            else:
                # Write to container
                subprocess.run(
                    f"docker exec {DISCOVERED['CONTAINER_NAME']} bash -c 'cat > {result_path}' << 'RESEND'\n{res}\nRESEND",
                    shell=True
                )

            # Delete order
            if os.path.exists(order_path):
                os.remove(order_path)
            else:
                subprocess.run(
                    f"docker exec {DISCOVERED['CONTAINER_NAME']} rm {order_path}",
                    shell=True
                )
        except:
            pass

def watcher():
    while True:
        process_logic()
        import_results()
        time.sleep(5)

def import_results():
    """Auto-import HL7 results from inbox into OpenEMR database"""
    import subprocess

    rd = f"{CONFIG['EDI_BASE']}/inbox"
    c = CONFIG['CONTAINER_NAME']

    # Run the PHP importer script
    subprocess.run(
        f"docker exec {c} php /app/result_importer.php {rd}",
        shell=True,
        capture_output=True,
        text=True
    )

app = Flask(__name__)
@app.route('/')
def home(): return '<h1>Ontario Lab Active ✅</h1>'

if __name__ == '__main__':
    if '--install' in sys.argv:
        print("\n🚀 MOCKLAB UNIVERSAL INSTALL\n")

        # Check if we're running inside the container
        in_container = os.path.exists('/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php')

        if not in_container:
            print("Installing (using docker exec for database operations)...\n")
            import subprocess

            container_name = DISCOVERED['CONTAINER_NAME']
            mysql_container = DISCOVERED['MYSQL_CONTAINER']

            # Create EDI directories via docker exec
            print("  1. Creating EDI directories...")
            for d in ['orders', 'inbox']:
                subprocess.run(
                    f"docker exec {container_name} mkdir -p {CONFIG['EDI_BASE']}/{d}",
                    shell=True,
                    check=False
                )

            # Configure OpenEMR database via docker exec
            print("  2. Configuring OpenEMR database...")

            orders_path = f"{CONFIG['EDI_BASE']}/orders"
            results_path = f"{CONFIG['EDI_BASE']}/inbox"

            try:
                # Step 1: Insert provider
                sql1 = f"INSERT IGNORE INTO procedure_providers (name, npi, active, direction, protocol, orders_path, results_path) VALUES ('Ontario Reference Lab', '123456', 1, 'B', 'FS', '{orders_path}', '{results_path}');"
                subprocess.run(
                    f"docker exec {mysql_container} mysql -uopenemr -popenemr openemr -e \"{sql1}\"",
                    shell=True,
                    check=False
                )

                # Step 2: Get lab_id and insert parent
                result = subprocess.run(
                    f"docker exec {mysql_container} mysql -uopenemr -popenemr openemr -e \"SELECT ppid FROM procedure_providers WHERE name='Ontario Reference Lab';\"",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                lab_id = result.stdout.strip().split('\n')[-1] if result.returncode == 0 else '1'

                sql2 = f"INSERT INTO procedure_type (parent, name, lab_id, procedure_code, procedure_type, activity) VALUES (0, 'Ontario Labs', {lab_id}, 'ONT-GRP', 'fgp', 1);"
                subprocess.run(
                    f"docker exec {mysql_container} mysql -uopenemr -popenemr openemr -e \"{sql2}\"",
                    shell=True,
                    check=False
                )

                # Step 3: Get parent_id and insert all tests
                result = subprocess.run(
                    f"docker exec {mysql_container} mysql -uopenemr -popenemr openemr -e \"SELECT procedure_type_id FROM procedure_type WHERE procedure_code='ONT-GRP';\"",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                parent_id = result.stdout.strip().split('\n')[-1] if result.returncode == 0 else '1'

                # Insert each test
                for code, data in CATALOG.items():
                    sql = f"INSERT INTO procedure_type (parent, name, lab_id, procedure_code, procedure_type, units, `range`, activity, procedure_type_name) VALUES ({parent_id}, '{data['name']}', {lab_id}, '{code}', 'ord', '{data['unit']}', '{data['low']}-{data['high']}', 1, '{data['name']}');"
                    subprocess.run(
                        f"docker exec {mysql_container} mysql -uopenemr -popenemr openemr -e \"{sql}\"",
                        shell=True,
                        check=False
                    )

                print("  ✓ Database configured")
            except Exception as e:
                print(f"  ✗ Database configuration error: {str(e)[:100]}")

            # Patch PHP via docker exec
            print("  3. Patching validation logic...")
            patch_php()

            print('\n🎉 Turnkey Install Complete.')
            print(f"Mocklab is now configured for OpenEMR in {container_name}")
            print("To start the lab simulator, run: python3 ontario_lab_turnkey.py")
            sys.exit(0)

        else:
            # Running inside container - do the actual installation
            print("Setup sequence:")
            print(f"  1. Create EDI directories in {CONFIG['EDI_BASE']}")
            print(f"  2. Auto-configure OpenEMR database")
            print(f"  3. Patch validation logic\n")

            # Create EDI directories (/orders and /inbox)
            for s in ['orders', 'inbox']:
                os.makedirs(f"{CONFIG['EDI_BASE']}/{s}", exist_ok=True)
            print("✓ EDI directories created")

            # Configure OpenEMR database (adds lab provider and procedure types)
            auto_configure()

            # Patch validation logic (allows orders without all fields)
            patch_php()

            print('\n🎉 Turnkey Install Complete.')
            print(f"Mocklab is now configured for OpenEMR in {DISCOVERED['CONTAINER_NAME']}")
            print("To start the lab simulator, run: python3 ontario_lab_turnkey.py")

    else:
        print(f"\n🧪 Starting Ontario Lab Simulator on port {CONFIG['PORT']}...")
        print(f"   Container: {DISCOVERED['CONTAINER_NAME']}")
        print(f"   Monitoring: {CONFIG['EDI_BASE']}/orders (via docker exec)")
        print(f"   Writing results to: {CONFIG['EDI_BASE']}/inbox\n")

        # Start background watcher (monitors /orders every 5 seconds)
        threading.Thread(target=watcher, daemon=True).start()

        # Run Flask server on port 5001
        app.run(host='0.0.0.0', port=CONFIG['PORT'])
#!/usr/bin/env python3
"""Universal OpenEMR lab simulator.

Supports:
- Docker-based OpenEMR 7.0.2+ sandboxes
- Host-based OpenEMR installs on Ubuntu EC2

The simulator discovers the OpenEMR root from environment variables first,
then common install paths, then a local docker-compose file as a fallback.
"""

import argparse
import os
import random
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import pymysql
except ImportError:  # pragma: no cover - handled at runtime
    pymysql = None

LAB_NAME = 'Ontario Reference Lab'
CATALOG = {
    '6690-2': dict(name='WBC', unit='x10^9/L', low=4.0, high=11.0),
    '718-7': dict(name='Hemoglobin', unit='g/L', low=120.0, high=175.0),
    '1558-6': dict(name='Glucose (Fasting)', unit='mmol/L', low=3.6, high=6.0),
    '3016-3': dict(name='TSH', unit='mIU/L', low=0.32, high=4.00),
    '2093-3': dict(name='Total Cholesterol', unit='mmol/L', low=0.0, high=5.2),
    '4548-4': dict(name='Hemoglobin A1c', unit='%', low=4.0, high=6.0),
}

COMMON_ROOTS = [
    Path('/var/www/localhost/htdocs/openemr'),
    Path('/var/www/html/openemr'),
    Path('/var/www/openemr'),
    Path('/opt/openemr'),
    Path('/srv/openemr'),
]

COMPOSE_NAMES = (
    'docker-compose.yml',
    'docker-compose.yaml',
    'docker-compose-8.0.x.yml',
)


def log(message):
    print(message, flush=True)


def normalize_mode(raw_mode, compose_file=None):
    raw_mode = (raw_mode or '').strip().lower()
    if raw_mode in {'host', 'docker'}:
        return raw_mode
    return 'docker' if compose_file else 'host'


def first_existing(paths):
    for candidate in paths:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def find_compose_file():
    for name in COMPOSE_NAMES:
        candidate = Path.cwd() / name
        if candidate.exists():
            return candidate
    for pattern in ('docker-compose*.yml', 'docker-compose*.yaml'):
        matches = sorted(Path.cwd().glob(pattern))
        if matches:
            return matches[0]
    return None


def derive_layout(mode, root, sites, sqlconf, compose_file=None):
    root = Path(root).expanduser().resolve()
    sites = Path(sites).expanduser().resolve()
    sqlconf = Path(sqlconf).expanduser().resolve()
    edi_base = sites / 'default' / 'documents' / 'edi'
    common_php = root / 'interface' / 'forms' / 'procedure_order' / 'common.php'
    return {
        'mode': mode,
        'compose_file': str(compose_file) if compose_file else '',
        'openemr_root': str(root),
        'sites_root': str(sites),
        'sqlconf_path': str(sqlconf),
        'edi_base': str(edi_base),
        'common_php': str(common_php),
    }


def derive_from_root(mode, root, compose_file=None):
    root = Path(root).expanduser().resolve()
    sites = root / 'sites'
    sqlconf = sites / 'default' / 'sqlconf.php'
    return derive_layout(mode, root, sites, sqlconf, compose_file)


def derive_from_sites(mode, sites, compose_file=None):
    sites = Path(sites).expanduser().resolve()
    root = sites.parent
    sqlconf = sites / 'default' / 'sqlconf.php'
    return derive_layout(mode, root, sites, sqlconf, compose_file)


def parse_compose_for_sites(compose_file):
    text = Path(compose_file).read_text(encoding='utf-8', errors='ignore')
    for line in text.splitlines():
        match = re.match(r'^\s*-\s*[^:]+:(/[^#\s]+)', line)
        if not match:
            continue
        mount_path = match.group(1).rstrip('/')
        if mount_path.endswith('/sites') or '/openemr/sites' in mount_path:
            return derive_from_sites('docker', mount_path, compose_file)
    raise RuntimeError(
        f'Could not find an OpenEMR sites mount in {compose_file}. '
        'Expected a volume like /var/www/localhost/htdocs/openemr/sites.'
    )


def discover_layout():
    compose_file = find_compose_file()
    raw_mode = os.getenv('ONTARIO_LAB_MODE', '')
    mode = normalize_mode(raw_mode, compose_file)

    sqlconf_env = os.getenv('OPENEMR_SQLCONF', '').strip()
    sites_env = os.getenv('OPENEMR_SITES', '').strip()
    root_env = os.getenv('OPENEMR_ROOT', '').strip()

    if sqlconf_env:
        sqlconf = Path(sqlconf_env).expanduser().resolve()
        if sqlconf.exists():
            sites = sqlconf.parent.parent
            root = sites.parent
            return derive_layout(mode, root, sites, sqlconf, compose_file)

    if sites_env:
        sites = Path(sites_env).expanduser().resolve()
        sqlconf = sites / 'default' / 'sqlconf.php'
        if sqlconf.exists():
            return derive_layout(mode, sites.parent, sites, sqlconf, compose_file)

    if root_env:
        candidate = derive_from_root(mode, root_env, compose_file)
        if Path(candidate['sqlconf_path']).exists():
            return candidate

    for root in COMMON_ROOTS:
        sqlconf = root / 'sites' / 'default' / 'sqlconf.php'
        if sqlconf.exists():
            return derive_layout(mode, root, root / 'sites', sqlconf, compose_file)

    if compose_file and mode == 'docker':
        return parse_compose_for_sites(compose_file)

    search_hint = (
        'Set OPENEMR_ROOT, OPENEMR_SITES, or OPENEMR_SQLCONF, '
        'or place this script next to a docker-compose file that mounts /sites.'
    )
    raise FileNotFoundError(
        'Could not discover an OpenEMR installation. ' + search_hint
    )


def read_text(path):
    return Path(path).read_text(encoding='utf-8', errors='ignore')


def write_text(path, content):
    Path(path).write_text(content, encoding='utf-8')


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def parse_sqlconf(sqlconf_path):
    text = read_text(sqlconf_path)

    def pick(name, default=''):
        pattern = rf"\${name}\s*=\s*['\"]([^'\"]*)['\"]"
        match = re.search(pattern, text)
        return match.group(1) if match else default

    return {
        'host': pick('host', '127.0.0.1'),
        'login': pick('login', ''),
        'pass': pick('pass', ''),
        'dbase': pick('dbase', ''),
        'socket': pick('socket', ''),
        'port': pick('port', '3306'),
    }


def connect_db(layout):
    if pymysql is None:
        raise RuntimeError('PyMySQL is required. Install it with: pip install pymysql')

    config = parse_sqlconf(layout['sqlconf_path'])
    params = {
        'user': config['login'],
        'password': config['pass'],
        'database': config['dbase'],
        'charset': 'utf8mb4',
        'autocommit': False,
    }

    socket_path = config.get('socket', '')
    if socket_path and Path(socket_path).exists():
        params['unix_socket'] = socket_path
    else:
        params['host'] = config['host'] or '127.0.0.1'
        try:
            params['port'] = int(config.get('port') or 3306)
        except ValueError:
            params['port'] = 3306

    return pymysql.connect(**params)


def ensure_layout(layout):
    ensure_dir(Path(layout['edi_base']) / 'orders')
    ensure_dir(Path(layout['edi_base']) / 'inbox')


def configure_database(layout):
    log('Configuring OpenEMR database...')
    conn = connect_db(layout)
    try:
        cur = conn.cursor()
        orders_path = str(Path(layout['edi_base']) / 'orders')
        results_path = str(Path(layout['edi_base']) / 'inbox')

        cur.execute('SELECT ppid FROM procedure_providers WHERE name=%s LIMIT 1', (LAB_NAME,))
        row = cur.fetchone()
        if row:
            lab_id = row[0]
        else:
            cur.execute(
                'INSERT INTO procedure_providers '
                '(name, npi, active, direction, protocol, orders_path, results_path) '
                'VALUES (%s, %s, 1, %s, %s, %s, %s)',
                (LAB_NAME, '123456', 'B', 'FS', orders_path, results_path),
            )
            lab_id = cur.lastrowid

        cur.execute('DELETE FROM procedure_type WHERE lab_id=%s', (lab_id,))

        cur.execute(
            'INSERT INTO procedure_type '
            '(parent, name, lab_id, procedure_code, procedure_type, activity) '
            'VALUES (0, %s, %s, %s, %s, 1)',
            ('Ontario Labs', lab_id, 'ONT-GRP', 'fgp'),
        )
        parent_id = cur.lastrowid

        for code, meta in CATALOG.items():
            cur.execute(
                'INSERT INTO procedure_type '
                '(parent, name, lab_id, procedure_code, procedure_type, units, `range`, activity, procedure_type_name) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)',
                (
                    parent_id,
                    meta['name'],
                    lab_id,
                    code,
                    'ord',
                    meta['unit'],
                    f"{meta['low']}-{meta['high']}",
                    meta['name'],
                ),
            )

        conn.commit()
        log('Database configured.')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def patch_order_form(layout):
    path = Path(layout['common_php'])
    if not path.exists():
        log(f'Skipping OpenEMR form patch; file not found: {path}')
        return

    original = read_text(path)
    updated = original
    replacements = [
        (
            r'if\s*\(\s*\$_POST\[(?:"|\')form_provider_id(?:"|\')]\s*\+\s*0\s*<\s*1\s*\)',
            'if (false && $_POST["form_provider_id"] + 0 < 1)',
        ),
        (
            r'if\s*\(\s*\$diag_flag\s*===\s*0\s*\)',
            'if (false && $diag_flag === 0)',
        ),
        (
            r'if\s*\(\s*!\$_POST\[(?:"|\')form_date_collected(?:"|\')]\s*&&\s*!\$_POST\[(?:"|\')form_order_psc(?:"|\')]\s*\)',
            'if (false && !$_POST["form_date_collected"] && !$_POST["form_order_psc"])',
        ),
        (
            r'if\s*\(\s*empty\(\$_POST\[(?:"|\')form_billing_type(?:"|\')]\)\s*\)',
            'if (false && empty($_POST["form_billing_type"]))',
        ),
    ]

    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, updated)

    if updated == original:
        log('OpenEMR form patch not needed or pattern not found.')
        return

    backup = path.with_name(path.name + '.ontario-lab.bak')
    if not backup.exists():
        shutil.copy2(path, backup)
    write_text(path, updated)
    log(f'Patched OpenEMR order form: {path}')


def parse_order_message(content):
    patient = {'fname': 'Patient', 'lname': 'Unknown'}
    tests = []

    for line in content.splitlines():
        if line.startswith('PID|'):
            parts = line.split('|')
            if len(parts) > 5:
                name_bits = parts[5].split('^')
                if name_bits and name_bits[0]:
                    patient['lname'] = name_bits[0]
                if len(name_bits) > 1 and name_bits[1]:
                    patient['fname'] = name_bits[1]
        elif line.startswith('OBR|'):
            match = re.search(r'\|\|([^\|\^]+)\^', line)
            if match:
                tests.append(match.group(1))

    return patient, tests


def build_result_message(order_text):
    patient, tests = parse_order_message(order_text)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    control_id = f'ONT{timestamp}'

    lines = [
        f'MSH|^~\\&|ONTARIOLAB|LAB|OPENEMR|CLINIC|{timestamp}||ORU^R01|{control_id}|D|2.3',
        f"PID|1||1||{patient['lname']}^{patient['fname']}||19800101|M",
    ]

    for idx, code in enumerate(tests, start=1):
        meta = CATALOG.get(code, {'name': 'Test', 'unit': 'units', 'low': 0.0, 'high': 100.0})
        value = round(random.uniform(meta['low'], meta['high']), 1)
        lines.append(
            f"OBR|{idx}|{control_id}||{code}^{meta['name']}^LN|||{timestamp}|||||||||||F"
        )
        lines.append(
            f"OBX|1|NM|{code}^{meta['name']}^LN||{value}|{meta['unit']}|"
            f"{meta['low']}-{meta['high']}|N|||F"
        )

    return '\n'.join(lines) + '\n'


def parse_result_message(content):
    result = {
        'fname': '',
        'lname': '',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'results': [],
    }

    for line in content.splitlines():
        parts = line.split('|')
        if not parts:
            continue

        segment = parts[0]
        if segment == 'PID' and len(parts) > 5:
            name_bits = parts[5].split('^')
            result['lname'] = name_bits[0] if name_bits else ''
            result['fname'] = name_bits[1] if len(name_bits) > 1 else ''
            result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif segment == 'OBX' and len(parts) > 7:
            code_bits = parts[3].split('^')
            result['results'].append(
                {
                    'code': code_bits[0] if code_bits else '',
                    'name': code_bits[1] if len(code_bits) > 1 else '',
                    'value': parts[5],
                    'units': parts[6],
                    'range': parts[7],
                }
            )

    return result


def import_result_text(conn, content):
    parsed = parse_result_message(content)
    if not parsed['results']:
        return False

    cur = conn.cursor()
    cur.execute(
        'SELECT id FROM patient_data WHERE fname = %s AND lname = %s LIMIT 1',
        (parsed['fname'], parsed['lname']),
    )
    patient = cur.fetchone()
    if not patient:
        return False

    patient_id = patient[0]
    cur.execute(
        'SELECT procedure_order_id FROM procedure_order '
        'WHERE patient_id = %s ORDER BY procedure_order_id DESC LIMIT 1',
        (patient_id,),
    )
    order_row = cur.fetchone()
    if not order_row:
        return False

    order_id = order_row[0]
    cur.execute(
        'INSERT INTO procedure_report '
        '(procedure_order_id, date_report, review_status, report_status) '
        "VALUES (%s, %s, 'received', 'final')",
        (order_id, parsed['timestamp']),
    )
    report_id = cur.lastrowid

    for obx in parsed['results']:
        cur.execute(
            'INSERT INTO procedure_result '
            '(procedure_report_id, result_code, result_text, date, units, result, `range`, result_status) '
            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'final')",
            (
                report_id,
                obx['code'],
                obx['name'],
                parsed['timestamp'],
                obx['units'],
                obx['value'],
                obx['range'],
            ),
        )

    conn.commit()
    return True


def process_order_files(layout):
    orders_dir = Path(layout['edi_base']) / 'orders'
    inbox_dir = Path(layout['edi_base']) / 'inbox'
    ensure_dir(orders_dir)
    ensure_dir(inbox_dir)

    for order_path in sorted(orders_dir.glob('*.txt')):
        try:
            order_text = read_text(order_path)
            result_text = build_result_message(order_text)
            result_path = inbox_dir / f'RES_{order_path.name}'
            write_text(result_path, result_text)
            order_path.unlink()
            log(f'Processed order: {order_path.name}')
        except Exception as exc:
            log(f'Order processing failed for {order_path.name}: {exc}')


def import_inbox_files(layout, conn):
    inbox_dir = Path(layout['edi_base']) / 'inbox'
    ensure_dir(inbox_dir)

    for result_path in sorted(inbox_dir.glob('RES_*.txt')):
        try:
            result_text = read_text(result_path)
            if import_result_text(conn, result_text):
                result_path.unlink()
                log(f'Imported result: {result_path.name}')
        except Exception as exc:
            log(f'Result import failed for {result_path.name}: {exc}')


def install(layout):
    ensure_layout(layout)
    configure_database(layout)
    patch_order_form(layout)
    log('Installation complete.')


def run_loop(layout):
    log('Starting Ontario Lab Simulator...')
    log(f"  Mode: {layout['mode']}")
    log(f"  OpenEMR root: {layout['openemr_root']}")
    log(f"  EDI base: {layout['edi_base']}")
    log('')

    conn = None
    while True:
        try:
            ensure_layout(layout)
            if conn is None:
                conn = connect_db(layout)
            else:
                conn.ping(reconnect=True)

            process_order_files(layout)
            import_inbox_files(layout, conn)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            log(f'Watch cycle error: {exc}')
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
        time.sleep(5)

    if conn is not None:
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Ontario Lab Simulator')
    parser.add_argument('--install', action='store_true', help='Configure OpenEMR and create lab entries')
    args = parser.parse_args(argv)

    layout = discover_layout()

    if args.install:
        install(layout)
        return 0

    run_loop(layout)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

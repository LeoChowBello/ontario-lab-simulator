#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""
Config Discovery Module: Auto-detect OpenEMR container and volume configuration

WHY THIS MATTERS:
=================
The original mocklab code was hardcoded for one specific OpenEMR installation:
  - Container name: openemr-openemr-1
  - Docker volume path: /var/lib/docker/volumes/openemr_openemr_sites/_data/...
  - MySQL IP: 172.18.0.3

When you upgrade to a new version (e.g., 8.0.x), the container name changes,
the volume path changes, the MySQL IP changes. The mocklab code would break.

This module AUTOMATICALLY discovers the correct configuration by reading the
docker-compose file. This makes mocklab truly "version-universal"—it works
on any OpenEMR version as long as there's a docker-compose file.

HOW IT WORKS:
=============
1. Finds the docker-compose*.yml file in the current directory
2. Parses it (YAML format) to extract:
   - OpenEMR container name (e.g., "openemr-8x-1", "openemr-openemr-1")
   - MySQL container name (e.g., "openemr-8x-mysql-1")
   - Docker volume name (e.g., "openemr-8x-sites")
   - Mount path inside container (e.g., "/var/www/localhost/htdocs/openemr/sites")
3. Constructs the EDI path dynamically
4. Returns a CONFIG dict that mocklab.py uses

EXAMPLE DISCOVERY:
==================
Input: docker-compose-8.0.x.yml with:
  services:
    openemr-8x:
      container_name: openemr-8x-1
      volumes:
        - openemr-8x-sites:/var/www/localhost/htdocs/openemr/sites
    openemr-8x-mysql:
      container_name: openemr-8x-mysql-1

Output CONFIG dict:
  {
    'CONTAINER_NAME': 'openemr-8x-1',
    'MYSQL_CONTAINER': 'openemr-8x-mysql-1',
    'DOCKER_VOLUME': 'openemr-8x-sites',
    'MOUNT_PATH': '/var/www/localhost/htdocs/openemr/sites',
    'EDI_BASE': '/var/www/localhost/htdocs/openemr/sites/default/documents/edi',
    'DB_CONFIG': '/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php'
  }

If a future OpenEMR 9.0 has container_name: "openemr-9-1", this code
automatically adapts—no hardcoding needed.
"""

import os
import re
import glob


def find_compose_file():
    """
    Find the docker-compose file in current directory.
    Looks for: docker-compose*.yml or docker-compose*.yaml
    Returns the first match (typically docker-compose.yml, but could be
    docker-compose-8.0.x.yml or docker-compose-7.0.2.yml).
    """
    patterns = ['docker-compose*.yml', 'docker-compose*.yaml']
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    raise FileNotFoundError(
        "No docker-compose file found in current directory.\n"
        "Place ontario_lab_turnkey.py in the same directory as your docker-compose*.yml file."
    )


def parse_compose_yaml(filepath):
    """
    Parse docker-compose YAML file WITHOUT requiring PyYAML dependency.

    This is a simple, regex-based parser that works for typical docker-compose
    structures. It extracts:
    - Service names
    - container_name values
    - Volume mount declarations (volume:path format)

    Why not use PyYAML? To keep mocklab a zero-dependency tool that students
    can run immediately without pip install. A regex parser is sufficient for
    our structured docker-compose format.
    """
    with open(filepath, 'r') as f:
        content = f.read()

    result = {
        'services': {},
        'volumes': {}
    }

    # Extract service name and indented block
    # Pattern: "  service_name:" followed by indented lines
    service_pattern = r'^  (\w+[-\w]*):\s*$'
    lines = content.split('\n')

    current_service = None
    service_indent = None

    for i, line in enumerate(lines):
        service_match = re.match(service_pattern, line)
        if service_match:
            current_service = service_match.group(1)
            result['services'][current_service] = {}
            service_indent = 4  # Services are indented 2 spaces, their properties 4+
            continue

        if current_service and line and not line[0].isspace():
            # Left the services block
            current_service = None
            continue

        if current_service:
            # Extract container_name
            container_match = re.match(r'    container_name:\s*([^\s]+)', line)
            if container_match:
                result['services'][current_service]['container_name'] = container_match.group(1)

            # Extract volumes (look for "- volume_name:path" format)
            volume_match = re.match(r'      - ([\w-]+):(/[^\s]+)', line)
            if volume_match:
                if 'volumes' not in result['services'][current_service]:
                    result['services'][current_service]['volumes'] = []
                result['services'][current_service]['volumes'].append({
                    'name': volume_match.group(1),
                    'path': volume_match.group(2)
                })

    return result


def discover_config():
    """
    Main discovery function. Auto-detects OpenEMR configuration.

    Returns:
        dict: Configuration dict with keys:
            - CONTAINER_NAME: OpenEMR container name
            - MYSQL_CONTAINER: MySQL container name
            - DOCKER_VOLUME: Docker volume name (the named volume)
            - MOUNT_PATH: Path inside container where volume is mounted
            - EDI_BASE: Full path to EDI directories (mount_path/default/documents/edi)
            - DB_CONFIG: Full path to sqlconf.php
    """
    print("🔍 Discovering OpenEMR configuration from docker-compose file...")

    compose_file = find_compose_file()
    print(f"   Found: {compose_file}")

    # Parse the docker-compose file
    config = parse_compose_yaml(compose_file)
    services = config['services']

    # Find OpenEMR service (contains "openemr" but NOT "mysql")
    openemr_service = None
    for service_name in services.keys():
        if 'openemr' in service_name and 'mysql' not in service_name:
            openemr_service = service_name
            break

    if not openemr_service:
        raise ValueError(
            f"Could not find OpenEMR service in {compose_file}. "
            "Services found: {', '.join(services.keys())}"
        )

    # Find MySQL service
    mysql_service = None
    for service_name in services.keys():
        if 'mysql' in service_name or 'mariadb' in service_name:
            mysql_service = service_name
            break

    if not mysql_service:
        raise ValueError(f"Could not find MySQL/MariaDB service in {compose_file}")

    # Extract details from OpenEMR service
    openemr_config = services[openemr_service]
    container_name = openemr_config.get('container_name')
    if not container_name:
        raise ValueError(
            f"OpenEMR service '{openemr_service}' has no container_name. "
            "Please add: container_name: openemr-8x-1 (or your version)"
        )

    volumes = openemr_config.get('volumes', [])
    if not volumes:
        raise ValueError(
            f"OpenEMR service '{openemr_service}' has no volumes. "
            "Mocklab needs a volume mount to access files."
        )

    # Extract volume name and mount path from first volume
    volume_info = volumes[0]
    docker_volume = volume_info['name']
    mount_path = volume_info['path']

    # Extract MySQL container name
    mysql_config = services[mysql_service]
    mysql_container = mysql_config.get('container_name', 'unknown')

    # Build final config
    discovered = {
        'COMPOSE_FILE': compose_file,
        'OPENEMR_SERVICE': openemr_service,
        'MYSQL_SERVICE': mysql_service,
        'CONTAINER_NAME': container_name,
        'MYSQL_CONTAINER': mysql_container,
        'DOCKER_VOLUME': docker_volume,
        'MOUNT_PATH': mount_path,
        'EDI_BASE': f"{mount_path}/default/documents/edi",
        'DB_CONFIG': f"{mount_path}/default/sqlconf.php"
    }

    # Print discovery results
    print(f"\n   ✅ OpenEMR service: {openemr_service}")
    print(f"   ✅ Container: {container_name}")
    print(f"   ✅ MySQL: {mysql_container}")
    print(f"   ✅ Volume: {docker_volume}")
    print(f"   ✅ Mount path: {mount_path}")
    print(f"   ✅ EDI base: {discovered['EDI_BASE']}\n")

    return discovered


if __name__ == '__main__':
    # Allow testing config discovery standalone
    try:
        cfg = discover_config()
        print("Final CONFIG dict:")
        for key, value in cfg.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        exit(1)

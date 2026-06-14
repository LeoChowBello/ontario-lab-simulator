FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask pymysql

# Copy mocklab files
COPY ontario_lab_turnkey.py .
COPY config_discovery.py .
COPY result_importer.php .
COPY docker-compose-8.0.x.yml docker-compose.yml

# Create EDI directories
RUN mkdir -p /edi/orders /edi/inbox

# Run the simulator (not --install, just the running mode)
CMD ["python3", "ontario_lab_turnkey.py"]

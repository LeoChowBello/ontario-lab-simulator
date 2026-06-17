FROM python:3.11-slim

WORKDIR /app

# Only one runtime dependency is needed for the simulator.
RUN pip install --no-cache-dir pymysql

# Copy the universal simulator and the bundled compose file for fallback discovery.
COPY ontario_lab_turnkey.py .
COPY docker-compose-8.0.x.yml .

# Create EDI directories for the bundled Docker layout.
RUN mkdir -p /edi/orders /edi/inbox

CMD ["python3", "ontario_lab_turnkey.py"]

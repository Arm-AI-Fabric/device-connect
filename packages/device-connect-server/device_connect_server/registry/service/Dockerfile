FROM python:3.11-slim

WORKDIR /app

# Copy only the registry service requirements
COPY device-connect-server/device_connect_server/registry/service/requirements.txt .
RUN pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Install device-connect-sdk from sibling repo
COPY device-connect-sdk/ /tmp/device-connect-sdk/
RUN pip install --no-cache-dir /tmp/device-connect-sdk/ && rm -rf /tmp/device-connect-sdk/

# Copy fabric library (dependency for registry service)
COPY device-connect-server/device_connect_server/ ./device_connect_server/

# Copy registry service code
COPY device-connect-server/device_connect_server/registry/service/*.py ./

RUN useradd -m -u 1000 appuser
USER appuser

CMD ["python", "-u", "main.py"]

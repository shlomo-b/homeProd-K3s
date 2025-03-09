# Use slim variant for smaller image size
FROM python:3.12.0-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY src/backup-fw/requirements.txt /app

RUN pip install --upgrade pip

# Install dependencies in a single RUN command to reduce layers
# Clean up apt cache to reduce image size
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
        curl \
        iputils-ping \
        net-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY src/backup-fw/fortigate_backup.py /app


# Start application
CMD ["python", "fortigate_backup.py"]

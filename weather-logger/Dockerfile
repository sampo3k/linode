# Weather Logger - Realtime Data Collector
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY realtime_collector.py .
COPY collector.py .
COPY backup.py .
COPY backup_scheduler.py .

# Create directories for data, logs, and config
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose no ports (this is a data collector, not a web service)

# Health check - verify the database exists and is accessible
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
  CMD sqlite3 /app/data/weather.db "SELECT COUNT(*) FROM weather_measurements;" > /dev/null || exit 1

# Default command - run realtime collector
# Can be overridden to run the polling collector instead
CMD ["python3", "realtime_collector.py"]

# Weather Logger Usage Guide

## Starting the Collector

The collector service (`collector.py`) is a simple, long-running process that:
- Polls the Ambient Weather API every 60 seconds
- Stores measurements in SQLite
- Handles errors gracefully
- Logs all activity

### Run the Collector

```bash
python3 collector.py
```

You'll see output like:
```
Weather Logger - Data Collection Service
============================================================

Collector is running. Press Ctrl+C to stop.
Collecting data every 60 seconds...
Logs: logs/weather_logger.log
```

### What Happens

1. **Startup**:
   - Loads configuration from `config.yaml`
   - Initializes database schema (if not exists)
   - Tests API connection
   - Starts collection loop

2. **Every 60 Seconds**:
   - Fetches latest weather data from API
   - Parses temperature, humidity, pressure, wind, rain, etc.
   - Stores in SQLite database
   - Logs the operation

3. **Graceful Shutdown**:
   - Press `Ctrl+C` or send `SIGTERM`
   - Completes current operation
   - Logs final statistics
   - Exits cleanly

### Monitoring

**Watch logs in real-time:**
```bash
tail -f logs/weather_logger.log
```

**Check recent activity:**
```bash
tail -20 logs/weather_logger.log
```

**Count records:**
```bash
sqlite3 data/weather.db "SELECT COUNT(*) FROM weather_measurements;"
```

**View latest data:**
```bash
sqlite3 data/weather.db "SELECT timestamp, temp_outdoor, humidity_outdoor FROM weather_measurements ORDER BY timestamp DESC LIMIT 5;"
```

## Running in Docker

The collector is designed to run in a Docker container (Phase 5):

```bash
# Example (once Docker image is created in Phase 5)
docker run -d \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name weather-logger \
  weather-logger:latest
```

The service handles Docker's `SIGTERM` signal for graceful shutdown.

## Typical Data Collection

With 60-second intervals:
- **Per hour**: 60 measurements
- **Per day**: 1,440 measurements
- **Per month**: ~43,200 measurements
- **Per year**: ~525,600 measurements

Storage per measurement: ~200 bytes
- **Daily**: ~280 KB
- **Yearly**: ~100 MB

SQLite easily handles this data volume.

## Error Handling

The collector handles various error conditions:

### API Rate Limiting
- **Limit**: 1 request per second
- **Handling**: Automatic 1-second delay between requests
- **Error**: Logged and skipped, next attempt in 60 seconds

### Network Issues
- **Timeout**: 10 seconds per request
- **Handling**: Logged as error, retries on next cycle
- **Warning**: After 5 consecutive failures

### Database Issues
- **Duplicates**: Automatically skipped (UNIQUE constraint)
- **Lock errors**: Retried automatically
- **Disk full**: Logged as critical error

### API Authentication
- **Invalid credentials**: Fails at startup
- **Expired keys**: Logged as error on each attempt

## Logs Explained

**INFO**: Normal operations
```
2026-01-01 14:26:00 - INFO - Received measurement: 2026-01-01 14:26:00, temp=55.6°F, humidity=54%
2026-01-01 14:26:00 - INFO - Stored measurement in database (row ID: 123)
```

**WARNING**: Non-critical issues
```
2026-01-01 14:26:00 - WARNING - No measurement data available from API
2026-01-01 14:26:00 - WARNING - 5 consecutive collection failures
```

**ERROR**: Failed operations
```
2026-01-01 14:26:00 - ERROR - API rate limit exceeded
2026-01-01 14:26:00 - ERROR - Database error: disk full
```

## Troubleshooting

### No data being collected
1. Check API credentials in `config.yaml`
2. Verify device MAC address is correct
3. Check network connectivity
4. Review logs for errors: `grep ERROR logs/weather_logger.log`

### Rate limit errors
- Normal if you're running multiple instances
- Wait 60 seconds between manual API tests
- Only run one collector instance per API key

### Database locked
- Ensure only one collector is running
- Check disk space: `df -h data/`
- Verify file permissions on `data/` directory

### Duplicate records
- Normal behavior - duplicates are automatically skipped
- This prevents data loss if collector restarts

## Production Deployment

### Run as Background Service

**Using nohup:**
```bash
nohup python3 collector.py > collector.out 2>&1 &
```

**Using systemd (recommended for Linux):**
```ini
# /etc/systemd/system/weather-logger.service
[Unit]
Description=Weather Logger Data Collector
After=network.target

[Service]
Type=simple
User=weather
WorkingDirectory=/opt/weather-logger
ExecStart=/usr/bin/python3 /opt/weather-logger/collector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable weather-logger
sudo systemctl start weather-logger
sudo systemctl status weather-logger
```

### Monitor Health

Create a monitoring script:
```bash
#!/bin/bash
# check_collector.sh

# Check if collector is running
if ! pgrep -f "collector.py" > /dev/null; then
    echo "ERROR: Collector is not running"
    exit 1
fi

# Check if data is recent (within last 5 minutes)
last_record=$(sqlite3 data/weather.db "SELECT MAX(timestamp) FROM weather_measurements;")
if [ -z "$last_record" ]; then
    echo "ERROR: No data in database"
    exit 1
fi

echo "OK: Collector running, last record: $last_record"
exit 0
```

Run this via cron every 5 minutes to alert if collector stops.

## Next Steps

Once you're comfortable with the collector:
1. Let it run for a few hours to collect data
2. Implement Phase 4 (Backups to B2)
3. Implement Phase 5 (Docker container)
4. Setup Grafana dashboards (Phase 6)

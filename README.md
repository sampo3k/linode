# Weather Station Data Logger

A Python application that collects weather data from the Ambient Weather API and stores it in SQLite for visualization with Grafana.

## Features

- **Realtime Data Collection**: Receives weather updates via WebSocket once per minute
- **SQLite Storage**: Time-series data stored in SQLite with optimized indexes
- **Automated Backups**: Daily backups to S3-compatible storage (Backblaze B2 or AWS S3)
- **Graceful Error Handling**: Rate limiting, retries, and comprehensive logging
- **Container Ready**: Designed to run in Docker with signal handling and health checks

## Project Status

- ✅ **Phase 1**: API Integration - Complete
- ✅ **Phase 2**: Database Setup - Complete
- ✅ **Phase 3**: Data Collection Service - Complete (Realtime WebSocket API)
- ✅ **Phase 4**: Backup System - Complete
- ✅ **Phase 5**: Docker Container - Complete
- ⏳ **Phase 6**: Grafana Integration - Pending

## Quick Start

### Local Development

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Configure

Copy the example configuration and add your API credentials:

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys and device MAC address
```

Get your API credentials from: https://ambientweather.net/account

#### 3. Test Setup

Validate your configuration and test API connectivity:

```bash
python3 test_setup.py
```

#### 4. Run Collector

Start the realtime data collection service (recommended):

```bash
python3 realtime_collector.py
```

Or use the polling collector:

```bash
python3 collector.py
```

The service will:
- Connect to the Ambient Weather API
- Receive data updates in realtime (once per minute)
- Store measurements in `data/weather.db`
- Log activity to `logs/weather_logger.log`

Press `Ctrl+C` to stop gracefully.

### Docker Deployment (Recommended for Production)

#### 1. Build and Start

```bash
# Build the Docker image
docker-compose build

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

#### 2. Verify

```bash
# Check that data is being collected
docker exec weather-logger sqlite3 /app/data/weather.db \
  "SELECT COUNT(*) FROM weather_measurements;"

# View latest records
docker exec weather-logger sqlite3 /app/data/weather.db \
  "SELECT timestamp, temp_outdoor, humidity_outdoor
   FROM weather_measurements
   ORDER BY timestamp DESC LIMIT 5;"
```

#### 3. Manage

```bash
# Stop the service
docker-compose stop

# Restart the service
docker-compose restart

# View logs
docker-compose logs -f

# Update and restart
docker-compose down
docker-compose build
docker-compose up -d
```

For full deployment instructions to a Linode VPS, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Project Structure

```
.
├── config.example.yaml          # Configuration template
├── config.yaml                  # Your config (gitignored)
├── requirements.txt             # Python dependencies
├── collector.py                 # Main collection service
├── test_setup.py               # Configuration validation script
├── src/weather_logger/         # Main package
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── models.py               # Data models
│   ├── api_client.py           # Ambient Weather API client
│   ├── database.py             # SQLite operations
│   └── utils.py                # Utilities and logging
├── tests/                      # Unit tests
├── data/                       # SQLite database
└── logs/                       # Application logs
```

## Configuration

Edit `config.yaml`:

```yaml
ambient_weather:
  api_key: "YOUR_API_KEY"
  application_key: "YOUR_APPLICATION_KEY"
  mac_address: "YOUR_DEVICE_MAC"
  poll_interval: 60

database:
  path: "data/weather.db"

logging:
  level: "INFO"
  file: "logs/weather_logger.log"
```

## Database Schema

Weather data is stored in SQLite with the following structure:

**Table: `weather_measurements`**
- Timestamp (indexed)
- Temperature fields (outdoor, indoor, feels like, dew point)
- Humidity fields (outdoor, indoor)
- Pressure fields (relative, absolute)
- Wind data (speed, gust, direction)
- Rain accumulation (hourly, daily, monthly, yearly)
- Solar/UV data (solar radiation, UV index)
- Device MAC address

**Indexes:**
- `idx_timestamp` - For time-based queries
- `idx_mac_address` - For device filtering
- `idx_mac_timestamp` - Composite for efficient device+time queries

## Querying Data

Use SQLite to query your data:

```bash
# View latest 5 measurements
sqlite3 data/weather.db "SELECT timestamp, temp_outdoor, humidity_outdoor FROM weather_measurements ORDER BY timestamp DESC LIMIT 5;"

# Get daily average temperature
sqlite3 data/weather.db "SELECT DATE(timestamp) as day, AVG(temp_outdoor) as avg_temp FROM weather_measurements GROUP BY day;"

# Count total records
sqlite3 data/weather.db "SELECT COUNT(*) FROM weather_measurements;"
```

## Running in Production

The collector is designed to run as a long-lived service:

```bash
# Run in background with nohup
nohup python3 collector.py > collector.out 2>&1 &

# Or use systemd, Docker, or your container orchestration platform
```

The service handles:
- `SIGTERM` - Graceful shutdown (Docker stop)
- `SIGINT` - Keyboard interrupt (Ctrl+C)
- API rate limiting (1 request/second)
- Automatic retries on transient errors
- Duplicate prevention in database

## Development

### Run Tests

```bash
# Run unit tests
python3 -m pytest tests/

# Test specific module
python3 -m pytest tests/test_config.py -v
```

### View Logs

```bash
# Tail logs
tail -f logs/weather_logger.log

# View recent errors
grep ERROR logs/weather_logger.log
```

## Automated Backups

The system includes automated backup functionality to S3-compatible storage:

- **Manual Backup**: `python3 backup.py`
- **Scheduled Backups**: `python3 backup_scheduler.py` (runs daily at configured time)
- **Supports**: AWS S3 and Backblaze B2
- **Features**: Automatic cleanup of old backups based on retention policy

To configure backups, edit the `backup` section in `config.yaml`:

```yaml
backup:
  enabled: true
  bucket_name: "weather-logger-backups"
  endpoint_url: "https://s3.us-west-002.backblazeb2.com"  # For B2, empty for AWS S3
  access_key_id: "YOUR_ACCESS_KEY"
  secret_access_key: "YOUR_SECRET_KEY"
  retention_days: 30
  schedule: "0 2 * * *"  # Daily at 2:00 AM
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed backup setup instructions.

## Next Steps

- **Phase 6**: Setup Grafana dashboards for data visualization

See [TODO.md](TODO.md) for detailed implementation plan.

## API Reference

- [Ambient Weather API Documentation](https://ambientweather.docs.apiary.io/)
- [Ambient Weather Account Dashboard](https://ambientweather.net/)

## License

MIT

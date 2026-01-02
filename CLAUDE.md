# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a weather station data logger that collects data from the Ambient Weather API and stores it in SQLite for visualization with Grafana. The system runs as a long-lived service using WebSocket connections for realtime data collection (preferred) or REST API polling (legacy). The repository also hosts two Hugo static sites: a public blog (port 80/443) and a private house manual (port 8080 with basic auth).

## Repository Structure

```
.
├── weather-logger/          # Weather data collection service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── realtime_collector.py
│   ├── backup.py
│   ├── backup_scheduler.py
│   ├── test_setup.py
│   ├── src/
│   │   └── weather_logger/
│   └── tests/
├── hugo-site/               # Public blog (Hugo + nginx)
│   ├── Dockerfile           # Multi-stage: Hugo build → nginx
│   ├── nginx.conf           # SSL-ready config (HTTP/HTTPS)
│   └── (Hugo site files)
├── house-manual/            # Private house manual (Hugo + nginx + auth)
│   ├── Dockerfile           # Multi-stage: Hugo build → nginx
│   ├── nginx.conf           # Port 8080 with basic auth
│   ├── .htpasswd            # Password file (gitignored)
│   └── (Hugo site files)
├── grafana/                 # Grafana provisioning configs
│   └── provisioning/
├── data/                    # SQLite database (persistent)
├── logs/                    # Application logs (persistent)
├── certs/                   # SSL certificates (gitignored)
├── config.yaml              # Weather logger configuration
├── docker-compose.yml       # Multi-service orchestration
├── CLOUDFLARE.md            # Cloudflare + SSL setup guide
├── README.md
└── CLAUDE.md
```

Each service is in its own directory with its own Dockerfile, following Docker best practices of one service per container.

## Architecture

### Core Components

**Weather Logger Service** (`weather-logger/`):
- `realtime_collector.py` - Primary collector using Socket.IO WebSocket for realtime updates (once per minute)
- `collector.py` - Legacy polling collector using REST API (deprecated, use realtime)
- `src/weather_logger/api_client.py` - Ambient Weather API client with rate limiting (1 req/sec)
- `src/weather_logger/database.py` - SQLite operations with WAL mode and indexed queries
- `src/weather_logger/models.py` - WeatherMeasurement data model with API response parsing
- `src/weather_logger/config.py` - YAML-based configuration with environment variable overrides

**Backup Service** (`weather-logger/`):
- `backup.py` - Manual backup script for SQLite to S3-compatible storage
- `backup_scheduler.py` - Automated daily backup service with tiered retention (45 days daily + monthly forever)
- Supports both AWS S3 and Backblaze B2

**Static Site Services**:

*Public Blog* (`hugo-site/`):
- Hugo static site generator with nginx web server
- Multi-stage Docker build (build with Hugo, serve with nginx)
- Configured with gzip compression and security headers
- Serves on ports 80/443 (HTTPS-ready, optionally proxied through Cloudflare)
- No authentication required

*House Manual* (`house-manual/`):
- Hugo static site with nginx and HTTP basic authentication
- Multi-stage Docker build (build with Hugo, serve with nginx)
- Serves on port 8080
- Username/password protection via `.htpasswd`
- Not proxied through Cloudflare (direct access only)

**Visualization Service**:
- Grafana dashboard with SQLite datasource plugin
- Pre-built dashboard at `grafana/provisioning/dashboards/weather-dashboard.json`
- Dashboard includes temperature, humidity, pressure, wind, rain, and solar panels

### Database Schema

**Table: `weather_measurements`**
- Primary key: `id` (auto-increment)
- Unique constraint: `(timestamp, mac_address)` prevents duplicates
- Indexes: `idx_timestamp`, `idx_mac_address`, `idx_mac_timestamp` for efficient queries
- Uses `INSERT OR IGNORE` pattern for duplicate prevention

**Table: `devices`**
- Stores device metadata (name, location, last_seen)
- Updated automatically when measurements are stored

### Configuration System

Configuration hierarchy (highest priority first):
1. Environment variables with `WEATHER_LOGGER_` prefix (e.g., `WEATHER_LOGGER_DATABASE_PATH`)
2. `config.yaml` file
3. Defaults in code

Key config sections:
- `ambient_weather` - API credentials and device MAC address
- `database` - SQLite path
- `logging` - Log level, file path, format
- `backup` - S3 credentials, retention policy, schedule

## Common Commands

### Development

```bash
# Weather Logger Service
cd weather-logger

# Install dependencies
pip install -r requirements.txt

# Run tests
python3 -m pytest tests/
python3 -m pytest tests/test_config.py -v

# Test API connectivity and configuration
python3 test_setup.py

# Run realtime collector (preferred)
python3 realtime_collector.py

# Run legacy polling collector
python3 collector.py

# Public Blog Hugo Site
cd hugo-site

# Initialize a new Hugo site (if starting fresh)
hugo new site . --force

# Or add your existing Hugo content to this directory
# Run Hugo dev server locally
hugo server -D

# House Manual Hugo Site
cd house-manual

# Initialize a new Hugo site
hugo new site . --force

# Create password file for basic auth
htpasswd -c .htpasswd yourusername
# Enter password when prompted

# Run Hugo dev server locally
hugo server -D -p 1314
```

### Database Operations

```bash
# View latest measurements
sqlite3 data/weather.db "SELECT timestamp, temp_outdoor, humidity_outdoor FROM weather_measurements ORDER BY timestamp DESC LIMIT 5;"

# Count records
sqlite3 data/weather.db "SELECT COUNT(*) FROM weather_measurements;"

# Get daily averages
sqlite3 data/weather.db "SELECT DATE(timestamp) as day, AVG(temp_outdoor) as avg_temp FROM weather_measurements GROUP BY day;"
```

### Docker

```bash
# Build and start all services (collector + backup + grafana + sites)
docker-compose build
docker-compose up -d

# Build individual services
docker-compose build weather-logger
docker-compose build static-site
docker-compose build house-manual

# View logs
docker-compose logs -f weather-logger
docker-compose logs -f backup-scheduler
docker-compose logs -f grafana
docker-compose logs -f static-site
docker-compose logs -f house-manual

# Check database
docker exec weather-logger sqlite3 /app/data/weather.db "SELECT COUNT(*) FROM weather_measurements;"

# Restart services
docker-compose restart
docker-compose restart static-site      # Restart only public blog
docker-compose restart house-manual     # Restart only house manual

# Stop and remove
docker-compose down

# Start/stop individual services
docker-compose up -d static-site
docker-compose stop house-manual
```

### Backup Operations

```bash
# From weather-logger directory
cd weather-logger

# Manual backup
python3 backup.py

# Run backup scheduler (background service)
python3 backup_scheduler.py
```

## Important Patterns

### Rate Limiting
The Ambient Weather API has a 1 request/second rate limit. The `AmbientWeatherClient._enforce_rate_limit()` method automatically handles this by sleeping between requests. Never bypass this rate limiting.

### Duplicate Prevention
Database inserts use `INSERT OR IGNORE` based on the `(timestamp, mac_address)` unique constraint. This means duplicate measurements are silently skipped. The insert methods return `None` for duplicates and a row ID for successful inserts.

### Signal Handling
Both collectors implement graceful shutdown via signal handlers:
- `SIGINT` (Ctrl+C) - User interrupt
- `SIGTERM` - Docker stop command
Always use these signals for clean shutdown rather than killing the process.

### WebSocket Reconnection
The realtime collector uses Socket.IO with automatic reconnection:
- Infinite retry attempts
- Exponential backoff (1-10 seconds)
- Maintains subscription after reconnect

### Timezone Handling
All timestamps are stored in UTC (ISO 8601 format). The Docker containers use `TZ=America/Los_Angeles` environment variable for log display only. Database timestamps remain in UTC.

## Testing

Unit tests use mocking for external dependencies (API calls, database connections). Test files mirror the source structure:
- `weather-logger/tests/test_api_client.py` - API client tests
- `weather-logger/tests/test_database.py` - Database operation tests
- `weather-logger/tests/test_config.py` - Configuration loading tests

The `weather-logger/test_setup.py` script is for integration testing - it validates configuration and tests actual API connectivity.

## Grafana Integration

Grafana accesses the SQLite database directly via the `frser-sqlite-datasource` plugin. The database file must be mounted to `/var/lib/weather-data/` inside the Grafana container with write access (SQLite needs write permissions for temp files, even for read-only queries).

The provisioned dashboard includes queries with timezone conversion using SQLite's `datetime()` function. When modifying dashboard queries, maintain timezone handling to match the `TZ` environment variable.

## API Credentials

Get API credentials from: https://ambientweather.net/account

Required configuration:
- `api_key` - Your Ambient Weather API key
- `application_key` - Your Ambient Weather Application key
- `mac_address` - Your weather station device MAC address (format: `XX:XX:XX:XX:XX:XX`)

The MAC address can be found in your Ambient Weather account under "Device MAC Address" for your registered weather station.

## Backup Retention Policy

The backup system uses tiered retention:
- **Daily backups**: Keep all backups from the last 45 days
- **Monthly backups**: Keep one backup per month (the first backup of each month) forever

This provides granular recent history while maintaining long-term monthly snapshots without unbounded storage growth.

## Service Independence

The repository follows Docker best practices with separate containers for each service:
- **weather-logger** - Python application, runs 24/7, collects data every minute
- **backup-scheduler** - Python application, runs daily backups on schedule
- **grafana** - Official Grafana image, port 3000, accesses SQLite database read-only
- **static-site** - Nginx web server, ports 80/443, serves pre-built Hugo static files (public blog)
- **house-manual** - Nginx web server, port 8080, serves pre-built Hugo static files with basic auth

Each service can be independently:
- Started/stopped/restarted without affecting others
- Updated and redeployed
- Scaled (though most are single-instance by design)
- Debugged with isolated logs

The services share minimal state:
- Weather logger writes to `data/weather.db`
- Grafana reads from `data/weather.db`
- Weather services read from `config.yaml`
- Static sites are completely independent (no shared data)

## Port Allocation

- **80** - Public blog (HTTP)
- **443** - Public blog (HTTPS, when SSL configured)
- **3000** - Grafana dashboard
- **8080** - House manual (with basic auth)

Weather logger and backup services have no exposed ports (background processes only).

## Static Site Setup

### Public Blog (hugo-site/)

1. Initialize Hugo site: `cd hugo-site && hugo new site . --force`
2. Add theme and content
3. Build: `docker-compose build static-site`
4. Deploy: `docker-compose up -d static-site`
5. Access: `http://your-server-ip/` or `https://your-domain.com/` (after SSL setup)

Optional: Set up Cloudflare for caching and free SSL (see CLOUDFLARE.md)

### House Manual (house-manual/)

1. Initialize Hugo site: `cd house-manual && hugo new site . --force`
2. Create password file: `htpasswd -c .htpasswd yourusername`
3. Add content (house docs, manuals, etc.)
4. Build: `docker-compose build house-manual`
5. Deploy: `docker-compose up -d house-manual`
6. Access: `http://your-server-ip:8080/` (enter username/password)

The house manual should NOT be proxied through Cloudflare to maintain direct access and avoid caching issues with authentication.

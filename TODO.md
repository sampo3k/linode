# Weather Station Data Logger

A Docker container that collects data from Ambient Weather API and stores it in a time-series database with automated backups.

## Project Overview

- Pull data from ambientweather.net API once per minute
- Store relevant fields in SQLite database
- Enable Grafana dashboard integration
- Daily automated backups to S3-compatible storage (B2/S3)

## TODO

### Phase 1: API Integration ✓ COMPLETED
- [x] Review Ambient Weather API documentation
- [x] Create API client module
  - [x] Implement authentication (API key + Application key)
  - [x] Create function to fetch device data
  - [x] Parse and extract once-per-minute fields
  - [x] Handle API rate limits and errors
- [x] Test API connectivity and data retrieval

### Phase 2: Database Setup ✓ COMPLETED
- [x] Design SQLite database schema
  - [x] Create table for weather measurements
  - [x] Add indexes for time-based queries
  - [x] Store device metadata
- [x] Implement database module
  - [x] Create connection management
  - [x] Write insert operations for weather data
  - [x] Add data retention/cleanup logic (optional)
- [x] Test database operations

### Phase 3: Data Collection Service ✓ COMPLETED
- [x] Create main collection service
  - [x] Implement once-per-minute polling loop
  - [x] Add error handling and retry logic
  - [x] Implement logging
- [x] Test continuous data collection
- [x] Add graceful shutdown handling

### Phase 4: Backup System ✓ COMPLETED
- [x] Implement S3-compatible backup module
  - [x] Support for AWS S3
  - [x] Support for Backblaze B2
  - [x] Configurable credentials and bucket
- [x] Create backup script (backup.py)
  - [x] Upload SQLite database to S3-compatible storage
  - [x] Add timestamp to backup filename
  - [x] Implement backup retention policy
  - [x] List and restore backup functionality
- [x] Create backup scheduler (backup_scheduler.py)
  - [x] Cron-like scheduling (e.g., "0 2 * * *" for daily at 2am)
  - [x] Graceful shutdown handling
  - [x] Automatic old backup cleanup
- [x] Docker integration (optional service in docker-compose.yml)
- [x] Documentation (DEPLOYMENT.md with B2/S3 setup guide)

### Phase 5: Docker Container ✓ COMPLETED
- [x] Create Dockerfile
  - [x] Choose base image (Python 3.11-slim)
  - [x] Install dependencies
  - [x] Copy application code
  - [x] Set up volume mounts for database
- [x] Create docker-compose.yml
  - [x] Define environment variables
  - [x] Configure volume mounts
  - [x] Set up resource limits and logging
- [x] Create .dockerignore file
- [x] Document deployment process
  - [x] Ambient Weather API credentials
  - [x] Configuration via config.yaml
  - [x] Volume mounting for data persistence
  - [x] Full Linode VPS deployment guide

### Phase 6: Grafana Integration ✓ COMPLETED
- [x] Add Grafana service to docker-compose.yml
- [x] Install SQLite data source plugin (frser-sqlite-datasource)
- [x] Configure data source provisioning
- [x] Create pre-built Weather Station Dashboard with 10 panels:
  - [x] Current temperature, humidity, wind speed gauges
  - [x] Temperature trends (outdoor, indoor, feels like, dew point)
  - [x] Humidity (indoor/outdoor)
  - [x] Barometric pressure
  - [x] Rainfall accumulation
  - [x] Wind data (speed, gusts, direction)
  - [x] Solar radiation and UV index
- [x] Document Grafana setup and usage in DEPLOYMENT.md
- [x] Deploy to production (Linode VPS)
- [x] Verify SQLite plugin installation
- [x] Test dashboard with live data

### Phase 7: Documentation & Testing ✓ MOSTLY COMPLETED
- [x] Write README.md
  - [x] Installation instructions
  - [x] Configuration guide
  - [x] API setup instructions
  - [x] Backup configuration
  - [x] Grafana setup
- [x] Add example configuration files (config.example.yaml)
- [x] Create troubleshooting guide (in DEPLOYMENT.md)
- [x] End-to-end testing (tested on production Linode VPS)

## Technical Decisions Made

- [x] Language/runtime: **Python 3.11** (chosen for excellent library support)
- [x] Database: **SQLite** with WAL mode (simple, file-based, perfect for single-device data)
- [x] Backup storage: **Backblaze B2** (S3-compatible, cost-effective, 10GB free tier)
- [x] Backup timing: **Daily at 2:00 AM** (Pacific Time)
- [x] Data retention policy: **Tiered retention**
  - Keep all daily backups for last 45 days
  - Keep one backup per month forever (older than 45 days)
- [x] Data collection: **Realtime WebSocket API** (once per minute updates)
- [x] Deployment: **Docker** with docker-compose (3 containers: collector, backup scheduler, Grafana)
- [x] Visualization: **Grafana** with SQLite data source plugin
- [x] Monitoring: Health checks on containers, auto-restart on failure

## API Fields to Store

Reference: https://ambientweather.docs.apiary.io/#introduction/helper-libraries

Common once-per-minute fields:
- Temperature (indoor/outdoor)
- Humidity (indoor/outdoor)
- Pressure
- Wind speed/direction
- Rain rate/accumulation
- Solar radiation
- UV index
- Battery levels
- Timestamp

## Resources

- API Documentation: https://ambientweather.docs.apiary.io/
- Ambient Weather Dashboard: https://ambientweather.net/

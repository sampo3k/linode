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

### Phase 6: Grafana Integration Prep
- [ ] Document database schema for Grafana
- [ ] Create example Grafana queries
- [ ] Test SQLite data source plugin compatibility
- [ ] (Optional) Consider adding Grafana to docker-compose

### Phase 7: Documentation & Testing
- [ ] Write README.md
  - [ ] Installation instructions
  - [ ] Configuration guide
  - [ ] API setup instructions
  - [ ] Backup configuration
- [ ] Add example configuration files
- [ ] Create troubleshooting guide
- [ ] End-to-end testing

## Technical Decisions Made

- [x] Language/runtime: **Python** (chosen for excellent library support)
- [x] Database: **SQLite** (simple, file-based, perfect for single-device data)
- [x] Backup storage: **Backblaze B2** (S3-compatible, cost-effective)
- [ ] Backup timing (specific time of day?)
- [ ] Data retention policy
- [ ] Monitoring/alerting for failures

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

# Deployment Guide - Weather Logger on Linode

This guide covers deploying the Weather Logger to a Linode VPS using Docker.

## Prerequisites

- Linode VPS (1GB RAM minimum recommended)
- SSH access to your Linode
- Docker and Docker Compose installed on the Linode

## Step 1: Prepare Your Linode

### SSH into your Linode

```bash
ssh root@your-linode-ip
```

### Install Docker and Docker Compose

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install -y docker-compose

# Verify installation
docker --version
docker-compose --version

# Enable Docker to start on boot
systemctl enable docker
```

## Step 2: Transfer Project Files

From your local machine, copy the project to your Linode:

```bash
# Create project directory on Linode
ssh root@your-linode-ip "mkdir -p /opt/weather-logger"

# Copy project files
scp -r /Users/nate/src/linode/* root@your-linode-ip:/opt/weather-logger/

# Or use rsync for better performance
rsync -avz --exclude 'data/' --exclude 'logs/' --exclude '.git/' \
  /Users/nate/src/linode/ root@your-linode-ip:/opt/weather-logger/
```

## Step 3: Configure the Application

SSH into your Linode and configure:

```bash
ssh root@your-linode-ip
cd /opt/weather-logger

# Edit config.yaml with your credentials
nano config.yaml
# Add your API keys and device MAC address

# Create necessary directories
mkdir -p data logs

# Set proper permissions
chmod 600 config.yaml
```

## Step 4: Build and Start the Container

```bash
cd /opt/weather-logger

# Build the Docker image
docker-compose build

# Start the service
docker-compose up -d

# Verify it's running
docker-compose ps

# View logs
docker-compose logs -f weather-logger
```

## Step 5: Verify Data Collection

After a minute or two, check that data is being collected:

```bash
# Check database
docker exec weather-logger sqlite3 /app/data/weather.db \
  "SELECT COUNT(*) FROM weather_measurements;"

# View latest records
docker exec weather-logger sqlite3 /app/data/weather.db \
  "SELECT timestamp, temp_outdoor, humidity_outdoor
   FROM weather_measurements
   ORDER BY timestamp DESC
   LIMIT 5;"

# Monitor logs in real-time
docker-compose logs -f
```

## Docker Commands

### Managing the Service

```bash
# Start the service
docker-compose up -d

# Stop the service
docker-compose stop

# Restart the service
docker-compose restart

# Stop and remove container
docker-compose down

# View logs
docker-compose logs -f

# View last 50 lines of logs
docker-compose logs --tail=50

# Check service status
docker-compose ps
```

### Updating the Application

```bash
# Pull latest code
cd /opt/weather-logger
git pull  # If using git

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Backup the Database

```bash
# Create backup
docker exec weather-logger sqlite3 /app/data/weather.db \
  ".backup /app/data/weather_backup_$(date +%Y%m%d).db"

# Copy backup to local machine
scp root@your-linode-ip:/opt/weather-logger/data/weather_backup_*.db ~/backups/
```

## Monitoring

### Check Container Health

```bash
# View container stats
docker stats weather-logger

# Check health status
docker inspect weather-logger | grep -A 10 Health
```

### View Resource Usage

```bash
# Memory usage
docker stats --no-stream weather-logger

# Disk usage
du -sh /opt/weather-logger/data/
```

### Log Management

The Docker Compose configuration includes log rotation:
- Max file size: 10MB
- Max files kept: 3
- Total max log size: ~30MB

To view logs:

```bash
# Last 100 lines
docker-compose logs --tail=100

# Follow logs in real-time
docker-compose logs -f

# View logs for specific time range
docker-compose logs --since 1h

# Search logs
docker-compose logs | grep ERROR
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker-compose logs

# Check if port is already in use
# (Not applicable for this service, but good to know)

# Verify config.yaml is correct
cat /opt/weather-logger/config.yaml

# Check file permissions
ls -la /opt/weather-logger/
```

### No Data Being Collected

```bash
# Check logs for errors
docker-compose logs -f | grep ERROR

# Verify API connectivity from container
docker exec -it weather-logger python3 -c "
from src.weather_logger import Config, AmbientWeatherClient
config = Config.load_from_file('config.yaml')
client = AmbientWeatherClient(
    config.get('ambient_weather.api_key'),
    config.get('ambient_weather.application_key')
)
print('Testing connection...')
print(client.test_connection())
"

# Check database permissions
docker exec weather-logger ls -la /app/data/
```

### Container Keeps Restarting

```bash
# View recent container logs
docker-compose logs --tail=100

# Check for crash reasons
docker inspect weather-logger | grep -A 20 State

# Remove and recreate
docker-compose down
docker-compose up -d
```

## Firewall Configuration

The weather logger doesn't need any incoming ports open. It only makes outbound connections to:
- Ambient Weather API (rt2.ambientweather.net, port 443)

If you have a firewall configured (recommended):

```bash
# No incoming ports needed for weather-logger
# Just ensure outbound HTTPS is allowed

# Example with ufw:
ufw allow outgoing 443/tcp
```

## Automatic Startup

Docker Compose is configured with `restart: unless-stopped`, so the container will:
- Start automatically when the server boots
- Restart automatically if it crashes
- Not restart if you manually stop it

To check the restart policy:

```bash
docker inspect weather-logger | grep -A 5 RestartPolicy
```

## Switching Between Realtime and Polling Collectors

Edit `docker-compose.yml` and change the command:

```yaml
# For realtime collector (default)
command: ["python3", "realtime_collector.py"]

# For polling collector
command: ["python3", "collector.py"]
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

## Resource Requirements

### Minimum Specs
- **RAM**: 256MB (128MB for container + 128MB overhead)
- **CPU**: 0.1 vCPU (very low usage)
- **Disk**: 100MB + database storage
- **Network**: Minimal (< 1MB/day)

### Storage Growth
- **Per day**: ~280 KB
- **Per month**: ~8 MB
- **Per year**: ~100 MB

A 1GB Linode ($5/month) is more than sufficient for this application.

## Security Best Practices

1. **Protect config.yaml**:
   ```bash
   chmod 600 /opt/weather-logger/config.yaml
   chown root:root /opt/weather-logger/config.yaml
   ```

2. **Regular updates**:
   ```bash
   apt-get update && apt-get upgrade -y
   docker-compose pull
   ```

3. **Firewall**:
   ```bash
   # Only allow SSH and any other needed services
   ufw allow OpenSSH
   ufw enable
   ```

4. **SSH hardening**:
   - Use SSH keys instead of passwords
   - Disable root login
   - Change default SSH port

## Configuring Automated Backups (Phase 4)

The weather logger includes automated backup functionality to S3-compatible storage (AWS S3 or Backblaze B2).

### Setting Up Backblaze B2 (Recommended)

1. **Create Backblaze B2 Account**:
   - Go to https://www.backblaze.com/b2/sign-up.html
   - Sign up for an account (10GB free storage)

2. **Create a Bucket**:
   ```
   - Log into Backblaze B2 dashboard
   - Click "Buckets" → "Create a Bucket"
   - Name: weather-logger-backups (or your choice)
   - Files in bucket: Private
   - Encryption: Disabled (or enable if you prefer)
   ```

3. **Create Application Key**:
   ```
   - Go to "App Keys" → "Add a New Application Key"
   - Name: weather-logger-backup
   - Access: Read and Write
   - Allow access to bucket: weather-logger-backups
   - Copy the keyID (access key) and applicationKey (secret key)
   - IMPORTANT: Save these immediately - you can't view the secret again!
   ```

4. **Get B2 Endpoint URL**:
   - Find your bucket region in the bucket details
   - Common endpoints:
     - US West: `https://s3.us-west-002.backblazeb2.com`
     - US East: `https://s3.us-east-005.backblazeb2.com`
     - EU Central: `https://s3.eu-central-003.backblazeb2.com`

### Setting Up AWS S3 (Alternative)

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://weather-logger-backups --region us-west-2
   ```

2. **Create IAM User**:
   - Create IAM user with S3 write permissions
   - Generate access key and secret key
   - Leave endpoint_url empty in config

### Configure Backups in config.yaml

Edit your `config.yaml` on the Linode:

```bash
ssh nate@farad.space
cd ~/weather-logger
nano config.yaml
```

Update the backup section:

```yaml
backup:
  # Enable backups
  enabled: true

  # Your B2 bucket name
  bucket_name: "weather-logger-backups"

  # B2 endpoint (leave empty for AWS S3)
  endpoint_url: "https://s3.us-west-002.backblazeb2.com"

  # B2 application key credentials
  access_key_id: "YOUR_B2_KEY_ID"
  secret_access_key: "YOUR_B2_APPLICATION_KEY"

  # Backup file prefix in bucket
  prefix: "weather-backups/"

  # Keep backups for 30 days (0 = keep forever)
  retention_days: 30

  # Backup schedule: Daily at 2am (cron format)
  schedule: "0 2 * * *"
```

### Test Manual Backup

Before enabling the scheduler, test that backups work:

```bash
cd ~/weather-logger

# Run a manual backup
docker exec weather-logger python3 backup.py

# Should see output like:
# ✓ Backup completed successfully
# Current backups (1):
#   - weather-backups/weather_20260101_143022.db (0.28 MB)
```

### Enable Backup Scheduler

Once manual backup works, enable the automated scheduler:

1. **Edit docker-compose.yml**:
   ```bash
   nano docker-compose.yml
   ```

2. **Uncomment the backup-scheduler service** (around line 75):
   ```yaml
   backup-scheduler:
     build:
       context: .
       dockerfile: Dockerfile
     image: weather-logger:latest
     container_name: weather-backup-scheduler
     restart: unless-stopped
     command: ["python3", "backup_scheduler.py"]
     volumes:
       - ./config.yaml:/app/config.yaml:ro
       - ./data:/app/data
       - ./logs:/app/logs
     environment:
       - TZ=America/Los_Angeles
     deploy:
       resources:
         limits:
           cpus: '0.2'
           memory: 128M
         reservations:
           cpus: '0.05'
           memory: 32M
   ```

3. **Restart services**:
   ```bash
   docker-compose up -d

   # Verify both containers are running
   docker-compose ps

   # Should see:
   # weather-logger          running
   # weather-backup-scheduler  running
   ```

4. **Check scheduler logs**:
   ```bash
   docker-compose logs -f backup-scheduler

   # Should see:
   # Backup scheduler running - backups at 02:00 daily
   # Next backup in X.X hours at YYYY-MM-DD HH:MM:SS
   ```

### Backup Commands

```bash
# Run manual backup
docker exec weather-logger python3 backup.py

# List backups in B2
docker exec weather-logger python3 -c "
from src.weather_logger import Config
from backup import BackupManager
config = Config.load_from_file('config.yaml')
mgr = BackupManager(config)
for b in mgr.list_backups():
    print(f\"{b['key']}: {b['size']/1024/1024:.2f} MB - {b['last_modified']}\")
"

# Restore from backup
docker exec weather-logger python3 -c "
from src.weather_logger import Config
from backup import BackupManager
config = Config.load_from_file('config.yaml')
mgr = BackupManager(config)
mgr.restore_backup('weather-backups/weather_20260101_143022.db', 'data/weather_restored.db')
"

# Check scheduler status
docker-compose logs backup-scheduler | tail -20
```

### Backup Storage Estimates

- **Per backup**: ~280 KB (varies with data retention)
- **Per month** (30 backups): ~8 MB
- **Per year** (365 backups, 30-day retention): ~8 MB (old backups auto-deleted)
- **Cost**: Well within Backblaze B2's 10GB free tier

### Troubleshooting Backups

**Backup fails with "Access Denied"**:
- Verify your B2 application key has read/write access
- Check bucket name matches exactly (case-sensitive)
- Ensure endpoint_url matches your bucket region

**Backup scheduler not running**:
```bash
# Check if backups are enabled
docker exec weather-logger grep "enabled:" /app/config.yaml

# Verify scheduler container is running
docker-compose ps backup-scheduler

# Check for errors in logs
docker-compose logs backup-scheduler | grep ERROR
```

**Old backups not being deleted**:
- Verify retention_days is set correctly
- Check logs for cleanup messages
- Manually list backups to verify dates

## Setting Up Grafana Dashboards (Phase 6)

Grafana is included in the Docker setup to visualize your weather data with interactive dashboards.

### Accessing Grafana

Once deployed, Grafana is accessible at:

**URL**: `http://your-linode-ip:3000` or `http://farad.space:3000`

**Default Login**:
- Username: `nate` (or whatever you set in `GF_SECURITY_ADMIN_USER`)
- Password: `haydencamille123` (or whatever you set in `GF_SECURITY_ADMIN_PASSWORD`)

**Important**: Change the default password after first login!

### What's Included

The deployment automatically provisions:

1. **SQLite Data Source**: Connected to your weather database
2. **Weather Station Dashboard**: Pre-built dashboard with 10 panels

### Dashboard Panels

The Weather Station Dashboard includes:

1. **Current Temperature** - Gauge showing latest outdoor temperature
2. **Current Humidity** - Gauge showing outdoor humidity
3. **Wind Speed** - Current wind speed gauge
4. **Temperature Trends** - Line graph with:
   - Outdoor temperature
   - Indoor temperature
   - Feels like temperature
   - Dew point
5. **Humidity** - Dual-axis showing indoor/outdoor humidity
6. **Barometric Pressure** - Relative and absolute pressure trends
7. **Rainfall (Hourly)** - Bar chart of hourly rain accumulation
8. **Wind** - Wind speed, gusts, and direction over time
9. **Solar Radiation & UV Index** - Solar and UV data

**Default Settings**:
- Time range: Last 24 hours
- Auto-refresh: Every 1 minute
- Timezone: America/Los_Angeles

### Managing Grafana

**View Grafana logs**:
```bash
docker compose logs -f grafana
```

**Restart Grafana**:
```bash
docker compose restart grafana
```

**Access Grafana shell** (for troubleshooting):
```bash
docker exec -it weather-grafana /bin/bash
```

### Customizing Dashboards

**To edit panels**:
1. Click on panel title → Edit
2. Modify query, visualization, or settings
3. Click Apply to save changes

**To create new dashboards**:
1. Click "+" icon → Dashboard
2. Add Panel → Select "Weather SQLite" data source
3. Write SQL queries against `weather_measurements` table

**Example queries**:

```sql
-- Temperature over time
SELECT timestamp, temp_outdoor
FROM weather_measurements
WHERE timestamp >= datetime('now', '-24 hours')
ORDER BY timestamp

-- Daily temperature averages
SELECT
  DATE(timestamp) as day,
  AVG(temp_outdoor) as avg_temp,
  MIN(temp_outdoor) as min_temp,
  MAX(temp_outdoor) as max_temp
FROM weather_measurements
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY day
ORDER BY day

-- Current conditions
SELECT
  temp_outdoor,
  humidity_outdoor,
  wind_speed,
  pressure_relative
FROM weather_measurements
ORDER BY timestamp DESC
LIMIT 1
```

### Firewall Configuration

If accessing Grafana remotely, ensure port 3000 is open:

```bash
# Using ufw
sudo ufw allow 3000/tcp

# Check firewall status
sudo ufw status
```

**For production**, consider:
- Setting up HTTPS with reverse proxy (nginx/caddy)
- Using a subdomain (e.g., grafana.yourdomain.com)
- Restricting access by IP address

### Security Best Practices

1. **Change default password**:
   - Go to profile icon → Preferences → Change Password

2. **Disable anonymous access** (already done):
   ```yaml
   - GF_AUTH_ANONYMOUS_ENABLED=false
   ```

3. **Use environment-specific passwords**:
   - Edit docker-compose.yml
   - Update `GF_SECURITY_ADMIN_PASSWORD`
   - Restart: `docker compose up -d`

4. **Set up HTTPS**:
   - Use a reverse proxy (nginx, caddy, traefik)
   - Obtain SSL certificate (Let's Encrypt)
   - Forward HTTPS to Grafana port 3000

### Troubleshooting Grafana

**Grafana won't start**:
```bash
# Check container status
docker compose ps grafana

# View logs
docker compose logs grafana | tail -50

# Check for permission errors on provisioning files
ls -la grafana/provisioning/
```

**Data source not working**:
```bash
# Verify database is accessible
docker exec weather-grafana ls -la /var/lib/weather-data/weather.db

# Check data source configuration
docker exec weather-grafana cat /etc/grafana/provisioning/datasources/sqlite.yaml

# Test SQLite connection from container
docker exec weather-grafana sqlite3 /var/lib/weather-data/weather.db "SELECT COUNT(*) FROM weather_measurements;"
```

**Dashboard not showing data**:
- Verify you have weather data collected: `docker exec weather-logger sqlite3 /app/data/weather.db "SELECT COUNT(*) FROM weather_measurements;"`
- Check time range (default is last 24 hours)
- Verify SQLite plugin is installed: Check logs for "frser-sqlite-datasource"
- Try running queries manually in Grafana's Explore view

**Plugin installation failed**:
```bash
# Check if plugin is installed
docker exec weather-grafana ls /var/lib/grafana/plugins/

# Manually install plugin
docker exec weather-grafana grafana-cli plugins install frser-sqlite-datasource

# Restart Grafana
docker compose restart grafana
```

### Grafana Storage

Grafana data is persisted in a Docker volume:

```bash
# List volumes
docker volume ls | grep grafana

# Inspect volume
docker volume inspect weather-logger_grafana-data

# Backup Grafana data
docker run --rm -v weather-logger_grafana-data:/data -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz -C /data .

# Restore Grafana data
docker run --rm -v weather-logger_grafana-data:/data -v $(pwd):/backup alpine tar xzf /backup/grafana-backup.tar.gz -C /data
```

### Updating Grafana

To update to the latest Grafana version:

```bash
# Pull latest image
docker compose pull grafana

# Restart with new image
docker compose up -d grafana

# Verify new version
docker compose logs grafana | grep "Starting Grafana"
```

### Additional Resources

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [SQLite Data Source Plugin](https://github.com/fr-ser/grafana-sqlite-datasource)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

## Next Steps

After deployment:
1. Let the collector run for a few hours to build up data
2. Configure automated backups to B2 (see above)
3. Access Grafana dashboards at http://your-server:3000
4. Customize dashboards and set up alerts as needed
5. Configure monitoring/alerting for the services

## Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify configuration: `cat config.yaml`
3. Test API connection manually
4. Check disk space: `df -h`
5. Check system resources: `free -h` and `top`

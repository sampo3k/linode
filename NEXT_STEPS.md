# Next Steps - Getting Started Without Cloudflare

Here's how to get your sites up and running. You can add Cloudflare later (see CLOUDFLARE.md when ready).

## Step 1: Set Up Hugo Sites Locally

### Public Blog

```bash
cd hugo-site

# Initialize Hugo site
hugo new site . --force

# Add a theme (example using PaperMod)
git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod

# Create config
cat > config.toml << 'EOF'
baseURL = 'http://example.org/'
languageCode = 'en-us'
title = 'My Blog'
theme = 'PaperMod'
EOF

# Create first post
hugo new posts/my-first-post.md

# Test locally
hugo server -D
# Visit http://localhost:1313
```

### House Manual

```bash
cd house-manual

# Initialize Hugo site
hugo new site . --force

# Add a simple theme
git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod

# Create config
cat > config.toml << 'EOF'
baseURL = 'http://localhost:8080/'
languageCode = 'en-us'
title = 'House Manual'
theme = 'PaperMod'
EOF

# Create house documentation
hugo new docs/appliances.md
hugo new docs/hvac.md
hugo new docs/plumbing.md

# Create password file (you'll be prompted for password)
htpasswd -c .htpasswd yourusername

# Test locally
hugo server -D -p 1314
# Visit http://localhost:1314
```

## Step 2: Deploy to Docker (Local Testing)

```bash
# From repository root
docker-compose build static-site house-manual
docker-compose up -d static-site house-manual

# Test
curl http://localhost/                     # Public blog
curl -u username:password http://localhost:8080/  # House manual
```

## Step 3: Deploy to Linode

### Copy files to Linode

```bash
# From your local machine
rsync -avz --exclude='.git' \
  ~/linode/ \
  root@YOUR_LINODE_IP:~/linode/

# Or if using SSH key
rsync -avz --exclude='.git' \
  -e "ssh -i ~/.ssh/your_key" \
  ~/linode/ \
  user@YOUR_LINODE_IP:~/linode/
```

### On Linode

```bash
# SSH into Linode
ssh root@YOUR_LINODE_IP

# Navigate to directory
cd ~/linode

# Build and start all services
docker-compose build
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 4: Access Your Sites

Once deployed on Linode:

- **Public Blog**: `http://YOUR_LINODE_IP/`
- **Grafana**: `http://YOUR_LINODE_IP:3000`
- **House Manual**: `http://YOUR_LINODE_IP:8080/` (enter username/password)

## Step 5: Point DNS (Optional)

If you have a domain:

1. Add DNS A record pointing to your Linode IP
   ```
   yourdomain.com  →  YOUR_LINODE_IP
   ```

2. Update nginx config to use your domain
   ```bash
   cd ~/linode/hugo-site
   nano nginx.conf
   # Change server_name from localhost to yourdomain.com
   ```

3. Restart
   ```bash
   docker-compose restart static-site
   ```

4. Access via domain: `http://yourdomain.com/`

## Step 6: Add SSL Later (Optional)

When ready for HTTPS, you have two options:

### Option A: Let's Encrypt (Free SSL)

```bash
# On Linode
apt-get update && apt-get install certbot

# Stop nginx temporarily
docker-compose stop static-site

# Get certificate
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certs
mkdir -p ~/linode/certs
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/linode/certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/linode/certs/

# Update nginx config (uncomment SSL sections)
nano ~/linode/hugo-site/nginx.conf

# Restart
docker-compose up -d static-site
```

### Option B: Add Cloudflare (Free SSL + Caching)

See CLOUDFLARE.md for full instructions.

## Updating Content

When you add new blog posts or update content:

```bash
# Local: edit content in hugo-site/content/ or house-manual/content/

# Rebuild containers
docker-compose build static-site house-manual

# Restart containers
docker-compose up -d static-site house-manual
```

Or if already deployed to Linode:

```bash
# From local machine
rsync -avz hugo-site/content/ root@YOUR_LINODE_IP:~/linode/hugo-site/content/
rsync -avz house-manual/content/ root@YOUR_LINODE_IP:~/linode/house-manual/content/

# On Linode
cd ~/linode
docker-compose build static-site house-manual
docker-compose up -d static-site house-manual
```

## Firewall Configuration

Make sure these ports are open on Linode:

```bash
# Ubuntu/Debian with ufw
ufw allow 80/tcp     # HTTP
ufw allow 443/tcp    # HTTPS (when you add SSL)
ufw allow 3000/tcp   # Grafana
ufw allow 8080/tcp   # House manual
ufw allow 22/tcp     # SSH (already open)
```

## Service Status

Check what's running:

```bash
docker-compose ps

# Expected output:
# static-site          running   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# house-manual         running   0.0.0.0:8080->8080/tcp
# weather-logger       running   (no ports)
# backup-scheduler     running   (no ports)
# weather-grafana      running   0.0.0.0:3000->3000/tcp
```

## Troubleshooting

### Site not loading

```bash
# Check if container is running
docker-compose ps

# Check logs
docker-compose logs static-site
docker-compose logs house-manual

# Rebuild
docker-compose build static-site house-manual
docker-compose up -d --force-recreate static-site house-manual
```

### Basic auth not working (house manual)

```bash
# Verify .htpasswd exists
ls -la house-manual/.htpasswd

# Recreate password file
cd house-manual
htpasswd -c .htpasswd yourusername

# Rebuild
cd ..
docker-compose build house-manual
docker-compose restart house-manual
```

### Can't access from outside

```bash
# Check firewall
ufw status

# Check nginx is listening
docker exec static-site netstat -tlnp
docker exec house-manual netstat -tlnp
```

## Summary

You now have:
- ✅ Weather logger collecting data every minute
- ✅ Automated daily backups to S3/B2
- ✅ Grafana visualizing weather data
- ✅ Public blog on port 80 (HTTP)
- ✅ Private house manual on port 8080 (with auth)

All running independently in Docker containers on your Linode server!

When ready, add:
- Cloudflare for caching and free SSL (see CLOUDFLARE.md)
- Custom domain names
- HTTPS/SSL certificates

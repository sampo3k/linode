# Cloudflare Setup Guide

This guide covers setting up Cloudflare with SSL/TLS for your public Hugo blog, including caching configuration.

## Architecture Overview

```
User Browser
    ↓ HTTPS (Cloudflare SSL)
Cloudflare CDN (caching, SSL termination)
    ↓ HTTPS (Origin Certificate or Let's Encrypt)
Your Linode Server (nginx on port 80/443)
```

**House Manual** (port 8080) bypasses Cloudflare entirely - direct access with basic auth.

## Setup Order

### Phase 1: Initial Deployment (HTTP Only)

1. **Deploy to Linode**
   ```bash
   # Build and start services
   docker-compose build
   docker-compose up -d

   # Verify sites are accessible
   curl http://YOUR_LINODE_IP/          # Public blog
   curl http://YOUR_LINODE_IP:8080/     # House manual (will prompt for auth)
   ```

2. **Test locally**
   - Visit `http://YOUR_LINODE_IP/` - should see blog
   - Visit `http://YOUR_LINODE_IP:3000` - Grafana
   - Visit `http://YOUR_LINODE_IP:8080` - House manual (enter credentials)

### Phase 2: DNS and Cloudflare

3. **Add domain to Cloudflare**
   - Go to https://dash.cloudflare.com
   - Click "Add a Site"
   - Enter your domain name
   - Choose Free plan
   - Update nameservers at your domain registrar to Cloudflare's nameservers

4. **Configure DNS records in Cloudflare**
   ```
   Type    Name               Content            Proxy Status    TTL
   A       yourdomain.com     YOUR_LINODE_IP     Proxied (🧡)   Auto
   A       www                YOUR_LINODE_IP     Proxied (🧡)   Auto
   ```

   **Important**: Make sure "Proxy status" is **Proxied** (orange cloud) for caching and SSL

5. **Wait for DNS propagation** (usually 5-30 minutes)
   ```bash
   # Check if DNS is pointing to Cloudflare
   dig yourdomain.com
   # Should show Cloudflare IPs (not your Linode IP directly)
   ```

### Phase 3: SSL/TLS Configuration

You have two options for SSL:

#### Option A: Cloudflare Origin Certificates (Recommended - Easier)

This uses Cloudflare's certificates between Cloudflare and your server.

1. **Generate Origin Certificate in Cloudflare**
   - Dashboard → SSL/TLS → Origin Server → Create Certificate
   - Choose "Generate private key and CSR with Cloudflare"
   - Hostnames: `yourdomain.com, *.yourdomain.com`
   - Validity: 15 years
   - Click "Create"
   - **Save both files**:
     - Origin Certificate → `cloudflare-origin.pem`
     - Private Key → `cloudflare-origin-key.pem`

2. **Install certificates on your server**
   ```bash
   # On your Linode
   mkdir -p ~/linode/certs
   cd ~/linode/certs

   # Copy the certificate and key (paste content, then Ctrl+D)
   cat > cloudflare-origin.pem
   [paste origin certificate]

   cat > cloudflare-origin-key.pem
   [paste private key]

   # Set permissions
   chmod 644 cloudflare-origin.pem
   chmod 600 cloudflare-origin-key.pem
   ```

3. **Update nginx config**
   ```bash
   cd ~/linode/hugo-site
   nano nginx.conf
   ```

   Uncomment and modify these lines:
   ```nginx
   # Uncomment these
   listen       443 ssl http2;
   listen  [::]:443 ssl http2;

   # Update server_name
   server_name  yourdomain.com www.yourdomain.com;

   # Uncomment SSL certificate paths (Cloudflare section)
   ssl_certificate     /etc/nginx/certs/cloudflare-origin.pem;
   ssl_certificate_key /etc/nginx/certs/cloudflare-origin-key.pem;

   # Uncomment SSL configuration
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers HIGH:!aNULL:!MD5;
   ssl_prefer_server_ciphers on;
   ssl_session_cache shared:SSL:10m;
   ssl_session_timeout 10m;
   ```

   And uncomment the HTTP → HTTPS redirect server block.

4. **Set Cloudflare SSL/TLS mode**
   - Dashboard → SSL/TLS → Overview
   - Set to **"Full (strict)"** - most secure
   - This encrypts traffic between Cloudflare and your server

5. **Rebuild and restart**
   ```bash
   cd ~/linode
   docker-compose build static-site
   docker-compose restart static-site
   ```

6. **Test HTTPS**
   - Visit `https://yourdomain.com` - should work with valid SSL

#### Option B: Let's Encrypt with Certbot (Alternative)

This uses free Let's Encrypt certificates.

1. **Install Certbot on Linode**
   ```bash
   apt-get update
   apt-get install certbot
   ```

2. **Stop nginx temporarily**
   ```bash
   docker-compose stop static-site
   ```

3. **Get certificate**
   ```bash
   certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
   ```

   Certificates will be in `/etc/letsencrypt/live/yourdomain.com/`

4. **Copy certificates to project**
   ```bash
   mkdir -p ~/linode/certs
   cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/linode/certs/
   cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/linode/certs/
   chmod 644 ~/linode/certs/fullchain.pem
   chmod 600 ~/linode/certs/privkey.pem
   ```

5. **Update nginx.conf** (use Let's Encrypt paths instead of Cloudflare)

6. **Set Cloudflare SSL/TLS mode to "Full (strict)"**

7. **Set up auto-renewal**
   ```bash
   # Test renewal
   certbot renew --dry-run

   # Add cron job
   crontab -e
   # Add this line:
   0 0 1 * * certbot renew --deploy-hook "docker-compose -f /root/linode/docker-compose.yml restart static-site"
   ```

### Phase 4: Cloudflare Caching

1. **Page Rules** (Dashboard → Rules → Page Rules)

   Create these rules in order (top = highest priority):

   **Rule 1: Bypass cache for admin areas** (if you add CMS later)
   ```
   URL: *yourdomain.com/admin*
   Settings: Cache Level: Bypass
   ```

   **Rule 2: Cache everything**
   ```
   URL: *yourdomain.com/*
   Settings:
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month
   - Browser Cache TTL: 4 hours
   ```

2. **Caching Configuration** (Dashboard → Caching)
   - Caching Level: Standard
   - Browser Cache TTL: Respect Existing Headers (nginx sets this)

3. **Set up cache purging** (when you update site)
   ```bash
   # After deploying new content
   curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/purge_cache" \
     -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     --data '{"purge_everything":true}'
   ```

   Or use the Dashboard → Caching → Purge Cache

### Phase 5: Additional Security

1. **Always Use HTTPS** (Dashboard → SSL/TLS → Edge Certificates)
   - Enable "Always Use HTTPS"
   - Enable "Automatic HTTPS Rewrites"

2. **Minimum TLS Version**
   - Set to TLS 1.2 or higher

3. **HSTS** (HTTP Strict Transport Security)
   - Enable with 6 months max-age
   - Include subdomains: No (unless you want)

4. **Firewall Rules** (optional)
   - Dashboard → Security → WAF
   - Set up custom rules if needed (e.g., block certain countries)

## Testing Your Setup

```bash
# Test SSL certificate
curl -vI https://yourdomain.com

# Check if Cloudflare is serving
curl -I https://yourdomain.com | grep -i cf-

# Should see headers like:
# cf-cache-status: HIT (or MISS on first request)
# cf-ray: ...
# server: cloudflare

# Test cache
curl -I https://yourdomain.com
# First request: cf-cache-status: MISS
curl -I https://yourdomain.com
# Second request: cf-cache-status: HIT

# Test house manual (direct access, not through Cloudflare)
curl -u username:password http://YOUR_LINODE_IP:8080/
```

## Cloudflare Best Practices

1. **Browser Cache TTL**: Set conservatively (4 hours)
   - Allows quick updates if needed
   - Edge cache is still long (1 month)

2. **Purge cache after updates**:
   ```bash
   # After rebuilding blog
   docker-compose build static-site
   docker-compose up -d static-site
   # Purge Cloudflare cache via dashboard or API
   ```

3. **Development mode**: Enable during active development
   - Dashboard → Caching → Configuration → Development Mode
   - Bypasses cache for 3 hours

4. **Monitor with Cloudflare Analytics**
   - Dashboard → Analytics
   - See bandwidth saved, threats blocked, etc.

## Troubleshooting

### "Too Many Redirects" Error
- Check Cloudflare SSL mode is "Full (strict)"
- Check nginx isn't forcing HTTPS redirect when receiving HTTPS

### 521 Error (Web server is down)
- Check nginx is running: `docker-compose ps`
- Check port 443 is open: `netstat -tlnp | grep 443`
- Verify certificates are valid

### 525 Error (SSL Handshake Failed)
- Certificate doesn't match domain
- Check certificate paths in nginx.conf
- Verify Cloudflare SSL mode is "Full (strict)"

### Cache not working
- Check "Proxy status" is orange (proxied) in DNS
- Check page rules are in correct order
- Use "Purge Everything" and test again

## House Manual Access

The house manual on port 8080 should NOT go through Cloudflare:

```bash
# Access directly via IP
http://YOUR_LINODE_IP:8080

# Or set up a separate DNS record (DNS only, not proxied)
Type    Name         Content            Proxy Status
A       manual       YOUR_LINODE_IP     DNS only (grey)
```

With DNS-only record, access at `http://manual.yourdomain.com:8080`

## Cost

- Cloudflare Free Plan: $0/month
  - Unlimited bandwidth
  - Free SSL certificates
  - Basic DDoS protection
  - Page rules: 3 (sufficient for this setup)

- Linode VPS: ~$5-10/month (your existing server)

Total additional cost: **$0**

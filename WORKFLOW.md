# Content Authoring & Deployment Workflow

Quick reference for authoring Hugo content on macOS and deploying to Linode with instant updates.

## Overview

**Simple workflow:**
1. Author and edit content on your Mac
2. Run `./deploy.sh` - builds Hugo sites and rsyncs to Linode
3. Changes are live in ~10 seconds (no container restart!)

**Architecture:**
- Hugo sites are built on your Mac
- `deploy.sh` rsyncs `public/` directories to Linode
- Nginx containers mount these directories and serve them
- Updates are instant - just rsync and refresh browser

## Directory Structure

### On Your Mac

```
~/projects/                      (or wherever you work)
├── linode/                      ← Infrastructure repo (this repo)
│   ├── deploy.sh                ← Deployment script
│   ├── public-blog/             ← Deployed blog (created by rsync)
│   ├── public-house-manual/     ← Deployed manual (created by rsync)
│   └── docker-compose.yml
├── blog-content/                ← Your blog content (separate repo)
│   ├── config.toml
│   ├── content/
│   ├── themes/
│   └── public/                  ← Built by Hugo
└── house-manual-content/        ← Your house manual (separate repo)
    ├── config.toml
    ├── content/
    ├── themes/
    └── public/                  ← Built by Hugo
```

### On Linode Server

```
~/projects/
└── linode/
    ├── public-blog/             ← Rsync'd from Mac
    ├── public-house-manual/     ← Rsync'd from Mac
    └── docker-compose.yml
```

**Note:** Content repos (`blog-content/` and `house-manual-content/`) do NOT need to be on the Linode server!

## One-Time Setup

### 1. Install Hugo on macOS

```bash
brew install hugo
hugo version
```

### 2. Set Up Content Repositories on Mac

```bash
cd ~/projects

# Create or clone blog content repo
mkdir blog-content && cd blog-content
hugo new site . --force
git init

# Add a theme (example using PaperMod)
git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod

# Create config
cat > config.toml <<EOF
baseURL = 'https://yourdomain.com/'
languageCode = 'en-us'
title = 'My Blog'
theme = 'PaperMod'
EOF

# Set up git remote
git remote add origin git@github.com:yourusername/blog-content.git
git add . && git commit -m "Initial commit" && git push -u origin main

# Create house manual repo
cd ~/projects
mkdir house-manual-content && cd house-manual-content
hugo new site . --force
git init
# ... similar setup ...
```

### 3. Configure Linode Server

```bash
# SSH to Linode
ssh root@YOUR_LINODE_IP

# Create directory structure
mkdir -p ~/projects/linode/{public-blog,public-house-manual}

# Clone infrastructure repo
cd ~/projects
git clone git@github.com:yourusername/linode.git

# Build and start containers (one-time)
cd linode
docker-compose build static-site house-manual
docker-compose up -d static-site house-manual
```

### 4. Configure Deploy Script

Edit `deploy.sh` or set environment variables:

```bash
# Option 1: Set environment variables (recommended)
export LINODE_HOST=root@123.45.67.89
export BLOG_CONTENT_DIR=~/projects/blog-content
export MANUAL_CONTENT_DIR=~/projects/house-manual-content

# Option 2: Edit deploy.sh directly
nano ~/projects/linode/deploy.sh
# Change LINODE_HOST="root@your-linode-ip" to your actual IP
```

Make deploy script executable:
```bash
cd ~/projects/linode
chmod +x deploy.sh
```

### 5. Set Up SSH Key (Optional but Recommended)

To avoid entering password on every deploy:

```bash
# On your Mac (if you don't have a key already)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy key to Linode
ssh-copy-id root@YOUR_LINODE_IP

# Test passwordless login
ssh root@YOUR_LINODE_IP
```

## Daily Workflow

### Writing Blog Posts

```bash
# On your Mac
cd ~/projects/blog-content

# Create new post
hugo new posts/my-awesome-post.md

# Edit content
open content/posts/my-awesome-post.md
# Or use your favorite editor: code, nano, vim, etc.

# Preview locally while editing
hugo server -D
# Visit http://localhost:1313
# Hot reload - changes appear instantly in browser!

# When satisfied, commit to git
git add .
git commit -m "Add post: My Awesome Post"
git push
```

### Deploying to Linode

```bash
# From the linode/ directory
cd ~/projects/linode

# Deploy everything (blog + house manual)
./deploy.sh

# Or deploy just blog
./deploy.sh blog

# Or deploy just house manual
./deploy.sh manual
```

**That's it!** Changes are live in ~10 seconds.

### What the Deploy Script Does

1. Builds Hugo sites locally (`hugo --minify`)
2. Rsyncs `public/` directories to Linode
3. Nginx picks up changes instantly (no restart needed)

### Full Workflow Example

```bash
# 1. Write a blog post
cd ~/projects/blog-content
hugo new posts/hello-world.md
echo "---
title: 'Hello World'
date: 2024-01-15
draft: false
---

This is my first post!
" > content/posts/hello-world.md

# 2. Preview locally
hugo server -D
# Check http://localhost:1313

# 3. Commit to git
git add .
git commit -m "Add hello world post"
git push

# 4. Deploy to Linode
cd ~/projects/linode
./deploy.sh blog

# Done! Visit your site to see the new post.
```

## Updating House Manual

```bash
# On your Mac
cd ~/projects/house-manual-content

# Create new documentation
hugo new docs/hvac-maintenance.md

# Edit content
open content/docs/hvac-maintenance.md

# Preview locally
hugo server -D -p 1314
# Visit http://localhost:1314

# Commit
git add .
git commit -m "Add HVAC maintenance guide"
git push

# Deploy
cd ~/projects/linode
./deploy.sh manual
```

## Advanced Usage

### Deploy Script Options

```bash
# Deploy only blog
./deploy.sh blog

# Deploy only house manual
./deploy.sh manual

# Deploy both (default)
./deploy.sh
./deploy.sh all
```

### Using Environment Variables

Create a `.env` file or add to your shell profile:

```bash
# ~/.zshrc or ~/.bash_profile
export LINODE_HOST=root@123.45.67.89
export BLOG_CONTENT_DIR=~/projects/blog-content
export MANUAL_CONTENT_DIR=~/projects/house-manual-content
export REMOTE_DIR=~/projects/linode

# Reload shell
source ~/.zshrc
```

### Manual Deployment (without script)

If you prefer to run commands manually:

```bash
# Build Hugo sites
cd ~/projects/blog-content && hugo --minify
cd ~/projects/house-manual-content && hugo --minify

# Rsync to server
rsync -avz --delete ~/projects/blog-content/public/ \
    root@YOUR_IP:~/projects/linode/public-blog/

rsync -avz --delete ~/projects/house-manual-content/public/ \
    root@YOUR_IP:~/projects/linode/public-house-manual/
```

### Creating an Alias

Add to `~/.zshrc` or `~/.bash_profile`:

```bash
alias deploy-blog='cd ~/projects/linode && ./deploy.sh blog'
alias deploy-manual='cd ~/projects/linode && ./deploy.sh manual'
alias deploy-all='cd ~/projects/linode && ./deploy.sh'
```

Then deploy from anywhere:
```bash
deploy-blog
```

## Updating Infrastructure

If you change nginx configs, Dockerfiles, or docker-compose.yml:

```bash
# On your Mac - edit infrastructure files
cd ~/projects/linode
nano hugo-site/nginx.conf
# or
nano docker-compose.yml

# Commit and push
git add .
git commit -m "Update nginx config"
git push

# On Linode - pull and rebuild
ssh root@YOUR_LINODE_IP
cd ~/projects/linode
git pull
docker-compose build static-site house-manual
docker-compose up -d static-site house-manual
```

Or create a script for infrastructure updates:

```bash
# infra-update.sh
ssh root@$LINODE_HOST << 'EOF'
cd ~/projects/linode
git pull
docker-compose build static-site house-manual
docker-compose up -d static-site house-manual
EOF
```

## Testing Locally Before Deploying

You can test the exact production setup on your Mac:

```bash
# Build Hugo sites
cd ~/projects/blog-content && hugo --minify
cd ~/projects/house-manual-content && hugo --minify

# Copy to local public directories
cp -r ~/projects/blog-content/public/* ~/projects/linode/public-blog/
cp -r ~/projects/house-manual-content/public/* ~/projects/linode/public-house-manual/

# Start Docker containers locally
cd ~/projects/linode
docker-compose up -d static-site house-manual

# Test
curl http://localhost/
curl -u username:password http://localhost:8080/

# When satisfied, deploy to Linode
./deploy.sh
```

## Common Tasks

### Checking Deployment Status

```bash
# Check if sites are running on Linode
ssh root@YOUR_LINODE_IP 'docker ps | grep -E "static-site|house-manual"'

# View logs
ssh root@YOUR_LINODE_IP 'docker logs -f static-site'
ssh root@YOUR_LINODE_IP 'docker logs -f house-manual'

# Check disk usage of public directories
ssh root@YOUR_LINODE_IP 'du -sh ~/projects/linode/public-*'
```

### Purging Cloudflare Cache

After deploying blog updates (if using Cloudflare):

```bash
# Via Cloudflare dashboard
# Go to: Caching → Purge Cache → Purge Everything

# Or use API
curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/purge_cache" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

You can add this to the deploy script if you deploy frequently.

### Backing Up Content

Your content is automatically backed up via git:

```bash
# Content repos are version controlled
cd ~/projects/blog-content
git log --oneline  # View history

# Make sure to push regularly
git push origin main

# Optional: Create a backup branch before major changes
git checkout -b backup-2024-01-15
git push origin backup-2024-01-15
git checkout main
```

### Viewing Live Site Stats

```bash
# Check nginx access logs on Linode
ssh root@YOUR_LINODE_IP 'docker logs --tail 100 static-site'

# Check site response time
time curl -I https://yourdomain.com/
```

## Troubleshooting

### Deploy script fails: "Cannot connect to host"

```bash
# Test SSH connection
ssh root@YOUR_LINODE_IP

# If it fails, check:
# 1. Is the IP correct?
# 2. Is the server running?
# 3. Are you on the right network? (VPN, firewall)

# Update LINODE_HOST
export LINODE_HOST=root@123.45.67.89
```

### Hugo not found

```bash
# Install Hugo
brew install hugo

# Verify installation
hugo version
```

### Content not appearing on site

```bash
# Check if files were rsync'd
ssh root@YOUR_LINODE_IP 'ls -la ~/projects/linode/public-blog/'

# Check if containers are running
ssh root@YOUR_LINODE_IP 'docker ps'

# Check nginx logs
ssh root@YOUR_LINODE_IP 'docker logs static-site'

# Verify Hugo built correctly
cd ~/projects/blog-content
hugo --minify
ls -la public/  # Should see index.html, posts/, etc.
```

### "Permission denied" when rsync'ing

```bash
# Check SSH key authentication
ssh -v root@YOUR_LINODE_IP

# Set up key-based auth
ssh-copy-id root@YOUR_LINODE_IP

# Or check if you need sudo on Linode
ssh root@YOUR_LINODE_IP 'ls -ld ~/projects/linode/public-blog'
```

### Changes not visible through Cloudflare

Cloudflare caches aggressively:

1. Purge cache manually (see above)
2. Enable Development Mode (disables caching temporarily)
3. Add cache-busting query strings: `?v=2`
4. Wait for TTL to expire (2-4 hours)

### Hugo build errors

```bash
# Check Hugo version (some themes require specific versions)
hugo version

# Update Hugo if needed
brew upgrade hugo

# Check theme compatibility
cd ~/projects/blog-content
cat themes/THEME_NAME/theme.toml  # Look for min_version

# Rebuild with verbose output
hugo --minify --verbose
```

### House manual password not working

The `.htpasswd` file must exist in `house-manual/` on Linode:

```bash
# Check if file exists
ssh root@YOUR_LINODE_IP 'ls -la ~/projects/linode/house-manual/.htpasswd'

# If missing, create it locally and rebuild
cd ~/projects/linode/house-manual
htpasswd -c .htpasswd yourusername

# Rebuild container
ssh root@YOUR_LINODE_IP 'cd ~/projects/linode && docker-compose build house-manual && docker-compose restart house-manual'
```

## Performance Notes

### Deployment Speed

**Typical deployment times:**
- Hugo build (small site): 0.5-2 seconds
- Rsync transfer (first time): 10-30 seconds
- Rsync transfer (updates): 2-5 seconds
- **Total**: ~10 seconds for updates

**Why it's fast:**
- Hugo is extremely fast (written in Go)
- Rsync only transfers changed files
- No Docker rebuild needed
- No container restart needed

### Rsync Efficiency

Rsync uses delta transfer algorithm:
- Only changed files are transferred
- Large unchanged images are skipped
- Extremely efficient for incremental updates

Example:
- Full site: 50 MB, first sync: 20 seconds
- Update one post: 5 KB, sync: 2 seconds

### Hugo Build Optimization

```bash
# Standard build
hugo --minify

# Faster build (skip minification for testing)
hugo

# Production build with all optimizations
hugo --minify --gc
```

## Workflow Summary

### Quick Reference

**Write content on Mac:**
```bash
cd ~/projects/blog-content
hugo new posts/new-post.md
# Edit content
hugo server -D  # Preview
git add . && git commit -m "New post" && git push
```

**Deploy to Linode:**
```bash
cd ~/projects/linode
./deploy.sh
```

**That's it!**

### Advantages of This Workflow

1. **Fast**: ~10 second deployments
2. **Simple**: One command to deploy
3. **Safe**: Content versioned in git
4. **Local preview**: See changes before deploying
5. **No server dependencies**: Hugo runs on Mac, not on Linode
6. **Instant updates**: No container restarts
7. **Bandwidth efficient**: Rsync only transfers changes

### Comparison to Other Workflows

**This workflow (rsync):**
- Build locally + rsync: ~10 seconds
- No server software needed (just nginx)

**Alternative: Build on server:**
- Git pull + Hugo build: ~15 seconds
- Requires Hugo installed on server

**Alternative: Docker multi-stage build:**
- Git pull + Docker build + restart: ~60 seconds
- Slow, wasteful

**Our workflow is the fastest and simplest!**

## Additional Tips

### Keep Content Repos Clean

```bash
# Ignore Hugo build artifacts
cat >> ~/projects/blog-content/.gitignore <<EOF
/public/
/resources/
.hugo_build.lock
EOF
```

### Use Draft Posts

```bash
# Create draft
hugo new posts/draft-post.md  # draft: true by default

# Preview drafts locally
hugo server -D

# When ready, edit frontmatter
# Change: draft: true → draft: false

# Deploy (only publishes non-draft posts)
cd ~/projects/linode && ./deploy.sh
```

### Automate with Git Hooks

Create `.git/hooks/post-commit` in content repo:

```bash
#!/bin/bash
echo "Content committed. Deploy with: cd ../linode && ./deploy.sh"
```

Or auto-deploy:
```bash
#!/bin/bash
cd ../linode && ./deploy.sh blog
```

### Use Hugo Shortcodes

Create reusable components in `layouts/shortcodes/`:

```html
<!-- layouts/shortcodes/note.html -->
<div class="note">
  {{ .Inner }}
</div>
```

Use in content:
```markdown
{{< note >}}
This is an important note!
{{< /note >}}
```

### Monitor Deployments

Add to `~/.zshrc`:

```bash
function deploy-notify() {
    cd ~/projects/linode && ./deploy.sh && \
    osascript -e 'display notification "Deployment complete!" with title "Hugo Deploy"'
}
```

## Conclusion

This workflow optimizes for:
- **Speed**: Fastest possible deployments
- **Simplicity**: One-command deploy
- **Safety**: Git version control
- **Developer experience**: Local preview with hot reload

You get the benefits of static sites (fast, secure, cheap) with a modern development workflow.

Happy blogging!

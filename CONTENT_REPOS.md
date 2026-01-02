# Separate Content Repositories Setup

This infrastructure repo expects Hugo content to be in **separate git repositories** as sibling directories.

## Directory Structure

```
~/projects/  (or wherever you work)
├── linode/                    # This repo (infrastructure)
│   ├── docker-compose.yml
│   ├── hugo-site/
│   │   ├── Dockerfile         # Build instructions
│   │   └── nginx.conf         # Nginx config
│   └── house-manual/
│       ├── Dockerfile         # Build instructions
│       ├── nginx.conf         # Nginx config
│       └── .htpasswd.example
│
├── blog-content/              # Separate repo for blog
│   ├── .git/
│   ├── config.toml
│   ├── content/
│   │   └── posts/
│   ├── themes/
│   └── static/
│
└── house-manual-content/      # Separate repo for house manual
    ├── .git/
    ├── config.toml
    ├── content/
    │   └── docs/
    ├── themes/
    ├── static/
    └── .htpasswd              # Password file
```

## Setting Up Content Repositories

### 1. Create Blog Content Repository

```bash
# Create new directory (sibling to linode/)
cd ~/projects  # or wherever your linode/ repo is
mkdir blog-content
cd blog-content

# Initialize git
git init

# Initialize Hugo site
hugo new site . --force

# Add a theme (example: PaperMod)
git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod

# Create config
cat > config.toml << 'EOF'
baseURL = 'https://yourdomain.com/'
languageCode = 'en-us'
title = 'My Blog'
theme = 'PaperMod'

[params]
  description = "My personal blog"
  author = "Your Name"

[menu]
  [[menu.main]]
    name = "Posts"
    url = "/posts/"
    weight = 1
  [[menu.main]]
    name = "About"
    url = "/about/"
    weight = 2
EOF

# Create first post
hugo new posts/my-first-post.md

# Create .gitignore
cat > .gitignore << 'EOF'
# Hugo build artifacts
public/
resources/
.hugo_build.lock

# OS files
.DS_Store
Thumbs.db
EOF

# Commit
git add .
git commit -m "Initial Hugo blog setup"

# Add remote (GitHub, GitLab, etc.)
git remote add origin git@github.com:yourusername/blog-content.git
git push -u origin main
```

### 2. Create House Manual Content Repository

```bash
# Create new directory (sibling to linode/)
cd ~/projects
mkdir house-manual-content
cd house-manual-content

# Initialize git
git init

# Initialize Hugo site
hugo new site . --force

# Add a theme
git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod

# Create config
cat > config.toml << 'EOF'
baseURL = 'http://localhost:8080/'
languageCode = 'en-us'
title = 'House Manual'
theme = 'PaperMod'

[params]
  description = "Private house documentation"
  ShowBreadCrumbs = true

[menu]
  [[menu.main]]
    name = "Appliances"
    url = "/docs/appliances/"
    weight = 1
  [[menu.main]]
    name = "HVAC"
    url = "/docs/hvac/"
    weight = 2
  [[menu.main]]
    name = "Plumbing"
    url = "/docs/plumbing/"
    weight = 3
EOF

# Create house documentation
hugo new docs/appliances.md
hugo new docs/hvac.md
hugo new docs/plumbing.md
hugo new docs/electrical.md

# Create password file
htpasswd -c .htpasswd yourusername

# Create .gitignore
cat > .gitignore << 'EOF'
# Hugo build artifacts
public/
resources/
.hugo_build.lock

# Password file (NEVER commit this!)
.htpasswd

# OS files
.DS_Store
Thumbs.db
EOF

# Commit
git add .
git commit -m "Initial house manual setup"

# Add remote (private repo recommended!)
git remote add origin git@github.com:yourusername/house-manual-content.git
git push -u origin main
```

**Important**: Make sure your house-manual-content repo is **private** since it contains sensitive house information!

## Local Development Workflow

### Working on Blog Posts

```bash
cd ~/projects/blog-content

# Create new post
hugo new posts/my-new-post.md

# Edit the post
nano content/posts/my-new-post.md

# Preview locally
hugo server -D
# Visit http://localhost:1313

# When happy, commit
git add .
git commit -m "Add new post: My New Post"
git push
```

### Building and Deploying Locally

```bash
cd ~/projects/linode

# Build blog (reads from ../blog-content)
docker-compose build static-site

# Build house manual (reads from ../house-manual-content)
docker-compose build house-manual

# Deploy both
docker-compose up -d static-site house-manual

# Test
curl http://localhost/
curl -u username:password http://localhost:8080/
```

## Deploying to Linode

### Initial Setup on Linode

```bash
# SSH to Linode
ssh root@YOUR_LINODE_IP

# Create directory structure
mkdir -p ~/projects
cd ~/projects

# Clone all three repos
git clone git@github.com:yourusername/linode.git
git clone git@github.com:yourusername/blog-content.git
git clone git@github.com:yourusername/house-manual-content.git  # If using SSH keys

# Verify structure
ls -la
# Should see: linode/ blog-content/ house-manual-content/

# Initialize submodules (for Hugo themes)
cd blog-content
git submodule update --init --recursive

cd ../house-manual-content
git submodule update --init --recursive

# Copy password file for house manual (if not in git)
cd house-manual-content
htpasswd -c .htpasswd yourusername

# Build and start
cd ../linode
docker-compose build
docker-compose up -d
```

### Updating Content on Linode

When you push new blog posts or update content:

```bash
# SSH to Linode
ssh root@YOUR_LINODE_IP
cd ~/projects

# Update blog content
cd blog-content
git pull
git submodule update --recursive  # Update themes if needed

# Update house manual content
cd ../house-manual-content
git pull
git submodule update --recursive

# Rebuild and redeploy
cd ../linode
docker-compose build static-site house-manual
docker-compose up -d static-site house-manual
```

### Automated Updates (Optional)

Create a deployment script on Linode:

```bash
cat > ~/deploy-sites.sh << 'EOF'
#!/bin/bash
set -e

cd ~/projects

echo "Updating blog content..."
cd blog-content
git pull
git submodule update --recursive

echo "Updating house manual content..."
cd ../house-manual-content
git pull
git submodule update --recursive

echo "Rebuilding Docker images..."
cd ../linode
docker-compose build static-site house-manual

echo "Restarting services..."
docker-compose up -d static-site house-manual

echo "Deployment complete!"
EOF

chmod +x ~/deploy-sites.sh

# Now you can just run:
# ~/deploy-sites.sh
```

## Content Repository .gitignore

Make sure each content repo has proper `.gitignore`:

**blog-content/.gitignore**:
```
# Hugo
public/
resources/
.hugo_build.lock

# OS
.DS_Store
Thumbs.db
```

**house-manual-content/.gitignore**:
```
# Hugo
public/
resources/
.hugo_build.lock

# Secrets (IMPORTANT!)
.htpasswd

# OS
.DS_Store
Thumbs.db
```

## Why This Approach?

✅ **Separation of Concerns**: Infrastructure vs content
✅ **Clean Git History**: Blog posts don't clutter infrastructure commits
✅ **Different Access Controls**: Can make house-manual-content private
✅ **Easier Collaboration**: Can share blog content repo without exposing infrastructure
✅ **Independent Updates**: Update blog without touching infrastructure
✅ **Reusable Infrastructure**: Could host multiple blogs with same setup

## Troubleshooting

### Error: "No Hugo config found"

This means the content directory doesn't exist or is empty:

```bash
# Check directory structure
cd ~/projects
ls -la
# Should see: linode/ blog-content/ house-manual-content/

# Check content repos have files
ls -la blog-content/
# Should see: config.toml, content/, themes/
```

### Error: "dockerfile: not found"

Paths in docker-compose.yml are wrong. Make sure:
- You're running `docker-compose` from the `linode/` directory
- The sibling directories exist: `../blog-content` and `../house-manual-content`

### Build Context Issues

Docker build context is the content directory, but Dockerfile is in infrastructure repo:

```yaml
build:
  context: ../blog-content               # Hugo files here
  dockerfile: ../linode/hugo-site/Dockerfile  # Dockerfile here
```

This works because Docker allows Dockerfile to be outside the context!

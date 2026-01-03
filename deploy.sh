#!/bin/bash
# Deploy Hugo sites and Grafana dashboards from macOS to Linode server
# Usage: ./deploy.sh [blog|manual|grafana|all]

set -e

# Configuration
# Set these environment variables or edit them here:
LINODE_HOST="${LINODE_HOST:-nate@farad.space}"
BLOG_CONTENT_DIR="${BLOG_CONTENT_DIR:-../blog-content}"
MANUAL_CONTENT_DIR="${MANUAL_CONTENT_DIR:-../house-manual-content}"
REMOTE_DIR="${REMOTE_DIR:-~/projects/linode}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to build Hugo site
build_hugo() {
    local dir=$1
    local name=$2

    if [ ! -d "$dir" ]; then
        warn "Directory not found: $dir"
        return 1
    fi

    info "Building $name..."
    cd "$dir"

    if ! command -v hugo &> /dev/null; then
        warn "Hugo not found. Install with: brew install hugo"
        return 1
    fi

    hugo --minify
    success "$name built successfully"
    cd - > /dev/null
}

# Function to rsync to server
rsync_to_server() {
    local local_dir=$1
    local remote_path=$2
    local name=$3

    if [ ! -d "$local_dir" ]; then
        warn "Directory not found: $local_dir"
        return 1
    fi

    info "Deploying $name to $LINODE_HOST..."

    # Create remote directory if it doesn't exist
    ssh "$LINODE_HOST" "mkdir -p $remote_path"

    # Rsync with delete (removes files that no longer exist locally)
    rsync -avz --delete \
        --exclude='.DS_Store' \
        --exclude='.git' \
        "$local_dir/" \
        "$LINODE_HOST:$remote_path/"

    success "$name deployed successfully"
}

# Function to check SSH connection
check_connection() {
    info "Checking connection to $LINODE_HOST..."
    if ! ssh -q "$LINODE_HOST" exit; then
        warn "Cannot connect to $LINODE_HOST"
        echo "  Set LINODE_HOST environment variable or edit deploy.sh"
        echo "  Example: export LINODE_HOST=root@123.45.67.89"
        exit 1
    fi
    success "Connected to $LINODE_HOST"
}

# Main deployment function
deploy_blog() {
    echo ""
    echo "=== Deploying Blog ==="
    build_hugo "$BLOG_CONTENT_DIR" "Blog"
    rsync_to_server "$BLOG_CONTENT_DIR/public" "$REMOTE_DIR/public-blog" "Blog"
}

deploy_manual() {
    echo ""
    echo "=== Deploying House Manual ==="
    build_hugo "$MANUAL_CONTENT_DIR" "House Manual"
    rsync_to_server "$MANUAL_CONTENT_DIR/public" "$REMOTE_DIR/public-house-manual" "House Manual"
}

deploy_grafana() {
    echo ""
    echo "=== Deploying Grafana Dashboards ==="

    local local_grafana_dir="grafana/provisioning"

    if [ ! -d "$local_grafana_dir" ]; then
        warn "Grafana provisioning directory not found: $local_grafana_dir"
        return 1
    fi

    info "Deploying Grafana provisioning files..."

    # Create remote directory if it doesn't exist
    ssh "$LINODE_HOST" "mkdir -p ~/weather-logger/grafana/provisioning"

    # Rsync Grafana provisioning directory
    rsync -avz --delete \
        --exclude='.DS_Store' \
        "$local_grafana_dir/" \
        "$LINODE_HOST:~/weather-logger/grafana/provisioning/"

    success "Grafana provisioning files deployed"

    # Restart Grafana container
    info "Restarting Grafana container..."
    ssh "$LINODE_HOST" "docker restart weather-grafana" > /dev/null 2>&1

    success "Grafana container restarted"
}

# Parse arguments
DEPLOY_TARGET="${1:-all}"

echo ""
echo "╔══════════════════════════════════╗"
echo "║  Hugo Site Deployment to Linode  ║"
echo "╚══════════════════════════════════╝"
echo ""

# Check configuration
if [ "$LINODE_HOST" = "root@your-linode-ip" ]; then
    warn "Please configure LINODE_HOST"
    echo "  Option 1: Set environment variable"
    echo "    export LINODE_HOST=root@123.45.67.89"
    echo ""
    echo "  Option 2: Edit deploy.sh and change LINODE_HOST value"
    echo ""
    exit 1
fi

# Check SSH connection
check_connection

# Deploy based on argument
case "$DEPLOY_TARGET" in
    blog)
        deploy_blog
        ;;
    manual)
        deploy_manual
        ;;
    grafana)
        deploy_grafana
        ;;
    all)
        deploy_blog
        deploy_manual
        deploy_grafana
        ;;
    *)
        warn "Invalid argument: $DEPLOY_TARGET"
        echo "Usage: $0 [blog|manual|grafana|all]"
        exit 1
        ;;
esac

echo ""
success "Deployment complete!"
echo ""

# Show which services were deployed
if [ "$DEPLOY_TARGET" = "blog" ] || [ "$DEPLOY_TARGET" = "all" ]; then
    echo "  Blog: http://$(echo $LINODE_HOST | cut -d@ -f2)/"
fi
if [ "$DEPLOY_TARGET" = "manual" ] || [ "$DEPLOY_TARGET" = "all" ]; then
    echo "  Manual: http://$(echo $LINODE_HOST | cut -d@ -f2):8080/"
fi
if [ "$DEPLOY_TARGET" = "grafana" ] || [ "$DEPLOY_TARGET" = "all" ]; then
    echo "  Grafana: http://$(echo $LINODE_HOST | cut -d@ -f2):3000/"
fi
echo ""

# Optional: Cloudflare cache purge reminder
if [ "$DEPLOY_TARGET" = "blog" ] || [ "$DEPLOY_TARGET" = "all" ]; then
    echo "💡 Tip: If using Cloudflare, purge the cache to see changes immediately:"
    echo "   Cloudflare Dashboard → Caching → Purge Cache → Purge Everything"
    echo ""
fi

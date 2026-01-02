# Simple nginx server for pre-built Hugo house manual site with basic auth
# Hugo should be built on the host, with public/ directory mounted at runtime
FROM nginx:alpine

# Install apache2-utils for htpasswd (needed for password verification)
RUN apk add --no-cache apache2-utils

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy htpasswd file for basic authentication
# This file should be created with: htpasswd -c .htpasswd username
COPY .htpasswd /etc/nginx/.htpasswd

# Content directory - will be mounted as volume at runtime
# Expects: ../house-manual-content/public mounted to /usr/share/nginx/html
VOLUME /usr/share/nginx/html

# Expose custom port (8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

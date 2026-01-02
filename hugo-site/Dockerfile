# Simple nginx server for pre-built Hugo static site
# Hugo should be built on the host, with public/ directory mounted at runtime
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Content directory - will be mounted as volume at runtime
# Expects: ../blog-content/public mounted to /usr/share/nginx/html
VOLUME /usr/share/nginx/html

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

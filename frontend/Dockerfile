# Multi-stage build for frontend
# Stage 1: Build the React application
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy and set permissions for healthcheck script
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Create necessary directories with proper permissions
RUN mkdir -p /var/cache/nginx /var/run \
    && chown -R appuser:appgroup /var/cache/nginx /var/run

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD /healthcheck.sh

# Expose port
EXPOSE 80

# Switch to non-root user for running Nginx
# Note: We need to use root to start Nginx but it will drop privileges
USER appuser

# Start Nginx
CMD ["nginx", "-g", "daemon off;"] 
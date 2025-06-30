# Build stage
FROM node:20-slim AS build

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production \
    NPM_CONFIG_LOGLEVEL=warn \
    NPM_CONFIG_FUND=false

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-slim AS production

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install serve for production
RUN npm install -g serve

# Copy built app from build stage
COPY --from=build --chown=appuser:appuser /app/build ./build

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Start the application
CMD ["serve", "-s", "build", "-l", "3000"]

# Development stage for hot reloading during development
FROM node:20-slim AS development

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=development

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Start the application in development mode
CMD ["npm", "start"] 
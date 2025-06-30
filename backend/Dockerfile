# Build stage
FROM python:3.12-slim AS build

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM python:3.12-slim AS development

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ffmpeg \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/* && \
    # Set proper permissions
    chmod 1777 /tmp && \
    # Add security packages
    apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy requirements and install dependencies
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Create necessary directories with proper permissions
RUN mkdir -p \
    downloads/youtube/videos downloads/youtube/images downloads/youtube/text \
    downloads/instagram/videos downloads/instagram/images downloads/instagram/text \
    downloads/threads/videos downloads/threads/images downloads/threads/text \
    downloads/rednote/videos downloads/rednote/images downloads/rednote/text \
    data logs \
    && chown -R appuser:appuser /app \
    && chmod -R 750 /app/downloads /app/data /app/logs

# Copy healthcheck script
COPY --chown=appuser:appuser healthcheck.sh /app/healthcheck.sh
RUN chmod 550 /app/healthcheck.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Switch to non-root user
USER appuser

# Start the application in development mode
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM python:3.12-slim AS production

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    chromium \
    chromium-driver \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    # Set proper permissions
    chmod 1777 /tmp

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy requirements and install dependencies
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p \
    downloads/youtube/videos downloads/youtube/images downloads/youtube/text \
    downloads/instagram/videos downloads/instagram/images downloads/instagram/text \
    downloads/threads/videos downloads/threads/images downloads/threads/text \
    downloads/rednote/videos downloads/rednote/images downloads/rednote/text \
    data logs \
    && chown -R appuser:appuser /app

# Set read-only permissions for application code
RUN chmod -R 550 /app/*.py /app/api /app/analytics /app/core /app/db /app/models /app/security /app/services /app/utils \
    && chmod -R 750 /app/downloads /app/data /app/logs \
    && chmod 550 /app/healthcheck.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Switch to non-root user
USER appuser

# Start the application in production mode
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"] 
# HTTPS Deployment Guide

This guide provides instructions for deploying the Social Media Analysis Platform with proper HTTPS configuration.

## Prerequisites

- A domain name
- SSL certificate (Let's Encrypt or commercial)
- Web server (Nginx or similar)
- Access to DNS settings for your domain

## Steps for HTTPS Configuration

### 1. Obtain an SSL Certificate

#### Using Let's Encrypt (Recommended for most deployments)

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

#### Using a Commercial Certificate

If you have a commercial SSL certificate, follow the provider's instructions for installation.

### 2. Configure Nginx as a Reverse Proxy

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/social-media-analysis
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect all HTTP traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    
    # HSTS (optional but recommended)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    
    # Proxy to FastAPI application
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/social-media-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Configure Application Environment Variables

Update your `.env` file with the following settings:

```
# Host settings
TRUSTED_HOSTS="yourdomain.com,www.yourdomain.com"
ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"

# CORS settings
CORS_ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

# Debug mode (must be False in production)
DEBUG=False
```

### 4. Run the Application

Start the FastAPI application:

```bash
cd /path/to/your/app
uvicorn main:app --host 0.0.0.0 --port 8000
```

For production use, consider using a process manager like Supervisor or systemd.

### 5. Verify HTTPS Configuration

Test your HTTPS configuration:

```bash
# Test HTTPS enforcement
python scripts/test_https_enforcement.py --url https://yourdomain.com/api/v1

# Test with SSL Labs (comprehensive SSL/TLS test)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

## Security Best Practices

1. **Keep certificates up to date**: Let's Encrypt certificates expire after 90 days
2. **Enable automatic renewal**: `sudo certbot renew --dry-run`
3. **Use strong cipher suites**: As configured in the Nginx example
4. **Enable HSTS**: Already included in the Nginx configuration
5. **Disable SSL/TLS 1.0 and 1.1**: Only TLS 1.2 and 1.3 are enabled in the example
6. **Regular security audits**: Use tools like SSL Labs to audit your configuration

## Troubleshooting

- **Certificate issues**: Check certificate validity with `openssl s_client -connect yourdomain.com:443`
- **Nginx errors**: Check logs with `sudo tail -f /var/log/nginx/error.log`
- **Application errors**: Check application logs
- **Redirect loops**: Ensure your application is not also redirecting HTTP to HTTPS (FastAPI's HTTPSRedirectMiddleware is disabled when behind a proxy)

## References

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx HTTPS Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [SSL Labs Testing Tool](https://www.ssllabs.com/ssltest/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

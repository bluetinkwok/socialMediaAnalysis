# Security Core Module

This directory contains core security components for the Social Media Analysis Platform.

## Components

### Security Headers Middleware

The `security_headers.py` module provides middleware for adding security headers to all responses, enforcing HTTPS, and validating trusted hosts.

- `SecurityHeadersMiddleware`: Adds security headers to all responses
- `add_security_middleware()`: Adds all security middleware to the FastAPI application

### Configuration

The `config.py` module provides configuration settings for the application, including security settings.

Security-related settings include:
- `secret_key`: Secret key for JWT token generation
- `algorithm`: Algorithm used for JWT token generation
- `access_token_expire_minutes`: Expiration time for access tokens
- `cors_allowed_origins`: Allowed origins for CORS
- `allowed_hosts`: Allowed hosts for the application
- `trusted_hosts`: Trusted hosts for the TrustedHostMiddleware

## Usage

```python
from fastapi import FastAPI
from core.security_headers import add_security_middleware

app = FastAPI()
add_security_middleware(app)
```

## Security Headers

The following security headers are added to all responses:

- `X-Content-Type-Options`: Prevents MIME type sniffing
- `X-Frame-Options`: Prevents clickjacking attacks
- `X-XSS-Protection`: Enables browser XSS filtering
- `Strict-Transport-Security`: Enforces HTTPS connections
- `Content-Security-Policy`: Restricts resource loading
- `Referrer-Policy`: Controls referrer information
- `Permissions-Policy`: Controls browser features

## HTTPS Enforcement

In production mode, all HTTP requests are automatically redirected to HTTPS using FastAPI's `HTTPSRedirectMiddleware`.

## Trusted Host Validation

In production mode, requests are validated against a list of trusted hosts using FastAPI's `TrustedHostMiddleware`.

## Testing

Unit tests for security components are located in `tests/test_security_headers.py`.

Run tests with:

```bash
pytest backend/tests/test_security_headers.py -v
```

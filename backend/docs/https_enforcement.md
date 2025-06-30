# HTTPS Enforcement and Trusted Host Middleware

This document provides information about the HTTPS enforcement and trusted host middleware implemented in the Social Media Analysis Platform.

## Overview

The application implements two critical security features:

1. **HTTPS Enforcement**: Automatically redirects all HTTP requests to HTTPS to ensure encrypted communication.
2. **Trusted Host Validation**: Validates that requests are coming from trusted hosts to prevent host header injection attacks.

## Configuration

These security features are configured through environment variables in the `.env` file:

```
# Host settings
TRUSTED_HOSTS="yourdomain.com,app.yourdomain.com"
```

## Implementation Details

### HTTPS Enforcement

The HTTPS enforcement is implemented using FastAPI's `HTTPSRedirectMiddleware`. When enabled (in non-debug mode), this middleware:

- Intercepts all HTTP requests
- Redirects them to the same URL but with the HTTPS scheme
- Returns a 307 Temporary Redirect response

```python
# Add HTTPS redirect middleware in production
if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)
```

### Trusted Host Validation

The trusted host validation is implemented using FastAPI's `TrustedHostMiddleware`. This middleware:

- Validates that the Host header in incoming requests matches one of the trusted hosts
- Returns a 400 Bad Request response if the Host header doesn't match
- Helps prevent host header injection attacks

```python
# Add trusted host middleware with allowed hosts
trusted_hosts = settings.trusted_hosts.split(",") if settings.trusted_hosts else ["localhost", "127.0.0.1"]
if not settings.debug:
    # In production, only allow specified hosts
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=trusted_hosts
    )
```

## Security Considerations

- **Debug Mode**: Both HTTPS enforcement and trusted host validation are disabled in debug mode to facilitate local development.
- **Production Environment**: In production, both middleware are enabled to ensure secure communication.
- **Host Configuration**: Always configure the `TRUSTED_HOSTS` environment variable in production to include all valid domains for your application.

## Testing

To test these security features:

1. **HTTPS Enforcement**: Try accessing the application via HTTP in production mode. You should be automatically redirected to HTTPS.
2. **Trusted Host Validation**: Try accessing the application with an invalid host header. You should receive a 400 Bad Request response.

```bash
# Test trusted host validation (should fail)
curl -H "Host: malicious-host.com" https://yourdomain.com/api/v1/health
```

## References

- [FastAPI HTTPS Redirect Middleware](https://fastapi.tiangolo.com/advanced/middleware/#httpsredirectmiddleware)
- [FastAPI Trusted Host Middleware](https://fastapi.tiangolo.com/advanced/middleware/#trustedhostmiddleware)
- [OWASP Host Header Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_Host_Header_Injection)

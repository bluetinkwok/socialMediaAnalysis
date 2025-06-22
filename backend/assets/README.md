# Backend Assets

This folder contains static assets and resources used by the FastAPI backend.

## Asset Categories

### Security Assets
- `ssl/` - SSL certificates and keys
- `keys/` - API keys, JWT secrets (encrypted)
- `blacklists/` - Malicious URL blacklists
- `user-agents/` - Browser user agent lists

### Web Scraping Resources
- `browser-profiles/` - Browser configuration profiles
- `proxies/` - Proxy server configurations
- `captcha-models/` - Captcha solving model files
- `selectors/` - CSS/XPath selectors for platforms

### Database Assets
- `migrations/` - Database migration files
- `schemas/` - Database schema definitions
- `seed-data/` - Sample/test data files
- `fixtures/` - Test fixtures

### Analytics & ML Models
- `models/` - Trained ML models for content analysis
- `templates/` - Report templates
- `analytics-configs/` - Analytics configuration files

### Documentation Assets
- `api-docs/` - OpenAPI/Swagger documentation assets
- `examples/` - API usage examples
- `postman/` - Postman collection files

### Configuration Files
- `logging/` - Logging configuration templates
- `deployment/` - Deployment configuration files
- `monitoring/` - Monitoring and alerting configs

## File Organization

```
backend/assets/
├── ssl/
│   ├── certificates/
│   └── keys/
├── web-scraping/
│   ├── user-agents.json
│   ├── selectors/
│   └── browser-profiles/
├── database/
│   ├── schemas/
│   └── seed-data/
├── models/
│   ├── content-analysis/
│   └── trend-prediction/
└── configs/
    ├── logging.yaml
    └── monitoring.yaml
```

## Security Notes

- **Never commit sensitive files** (API keys, certificates, passwords)
- Use `.env` files for sensitive configuration
- Encrypt sensitive assets before storage
- Use proper file permissions (600/700) for security assets 
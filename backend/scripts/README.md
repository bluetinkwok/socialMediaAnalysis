# Backend Scripts

This folder contains Python scripts for backend operations and utilities.

## Script Categories

### Database Management
- `init_db.py` - Initialize database schema and tables
- `migrate_db.py` - Run database migrations
- `seed_data.py` - Populate database with test/sample data
- `backup_db.py` - Create database backups

### Content Management  
- `bulk_download.py` - Batch download content from multiple URLs
- `cleanup_downloads.py` - Clean up old/expired downloaded content
- `validate_downloads.py` - Verify integrity of downloaded files
- `export_content.py` - Export content data to various formats

### Web Scraping Utilities
- `test_scrapers.py` - Test individual platform scrapers
- `update_user_agents.py` - Update browser user agent lists
- `proxy_manager.py` - Manage proxy rotation for scraping
- `captcha_solver.py` - Handle captcha challenges

### Analytics & Reports
- `generate_analytics.py` - Generate content performance reports
- `export_metrics.py` - Export analytics data
- `trend_analysis.py` - Analyze content trends

### Development Utilities
- `setup_dev_env.py` - Setup development environment
- `run_tests.py` - Execute test suites
- `lint_code.py` - Code quality checks
- `generate_docs.py` - Generate API documentation

### Security & Maintenance
- `security_scan.py` - Run security vulnerability scans
- `malware_scan.py` - Scan downloaded content for malware
- `log_analyzer.py` - Analyze application logs
- `health_check.py` - System health monitoring

## Usage

Run scripts from the backend root directory:
```bash
cd backend
python scripts/script_name.py
``` 
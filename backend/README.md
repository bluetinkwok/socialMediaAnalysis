# Social Media Analysis Platform - Backend

This is the backend API for the Social Media Analysis Platform with advanced security features for file uploads.

## Features

- File upload API with comprehensive security features
- Malware scanning using ClamAV
- Suspicious pattern detection using YARA rules
- Metadata sanitization for uploaded files
- Security event logging and reporting
- Authentication and authorization

## Security Components

The file upload security system consists of several integrated components:

1. **ClamAV Integration**: Scans uploaded files for known malware
2. **YARA Pattern Analysis**: Detects suspicious patterns in files
3. **Metadata Sanitization**: Removes sensitive metadata from files
4. **Security Logging**: Records security events for auditing
5. **Security Integrator**: Coordinates all security components

## Setup

### Prerequisites

- Python 3.8+
- ClamAV (optional but recommended)
- YARA (optional but recommended)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Create a `.env` file based on the example below:
   ```
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   UPLOAD_DIR=uploads
   CLAMAV_SOCKET_PATH=/var/run/clamav/clamd.sock
   YARA_RULES_PATH=security/rules
   SECURITY_LOG_PATH=logs/security.log
   ```

## Running the Application

```bash
cd backend
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

Once the application is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security Notes

- ClamAV should be installed and running for malware scanning
- YARA rules should be customized for your specific security requirements
- In production, set appropriate CORS origins and other security headers

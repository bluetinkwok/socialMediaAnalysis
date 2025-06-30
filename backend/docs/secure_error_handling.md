# Secure Error Handling

This document describes the secure error handling implementation in the Social Media Analysis Platform.

## Overview

The platform implements a comprehensive error handling system that prevents information leakage while still providing useful error messages to clients and detailed logs for debugging.

## Key Features

1. **Standardized Error Format**: All errors follow a consistent JSON format
2. **Information Hiding**: Sensitive details are only included in debug mode
3. **Detailed Logging**: Full error details are logged for debugging
4. **Error Tracking**: Unique error IDs for tracking production issues
5. **Custom Error Classes**: Specific error types for different scenarios

## Error Response Format

All error responses follow this standard format:

```json
{
  "error": {
    "code": "ERR_CODE",
    "message": "Human-readable error message",
    "error_id": "uuid-for-tracking" // Only for 500 errors
  }
}
```

In debug mode, additional details may be included:

```json
{
  "error": {
    "code": "ERR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional context about the error
    }
  }
}
```

## Error Types

The system provides several custom exception classes:

| Class | Status Code | Description |
|-------|------------|-------------|
| `BadRequestError` | 400 | Invalid client request |
| `UnauthorizedError` | 401 | Authentication required |
| `ForbiddenError` | 403 | Permission denied |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Resource conflict |
| `RateLimitError` | 429 | Rate limit exceeded |
| `ServerError` | 500 | Internal server error |

## Usage Examples

### Raising Custom Errors

```python
from core.error_handlers import NotFoundError

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = db.get_user(user_id)
    if not user:
        # Will return a 404 with standardized format
        raise NotFoundError(
            message=f"User with ID {user_id} not found",
            details={"user_id": user_id}
        )
    return user
```

### Handling Validation Errors

The system automatically handles validation errors from Pydantic models and path/query parameters:

```python
@app.post("/users/")
async def create_user(user: UserCreate):
    # If UserCreate validation fails, a 422 error is returned
    # with standardized format
    return db.create_user(user)
```

## Security Considerations

1. **No Stack Traces**: Stack traces are never returned to clients
2. **No Implementation Details**: Error messages don't reveal implementation details
3. **No Sensitive Data**: Sensitive data is filtered from error responses
4. **Consistent Messages**: Generic messages for server errors
5. **Error Tracking**: Unique error IDs allow tracking without exposing internals

## Logging

All errors are logged with appropriate severity:
- 400-level errors are logged as warnings
- 500-level errors are logged as errors

Logs include:
- Error code and message
- Request path and method
- Client IP address
- Full error details (including stack traces for 500 errors)
- Unique error ID for 500 errors

## Configuration

Error handling behavior can be configured through environment variables:

- `DEBUG`: When true, includes error details in responses (default: false)

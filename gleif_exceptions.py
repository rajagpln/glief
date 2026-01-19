"""
Custom exceptions for GLEIF API operations.
"""


class GLEIFAPIError(Exception):
    """Base exception for all GLEIF API-related errors."""
    
    pass


class GLEIFValidationError(GLEIFAPIError):
    """Raised when input validation fails."""
    
    pass


class GLEIFNetworkError(GLEIFAPIError):
    """Raised when API request fails due to network issues."""
    
    pass


class GLEIFDataError(GLEIFAPIError):
    """Raised when API response data is malformed or unexpected."""
    
    pass

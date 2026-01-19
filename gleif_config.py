"""
Configuration for GLEIF API clients.

Centralizes magic numbers and constants for easier maintenance.
"""


class APIConfig:
    """API configuration constants."""
    
    BASE_URL = "https://api.gleif.org/api/v1"
    TIMEOUT_SECONDS = 10
    
    # Rate Limiting
    # GLEIF API: 60 requests per minute per user
    RATE_LIMIT_CODES = {429, 500, 502, 503, 504}
    
    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_BASE = 0.5
    
    # Pagination
    SEARCH_PAGE_SIZE = 100
    REFERENCE_PAGE_SIZE = 200
    
    # Instruments
    DEFAULT_INSTRUMENT_BUDGET = 20
    INSTRUMENT_PAGE_SIZE = 200


class SearchConfig:
    """Search-specific configuration."""
    
    VALID_SEARCH_TYPES = {"name", "fulltext"}
    COUNTRY_CODE_LENGTH = 2

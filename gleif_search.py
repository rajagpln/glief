#!/usr/bin/env python3
"""
GLEIF Legal Entity Search Tool

This module provides functionality to search the GLEIF API for legal entities.

Key Classes:
    GLEIFSearcher: Main search class for entity lookups

Usage:
    from gleif_search import GLEIFSearcher
    searcher = GLEIFSearcher()
    results = searcher.search_entities("Citibank")

Command-line usage:
    python gleif_search.py "search string"
    python gleif_search.py "Citibank" --fulltext --country GB
"""

import json
import sys
import argparse
import time
import logging
import requests
from typing import List, Dict, Any, Optional

from gleif_config import APIConfig, SearchConfig
from gleif_exceptions import (
    GLEIFValidationError,
    GLEIFNetworkError,
    GLEIFDataError,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add stderr handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class GLEIFSearcher:
    """Search for legal entities using the GLEIF API."""

    def __init__(
        self,
        page_size: int = APIConfig.SEARCH_PAGE_SIZE,
        instrument_request_budget: int = APIConfig.DEFAULT_INSTRUMENT_BUDGET,
        max_retries: int = APIConfig.DEFAULT_MAX_RETRIES,
        backoff_base_seconds: float = APIConfig.DEFAULT_BACKOFF_BASE,
    ):
        """
        Initialize the GLEIF searcher.

        Args:
            page_size: Number of results per page (max 100)
            instrument_request_budget: Max number of instrument lookup requests
            max_retries: Max retries for transient instrument lookup failures
            backoff_base_seconds: Base seconds for exponential backoff
        """
        self.page_size = min(page_size, APIConfig.SEARCH_PAGE_SIZE)
        self.instrument_request_budget = max(0, instrument_request_budget)
        self.max_retries = max(0, max_retries)
        self.backoff_base_seconds = max(0.0, backoff_base_seconds)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "GLEIF-Search-Tool/1.0"
        })

    def search_entities(
        self,
        query: str,
        search_type: str = "name",
        country_of_jurisdiction: Optional[str] = None,
        include_instruments: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search for legal entities matching the given query.

        Args:
            query: Search string to find matching entities
            search_type: Type of search - "name" (default) for legal entity name only,
                        or "fulltext" to search across all fields
            country_of_jurisdiction: Optional 2-letter country code to filter results
            include_instruments: Whether to include BIC/ISIN enrichment

        Returns:
            List of matching entities with extracted information
            
        Raises:
            GLEIFValidationError: If input parameters are invalid
        """
        # Validate input parameters
        self._validate_search_params(query, search_type, country_of_jurisdiction)
        
        entities = []
        page_num = 1

        # Set filter based on search type
        if search_type == "fulltext":
            filter_field = "fulltext"
        else:
            filter_field = "entity.legalName"

        logger.info(f"Starting search for '{query}' (type: {search_type})")
        if country_of_jurisdiction:
            logger.info(f"Filtering by country: {country_of_jurisdiction.upper()}")

        while True:
            try:
                # Use lei-records endpoint with appropriate filter
                params = {
                    f"filter[{filter_field}]": query,
                    "page[number]": page_num,
                    "page[size]": self.page_size
                }
                
                # Add country filter if provided
                if country_of_jurisdiction:
                    params["filter[entity.legalAddress.country]"] = country_of_jurisdiction.upper()

                response = self._get_with_backoff(
                    f"{APIConfig.BASE_URL}/lei-records",
                    params=params
                )
                response.raise_for_status()

                data = response.json()

                # Extract the matched LEI data
                if "data" not in data or not data["data"]:
                    break

                for item in data["data"]:
                    lei_record = self._extract_lei_record_info(item, include_instruments)
                    if lei_record:
                        entities.append(lei_record)

                # Check if there are more results
                meta = data.get("meta", {})
                pagination = meta.get("pagination", {})
                if self._should_stop_pagination(pagination, page_num):
                    break

                page_num += 1

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"API request failed on page {page_num} for query '{query}': {e}",
                    exc_info=True
                )
                logger.info(f"Retrieved {len(entities)} results before failure")
                break
            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing API response: {e}", exc_info=True)
                break

        logger.info(f"Search complete: {len(entities)} entities found")
        return entities

    def _validate_search_params(
        self,
        query: str,
        search_type: str,
        country: Optional[str],
    ) -> None:
        """
        Validate search parameters.
        
        Args:
            query: Search query string
            search_type: Type of search ("name" or "fulltext")
            country: Optional country code
            
        Raises:
            GLEIFValidationError: If any parameter is invalid
        """
        if not query or not isinstance(query, str):
            raise GLEIFValidationError("Query must be a non-empty string")
        
        if search_type not in SearchConfig.VALID_SEARCH_TYPES:
            raise GLEIFValidationError(
                f"Invalid search_type '{search_type}'. "
                f"Must be one of: {SearchConfig.VALID_SEARCH_TYPES}"
            )
        
        if country:
            if not isinstance(country, str) or len(country) != SearchConfig.COUNTRY_CODE_LENGTH:
                raise GLEIFValidationError(
                    f"Invalid country code '{country}'. "
                    f"Must be a 2-letter ISO country code."
                )

    def _extract_lei_record_info(
        self,
        record: Dict[str, Any],
        include_instruments: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract relevant information from a lei-records result.

        Args:
            record: Raw LEI record from response
            include_instruments: Whether to include BIC/ISIN enrichment

        Returns:
            Structured entity information or None if extraction fails
        """
        # Type validation
        if not isinstance(record, dict):
            logger.warning(
                f"Expected dict record, got {type(record).__name__}. Skipping."
            )
            return None
        
        try:
            attributes = record.get("attributes", {})
            entity = attributes.get("entity", {})
            lei = attributes.get("lei")

            if not lei:
                return None

            # Extract the information we need
            registration = attributes.get("registration", {})
            entity_info = {
                "legal_entity_id": lei,
                "legal_entity_name": entity.get("legalName"),
                "region": self._extract_region(entity),
                "country": self._extract_country(entity),
                "country_of_jurisdiction": self._extract_jurisdiction(entity, registration),
                "address": self._extract_address(entity)
            }
            if include_instruments:
                entity_info["tickers_and_instruments"] = self._extract_financial_instruments(record)

            return entity_info

        except Exception as e:
            logger.error(f"Error extracting LEI record info: {e}", exc_info=True)
            return None


    def _fetch_lei_record(self, lei: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the complete LEI record for a given LEI.

        Args:
            lei: The LEI code to fetch

        Returns:
            Structured entity information or None if fetch fails
        """
        pass  # Deprecated - use search_entities() instead


    def _extract_region(self, entity: Dict[str, Any]) -> Optional[str]:
        """Extract region information from entity data."""
        legal_address = entity.get("legalAddress", {})
        return legal_address.get("region")

    def _extract_country(self, entity: Dict[str, Any]) -> Optional[str]:
        """Extract country information from entity data."""
        legal_address = entity.get("legalAddress", {})
        return legal_address.get("country")

    def _extract_jurisdiction(
        self,
        entity: Dict[str, Any],
        registration: Dict[str, Any],
    ) -> Optional[str]:
        """Extract jurisdiction information from entity data."""
        # Jurisdiction is typically the country of legal address
        legal_address = entity.get("legalAddress", {})
        country = legal_address.get("country")
        
        # Try to get more specific jurisdiction info if available
        jurisdiction = registration.get("jurisdiction")
        
        return jurisdiction or country

    def _extract_address(self, entity: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract address information from entity data."""
        legal_address = entity.get("legalAddress", {})

        if not legal_address:
            return None

        address = {}
        if legal_address.get("firstAddressLine"):
            address["street"] = legal_address.get("firstAddressLine")
        if legal_address.get("additionalAddressLine"):
            address["additional"] = legal_address.get("additionalAddressLine")
        if legal_address.get("city"):
            address["city"] = legal_address.get("city")
        if legal_address.get("postalCode"):
            address["postal_code"] = legal_address.get("postalCode")
        if legal_address.get("country"):
            address["country"] = legal_address.get("country")

        return address if address else None

    def _get_with_backoff(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        GET with simple retry/backoff for transient errors.
        
        Args:
            url: URL to request
            params: Query parameters
            
        Returns:
            Response object
            
        Raises:
            GLEIFNetworkError: If all retry attempts fail
        """
        for attempt in range(self.max_retries + 1):
            response = self.session.get(url, params=params, timeout=APIConfig.TIMEOUT_SECONDS)
            if response.status_code not in APIConfig.RATE_LIMIT_CODES:
                return response
            if attempt < self.max_retries:
                delay = self.backoff_base_seconds * (2 ** attempt)
                logger.warning(
                    f"Rate limited (status {response.status_code}). "
                    f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(delay)
        return response

    def _extract_financial_instruments(self, record: Dict[str, Any]) -> Optional[List[Dict[str, str]]]:
        """Extract ticker symbols and financial instruments associated with the entity."""
        instruments = []

        # Try to get ISINs from related data
        relationships = record.get("relationships", {})
        if "isins" in relationships:
            isins_link = relationships["isins"].get("links", {}).get("related")
            if isins_link:
                try:
                    page_num = 1
                    while True:
                        if self.instrument_request_budget <= 0:
                            logger.warning("Instrument lookup budget exhausted; stopping ISIN enrichment.")
                            break
                        params = {
                            "page[number]": page_num,
                            "page[size]": APIConfig.INSTRUMENT_PAGE_SIZE,
                        }
                        response = self._get_with_backoff(isins_link, params=params)
                        self.instrument_request_budget -= 1
                        response.raise_for_status()
                        isins_data = response.json()

                        for isin_item in isins_data.get("data", []):
                            isin_attrs = isin_item.get("attributes", {})
                            instruments.append({
                                "type": "ISIN",
                                "value": isin_attrs.get("isin")
                            })

                        meta = isins_data.get("meta", {})
                        pagination = meta.get("pagination", {})
                        if self._should_stop_pagination(pagination, page_num):
                            break

                        page_num += 1
                except Exception as e:
                    logger.error(f"Error fetching ISINs: {e}", exc_info=True)

        # Try to get BIC codes
        attributes = record.get("attributes", {})
        bic = attributes.get("bic")
        if bic:
            instruments.append({
                "type": "BIC",
                "value": bic
            })

        return instruments if instruments else None

    @staticmethod
    def _should_stop_pagination(pagination: Dict[str, Any], current_page: int) -> bool:
        """
        Determine if pagination should stop.
        
        Args:
            pagination: Pagination metadata from API response
            current_page: Current page number
            
        Returns:
            True if pagination should stop, False otherwise
        """
        last_page = pagination.get("lastPage")
        return not last_page or last_page == current_page


def main():
    """Main function to handle command-line execution."""
    parser = argparse.ArgumentParser(
        description="Search the GLEIF API for legal entities matching a query string.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Search for entities with "Citibank" in their legal name (default):
    python gleif_search.py "Citibank"
    
  Search across all fields (name, address, etc.):
    python gleif_search.py --fulltext "Citibank"
    
  Search for entities with "Citibank" in the United Kingdom:
    python gleif_search.py "Citibank" --country GB
    
  Search across all fields and filter by country:
    python gleif_search.py --fulltext "Bank" --country CN
        """
    )

    parser.add_argument(
        "query",
        help="Search string to find matching legal entities"
    )
    parser.add_argument(
        "--fulltext",
        action="store_true",
        help="Search across all fields (name, address, metadata). "
             "Default is to search only in legal entity names."
    )
    parser.add_argument(
        "--country",
        "-c",
        help="Filter results by country (2-letter ISO country code, e.g., 'GB', 'US', 'CN'). Optional."
    )
    parser.add_argument(
        "--include-instruments",
        action="store_true",
        help="Include BIC/ISIN enrichment (may increase API requests)."
    )
    parser.add_argument(
        "--instrument-request-budget",
        type=int,
        default=APIConfig.DEFAULT_INSTRUMENT_BUDGET,
        help=f"Max number of instrument lookup requests (default: {APIConfig.DEFAULT_INSTRUMENT_BUDGET})."
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Configure logging level
    logger.setLevel(getattr(logging, args.log_level))

    try:
        if not args.query:
            parser.print_help()
            sys.exit(1)

        query = args.query
        search_type = "fulltext" if args.fulltext else "name"

        logger.info(f"Searching for: {query}")
        logger.info(f"Search type: {'Full-text (name, address, metadata)' if args.fulltext else 'Legal entity name only'}")
        if args.country:
            logger.info(f"Country filter: {args.country.upper()}")

        searcher = GLEIFSearcher(instrument_request_budget=args.instrument_request_budget)
        results = searcher.search_entities(
            query,
            search_type=search_type,
            country_of_jurisdiction=args.country,
            include_instruments=args.include_instruments,
        )

        # Format output as JSON
        output = {
            "query": query,
            "search_type": search_type,
            "country_filter": args.country.upper() if args.country else None,
            "results_count": len(results),
            "results": results
        }

        print(json.dumps(output, indent=2))

    except GLEIFValidationError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

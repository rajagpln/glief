#!/usr/bin/env python3
"""
GLEIF Legal Entity Search Tool

This script takes a search string as input and uses the GLEIF API to find
all matching legal entities, returning relevant information in JSON format.

Usage:
    python gleif_search.py "search string"
"""

import json
import sys
import argparse
import time
import requests
from typing import List, Dict, Any, Optional

# GLEIF API base URL
BASE_URL = "https://api.gleif.org/api/v1"


class GLEIFSearcher:
    """Search for legal entities using the GLEIF API."""

    def __init__(
        self,
        page_size: int = 100,
        instrument_request_budget: int = 20,
        max_retries: int = 3,
        backoff_base_seconds: float = 0.5,
    ):
        """
        Initialize the GLEIF searcher.

        Args:
            page_size: Number of results per page (max 100)
            instrument_request_budget: Max number of instrument lookup requests
            max_retries: Max retries for transient instrument lookup failures
            backoff_base_seconds: Base seconds for exponential backoff
        """
        self.page_size = min(page_size, 100)
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
        """
        entities = []
        page_num = 1

        # Set filter based on search type
        if search_type == "fulltext":
            filter_field = "fulltext"
        else:
            filter_field = "entity.legalName"

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
                    f"{BASE_URL}/lei-records",
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
                if not pagination.get("lastPage") or pagination.get("lastPage") == page_num:
                    break

                page_num += 1

            except requests.exceptions.RequestException as e:
                print(f"Error during API request: {e}", file=sys.stderr)
                break
            except (KeyError, ValueError) as e:
                print(f"Error parsing API response: {e}", file=sys.stderr)
                break

        return entities

    def _extract_lei_record_info(
        self,
        record: Dict[str, Any],
        include_instruments: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract relevant information from a lei-records result.

        Args:
            record: Raw LEI record from response

        Returns:
            Structured entity information or None if extraction fails
        """
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
            print(f"Error extracting LEI record info: {e}", file=sys.stderr)
            return None


    def _fetch_lei_record(self, lei: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the complete LEI record for a given LEI.

        Args:
            lei: The LEI code to fetch

        Returns:
            Structured entity information or None if fetch fails
        """
        pass  # No longer needed, removed to avoid confusion


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
        """GET with simple retry/backoff for transient errors."""
        for attempt in range(self.max_retries + 1):
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            if attempt < self.max_retries:
                delay = self.backoff_base_seconds * (2 ** attempt)
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
                            print("Instrument lookup budget exhausted; stopping ISIN enrichment.", file=sys.stderr)
                            break
                        params = {
                            "page[number]": page_num,
                            "page[size]": 200,
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
                        if not pagination.get("lastPage") or pagination.get("lastPage") == page_num:
                            break

                        page_num += 1
                except Exception as e:
                    print(f"Error fetching ISINs: {e}", file=sys.stderr)

        # Try to get BIC codes
        attributes = record.get("attributes", {})
        bic = attributes.get("bic")
        if bic:
            instruments.append({
                "type": "BIC",
                "value": bic
            })

        return instruments if instruments else None


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
        help="Filter results by country of jurisdiction (2-letter ISO country code, e.g., 'GB', 'US', 'CN'). Optional."
    )
    parser.add_argument(
        "--include-instruments",
        action="store_true",
        help="Include BIC/ISIN enrichment (may increase API requests)."
    )
    parser.add_argument(
        "--instrument-request-budget",
        type=int,
        default=20,
        help="Max number of instrument lookup requests (default: 20)."
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(1)

    query = args.query
    search_type = "fulltext" if args.fulltext else "name"

    print(f"Searching for: {query}", file=sys.stderr)
    print(f"Search type: {'Full-text (name, address, metadata)' if args.fulltext else 'Legal entity name only'}", file=sys.stderr)
    if args.country:
        print(f"Country filter: {args.country.upper()}", file=sys.stderr)
    print("", file=sys.stderr)

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


if __name__ == "__main__":
    main()

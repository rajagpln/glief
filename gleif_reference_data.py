#!/usr/bin/env python3
"""
GLEIF Reference Data Fetcher

This module provides functionality to fetch and manage reference data from the GLEIF API.

Key Classes:
    GLEIFReferenceDataFetcher: Fetches standardized lookup tables

Usage:
    from gleif_reference_data import GLEIFReferenceDataFetcher
    fetcher = GLEIFReferenceDataFetcher()
    fetcher.fetch_all_data()

Command-line usage:
    python gleif_reference_data.py --all
    python gleif_reference_data.py countries
    python gleif_reference_data.py --list
"""

import json
import sys
import argparse
import logging
import requests
import os
from typing import Dict, List, Any, Optional

from gleif_config import APIConfig

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


class GLEIFReferenceDataFetcher:
    """Fetch reference data from the GLEIF API."""

    def __init__(
        self,
        output_dir: str = "./reference_data",
        max_retries: int = APIConfig.DEFAULT_MAX_RETRIES,
        backoff_base_seconds: float = APIConfig.DEFAULT_BACKOFF_BASE,
    ):
        """Initialize the reference data fetcher.
        
        Args:
            output_dir: Directory to save JSON files (default: ./reference_data)
            max_retries: Max retries for transient failures
            backoff_base_seconds: Base seconds for exponential backoff
        """
        self.output_dir = output_dir
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created directory: {self.output_dir}")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "GLEIF-Reference-Data-Tool/1.0"
        })
        self.max_retries = max(0, max_retries)
        self.backoff_base_seconds = max(0.0, backoff_base_seconds)
        self.endpoints = {
            "countries": {
                "url": f"{APIConfig.BASE_URL}/countries",
                "description": "ISO country codes and names"
            },
            "regions": {
                "url": f"{APIConfig.BASE_URL}/regions",
                "description": "ISO 3166-2 region/subdivision codes"
            },
            "entity-legal-forms": {
                "url": f"{APIConfig.BASE_URL}/entity-legal-forms",
                "description": "Legal entity form types (e.g., Corporation, LLC, Ltd)"
            },
            "jurisdictions": {
                "url": f"{APIConfig.BASE_URL}/jurisdictions",
                "description": "Jurisdictions for entity registration"
            },
            "registration-authorities": {
                "url": f"{APIConfig.BASE_URL}/registration-authorities",
                "description": "Business register authorities"
            },
            "registration-agents": {
                "url": f"{APIConfig.BASE_URL}/registration-agents",
                "description": "LEI registration agents"
            },
            "official-organizational-roles": {
                "url": f"{APIConfig.BASE_URL}/official-organizational-roles",
                "description": "Organizational role types"
            }
        }

    def fetch_all_data(self) -> Dict[str, Any]:
        """
        Fetch all reference data from GLEIF API and save to JSON files.

        Returns:
            Dictionary with metadata about saved files
        """
        summary = {
            "timestamp": self._get_timestamp(),
            "api_version": "v1",
            "source": "GLEIF API",
            "output_directory": self.output_dir,
            "files_saved": {}
        }

        for endpoint_name, endpoint_info in self.endpoints.items():
            logger.info(f"Fetching {endpoint_name}...")
            try:
                data = self._fetch_endpoint(endpoint_info["url"])
                if data:
                    # Create the data structure
                    file_data = {
                        "timestamp": self._get_timestamp(),
                        "type": endpoint_name,
                        "description": endpoint_info["description"],
                        "count": len(data),
                        "items": data
                    }
                    
                    # Save to file
                    filename = f"{endpoint_name}.json"
                    filepath = os.path.join(self.output_dir, filename)
                    self._save_to_file(filepath, file_data)
                    
                    summary["files_saved"][endpoint_name] = {
                        "filename": filename,
                        "count": len(data),
                        "filepath": filepath
                    }
                    logger.info(f"  ✓ Retrieved {len(data)} items → {filename}")
            except Exception as e:
                logger.error(f"  ✗ Error fetching {endpoint_name}: {e}", exc_info=True)
                summary["files_saved"][endpoint_name] = {
                    "error": str(e)
                }

        # Save summary file
        summary_path = os.path.join(self.output_dir, "_summary.json")
        self._save_to_file(summary_path, summary)
        logger.info(f"✓ Summary saved to _summary.json")
        
        return summary

    def fetch_data_by_type(self, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific type of reference data and save to JSON file.

        Args:
            data_type: Type of data to fetch (countries, regions, etc.)

        Returns:
            Dictionary with the reference data or None if type not found
        """
        if data_type not in self.endpoints:
            logger.error(f"Unknown data type '{data_type}'")
            logger.info(f"Available types: {', '.join(self.endpoints.keys())}")
            return None

        endpoint_info = self.endpoints[data_type]
        logger.info(f"Fetching {data_type}...")

        try:
            data = self._fetch_endpoint(endpoint_info["url"])
            if data:
                result = {
                    "timestamp": self._get_timestamp(),
                    "type": data_type,
                    "description": endpoint_info["description"],
                    "count": len(data),
                    "items": data
                }
                
                # Save to file
                filename = f"{data_type}.json"
                filepath = os.path.join(self.output_dir, filename)
                self._save_to_file(filepath, result)
                
                logger.info(f"✓ Retrieved {len(data)} items → {filename}")
                return result
        except Exception as e:
            logger.error(f"✗ Error: {e}", exc_info=True)
            return None

    def _fetch_endpoint(self, url: str, page_size: int = APIConfig.REFERENCE_PAGE_SIZE) -> List[Dict[str, Any]]:
        """
        Fetch all data from a given endpoint with pagination.

        Args:
            url: The API endpoint URL
            page_size: Number of items per page

        Returns:
            List of all items from the endpoint
        """
        all_items = []
        page_num = 1

        while True:
            params = {
                "page[number]": page_num,
                "page[size]": page_size
            }

            response = self._get_with_backoff(url, params=params)
            response.raise_for_status()

            data = response.json()

            if "data" not in data or not data["data"]:
                break

            # Process items and extract key information
            for item in data["data"]:
                processed_item = self._process_item(item)
                all_items.append(processed_item)

            # Check if there are more pages
            meta = data.get("meta", {})
            pagination = meta.get("pagination", {})
            if self._should_stop_pagination(pagination, page_num):
                break

            page_num += 1

        return all_items

    def _get_with_backoff(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        GET with simple retry/backoff for transient errors.
        
        Args:
            url: URL to request
            params: Query parameters
            
        Returns:
            Response object
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

    def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single item from the API response.

        Args:
            item: Raw item from API response

        Returns:
            Processed item with key information
        """
        attributes = item.get("attributes", {})
        item_id = item.get("id", "")

        processed = {
            "id": item_id,
        }

        # Add all attributes
        processed.update(attributes)

        return processed

    def _save_to_file(self, filepath: str, data: Dict[str, Any]) -> None:
        """Save data to a JSON file.
        
        Args:
            filepath: Path to save the file
            data: Data to save
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving to {filepath}: {e}", exc_info=True)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def list_available_types(self) -> None:
        """Print available reference data types."""
        logger.info("Available Reference Data Types:")
        logger.info("")
        for name, info in self.endpoints.items():
            logger.info(f"  {name:35} - {info['description']}")
        logger.info("")

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
        description="Fetch GLEIF API reference data (countries, regions, legal forms, etc.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Fetch all reference data types:
    python gleif_reference_data.py --all
    
  Fetch only country codes:
    python gleif_reference_data.py countries
    
  Fetch only region codes:
    python gleif_reference_data.py regions
    
  Fetch entity legal forms:
    python gleif_reference_data.py entity-legal-forms
    
  List available data types:
    python gleif_reference_data.py --list
        """
    )

    parser.add_argument(
        "data_type",
        nargs="?",
        help="Type of reference data to fetch (countries, regions, entity-legal-forms, etc.)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all reference data types"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available reference data types"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./reference_data",
        help="Output directory for JSON files (default: ./reference_data)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=APIConfig.DEFAULT_MAX_RETRIES,
        help=f"Max retries for transient failures (default: {APIConfig.DEFAULT_MAX_RETRIES})"
    )
    parser.add_argument(
        "--backoff-base-seconds",
        type=float,
        default=APIConfig.DEFAULT_BACKOFF_BASE,
        help=f"Base seconds for exponential backoff (default: {APIConfig.DEFAULT_BACKOFF_BASE})"
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

    fetcher = GLEIFReferenceDataFetcher(
        output_dir=args.output,
        max_retries=args.max_retries,
        backoff_base_seconds=args.backoff_base_seconds,
    )

    # Handle --list
    if args.list:
        fetcher.list_available_types()
        sys.exit(0)

    # Handle --all
    if args.all:
        result = fetcher.fetch_all_data()
        logger.info(f"All reference data saved to: {args.output}")
        sys.exit(0)

    # Handle specific data type
    if args.data_type:
        result = fetcher.fetch_data_by_type(args.data_type)
        if result:
            logger.info(f"Data saved to: {args.output}/{args.data_type}.json")
        sys.exit(0)

    # No arguments provided
    parser.print_help()
    sys.exit(1)
        help="Base seconds for exponential backoff (default: 0.5)"
    )

    args = parser.parse_args()

    fetcher = GLEIFReferenceDataFetcher(
        output_dir=args.output,
        max_retries=args.max_retries,
        backoff_base_seconds=args.backoff_base_seconds,
    )

    # Handle --list
    if args.list:
        fetcher.list_available_types()
        sys.exit(0)

    # Handle --all
    if args.all:
        result = fetcher.fetch_all_data()
        print(f"\nAll reference data saved to: {args.output}", file=sys.stderr)
        sys.exit(0)

    # Handle specific data type
    if args.data_type:
        result = fetcher.fetch_data_by_type(args.data_type)
        if result:
            print(f"\nData saved to: {args.output}/{args.data_type}.json", file=sys.stderr)
        sys.exit(0)

    # No arguments provided
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()

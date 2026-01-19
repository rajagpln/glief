#!/usr/bin/env python3
"""
GLEIF Reference Data Extractor

This script fetches reference data from the GLEIF API and saves it as JSON files.
Includes country codes, region codes, entity legal forms, etc.

Usage:
    python gleif_reference_data.py [data_type]
    python gleif_reference_data.py --all
    python gleif_reference_data.py --output /path/to/directory
"""

import json
import sys
import argparse
import requests
import os
from typing import Dict, List, Any, Optional

# GLEIF API base URL
BASE_URL = "https://api.gleif.org/api/v1"


class GLEIFReferenceDataFetcher:
    """Fetch reference data from the GLEIF API."""

    def __init__(self, output_dir: str = "./reference_data"):
        """Initialize the reference data fetcher.
        
        Args:
            output_dir: Directory to save JSON files (default: ./reference_data)
        """
        self.output_dir = output_dir
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created directory: {self.output_dir}", file=sys.stderr)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "GLEIF-Reference-Data-Tool/1.0"
        })
        self.endpoints = {
            "countries": {
                "url": f"{BASE_URL}/countries",
                "description": "ISO country codes and names"
            },
            "regions": {
                "url": f"{BASE_URL}/regions",
                "description": "ISO 3166-2 region/subdivision codes"
            },
            "entity-legal-forms": {
                "url": f"{BASE_URL}/entity-legal-forms",
                "description": "Legal entity form types (e.g., Corporation, LLC, Ltd)"
            },
            "jurisdictions": {
                "url": f"{BASE_URL}/jurisdictions",
                "description": "Jurisdictions for entity registration"
            },
            "registration-authorities": {
                "url": f"{BASE_URL}/registration-authorities",
                "description": "Business register authorities"
            },
            "registration-agents": {
                "url": f"{BASE_URL}/registration-agents",
                "description": "LEI registration agents"
            },
            "official-organizational-roles": {
                "url": f"{BASE_URL}/official-organizational-roles",
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
            print(f"Fetching {endpoint_name}...", file=sys.stderr)
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
                    print(f"  ✓ Retrieved {len(data)} items → {filename}", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ Error: {e}", file=sys.stderr)
                summary["files_saved"][endpoint_name] = {
                    "error": str(e)
                }

        # Save summary file
        summary_path = os.path.join(self.output_dir, "_summary.json")
        self._save_to_file(summary_path, summary)
        print(f"\n✓ Summary saved to _summary.json", file=sys.stderr)
        
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
            print(f"Error: Unknown data type '{data_type}'", file=sys.stderr)
            print(f"Available types: {', '.join(self.endpoints.keys())}", file=sys.stderr)
            return None

        endpoint_info = self.endpoints[data_type]
        print(f"Fetching {data_type}...", file=sys.stderr)

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
                
                print(f"✓ Retrieved {len(data)} items → {filename}", file=sys.stderr)
                return result
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            return None

    def _fetch_endpoint(self, url: str, page_size: int = 200) -> List[Dict[str, Any]]:
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

            response = self.session.get(url, params=params, timeout=10)
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
            if not pagination.get("lastPage") or pagination.get("lastPage") == page_num:
                break

            page_num += 1

        return all_items

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
            print(f"Error saving to {filepath}: {e}", file=sys.stderr)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def list_available_types(self) -> None:
        """Print available reference data types."""
        print("Available Reference Data Types:", file=sys.stderr)
        print("", file=sys.stderr)
        for name, info in self.endpoints.items():
            print(f"  {name:35} - {info['description']}", file=sys.stderr)
        print("", file=sys.stderr)


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

    args = parser.parse_args()

    fetcher = GLEIFReferenceDataFetcher(output_dir=args.output)

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

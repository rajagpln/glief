#!/usr/bin/env python3
"""
Unit tests for gleif_search.py

Tests cover:
- Data extraction methods (_extract_* functions)
- Search parameter building
- Error handling
- Response parsing
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import json
from gleif_search import GLEIFSearcher


class TestGLEIFSearcherExtraction(unittest.TestCase):
    """Test data extraction methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.searcher = GLEIFSearcher()

    def test_extract_region_valid(self):
        """Test region extraction with valid data."""
        entity = {
            "legalAddress": {
                "region": "GB-LND",
                "country": "GB"
            }
        }
        result = self.searcher._extract_region(entity)
        self.assertEqual(result, "GB-LND")

    def test_extract_region_missing(self):
        """Test region extraction when region is missing."""
        entity = {"legalAddress": {"country": "GB"}}
        result = self.searcher._extract_region(entity)
        self.assertIsNone(result)

    def test_extract_region_no_address(self):
        """Test region extraction when legalAddress is missing."""
        entity = {}
        result = self.searcher._extract_region(entity)
        self.assertIsNone(result)

    def test_extract_country_valid(self):
        """Test country extraction with valid data."""
        entity = {"legalAddress": {"country": "US"}}
        result = self.searcher._extract_country(entity)
        self.assertEqual(result, "US")

    def test_extract_country_missing(self):
        """Test country extraction when country is missing."""
        entity = {"legalAddress": {}}
        result = self.searcher._extract_country(entity)
        self.assertIsNone(result)

    def test_extract_jurisdiction_from_registration(self):
        """Test jurisdiction extraction from registration data."""
        entity = {"legalAddress": {"country": "US"}}
        registration = {"jurisdiction": "US-CA"}
        result = self.searcher._extract_jurisdiction(entity, registration)
        self.assertEqual(result, "US-CA")

    def test_extract_jurisdiction_fallback_to_country(self):
        """Test jurisdiction fallback to country when registration missing."""
        entity = {"legalAddress": {"country": "GB"}}
        registration = {}
        result = self.searcher._extract_jurisdiction(entity, registration)
        self.assertEqual(result, "GB")

    def test_extract_jurisdiction_both_missing(self):
        """Test jurisdiction when both registration and country are missing."""
        entity = {"legalAddress": {}}
        registration = {}
        result = self.searcher._extract_jurisdiction(entity, registration)
        self.assertIsNone(result)

    def test_extract_address_complete(self):
        """Test address extraction with all fields."""
        entity = {
            "legalAddress": {
                "firstAddressLine": "123 Main St",
                "additionalAddressLine": "Suite 100",
                "city": "London",
                "postalCode": "E14 5LB",
                "country": "GB"
            }
        }
        result = self.searcher._extract_address(entity)
        self.assertEqual(result["street"], "123 Main St")
        self.assertEqual(result["additional"], "Suite 100")
        self.assertEqual(result["city"], "London")
        self.assertEqual(result["postal_code"], "E14 5LB")
        self.assertEqual(result["country"], "GB")

    def test_extract_address_partial(self):
        """Test address extraction with partial data."""
        entity = {
            "legalAddress": {
                "city": "New York",
                "country": "US"
            }
        }
        result = self.searcher._extract_address(entity)
        self.assertEqual(result["city"], "New York")
        self.assertEqual(result["country"], "US")
        self.assertNotIn("street", result)

    def test_extract_address_empty(self):
        """Test address extraction with empty legalAddress."""
        entity = {"legalAddress": {}}
        result = self.searcher._extract_address(entity)
        self.assertIsNone(result)

    def test_extract_address_no_address(self):
        """Test address extraction with missing legalAddress."""
        entity = {}
        result = self.searcher._extract_address(entity)
        self.assertIsNone(result)


class TestGLEIFSearcherExtractRecord(unittest.TestCase):
    """Test LEI record extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.searcher = GLEIFSearcher()

    def test_extract_lei_record_valid(self):
        """Test complete LEI record extraction."""
        record = {
            "attributes": {
                "lei": "549300U8H3KN0K301B23",
                "bic": "CIUKGB2LXXX",
                "entity": {
                    "legalName": "CITIBANK UK LIMITED",
                    "legalAddress": {
                        "firstAddressLine": "123 Main St",
                        "city": "London",
                        "postalCode": "E14 5LB",
                        "country": "GB",
                        "region": "GB-LND"
                    }
                },
                "registration": {
                    "jurisdiction": "GB"
                }
            },
            "relationships": {}
        }
        result = self.searcher._extract_lei_record_info(record, include_instruments=False)
        
        self.assertEqual(result["legal_entity_id"], "549300U8H3KN0K301B23")
        self.assertEqual(result["legal_entity_name"], "CITIBANK UK LIMITED")
        self.assertEqual(result["region"], "GB-LND")
        self.assertEqual(result["country"], "GB")
        self.assertEqual(result["country_of_jurisdiction"], "GB")
        self.assertIsNotNone(result["address"])
        self.assertEqual(result["address"]["city"], "London")

    def test_extract_lei_record_missing_lei(self):
        """Test extraction fails gracefully when LEI is missing."""
        record = {
            "attributes": {
                "entity": {"legalName": "Test"},
                "registration": {}
            }
        }
        result = self.searcher._extract_lei_record_info(record, include_instruments=False)
        self.assertIsNone(result)

    def test_extract_lei_record_with_instruments(self):
        """Test extraction includes instruments when requested."""
        record = {
            "attributes": {
                "lei": "549300U8H3KN0K301B23",
                "bic": "CIUKGB2LXXX",
                "entity": {
                    "legalName": "TEST BANK",
                    "legalAddress": {
                        "city": "London",
                        "country": "GB"
                    }
                },
                "registration": {}
            },
            "relationships": {}
        }
        result = self.searcher._extract_lei_record_info(record, include_instruments=True)
        
        self.assertIn("tickers_and_instruments", result)

    def test_extract_lei_record_malformed_json(self):
        """Test extraction handles malformed data gracefully."""
        record = {
            "attributes": None
        }
        result = self.searcher._extract_lei_record_info(record, include_instruments=False)
        self.assertIsNone(result)


class TestGLEIFSearcherSearchParameters(unittest.TestCase):
    """Test search parameter building and API requests."""

    def setUp(self):
        """Set up test fixtures."""
        self.searcher = GLEIFSearcher(page_size=100)

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_name_mode(self, mock_get):
        """Test search builds correct parameters for name mode."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [],
            "meta": {"pagination": {"lastPage": True, "page": 1}}
        }
        mock_get.return_value = mock_response

        self.searcher.search_entities("Citibank", search_type="name")

        # Verify correct filter was used
        call_args = mock_get.call_args
        self.assertIn("filter[entity.legalName]", call_args[1]["params"])
        self.assertEqual(call_args[1]["params"]["filter[entity.legalName]"], "Citibank")

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_fulltext_mode(self, mock_get):
        """Test search builds correct parameters for fulltext mode."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [],
            "meta": {"pagination": {"lastPage": True, "page": 1}}
        }
        mock_get.return_value = mock_response

        self.searcher.search_entities("Citibank", search_type="fulltext")

        call_args = mock_get.call_args
        self.assertIn("filter[fulltext]", call_args[1]["params"])
        self.assertEqual(call_args[1]["params"]["filter[fulltext]"], "Citibank")

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_with_country_filter(self, mock_get):
        """Test search includes country filter when provided."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [],
            "meta": {"pagination": {"lastPage": True, "page": 1}}
        }
        mock_get.return_value = mock_response

        self.searcher.search_entities("Bank", country_of_jurisdiction="us")

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        self.assertIn("filter[entity.legalAddress.country]", params)
        self.assertEqual(params["filter[entity.legalAddress.country]"], "US")

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_pagination(self, mock_get):
        """Test search handles pagination correctly."""
        # First page with 2 results, lastPage is False (there's a next page)
        mock_response_1 = Mock()
        mock_response_1.json.return_value = {
            "data": [
                {
                    "attributes": {
                        "lei": "LEI001",
                        "entity": {
                            "legalName": "Bank 1",
                            "legalAddress": {"country": "GB"}
                        },
                        "registration": {}
                    }
                },
                {
                    "attributes": {
                        "lei": "LEI002",
                        "entity": {
                            "legalName": "Bank 2",
                            "legalAddress": {"country": "GB"}
                        },
                        "registration": {}
                    }
                }
            ],
            "meta": {"pagination": {"lastPage": 2, "page": 1}}
        }

        # Second page with 1 result, lastPage is 2 (which equals current page), so stop
        mock_response_2 = Mock()
        mock_response_2.json.return_value = {
            "data": [
                {
                    "attributes": {
                        "lei": "LEI003",
                        "entity": {
                            "legalName": "Bank 3",
                            "legalAddress": {"country": "GB"}
                        },
                        "registration": {}
                    }
                }
            ],
            "meta": {"pagination": {"lastPage": 2, "page": 2}}
        }

        mock_get.side_effect = [mock_response_1, mock_response_2]

        results = self.searcher.search_entities("Bank")

        self.assertEqual(len(results), 3)
        self.assertEqual(mock_get.call_count, 2)

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_no_results(self, mock_get):
        """Test search handles no results gracefully."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [],
            "meta": {"pagination": {}}
        }
        mock_get.return_value = mock_response

        results = self.searcher.search_entities("NonexistentEntity12345")

        self.assertEqual(len(results), 0)


class TestGLEIFSearcherErrorHandling(unittest.TestCase):
    """Test error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.searcher = GLEIFSearcher()

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_network_error(self, mock_get):
        """Test search handles network errors gracefully."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        results = self.searcher.search_entities("Test")

        self.assertEqual(len(results), 0)

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_invalid_json(self, mock_get):
        """Test search handles invalid JSON responses."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        results = self.searcher.search_entities("Test")

        self.assertEqual(len(results), 0)

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_search_missing_data_key(self, mock_get):
        """Test search handles missing 'data' key in response."""
        mock_response = Mock()
        mock_response.json.return_value = {"meta": {}}
        mock_get.return_value = mock_response

        results = self.searcher.search_entities("Test")

        self.assertEqual(len(results), 0)


class TestGLEIFSearcherInitialization(unittest.TestCase):
    """Test searcher initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        searcher = GLEIFSearcher()
        self.assertEqual(searcher.page_size, 100)
        self.assertEqual(searcher.instrument_request_budget, 20)
        self.assertEqual(searcher.max_retries, 3)
        self.assertEqual(searcher.backoff_base_seconds, 0.5)

    def test_init_custom_page_size(self):
        """Test initialization with custom page size."""
        searcher = GLEIFSearcher(page_size=50)
        self.assertEqual(searcher.page_size, 50)

    def test_init_page_size_capped_at_100(self):
        """Test page size is capped at 100."""
        searcher = GLEIFSearcher(page_size=200)
        self.assertEqual(searcher.page_size, 100)

    def test_init_negative_values_handled(self):
        """Test negative values are converted to valid defaults."""
        searcher = GLEIFSearcher(
            instrument_request_budget=-5,
            max_retries=-2,
            backoff_base_seconds=-0.5
        )
        self.assertEqual(searcher.instrument_request_budget, 0)
        self.assertEqual(searcher.max_retries, 0)
        self.assertEqual(searcher.backoff_base_seconds, 0.0)


class TestFinancialInstrumentsExtraction(unittest.TestCase):
    """Test financial instruments extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.searcher = GLEIFSearcher()

    def test_extract_bic_only(self):
        """Test extraction of BIC code only."""
        record = {
            "attributes": {"bic": "CIUKGB2LXXX"},
            "relationships": {}
        }
        result = self.searcher._extract_financial_instruments(record)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "BIC")
        self.assertEqual(result[0]["value"], "CIUKGB2LXXX")

    def test_extract_no_instruments(self):
        """Test extraction when no instruments are present."""
        record = {
            "attributes": {},
            "relationships": {}
        }
        result = self.searcher._extract_financial_instruments(record)
        self.assertIsNone(result)

    @patch('gleif_search.GLEIFSearcher._get_with_backoff')
    def test_extract_isin_with_pagination(self, mock_get):
        """Test ISIN extraction with pagination."""
        # First ISIN page, not last
        isin_response_1 = Mock()
        isin_response_1.json.return_value = {
            "data": [
                {
                    "attributes": {"isin": "US1234567890"}
                }
            ],
            "meta": {"pagination": {"lastPage": 2, "page": 1}}
        }

        # Second ISIN page, is last
        isin_response_2 = Mock()
        isin_response_2.json.return_value = {
            "data": [
                {
                    "attributes": {"isin": "US9876543210"}
                }
            ],
            "meta": {"pagination": {"lastPage": 2, "page": 2}}
        }

        mock_get.side_effect = [isin_response_1, isin_response_2]

        record = {
            "attributes": {"bic": "TESTBIC123"},
            "relationships": {
                "isins": {
                    "links": {"related": "https://api.gleif.org/api/v1/lei/isins"}
                }
            }
        }
        result = self.searcher._extract_financial_instruments(record)

        # Should have 2 ISINs + BIC = 3 total
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["type"], "ISIN")
        self.assertEqual(result[1]["type"], "ISIN")
        self.assertEqual(result[2]["type"], "BIC")


if __name__ == "__main__":
    unittest.main()

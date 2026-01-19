# GLEIF Legal Entity Search Tool

A comprehensive Python toolkit for searching and retrieving data from the GLEIF (Global Legal Entity Identifier Foundation) API. Includes two main scripts for entity searches and reference data lookups.

## Features

### gleif_search.py
- **Full-text search**: Search across all legal entity data fields or by name only
- **Pagination support**: Automatically handles multiple pages of results
- **Comprehensive output**: Returns information including:
  - Legal Entity Name and ID (LEI)
  - Region and Country
  - Country of Jurisdiction
  - Address information
  - Associated financial instruments (BIC codes, ISINs)
- **Flexible search**: Two search modes - name-only (default) or full-text

### gleif_reference_data.py
- **Reference data fetcher**: Retrieves standardized codes and definitions from GLEIF API
- **Multiple data types**: Supports countries, regions, entity forms, jurisdictions, etc.
- **Batch export**: Can fetch all reference data at once
- **Individual lookups**: Fetch specific reference data types

## Installation

### Prerequisites
- Python 3.7+
- `requests` library

### Setup

1. Create a virtual environment (optional but recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install requests
```

## Usage

### Basic Usage

```bash
python gleif_search.py "search string"
```

By default, the script searches only in **legal entity names**. To search across all fields (names, addresses, metadata), use the `--fulltext` flag:

```bash
python gleif_search.py --fulltext "search string"
```

### Examples

**Search for entities with "Citibank" in their legal name (default):**
```bash
python gleif_search.py "Citibank"
```

**Search across all fields for Citibank-related entities (including nominees, trustees, etc.):**
```bash
python gleif_search.py --fulltext "Citibank"
```

**Search for a specific company by exact name:**
```bash
python gleif_search.py "Microsoft Corporation"
```

**Search for entities in a specific region:**
```bash
python gleif_search.py "Bank of England"
```

### Output Format

The script outputs JSON with the following structure:

```json
{
  "query": "search string",
  "search_type": "name",
  "results_count": 50,
  "results": [
    {
      "legal_entity_id": "549300U8H3KN0K301B23",
      "legal_entity_name": "CITIBANK UK LIMITED",
      "region": "GB-LND",
      "country": "GB",
      "country_of_jurisdiction": "GB",
      "address": {
        "street": "...",
        "city": "London",
        "postal_code": "E14 5LB",
        "country": "GB"
      },
      "tickers_and_instruments": [
        {
          "type": "BIC",
          "value": ["CIUKGB2LXXX"]
        }
      ]
    }
  ]
}
```

The `search_type` field indicates whether the search was:
- `"name"`: Search only in legal entity names (default)
- `"fulltext"`: Search across all fields including addresses and metadata

## API Information

- **Base URL**: https://api.gleif.org/api/v1
- **Rate Limit**: 60 requests per minute per user
- **Documentation**: https://api.gleif.org/docs
- **Data Terms**: https://www.gleif.org/en/meta/lei-data-terms-of-use/

## Features Explained

### Legal Entity Name
The official, registered legal name of the entity. May include language specification.

### LEI (Legal Entity Identifier)
A 20-character unique identifier assigned to each legal entity.

### Region and Country
- **Region**: Regional subdivision code (e.g., US-NY for New York)
- **Country**: ISO 3166-1 alpha-2 country code (e.g., US, GB)

### Country of Jurisdiction
The country whose legal system governs the entity.

### Address
Complete address information including:
- Street address
- City
- Postal code
- Country

### Tickers and Financial Instruments
- **BIC (Bank Identifier Code)**: Used for financial transactions
- **ISIN (International Securities Identification Number)**: Used for financial securities

## Search Types

### Name-Only Search (Default)

When you run `python gleif_search.py "Citibank"`, the script searches only in the **legal entity names** field. This provides more precise results focused on entities with the search term in their official registered name.

**Advantages:**
- More focused results
- Fewer false positives
- Faster queries
- Easier to identify direct matches

**Example:**
```bash
python gleif_search.py "Citibank"
# Returns ~100 entities with "Citibank" in their legal name
```

### Full-Text Search

When you run `python gleif_search.py --fulltext "Citibank"`, the script searches across **all fields** in the LEI record including:
- Legal entity names
- Addresses (street, city, postal code)
- All metadata and associated information
- Nominee and trustee relationships

This returns entities indirectly related to your search term.

**Advantages:**
- Comprehensive results
- Finds related entities (nominees, trustees, custodians)
- Useful for discovering business relationships

**Disadvantages:**
- Larger result sets (may include false positives)
- Slower queries
- Requires more result filtering

**Example:**
```bash
python gleif_search.py --fulltext "Citibank"
# Returns ~592 entities including nominees, funds with Citibank as custodian, etc.
```

### When to Use Each

| Scenario | Search Type | Command |
|----------|------------|---------|
| Find entities named "Citibank" | Name | `python gleif_search.py "Citibank"` |
| Find all Citibank-related entities | Full-text | `python gleif_search.py --fulltext "Citibank"` |
| Search for a specific company | Name | `python gleif_search.py "Microsoft"` |
| Find entities at a location | Full-text | `python gleif_search.py --fulltext "London"` |

## Notes

- The API is free to use
- Results are paginated; the script automatically handles multiple pages
- Some entities may not have all fields populated (address, instruments, etc.)
- Fuzzy matching is based on statistical similarity and may include false positives
- Always verify results against your own data sources

## Notes

- The API is free to use
- Results are paginated; the script automatically handles multiple pages
- Some entities may not have all fields populated (address, instruments, etc.)
- Fuzzy matching is based on statistical similarity and may include false positives
- Always verify results against your own data sources

## Understanding the Codes

### Country Codes
**Format**: ISO 3166-1 alpha-2 (2-letter codes)
- **Examples**: `GB` (United Kingdom), `US` (United States), `CN` (China)
- **Definition**: International standard codes assigned by ISO to every country

### Region Codes
**Format**: ISO 3166-2 (country-subdivision format: `COUNTRY-REGION`)
- **Examples**: 
  - `GB-LND` = United Kingdom, London
  - `US-NY` = United States, New York
  - `CA-ON` = Canada, Ontario
- **Definition**: Regional subdivisions within countries (states, provinces, districts)

### Country of Jurisdiction
The country whose **legal/regulatory system** governs the entity. Usually matches the registered country but can differ for multinational or cross-border entities.

---

## gleif_reference_data.py - Reference Data Tool

Fetch standardized codes and definitions from the GLEIF API.

### Usage

```bash
# Fetch all reference data types
python gleif_reference_data.py --all

# Fetch a specific reference type
python gleif_reference_data.py countries
python gleif_reference_data.py regions
python gleif_reference_data.py entity-legal-forms
python gleif_reference_data.py jurisdictions

# List available reference data types
python gleif_reference_data.py --list
```

### Available Reference Data Types

| Type | Description |
|------|-------------|
| `countries` | ISO country codes and official names (250 entries) |
| `regions` | ISO 3166-2 region/subdivision codes (5000+ entries) |
| `entity-legal-forms` | Legal entity form types by country/jurisdiction (3400+ entries) |
| `jurisdictions` | Jurisdiction codes for entity registration (5200+ entries) |
| `registration-authorities` | Business register authorities (1000+ entries) |
| `official-organizational-roles` | Organizational role types (2100+ entries) |

### Examples

**Get all countries with names:**
```bash
python gleif_reference_data.py countries > countries_reference.json
```

**Get all region codes:**
```bash
python gleif_reference_data.py regions > regions_reference.json
```

**Get entity legal forms (useful for understanding entity types):**
```bash
python gleif_reference_data.py entity-legal-forms > legal_forms.json
```

**Export all reference data:**
```bash
python gleif_reference_data.py --all > gleif_reference_data.json
```

### Example Output

**Countries:**
```json
{
  "id": "GB",
  "code": "GB",
  "name": "United Kingdom"
}
```

**Regions:**
```json
{
  "id": "GB-LND",
  "code": "GB-LND",
  "name": null,
  "names": [
    {
      "language": "en",
      "name": "London"
    }
  ]
}
```

**Entity Legal Forms:**
```json
{
  "id": "1GEE",
  "code": "1GEE",
  "country": "United States of America",
  "countryCode": "US",
  "subdivisionCode": "US-DE",
  "status": "ACTV",
  "names": [
    {
      "localName": "Corporation",
      "language": "English",
      "languageCode": "en"
    }
  ]
}
```

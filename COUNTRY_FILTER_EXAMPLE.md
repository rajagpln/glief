# Country of Jurisdiction Filter - Usage Guide

The `gleif_search.py` script now supports filtering results by **Country of Jurisdiction** using the optional `--country` or `-c` flag.

## Usage

### Basic Syntax
```bash
python gleif_search.py "search query" --country [2-LETTER-CODE]
python gleif_search.py "search query" -c [2-LETTER-CODE]
```

## Examples

### Example 1: Find all Citibanks in the UK
```bash
python gleif_search.py "Citibank" --country GB
```

**Results:**
- 6 entities with "Citibank" in the legal name in the UK
- Includes: CITIBANK UK LIMITED, CITIBANK INVESTMENTS LIMITED, etc.

### Example 2: Find all Citibanks in the US
```bash
python gleif_search.py "Citibank" --country US
```

**Results:**
- 14 entities with "Citibank" in the legal name in the US

### Example 3: Find all Citibanks in Brazil
```bash
python gleif_search.py "Citibank" --country BR
```

**Results:**
- 4 entities with "Citibank" in the legal name in Brazil

### Example 4: Full-text search with country filter
```bash
python gleif_search.py --fulltext "Bank" --country CN
```

**Results:**
- 603 entities with "Bank" anywhere in their record in China
- Includes direct bank names and related fund names

### Example 5: Multiple searches with different countries
```bash
# Find all banks in Germany
python gleif_search.py "Bank" --country DE

# Find all banks in France
python gleif_search.py "Bank" --country FR

# Find all banks in India
python gleif_search.py "Bank" --country IN
```

## Common Country Codes

| Code | Country |
|------|---------|
| `GB` | United Kingdom |
| `US` | United States |
| `CN` | China |
| `JP` | Japan |
| `DE` | Germany |
| `FR` | France |
| `CA` | Canada |
| `AU` | Australia |
| `IN` | India |
| `BR` | Brazil |
| `MX` | Mexico |
| `SG` | Singapore |
| `HK` | Hong Kong |
| `IE` | Ireland |
| `NL` | Netherlands |

## Combining Filters

### Name Search + Country Filter
```bash
python gleif_search.py "Citibank" --country GB
```
- Searches only in legal entity names
- Filters to UK jurisdiction
- Result: 6 entities

### Full-text Search + Country Filter
```bash
python gleif_search.py --fulltext "Citibank" --country GB
```
- Searches across all fields (name, address, metadata)
- Filters to UK jurisdiction
- Result: More entities than name-only search

## Output Format

The JSON output includes the country filter information:

```json
{
  "query": "Citibank",
  "search_type": "name",
  "country_filter": "GB",
  "results_count": 6,
  "results": [
    {
      "legal_entity_id": "549300U8H3KN0K301B23",
      "legal_entity_name": "CITIBANK UK LIMITED",
      "region": "GB-LND",
      "country": "GB",
      "country_of_jurisdiction": "GB",
      ...
    }
  ]
}
```

## Filter Behavior

- **Case-insensitive**: Both `GB` and `gb` work
- **Optional**: Omit the flag to search without country filtering
- **API-native**: Uses GLEIF API's `entity.legalAddress.country` filter for efficiency
- **Combined with search type**: Works with both `--fulltext` and name-only searches

## Tips

1. **Get reference data first**: Download country codes using:
   ```bash
   python gleif_reference_data.py countries
   ```

2. **Export filtered results**: Save to file:
   ```bash
   python gleif_search.py "Citibank" --country GB > citibank_uk.json
   ```

3. **Filter by country and then by region**: Use jq:
   ```bash
   python gleif_search.py "Citibank" --country GB | \
     jq '.results[] | select(.region == "GB-LND")'
   ```

4. **Count entities per country**:
   ```bash
   python gleif_search.py --fulltext "Bank" --country CN | \
     jq '.results_count'
   ```

## Performance

- Country filtering is applied **server-side** at the GLEIF API level
- Reduces data transfer and processing time
- More efficient than client-side filtering

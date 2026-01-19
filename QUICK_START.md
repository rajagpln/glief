# GLEIF Toolkit - Quick Start Guide

A complete guide to using the GLEIF search and reference data tools together.

## What You Have

### 1. gleif_search.py
Search for legal entities by name or across all fields

### 2. gleif_reference_data.py
Fetch standardized codes and definitions (countries, regions, entity types)

### 3. CODE_REFERENCE.md
Complete guide to understanding the codes in the output

---

## Quick Examples

### Example 1: Find a Citibank in London

```bash
# Search for Citibank (name-only)
python gleif_search.py "Citibank" | jq '.results[] | select(.region == "GB-LND")'
```

**Output:**
```json
{
  "legal_entity_id": "549300U8H3KN0K301B23",
  "legal_entity_name": "CITIBANK UK LIMITED",
  "region": "GB-LND",
  "country": "GB",
  "country_of_jurisdiction": "GB",
  "address": {
    "city": "London",
    "postal_code": "E14 5LB",
    "country": "GB"
  }
}
```

**Decoding the codes:**
- `country`: `GB` = United Kingdom
- `region`: `GB-LND` = London, United Kingdom
- BIC Code: `CIUKGB2LXXX` = Citibank, United Kingdom, London

### Example 2: Get all countries reference data

```bash
python gleif_reference_data.py countries > countries.json

# Find what "GB" means
cat countries.json | jq '.items[] | select(.code == "GB")'
```

**Output:**
```json
{
  "id": "GB",
  "code": "GB",
  "name": "United Kingdom"
}
```

### Example 3: Understand entity types by looking up legal forms

```bash
# Get entity legal forms for United States
python gleif_reference_data.py entity-legal-forms > legal_forms.json

# Find "Corporation" entities in Delaware
cat legal_forms.json | jq '.items[] | select(.subdivisionCode == "US-DE" and .names[0].localName == "Corporation")' | head -5
```

### Example 4: Map region codes to names

```bash
# Get all region codes
python gleif_reference_data.py regions > regions.json

# Look up what "US-NY" means
cat regions.json | jq '.items[] | select(.code == "US-NY")'
```

**Output:**
```json
{
  "id": "US-NY",
  "code": "US-NY",
  "names": [
    {
      "language": "en",
      "name": "New York"
    }
  ]
}
```

### Example 5: Full-text search with geographic filtering

```bash
# Search for all "Bank" entities (full-text search)
python gleif_search.py --fulltext "Bank" | \
  jq '.results[] | select(.country == "CN")'
```

This finds all entities with "Bank" anywhere in their record, filtered to China only.

---

## Workflow: Complete Entity Investigation

Let's say you found an LEI and want to understand all the codes:

### Step 1: Get the entity details

```bash
python gleif_search.py "Citibank" > citibank_results.json

# Extract specific entity
cat citibank_results.json | \
  jq '.results[] | select(.legal_entity_id == "549300U8H3KN0K301B23")'
```

**Result includes:**
```json
{
  "legal_entity_id": "549300U8H3KN0K301B23",
  "legal_entity_name": "CITIBANK UK LIMITED",
  "region": "GB-LND",
  "country": "GB",
  "country_of_jurisdiction": "GB",
  "address": {...},
  "tickers_and_instruments": [
    {
      "type": "BIC",
      "value": ["CIUKGB2LXXX"]
    }
  ]
}
```

### Step 2: Look up the country code

```bash
python gleif_reference_data.py countries | \
  jq '.items[] | select(.code == "GB")'
```

**Result:**
```json
{
  "id": "GB",
  "code": "GB",
  "name": "United Kingdom"
}
```

✅ Country confirmed: **United Kingdom**

### Step 3: Look up the region code

```bash
python gleif_reference_data.py regions | \
  jq '.items[] | select(.code == "GB-LND")'
```

**Result:**
```json
{
  "id": "GB-LND",
  "code": "GB-LND",
  "names": [{"language": "en", "name": "London"}]
}
```

✅ Region confirmed: **London**

### Step 4: Look up the BIC code

The BIC `CIUKGB2LXXX` breaks down as:
- `CIUK` = Citibank UK
- `GB` = Great Britain
- `2L` = London area
- `XXX` = Primary office

You can verify this at https://www.swift.com/

### Step 5: Look up financial instruments

If there were ISINs, search at https://www.isin.net/

---

## Combining with jq for Advanced Queries

### Find all entities in a specific region

```bash
python gleif_search.py "Citibank" | \
  jq '.results[] | select(.region | startswith("US-"))'
```

### Get a summary of all countries where entities operate

```bash
python gleif_search.py --fulltext "Citibank" | \
  jq '.results | group_by(.country) | map({country: .[0].country, count: length})'
```

### Extract all BIC codes

```bash
python gleif_search.py "Citibank" | \
  jq '.results[] | select(.tickers_and_instruments != null) | .tickers_and_instruments[] | select(.type == "BIC")'
```

### Create a CSV export

```bash
python gleif_search.py "Citibank" | \
  jq -r '.results[] | [.legal_entity_id, .legal_entity_name.name, .country, .region] | @csv' > entities.csv
```

---

## Saving Reference Data for Offline Use

### Download all reference data once

```bash
# Create a master reference file
python gleif_reference_data.py --all > gleif_reference_master.json

# Create individual reference files
python gleif_reference_data.py countries > countries_ref.json
python gleif_reference_data.py regions > regions_ref.json
python gleif_reference_data.py entity-legal-forms > legal_forms_ref.json
python gleif_reference_data.py jurisdictions > jurisdictions_ref.json
```

### Create a lookup script

You can now use these reference files offline to decode codes:

```bash
# Look up country name from code
cat countries_ref.json | jq '.items[] | select(.code == "MA") | .name'

# Look up region name from code
cat regions_ref.json | jq '.items[] | select(.code == "MA-CAS") | .names[0].name'
```

---

## API Rate Limits and Best Practices

- **Rate limit**: 60 requests per minute per user
- **No authentication required**
- **Free to use**: No API key needed

### Tips for efficient usage

1. **Batch requests**: Download reference data once with `--all`
2. **Cache results**: Save search results to JSON files
3. **Use filters**: Pipe results through `jq` to filter before analysis
4. **Plan ahead**: Fetch all reference data you might need in one session

---

## Troubleshooting

### "No results found"

```bash
# Try full-text search if name-only returns nothing
python gleif_search.py --fulltext "company name"

# Check entity name variations
python gleif_search.py "citibank"  # lowercase
python gleif_search.py "citi"      # partial name
```

### "Region code not found"

Reference data might not include all historical codes. This is normal - GLEIF updates codes periodically.

### "BIC/ISIN not available"

Not all entities have financial instruments. These are only populated when:
- The entity is registered with SWIFT (for BIC)
- The entity has issued securities (for ISIN)

---

## Example Scripts

### Script 1: Find entities by country

```bash
#!/bin/bash
# find_by_country.sh
COUNTRY=$1
python gleif_search.py "Citibank" | \
  jq ".results[] | select(.country == \"$COUNTRY\")" | \
  jq '{name: .legal_entity_name.name, id: .legal_entity_id, city: .address.city}'
```

Usage:
```bash
./find_by_country.sh "GB"
```

### Script 2: Create a master reference database

```bash
#!/bin/bash
# build_reference_db.sh
mkdir -p reference_data
python gleif_reference_data.py countries > reference_data/countries.json
python gleif_reference_data.py regions > reference_data/regions.json
python gleif_reference_data.py entity-legal-forms > reference_data/legal_forms.json
echo "Reference data downloaded to reference_data/"
```




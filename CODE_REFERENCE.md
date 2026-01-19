# GLEIF Code Reference Guide

This document explains the codes found in GLEIF API responses and how to interpret them.

## Country Codes (ISO 3166-1 Alpha-2)

**Format**: 2-letter codes  
**Standard**: ISO 3166-1 Alpha-2  
**Source**: International Organization for Standardization

### Examples from Your Data

| Code | Country | Example Entity |
|------|---------|----------------|
| `MA` | Morocco | CITIBANK MAGHREB (Casablanca) |
| `SN` | Senegal | CITIBANK SENEGAL (Dakar) |
| `MY` | Malaysia | CITIBANK BERHAD (Kuala Lumpur) |
| `CA` | Canada | CITIBANK CANADA (Halifax) |
| `GB` | United Kingdom | CITIBANK UK LIMITED (London) |
| `US` | United States | Citibank, National Association (Sioux Falls) |
| `CN` | China | 花旗银行（中国）有限公司 (Shanghai) |
| `BR` | Brazil | BANCO CITIBANK S A (São Paulo) |
| `JP` | Japan | CITIBANK JAPAN LIMITED (Tokyo) |
| `HK` | Hong Kong | Citigroup Global Markets Hong Kong Nominee Limited |

**How to use**: Look up country codes at https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

---

## Region Codes (ISO 3166-2)

**Format**: `COUNTRY-REGION` (e.g., `MA-CAS`, `US-NY`)  
**Standard**: ISO 3166-2  
**Coverage**: States, provinces, districts, and other subdivisions

### Examples from Your Data

| Code | Country | Region | Example Entity |
|------|---------|--------|----------------|
| `MA-CAS` | Morocco | Casablanca | CITIBANK MAGHREB |
| `SN-DK` | Senegal | Dakar | CITIBANK SENEGAL |
| `MY-14` | Malaysia | Kuala Lumpur | CITIBANK BERHAD |
| `CA-NS` | Canada | Nova Scotia | CITIBANK CANADA |
| `GB-LND` | United Kingdom | London | CITIBANK UK LIMITED, CITIBANK INVESTMENTS LIMITED |
| `US-SD` | United States | South Dakota | Citibank, National Association |
| `US-DE` | United States | Delaware | Citibank Overseas Investment Corporation |
| `US-NY` | United States | New York | CITIBANK OMNI MASTER TRUST |
| `CN-SH` | China | Shanghai | 花旗银行（中国）有限公司 |
| `BR-SP` | Brazil | São Paulo | BANCO CITIBANK S A |
| `JP-13` | Japan | Tokyo (13) | CITIBANK JAPAN LIMITED |
| `PL-14` | Poland | Mazovia | Citibank Europe plc Branch in Poland |

### How to Interpret Region Codes

The format is always: `[COUNTRY_CODE]-[REGION_CODE]`

**Examples:**
- `GB-LND` = Split on hyphen → `GB` (United Kingdom) + `LND` (London)
- `US-CA` = Split on hyphen → `US` (United States) + `CA` (California)
- `JP-13` = Split on hyphen → `JP` (Japan) + `13` (Tokyo Prefecture)

**Note**: Region codes are country-specific and don't follow a global standard format. Some use abbreviations (LND=London), some use numbers (JP=13), some use longer codes (MY-14).

---

## Country of Jurisdiction

**Definition**: The country whose legal/regulatory system governs the entity

**Relationship to Country field**:
- Usually **identical** to the `country` field
- Can differ for multinational entities
- Determines which laws apply to the entity

### Example

```json
{
  "legal_entity_name": "Citibank, National Association",
  "country": "US",
  "country_of_jurisdiction": "US",
  "address": {
    "city": "Sioux Falls",
    "postal_code": "57108",
    "country": "US"
  }
}
```

In this case:
- Entity operates in the **US** (country)
- Entity is governed by **US** law (country_of_jurisdiction)
- Both are the same

---

## Entity Legal Form Codes

**What they represent**: Type of business entity (Corporation, Limited Liability Company, Bank, etc.)  
**Format**: 4-character alphanumeric codes (e.g., `1GEE`, `0AWU`)  
**Jurisdiction**: Country/state-specific

### Examples

| Code | Country | Jurisdiction | Legal Form | Status |
|------|---------|--------------|------------|--------|
| `1GEE` | United States | Delaware | Corporation | ACTV (Active) |
| `0AWU` | United States | Oregon | Credit Union | ACTV |
| `10UR` | Canada | Quebec | Syndicat coopératif | ACTV |
| `106J` | Belarus | - | Закрытое акционерное общество (Closed JSC) | ACTV |
| `0OCP` | Vietnam | - | Công ty trách nhiệm hữu hạn (Limited Liability Co.) | ACTV |

### How to Use Legal Form Codes

The `gleif_reference_data.py` script fetches all legal forms:

```bash
python gleif_reference_data.py entity-legal-forms
```

This returns detailed information including:
- Code
- Country
- Jurisdiction (state/province)
- Local name (in native language)
- Transliterated name (in English/Latin characters)
- Status (ACTV, INACT, etc.)

---

## BIC (Bank Identifier Code)

**Format**: 8 or 11 characters  
**Standard**: ISO 9362  
**Purpose**: Identify banks in financial transactions

### Examples from Your Data

| BIC | Bank | Country |
|-----|------|---------|
| `CITIMAMCXXX` | Citibank Maghreb | Morocco |
| `CITIMYKLXXX` | Citibank Malaysia | Malaysia |
| `CITICATTXXX` | Citibank Canada | Canada |
| `CIUKGB2LXXX` | Citibank UK | United Kingdom |
| `CITIJPJTXXX` | Citibank Japan | Japan |
| `CITICOBBXXX` | Citibank Colombia | Colombia |

### BIC Code Format

8-character format: `AAAA BB CC`
- **AAAA**: Bank code (4 letters)
- **BB**: Country code (2 letters)
- **CC**: Location code (2 letters)

11-character format: `AAAA BB CC DDD`
- Additional **DDD**: Branch identifier (3 letters)

---

## ISIN (International Securities Identification Number)

**Format**: 12 characters (letters and numbers)  
**Standard**: ISO 6166  
**Purpose**: Identify financial securities (bonds, stocks, etc.)

### Examples from Your Data

| ISIN | Issuer/Description |
|------|-------------------|
| `US17303CAC55` | Citibank Credit Card Master Trust I |
| `NGCP26CITI62` | Citibank Nigeria Limited |
| `US17305EGE95` | Citibank Credit Card Issuance Trust |
| `USU3090TAD01` | Citibank OMNI Master Trust |

### ISIN Format

`CC NNNNNNNNNNN C`
- **CC**: 2-letter country code
- **NNNNNNNNNNN**: 9-character NSIN (National Securities Identification Number)
- **C**: Check digit (calculated from the other characters)

### Example Breakdown

For `US17303CAC55`:
- **US** = United States
- **17303CAC55** = Specific security identifier
- Forms the unique identifier for that particular financial instrument

---

## How to Look Up Codes

### Online Resources

1. **Country Codes**: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
2. **Region Codes**: https://en.wikipedia.org/wiki/ISO_3166-2
3. **BIC Lookup**: https://www.swift.com/
4. **ISIN Search**: https://www.isin.net/

### Using gleif_reference_data.py

```bash
# Get all country codes
python gleif_reference_data.py countries

# Get all region codes
python gleif_reference_data.py regions

# Get all entity legal forms for a specific country
python gleif_reference_data.py entity-legal-forms | \
  grep -A 10 '"countryCode": "MA"'

# Get all reference data at once
python gleif_reference_data.py --all > all_references.json
```

---

## Common Use Cases

### Find all Citibanks in a specific country

```bash
# Name-only search (default)
python gleif_search.py "Citibank" | \
  jq '.results[] | select(.country == "GB")'
```

### Find entity type for an LEI

Get the LEI record from search results, note the `country` and `country_of_jurisdiction`, then look up the entity legal form code in the reference data.

### Map location codes to names

1. Get `country` code from entity (e.g., `GB`)
2. Look up in countries reference: `GB` → `United Kingdom`
3. Get `region` code from entity (e.g., `GB-LND`)
4. Look up in regions reference: `GB-LND` → `London`

### Understand financial instruments

1. Find `BIC` code in entity results
2. Look up at https://www.swift.com to get bank details
3. Find `ISIN` codes in entity results
4. Search at https://www.isin.net for security details


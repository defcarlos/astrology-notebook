---
type: Astrology Data Validator
title: JSON Payload & Profile Schema Validator
description: Validates astrological JSON payloads (*_llm_payload.json) and calculation profiles (*_astrology_profile.json) before report generation.
tags: [validation, schema, astrology, data quality, okf]
version: 1.1.0
---

# Astrology Data Validator

## Purpose
Validates pre-calculated astrological JSON payloads before chat synthesis, ensuring data integrity and schema completeness. It supports both **LLM Structured Payloads** (`*_llm_payload.json`) and **Full Calculation Engine Profiles** (`*_astrology_profile.json`).

---

## Schema Validation Rules

### 1. LLM Structured Payload Schema (`*_llm_payload.json`)
This is the primary input consumed by synthesis agents and LLM tooling.

#### Required Top-Level Fields:
```json
{
  "subject": { "name": "string", "birth": "string", "timezone": "string", "coordinates": [number, number] },
  "ascendant": { "sign": "string", "degree_in_house": number, "nakshatra": "string", "nakshatra_pada": number },
  "current_dasha": { "mahadasha": { "lord", "start", "end" }, "antardasha": { "lord", "start", "end" }, "pratyantardasha": { "lord", "start", "end" } },
  "next_antardasha": "string",
  "planets": {
    "Sun": { "sign", "house", "placed_in_house", "deg", "nakshatra", "nakshatra_pada", "dignity", "power", "bala", "d9", "d10", "karaka", "takeaway", "avasthas" },
    "Moon": { ... },
    "Mercury": { ... },
    "Venus": { ... },
    "Mars": { ... },
    "Jupiter": { ... },
    "Saturn": { ... },
    "Rahu": { ... },
    "Ketu": { ... }
  },
  "active_yogas": [{ "name": "string", "planets": ["string"], "results": "string" }],
  "key_aspects": ["string"],
  "parashari_aspects": ["string"],
  "transits": { "Planet": { "sign", "house_from_moon", "is_auspicious" } },
  "panchanga": { "tithi": "string", "nakshatra": "string", "vara": "string", "yoga": "string" },
  "sav_bindus": [number, number, ...]
}
```

#### Validation Checklist for `*_llm_payload.json`:
- ✅ **Subject**: Name non-empty, birth string formatted, valid IANA timezone, coordinates array with `[lat, lon]`.
- ✅ **Ascendant**: Tropical sign, degree (0–30°), Vedic Nakshatra and Pada (1–4).
- ✅ **Current Dasha**: Mahadasha, Antardasha, Pratyantardasha each with valid planet lord, start date, and end date.
- ✅ **Planets Map**: All 9 core Vedic bodies present (`Sun`, `Moon`, `Mercury`, `Venus`, `Mars`, `Jupiter`, `Saturn`, `Rahu`, `Ketu`).
- ✅ **Planet Structure**:
  - `placed_in_house` (1–12) and `rules_houses` array (e.g. `[12]` or `[1, 10]`).
  - Vedic `nakshatra` and `nakshatra_pada` (1–4).
  - Classical `dignity` and upstream flags (`is_retrograde`, `is_combust`).
  - Raw power metrics: `power` label and `bala` (Shadbala score, or `null` for Rahu/Ketu).
  - Divisional placements: `d9` (Navamsa sign) and `d10` (Dashamsha sign).
  - Jaimini `karaka` (Chara Karaka assignment) and synthesized `takeaway`.
  - Classical `avasthas` object with `baladi`, `jagradadi`, and `diptadi`.
- ✅ **SAV Bindus**: Exactly 12 integer bindu scores representing Houses 1 through 12.
- ✅ **Panchanga**: Valid `tithi`, `nakshatra`, `vara`, and `yoga`.

---

### 2. Full Calculation Engine Profile Schema (`*_astrology_profile.json`)
This is the raw, exhaustive calculation output from Universal Astrological OKF Engine v2.0 (~300 KB).

#### Required Top-Level Fields:
```json
{
  "metadata": { "engine": "string", "version": "string", "settings": { ... } },
  "fingerprint": "string",
  "subject": { "name": "string", "birth_data": { "date", "time", "timezone", "latitude", "longitude" } },
  "astrological_chart": { "ascendant", "planets", "houses", "ashtakavarga", "active_yogas" },
  "planetary_friendships": { "natural", "temporal", "compound" }
}
```

---

## Validation Output

### Success Response
```json
{
  "valid": true,
  "payload_type": "llm_payload",
  "subject": "Sample Subject",
  "data_quality_score": 100,
  "warnings": [],
  "missing_optional": []
}
```

### Failure Response
```json
{
  "valid": false,
  "payload_type": "llm_payload",
  "errors": [
    "Missing subject.name",
    "sav_bindus must contain exactly 12 house scores, found 11",
    "Planet 'Mars' missing required field: 'rules_houses'"
  ],
  "data_quality_score": 45
}
```

---

## Data Quality Scoring

| Score Range | Quality Level | Action |
|-------------|---------------|--------|
| 90-100 | Excellent | Proceed with high confidence |
| 75-89 | Good | Proceed with warnings logged |
| 50-74 | Fair | Review required before proceeding |
| 0-49 | Poor | Abort - critical data missing |

---

## Integration Points

### Pre-Processing Hook
Called before any Phase 1-3 execution:
```bash
astrology_data_validator payload=[subject]_llm_payload.json
```

### Output Storage
- Validation results cached in KV store.
- Quality score used for report metadata.
- Warnings included in response if score < 90.

---

## Error Codes

| Code | Description | Recovery |
|------|-------------|----------|
| `VALIDATION_ERROR` | Schema mismatch | Fix JSON structure |
| `MISSING_REQUIRED` | Critical field absent | Add required data |
| `FORMAT_INVALID` | Date/time/format error | Correct format |
| `RANGE_ERROR` | Values out of bounds (e.g. SAV or degree) | Check calculations |
| `PLANET_COUNT_ERROR` | Less than 9 core planets | Include all Vedic planets |

---

## Usage Example

```bash
# Validate payload
validator_result=$(astrology_data_validator payload=[subject]_llm_payload.json)

# Check score
quality_score=$(echo $validator_result | jq '.data_quality_score')

if [ "$quality_score" -lt 75 ]; then
  echo "Low quality score - review before proceeding"
  exit 1
fi

# Proceed with synthesis
astrology_synthesis_agent subject=[subject]
```
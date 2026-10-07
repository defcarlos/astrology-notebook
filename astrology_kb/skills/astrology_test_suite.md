---
type: Automated Testing Suite
title: Astrology Report Test Generator
description: Generates synthetic test payloads and validates report output quality.
tags: [testing, validation, quality assurance, automation]
---

# Astrology Report Test Suite

## Purpose
Automated testing framework for validating astrology report generation across various chart configurations and edge cases.

## Test Categories

### 1. Schema Validation Tests
```
test_schema_complete.json      # All fields present
test_schema_minimal.json       # Only required fields
test_schema_missing_yogas.json # Yogas absent
test_schema_missing_shadbala.json # Strength data absent
```

### 2. Edge Case Tests
```
test_rare_ascendant.json       # Scorpio ascendant (uncommon)
test_planet_conjunction.json   # Multiple planets same sign
test_empty_yogas.json          # No active yogas
test_weak_chart.json           # All planets weak
test_strong_chart.json         # All planets strong
```

### 3. Boundary Tests
```
test_newborn.json              # Birth date: 2024-01-01
test_elder.json                # Birth date: 2023-01-01
test_meridian.json             # Time: 00:00:00
test_solstice.json             # Birth during solstice
test_equinox.json              # Birth during equinox
```

### 4. Integration Tests
```
test_full_workflow.json        # Complete 3-phase execution
test_batch_processing.json     # Multiple subjects
test_cache_efficiency.json     # KV cache performance
test_template_rendering.json   # Template variable substitution
```

## Test Execution

### Single Test
```bash
test_run payload=test_schema_complete.json
# Output: { passed: true, duration: 2.3s, score: 98 }
```

### Batch Tests
```bash
test_run suite=full
# Executes all 47 test cases
# Output:
#   Total: 47
#   Passed: 45
#   Failed: 2
#   Skipped: 0
#   Score: 95.7%
```

### Regression Tests
```bash
test_run suite=regression baseline=v1.0
# Compares output against known-good baseline
```

## Test Metrics

### Quality Score Calculation
```
score = (
  schema_valid * 30 +
  phase1_complete * 15 +
  phase2_complete * 15 +
  phase3_complete * 15 +
  formatting_correct * 15 +
  data_accuracy * 10 +
  consistency_score * 10
)
```

### Pass/Fail Criteria
| Metric | Pass | Fail |
|--------|------|------|
| Schema validation | 100% | < 100% |
| Phase completion | All 3 phases (Foundation, Modifiers, Verdict) | Missing phases |
| Formatting | No errors | Syntax errors |
| Data accuracy | Matches JSON | Discrepancies found |
| Cross-references | All valid | Invalid references |

## Test Output Format

### Success
```json
{
  "test_name": "test_schema_complete",
  "passed": true,
  "duration_ms": 2340,
  "score": 100,
  "output_sample": "sample_chart_output.md",
  "metrics": {
    "kv_hits": 12,
    "kv_misses": 0,
    "file_ops": 3,
    "render_time_ms": 45
  }
}
```

### Failure
```json
{
  "test_name": "test_missing_planet",
  "passed": false,
  "duration_ms": 1200,
  "score": 45,
  "errors": [
    "Phase 1: Missing Moon data",
    "Phase 2: D-9 Navamsa placement incomplete",
    "Phase 3: Planetary friendship analysis incomplete"
  ],
  "suggestions": [
    "Add fallback 'Not Provided' handling",
    "Validate planet count before processing"
  ]
}
```

## Test Data Generation

### Synthetic Payload Generator
```bash
payload_generate type=random count=100
# Creates 100 random test payloads
# Covers:
#   - All 12 ascendants
#   - All 12 moon signs
#   - All dignity states
#   - Random yoga combinations
```

### Parameterized Tests
```bash
payload_generate type=parameterized \
  var=ascendant values=[Cancer, Scorpio, Aquarius] \
  var=moon_sign values=[Leo, Capricorn, Pisces] \
  count=9
# Creates 9 payloads testing specific combinations
```

## Performance Tests

### Load Testing
```bash
performance_test concurrent=10 payload_count=50
# Simulates 10 concurrent report generations
# Measures:
#   - Response time (p50, p95, p99)
#   - Cache hit ratio
#   - Memory usage
#   - Disk I/O
```

### Stress Testing
```bash
stress_test payload_size=50KB duration=1hr
# Tests system under load
# Detects:
#   - Memory leaks
#   - Cache bloat
#   - I/O bottlenecks
```

## Continuous Integration

### CI Pipeline
```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - run: test_run suite=full
      - run: test_run suite=regression
      - run: test_run suite=performance
```

### Scheduled Tests
```bash
# Daily
cron 0 2 * * * test_run suite=regression

# Weekly
cron 0 3 * * 0 test_run suite=full

# Monthly
cron 0 4 1 * * test_run suite=performance
```

## Test Coverage Goals

| Area | Target | Current |
|------|--------|---------|
| Schema validation (`*_llm_payload.json` & `*_astrology_profile.json`) | 100% | 98% |
| Phase 1: Foundation (Tripod & Core Structure) | 100% | 98% |
| Phase 2: Modifiers & Timing (Vargas, Dashas, SAV) | 100% | 97% |
| Phase 3: Synergy & Verdict (Friendships & Confluence) | 100% | 96% |
| Template rendering (Markdown & HTML) | 100% | 99% |
| KV caching | 100% | 92% |
| Error handling & fallbacks | 100% | 90% |

## Test Reporting

### HTML Report
```bash
test_report format=html output=test_report.html
# Includes:
#   - Pass/fail summary
#   - Detailed logs
#   - Performance metrics
#   - Coverage statistics
```

### JSON Summary
```bash
test_report format=json output=test_report.json
# Machine-readable for CI/CD
```

## Usage Example
```bash
# Run full test suite
test_run suite=full

# View failed tests
test_report failed=true

# Generate coverage report
test_report coverage=true format=html

# Fix failing tests
test_fix test=test_schema_minimal
```
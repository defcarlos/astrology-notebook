---
type: Skill Index
title: Astrology Knowledge Base Skills
description: Complete index and quick reference for all astrology synthesis skills.
tags: [index, reference, skills, navigation]
---

# Astrology Knowledge Base - Skills Index

## Quick Start

### 💬 For Interactive Chat (LM Studio Bionic)

#### Workflow 1: Astrology Writer (Client Reading)
1. **System Prompt Preset:** Create preset `Astrology Writer` with the instruction:
   > *"You are an expert astrologer writing a direct chat message to a client. Use the attached natal placements file to generate the report."*
2. **Model Parameters:** Context Length $\ge 8,192$ tokens; Temperature `0.5`–`0.7`.
3. **Load Skill / Knowledge Base:** Import the [Astrology Writer Skill](../astrology-writer/SKILL.md) (or from `~/.lmstudio/skills/astrology-writer/`) into LM Studio Bionic, or add `/astrology_kb` as a local document collection.
4. **Input:** Drag & drop or paste the client's `[name]_llm_context.md` into chat.
5. **Quality Assurance & Visual Proof:** For automated verification against hallucinations, planetary omissions, and layout errors, pair with the [Astrology Report Gatekeeper Skill](../astrology-report-gatekeeper/SKILL.md). The Gatekeeper prints a visible `### 🛡️ Gatekeeper Verification Checklist` badge at the top of the message to confirm verification before the report is displayed.

### 📄 Standard Artifact Suite
Upstream astrological engines and tools provide:
```bash
ls ./[subject]/
# [subject]_astrology_profile.json  (raw engine profile)
# [subject]_llm_payload.json        (clean LLM payload)
# [subject]_llm_context.md          (markdown context sheet)
# [subject]_report.html             (visual HTML report)
```

---

## Skills Overview

### 1. [astrology_synthesis_agent.md](astrology_synthesis_agent.md) (Primary)
- **Purpose**: 3-phase interactive chat report generation engine
- **Input**: `*_llm_payload.json` or `*_llm_context.md`
- **Output**: Direct chat analysis (no document creation required)
- **Complexity**: Medium-High
- **Time**: ~3 minutes per report
- **Best for**: Production report generation

**Key Features:**
- 3-phase execution framework
- Tropical-Vedic hybrid methodology
- Automatic template rendering
- Quality validation
- Error handling with fallbacks

**When to Use:**
- Generating individual natal reports
- Standard chart synthesis
- When data quality is good (>75%)

---

### 2. [astrology_data_validator.md](astrology_data_validator.md) (Pre-Processing)
- **Purpose**: Schema validation and quality scoring for LLM payloads and engine profiles
- **Input**: `*_llm_payload.json` or `*_astrology_profile.json`
- **Output**: Validation report with quality score
- **Complexity**: Low
- **Time**: ~30 seconds
- **Best for**: Data quality assurance

**Key Features:**
- JSON schema validation
- Required field checking
- Quality scoring (0-100)
- Warning generation
- Missing field detection

**When to Use:**
- Before running synthesis agent
- When data source is questionable
- For compliance/audit purposes

**Example Workflow:**
```bash
# Validate first
validator=$(astrology_data_validator payload=chart.json)
score=$(echo $validator | jq '.data_quality_score')

if [ "$score" -lt 75 ]; then
  echo "Low quality - review before proceeding"
  exit 1
fi

# Then synthesize
astrology_synthesis_agent subject=chart
```

---

### 3. [astrology_kv_cache.md](astrology_kv_cache.md) (Performance)
- **Purpose**: KV store caching for reference files
- **Input**: None (auto-manages cache)
- **Output**: Cached references in KV store
- **Complexity**: Low
- **Time**: ~100ms initial load, <10ms lookups
- **Best for**: Performance optimization

**Key Features:**
- Automatic file hashing
- TTL-based expiration
- LRU eviction policy
- Shared cache across workers
- Memory management

**When to Use:**
- Batch processing (always)
- Frequent report generation
- When reference files don't change

**Benefits:**
- 60x faster lookups
- 90% reduction in file I/O
- Consistent performance

---

### 4. [astrology_template_engine.md](astrology_template_engine.md) (Formatting)
- **Purpose**: Modular template management
- **Input**: Payload data + phase content
- **Output**: Formatted markdown report
- **Complexity**: Medium
- **Time**: <1ms substitution
- **Best for**: Consistent output formatting

**Key Features:**
- Variable substitution (`{{VAR}}`)
- Phase-specific templates
- Style customization (concise/verbose/executive)
- Subject-specific overrides
- Validation of template integrity

**When to Use:**
- Custom report styling needed
- Subject-specific formatting
- Executive summary generation

---

### 5. [astrology_test_suite.md](astrology_test_suite.md) (Quality Assurance)
- **Purpose**: Automated testing and validation
- **Input**: Test payloads or report outputs
- **Output**: Test results with pass/fail scores
- **Complexity**: Medium
- **Time**: 2-30 seconds per test
- **Best for**: CI/CD, regression testing

**Key Features:**
- 47+ automated test cases
- Schema validation tests
- Edge case coverage
- Performance benchmarks
- Coverage reporting

**When to Use:**
- Before deploying changes
- CI/CD pipelines
- Regression testing
- New feature validation

**Test Categories:**
- Schema validation (4 tests)
- Edge cases (8 tests)
- Boundary conditions (6 tests)
- Integration tests (10 tests)
- Performance tests (5 tests)
- Regression tests (14 tests)

---

### 6. [astrology_batch_processor.md](astrology_batch_processor.md) (Throughput)
- **Purpose**: Parallel batch processing
- **Input**: Multiple `*_llm_payload.json` files
- **Output**: Multiple reports + batch summary
- **Complexity**: High
- **Time**: 3-5 minutes for 10 subjects (parallel)
- **Best for**: Bulk report generation

**Key Features:**
- Parallel worker pool (1-32 workers)
- Shared KV cache
- Adaptive load balancing
- Priority queuing
- Per-subject error handling
- Batch-level metrics

**When to Use:**
- Processing monthly archives
- Client batch requests
- Historical chart reviews
- When throughput matters more than speed

**Performance:**
- Sequential: 3 min/report × N subjects
- Parallel (8 workers): ~4 min for 8 subjects (vs. 24 min sequential)
- Speedup: Up to 8x for large batches

---

## Skill Dependencies

```
astrology_synthesis_agent
├── astrology_kv_cache (required)
├── astrology_template_engine (required)
├── astrology_data_validator (optional, recommended)
└── astrology_batch_processor (optional, for batches)

astrology_data_validator
└── (standalone, no dependencies)

astrology_kv_cache
└── (standalone, no dependencies)

astrology_template_engine
└── (standalone, no dependencies)

astrology_test_suite
├── astrology_synthesis_agent (for integration tests)
└── astrology_data_validator (for schema tests)

astrology_batch_processor
├── astrology_synthesis_agent (required)
├── astrology_kv_cache (required)
├── astrology_template_engine (required)
└── astrology_test_suite (optional, for validation)
```

---

## Typical Workflows

### Workflow 1: Single Report (Recommended)
```bash
# 1. Validate
astrology_data_validator payload=[subject]_llm_payload.json

# 2. Generate
astrology_synthesis_agent subject=[subject]

# 3. Verify
test_run test=report_format subject=[subject]
```

### Workflow 2: Batch Processing
```bash
# 1. Warm cache (one-time per batch)
cache_warmup profiles=all

# 2. Process with parallel workers
batch_process \
  payloads=*_llm_payload.json \
  mode=parallel \
  workers=8

# 3. Monitor
batch_status batch_id=batch_20260707_143022

# 4. Export metrics
batch_metrics format=json > batch_results.json
```

### Workflow 3: CI/CD Pipeline
```yaml
# .github/workflows/astrology_tests.yml
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - run: test_run suite=regression
  full_test:
    runs-on: ubuntu-latest
    steps:
      - run: test_run suite=full
  performance:
    runs-on: ubuntu-latest
    steps:
      - run: performance_test concurrent=4 payload_count=20
```

### Workflow 4: Quality-First Generation
```bash
# 1. Validate and score
score=$(astrology_data_validator payload=chart.json | jq '.data_quality_score')

# 2. Route based on quality
if [ "$score" -ge 90 ]; then
  # Excellent quality - auto-generate
  astrology_synthesis_agent subject=chart
elif [ "$score" -ge 75 ]; then
  # Good quality - generate with warnings
  astrology_synthesis_agent subject=chart mode=warn
else
  # Poor quality - require manual review
  echo "Quality score $score - manual review required"
fi
```

---

## Performance Benchmarks

| Operation | Sequential | Parallel (8) | Improvement |
|-----------|------------|--------------|-------------|
| Single report | 3 min | N/A | - |
| 10 reports | 30 min | 4 min | **7.5x** |
| 50 reports | 150 min | 19 min | **7.9x** |
| 100 reports | 300 min | 38 min | **7.9x** |
| Cache warmup | 500ms | 100ms | **5x** |
| Reference lookup | 500ms | 10ms | **50x** |

---

## Troubleshooting

### Common Issues

**Issue**: "Phase 1 validation failed"
```bash
# Fix: Validate payload first
astrology_data_validator payload=chart.json
# Output missing fields? Add them to JSON
```

**Issue**: "KV cache miss ratio high"
```bash
# Fix: Warm cache before batch
cache_warmup profiles=all
```

**Issue**: "Template rendering error"
```bash
# Fix: Check template integrity
template_validate payload=chart.json
```

**Issue**: "Batch processing too slow"
```bash
# Fix: Increase workers or check system load
batch_process workers=16
# Or use adaptive mode
batch_process mode=adaptive
```

---

## File Locations

```
astrology-prj/
├── astrology_kb/
│   ├── agent_playbooks/
│   │   └── 3_phase_synthesis_agent.md
│   ├── core_elements/
│   │   ├── houses_bhavas/
│   │   │   └── the_12_bhavas.md
│   ├── astrology-writer/
│   │   └── SKILL.md                     # Primary decoding guide & complete planetary reading skill
│   ├── astrology-report-gatekeeper/
│   │   └── SKILL.md                     # In-memory verification & auto-correction gatekeeper
│   ├── astrology_writer.md              # Symlink to astrology-writer/SKILL.md
│   ├── astrology_report_gatekeeper.md   # Symlink to astrology-report-gatekeeper/SKILL.md
│   └── skills/
│       ├── astrology_synthesis_agent.md
│       ├── astrology_data_validator.md
│       ├── astrology_kv_cache.md
│       ├── astrology_template_engine.md
│       ├── astrology_test_suite.md
│       └── astrology_batch_processor.md
└── [subject]/                          # Standard subject directory
    ├── [subject]_astrology_profile.json  # Raw engine profile (v2.0)
    ├── [subject]_llm_payload.json        # Structured LLM payload
    ├── [subject]_llm_context.md          # Diagnostic markdown context sheet
    └── [subject]_report.html             # Visual cosmic HTML report
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-10-03 | Fully generic artifact structure; emphasized direct chat delivery and `<self_check>` protocol for local models (Qwen 9B, Gemma 4B) |
| 1.0.0 | 2026-07-07 | Initial skill package release |
| - | - | All 6 skills documented |
| - | - | KV caching layer added |
| - | - | Batch processing engine |
| - | - | Test suite with 47+ cases |

---

## Support

### Getting Help
1. Check skill documentation in `astrology_kb/skills/`
2. Run diagnostic: `test_run suite=regression`
3. Validate input: `astrology_data_validator payload=[subject]_llm_payload.json`

### Reporting Issues
Include:
- Payload sample (sanitized)
- Error message
- Command used
- Expected vs. actual output

### Contributing
To add new features:
1. Update relevant skill markdown
2. Add test cases in `astrology_test_suite.md`
3. Update benchmarks
4. Submit for review

---

## Quick Reference Commands

```bash
# Generate single chart analysis
astrology_synthesis_agent subject=[subject]

# Validate payload
astrology_data_validator payload=[subject]_llm_payload.json

# Warm cache
cache_warmup profiles=all

# Template check
template_validate payload=[subject]_llm_payload.json

# Run tests
test_run suite=full

# Batch process
batch_process payloads=*_llm_payload.json workers=8

# Check status
batch_status batch_id=batch_20261003_143022

# View metrics
batch_metrics format=json

# Performance test
performance_test concurrent=4 payload_count=20

# Cache stats
cache_stats prefix=astrology_kb

# Template help
template_help

# Validator help
validator_help
```

---

**Last Updated**: 2026-10-03  
**Version**: 1.2.0  
**Status**: Production Ready
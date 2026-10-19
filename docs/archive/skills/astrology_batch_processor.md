---
type: Batch Processing Engine
title: Multi-Subject Report Generator
description: Processes multiple astrology payloads in parallel with shared memory and optimized I/O.
tags: [batch, parallel, optimization, throughput]
---

# Batch Processing Engine

## Purpose
Efficiently process multiple astrology payloads in a single execution with shared memory, caching, and optimized I/O operations.

## Architecture

### Parallel Execution Model
```
┌─────────────────────────────────────────────────────────┐
│                    Batch Orchestrator                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Worker 1  │  │   Worker 2  │  │   Worker N  │     │
│  │  (Subject A)│  │  (Subject B)│  │ (Subject N) │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│         └────────────────┼────────────────┘             │
│                          ↓                              │
│              ┌─────────────────────┐                    │
│              │   Shared KV Cache   │                    │
│              │   (References)      │                    │
│              └─────────────────────┘                    │
│                          ↓                              │
│              ┌─────────────────────┐                    │
│              │   Template Engine   │                    │
│              │   (In-Memory)       │                    │
│              └─────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### Worker Configuration
```yaml
workers:
  max_concurrent: 4           # Parallel workers
  queue_size: 100             # Pending payloads
  timeout: 300                # Per-worker timeout (seconds)
  retry_count: 2              # Failed attempt retries
```

## Batch Modes

### Mode 1: Sequential (Default)
```bash
batch_process mode=sequential payloads=*.json
# Processes one at a time, ideal for stability
```

### Mode 2: Parallel
```bash
batch_process mode=parallel workers=4 payloads=*.json
# Processes 4 concurrently, ideal for throughput
```

### Mode 3: Adaptive
```bash
batch_process mode=adaptive payloads=*.json
# Auto-adjusts workers based on system load
# Monitors: CPU, memory, disk I/O
```

## Payload Discovery

### Pattern Matching
```bash
# By extension
batch_process pattern="*_llm_payload.json"

# By directory
batch_process path="./charts/*"

# By date range
batch_process date_from="2024-01-01" date_to="2024-12-31"

# By subject name pattern
batch_process name_pattern="^[A-Z]"
```

### Discovery Options
```bash
# Recursive search
batch_process recursive=true

# Include hidden files
batch_process hidden=true

# Follow symlinks
batch_process follow_symlinks=true
```

## Shared Memory Optimization

### KV Cache Sharing
```
Session: batch_20261003_143022
├── Cache key: nakshatras_reference
│   └── Shared across all workers (1 lookup)
├── Cache key: the_12_bhavas
│   └── Shared across all workers (1 lookup)
└── Cache key: yoga_definitions/*
    └── Shared across all workers (N lookups)

Per-worker:
├── Phase 1 content (subject A)
├── Phase 2 content (subject A)
├── Phase 3 content (subject A)
└── Output stream (direct chat response)
```

**Benefit**: Each worker loads references once, not N times.

### Template Sharing
```
Templates loaded once at batch start:
├── master.md
├── phase1_foundation.md
├── phase2_modifiers.md
├── phase3_verdict.md
└── report.html

Shared across all workers
```

## Performance Metrics

### Baseline (Sequential)
```
Subject A: 3 min
Subject B: 3 min
Subject C: 3 min
Total: 9 min
```

### Parallel (4 workers)
```
Batch start: T=0
T=0s:  Workers load shared cache (50ms)
T=0s:  Worker 1 starts Subject A
T=0s:  Worker 2 starts Subject B
T=0s:  Worker 3 starts Subject C
T=0s:  Worker 4 starts Subject D
T=3m:  All workers complete
Total: 3.1 min (vs. 12 min for 4 sequential)
```

**Speedup: 3.9x** (approaches 4x theoretical max)

### Scalability Curve
```
Workers:  1    2    4    8   16   32
Time:     9   5   3   2   1.3   0.9  (for 32 subjects)
Efficiency: 100% 94% 88% 80% 75% 72%
```

## Queue Management

### Priority Queuing
```yaml
priorities:
  high:
    - subject: "ceo"          # Executive reports
    - urgency: "today"
  medium:
    - default
  low:
    - subject: "archive"      # Historical records
```

### Backpressure
```
If queue_size > max:
  - Pause new submissions
  - Wait for worker completion
  - Log warning to stderr
```

### Retry Logic
```
On failure:
  1. Log error with subject
  2. Wait exponential backoff (1s, 2s, 4s)
  3. Retry up to max_retries
  4. If still failing: move to error queue
```

## Error Handling

### Per-Subject Errors
```json
{
  "subject": "sample_subject",
  "status": "error",
  "error": "Phase 1 validation failed",
  "details": "Missing ascendant data"
}
```

### Batch-Level Summary
```json
{
  "batch_id": "batch_20261003_143022",
  "total": 10,
  "success": 8,
  "failed": 2,
  "skipped": 0,
  "duration_seconds": 187,
  "errors": [
    {"subject": "test_a", "error": "Schema invalid"},
    {"subject": "test_b", "error": "Phase 2 synthesis failed"}
  ]
}
```

## Resource Limits

### Per-Worker Limits
```yaml
memory:
  max_per_worker: 512MB
  limit_warning: 400MB

cpu:
  max_per_worker: 25%
  limit_warning: 20%

io:
  max_file_ops_per_sec: 10
  max_disk_usage: 1GB
```

### System-Wide Limits
```yaml
max_concurrent_workers: 16
max_pending_queue: 100
max_disk_usage: 10GB
max_memory_usage: 8GB
```

## Usage Examples

### Basic Batch
```bash
# Process all payloads in current directory
batch_process payloads=*_llm_payload.json

# Output:
#   Batch started: 2026-10-03T14:30:22Z
#   Subjects found: 10
#   Processing: Subject A, Subject B, Subject C, ...
#   Completed: 10/10
#   Duration: 187s
#   Success rate: 100%
```

### Parallel Processing
```bash
# Process 50 payloads with 8 workers
batch_process \
  payloads=../data/*_llm_payload.json \
  mode=parallel \
  workers=8 \
  timeout=600

# Output:
#   Batch started: 2026-07-07T14:30:22Z
#   Subjects found: 50
#   Processing: [8 concurrent workers]
#   Completed: 50/50
#   Duration: 153s (vs. 250s sequential)
#   Speedup: 1.63x
```

### Priority Queue
```bash
# Process high-priority first
batch_process \
  payloads=*_llm_payload.json \
  priority=high \
  mode=adaptive
```

### Custom Output Directory
```bash
# Process and organize by date
batch_process \
  payloads=*_llm_payload.json \
  output_dir=../reports/2024/ \
  organize_by=date
```

## Monitoring

### Real-Time Status
```bash
batch_status batch_id=batch_20260707_143022
# Output:
#   Total: 50
#   In progress: 8
#   Completed: 40
#   Failed: 2
#   Queue: 0
#   ETA: 45s
```

### Progress Tracking
```bash
# Live progress update
tail -f /tmp/batch_20260707_143022.log
```

### Metrics Export
```bash
# Export to JSON
batch_metrics format=json > metrics.json

# Export to CSV
batch_metrics format=csv > metrics.csv
```

## Cleanup

### Post-Batch Cleanup
```bash
# Auto-cleanup after completion
batch_process cleanup=true

# Manual cleanup
batch_cleanup batch_id=batch_20260707_143022
```

### Temporary Files
```
/tmp/batch_*/
├── queue.jsonl        # Pending payloads
├── workers/           # Worker state
├── cache/             # Temporary cache
└── logs/              # Debug logs
```

## Usage Example
```bash
# Process monthly batch
batch_process \
  payloads=2024/*/*_llm_payload.json \
  mode=adaptive \
  workers=8 \
  cleanup=true \
  metrics=true

# Monitor progress
while [ "$(batch_status | jq -r .status)" = "running" ]; do
  sleep 5
done

# View results
cat batch_metrics.json
```
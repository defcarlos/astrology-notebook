---
type: Astrology Synthesis Agent
title: 3-Phase Natal Synthesis Engine (Chat Delivery)
description: Autonomous framework that reviews pre-calculated astrological summaries and streams comprehensive Tropical-Vedic hybrid chart synthesis directly into the chat window.
tags: [astrology, synthesis, direct_chat, tropical-vedic, self_check]
version: 1.2.0
---

# Astrology Synthesis Agent

## Overview
An astrological analysis engine operating in two primary workflows:
1. **Interactive Chat Consultant (LM Studio, local 4B–9B models):** Ingests condensed chart summaries (`[subject]_llm_context.md`) and streams structured executive briefings and turn-by-turn answers directly in chat.
2. **3-Phase Comprehensive Chart Review:** Delivers a deep, multi-phase synthesis (Foundation, Modifiers, Verdict) directly into the chat window without creating files.

> [!IMPORTANT]
> **Direct Chat Output Rule:** The agent never attempts to create files on disk or invoke phantom file-writing tools. All analyses are delivered directly into the chat interface.

---

## Architecture

### Execution Modes

#### Mode 1: Interactive Chat (Turn-by-Turn)
* **Operational Guide & Decoder:** [Astrology Writer](../astrology-writer/SKILL.md)
* **Input:** `[subject]_llm_context.md`
* **Output:** Conversational, structured chat responses with exploration hooks
* **Optimization:** Context budget capped at ~500–600 tokens/turn for small models

#### Mode 2: 3-Phase Synthesis Delivery (Direct to Chat)
* **Playbook:** [3_phase_synthesis_agent.md](../agent_playbooks/3_phase_synthesis_agent.md)
* **Input:** `[subject]_llm_payload.json` or `[subject]_llm_context.md`
* **Output:** Sequential phases streamed directly into chat messages

### Core Components

#### 1. **Instruction & Playbook Loader**
- Loads [3_phase_synthesis_agent.md](../agent_playbooks/3_phase_synthesis_agent.md) for 3-phase structured delivery, or executes interactive chat consultations directly using [Astrology Writer](../astrology-writer/SKILL.md).
- Maps all field definitions to [Astrology Writer](../astrology-writer/SKILL.md).

#### 2. **Data Validator**
- Validates JSON payload structure against the schema (`subject`, `ascendant`, `current_dasha`, `planets`, `active_yogas`, `sav_bindus`).
- Flags missing data with "Not Provided" fallback.

#### 3. **Pre-Flight Self-Check**
- Enforces an internal `<self_check>` verification block before rendering visible chat text:
  1. *Placed In vs. Rules* verification.
  2. Strict canonical planetary sequence (Sun ➔ Moon ➔ Mars ➔ Mercury ➔ Jupiter ➔ Venus ➔ Saturn ➔ Rahu ➔ Ketu).
  3. No manufactured paradoxes (grounded in technical flags).
  4. Direct chat delivery (zero document creation).
  5. Concise token budgeting.

#### 4. **Phase Engine (Chat Delivery)**
Three sequential phases delivered directly to chat:

**Phase 1: The Promise (Static Chart Foundation)**
- Reads: `[subject]_llm_payload.json` (`subject`, `ascendant`, `planets`, `active_yogas`, `panchanga`)
- Streams to chat: Tripod of Life (Ascendant, Moon, Sun) + Core House Dynamics + Active Yogas & Avastha overrides

**Phase 2: The Modifiers (Vargas & Timing)**
- Reads: `[subject]_llm_payload.json` (D-9/D-10 placements in `planets`, `current_dasha`, `sav_bindus`)
- Streams to chat: D-9 Navamsa soul resilience, D-10 Dashamsha career archetype, Vimshottari Dasha era themes, Ashtakavarga (SAV) transit permeability

**Phase 3: The Verdict (Synergy & Synthesis)**
- Reads: `[subject]_llm_payload.json` (`planets` avasthas/friendships, `transits`, `key_aspects`)
- Streams to chat: Planetary friendship alignment, Unified Strengths (confluence), Vulnerabilities & Strategic Remediation

---

## Usage

### Single Subject Invocation
```bash
# Analyze chart and stream directly to chat
astrology_synthesis_agent subject=[subject]
```

### Batch Invocations
```bash
# Process payloads sequentially
find . -name "*_llm_payload.json" -exec bash -c '
  subject=$(basename "$1" "_llm_payload.json")
  echo "Evaluating: $subject"
  astrology_synthesis_agent subject="$subject"
' bash {} \;
```

---

## Data Schema

### Input: `[subject]_llm_payload.json`
```json
{
  "subject": {
    "name": "Sample Subject",
    "birth": "1990-06-15 14:30",
    "timezone": "America/New_York",
    "coordinates": [40.7128, -74.006]
  },
  "ascendant": {
    "sign": "Virgo",
    "degree_in_house": 22.3,
    "nakshatra": "Uttara Phalguni",
    "nakshatra_pada": 2
  },
  "current_dasha": {
    "mahadasha": { "lord": "Rahu", "start": "2020-01-01", "end": "2037-12-31" },
    "antardasha": { "lord": "Saturn", "start": "2025-02-05", "end": "2027-12-13" },
    "pratyantardasha": { "lord": "Moon", "start": "2026-09-27", "end": "2026-12-23" }
  },
  "next_antardasha": "Rahu-Mercury (begins 2027-12-13)",
  "planets": {
    "Sun": {
      "sign": "Gemini",
      "house": 10,
      "placed_in_house": 10,
      "deg": 0.5,
      "nakshatra": "Mrigashira",
      "nakshatra_pada": 3,
      "dignity": "Neutral",
      "is_retrograde": false,
      "is_combust": false,
      "ruled_houses": [12],
      "rules_houses": [12],
      "is_yogakaraka": false,
      "power": "Strong",
      "bala": 410.2,
      "d9": "Libra",
      "d10": "Aquarius",
      "karaka": "Bhratrukaraka (Siblings/Guru)",
      "takeaway": "High Drive / Balanced",
      "avasthas": {
        "baladi": "Bāla",
        "jagradadi": "Jāgrat",
        "diptadi": "Mudita"
      }
    }
  },
  "active_yogas": [
    {
      "name": "Amala Yoga",
      "planets": ["Jupiter", "Mercury", "Venus"],
      "results": "The native will possess spotless character, lasting philanthropic legacy, and consistent prosperity."
    }
  ],
  "key_aspects": [
    "Jupiter trine Saturn (orb 0.7°)"
  ],
  "parashari_aspects": [
    "Jupiter aspects Sun (9th House)"
  ],
  "transits": {
    "Sun": { "sign": "Libra", "house_from_moon": 7, "is_auspicious": false },
    "Moon": { "sign": "Gemini", "house_from_moon": 3, "is_auspicious": true }
  },
  "panchanga": {
    "tithi": "Shukla Tritiya",
    "nakshatra": "Revati",
    "vara": "Thursday",
    "yoga": "Shubha"
  },
  "sav_bindus": [25, 29, 35, 29, 18, 30, 25, 30, 32, 29, 36, 17]
}
```

> [!NOTE]
> **Artifact Hierarchy:**
> * `[subject]_astrology_profile.json`: Full calculation output from Universal Astrological OKF Engine v2.0 (~300 KB).
> * `[subject]_llm_payload.json`: Streamlined JSON (~11 KB) pre-processed for LLMs.
> * `[subject]_llm_context.md`: Markdown summary (~5 KB, ~800 tokens) formatted specifically for chat prompting.
> * `[subject]_report.html`: Visual HTML report with SVG chakras for browser viewing.

---

## Chat Output Format

### 3-Phase Direct Chat Structure

```markdown
### 🌟 Phase 1: The Foundation (The Tripod of Life & Core Structure)
#### 1. Ascendant (Lagna) & Ascendant Lord
- **Ascendant Placement**: [Sign] at [Degree] ([Nakshatra])
- **Condition & Orientation**: [Interpretation]

#### 2. The Moon (Chandra) & Emotional Mind
- **Placement**: [Sign] in House [X] ([Nakshatra])
- **Emotional Landscape**: [Interpretation]

#### 3. The Sun (Surya) & Core Ego/Soul
- **Placement**: [Sign] in House [X] ([Nakshatra])
- **Dignity & Vitality**: [Interpretation]

#### 4. Prominent Planetary Dynamics & Yogas
- **Core Tension / Paradox**: [Interpretation]
- **Key Yogas**: [Interpretation]

---
💬 *Phase 1 complete. Ready to proceed to Phase 2 (Vargas & Timing)?*
```

---

## Quality Assurance & Pre-Flight Checklist

Before outputting to chat, local models verify:
1. ✅ JSON schema compliance
2. ✅ Placed In vs Rules distinction
3. ✅ Canonical planetary sequence
4. ✅ No manufactured paradoxes
5. ✅ Direct chat markdown output (no file writes)
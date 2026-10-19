---
type: Template Engine
title: Astrology Report Template Manager
description: Manages modular markdown and HTML templates for consistent report generation following the 3-phase framework.
tags: [templates, markdown, html, formatting, consistency]
version: 1.1.0
---

# Astrology Report Template Manager

## Purpose
Provides modular, reusable templates for consistent astrology report generation across all subjects, aligning with the 3-Phase Execution Framework and supporting both markdown chat outputs and visual HTML reports.

---

## Template Structure

### Master Markdown Template (`master.md`)
```markdown
# {{SUBJECT}} - Advanced Natal Astrology Report

## 📋 Report Overview
- **Subject**: {{SUBJECT}}
- **Birth Date**: {{BIRTH_DATE}}
- **Birth Time**: {{BIRTH_TIME}} (Timezone: {{TIMEZONE}})
- **Location**: Lat {{LATITUDE}} / Lon {{LONGITUDE}}

> **Astrological Methodology:** This analysis utilizes a **Tropical-Vedic Hybrid approach**. It bases psychological profiling and core planetary placements on the Tropical zodiac, while integrating the predictive and karmic dimensions of Vedic astrology (Nakshatras, Vargas, and Vimshottari Dashas).

{{PHASE_1_CONTENT}}

{{PHASE_2_CONTENT}}

{{PHASE_3_CONTENT}}
```

---

### Phase Templates (3-Phase Framework)

#### Phase 1: The Foundation Template (`phase1_foundation.md`)
```markdown
## 🌟 Phase 1: The Foundation (The Tripod of Life & Core Structure)

### 1. Ascendant (Lagna) & Ascendant Lord
- **Ascendant Placement**: {{ASC_SIGN}} at {{ASC_DEG}}° ({{ASC_NAKSHATRA}} P{{ASC_PADA}})
- **Condition & Orientation**: {{ASC_INTERPRETATION}}

### 2. The Moon (Chandra) & Emotional Mind
- **Placement**: {{MOON_SIGN}} in House {{MOON_PLACED_IN}}, Rules: House {{MOON_RULES}} ({{MOON_NAKSHATRA}} P{{MOON_PADA}})
- **Emotional Landscape**: {{MOON_INTERPRETATION}}

### 3. The Sun (Surya) & Core Ego/Soul
- **Placement**: {{SUN_SIGN}} in House {{SUN_PLACED_IN}}, Rules: House {{SUN_RULES}} ({{SUN_NAKSHATRA}} P{{SUN_PADA}})
- **Dignity & Vitality**: {{SUN_INTERPRETATION}}

### 4. Prominent Planetary Dynamics & Yogas
- **Core Tension / Paradox**: {{POLARITY_OR_AVASTHA_TENSION}}
- **Key Yogas**: {{ACTIVE_YOGAS_LIST}}
```

#### Phase 2: Modifiers & Timing Template (`phase2_modifiers.md`)
```markdown
## 🔍 Phase 2: Divisional Overlays & Timing Cycles

### 1. Divisional Insights (D-9 Navamsa & D-10 Dashamsha)
- **D-9 Navamsa (Soul Resilience)**: {{NAVAMSA_INTERPRETATION}}
- **D-10 Dashamsha (Career Archetype)**: {{D10_INTERPRETATION}}

### 2. Vimshottari Dasha Timing
- **Current Era**: {{MD_LORD}} > {{AD_LORD}} > {{PD_LORD}}
- **Karmic Theme**: {{DASHA_THEMES}}
- **Upcoming Shift**: {{NEXT_AD_TRANSITION}}

### 3. Ashtakavarga (SAV) Capacity & Transits
- **Matrix Distribution**: Peak House H{{PEAK_HOUSE}} @ {{PEAK_SCORE}} bindus vs Depleted House H{{LOW_HOUSE}} @ {{LOW_SCORE}} bindus
- **Transit Permeability**: {{TRANSIT_SAV_ANALYSIS}}
```

#### Phase 3: Synergy & Verdict Template (`phase3_verdict.md`)
```markdown
## 🤝 Phase 3: Interplanetary Synergy & Final Verdict

### 1. Planetary Friendships & Internal Alignment
- **Supportive Alliances (Adhi Mitra / Mitra)**: {{SUPPORTIVE_ALLIANCES}}
- **Internal Friction (Adhi Shatru / Shatru)**: {{INTERNAL_FRICTION}}

### 2. Final Synthesis & Chart Confluence
- **Unified Strengths (Confluence)**: {{UNIFIED_STRENGTHS}}
- **Vulnerabilities & Strategic Remediation**: {{REMEDIATION_STRATEGY}}
```

---

## Variable Substitution

### Automatic Variables
```
{{SUBJECT}}              → From subject.name in JSON payload
{{GENERATED_DATE}}       → Current date (ISO 8601)
{{BIRTH_DATE}}           → From subject.birth in JSON payload
{{BIRTH_TIME}}           → From subject.birth in JSON payload
{{TIMEZONE}}             → From subject.timezone in JSON payload
{{LATITUDE}}             → From subject.coordinates[0]
{{LONGITUDE}}            → From subject.coordinates[1]
```

### Dynamic Variables
```
{{ASC_SIGN}}             → Ascendant sign
{{ASC_DEG}}              → Ascendant degree in house
{{ASC_NAKSHATRA}}        → Ascendant nakshatra
{{ASC_PADA}}             → Ascendant nakshatra pada
{{MOON_SIGN}}            → Moon sign
{{MOON_PLACED_IN}}       → Moon placed_in_house
{{MOON_RULES}}           → Moon ruled house(s)
{{MOON_NAKSHATRA}}       → Moon nakshatra
{{SUN_SIGN}}             → Sun sign
{{SUN_PLACED_IN}}        → Sun placed_in_house
{{SUN_RULES}}            → Sun ruled house(s)
{{SUN_NAKSHATRA}}        → Sun nakshatra
{{ACTIVE_YOGAS_LIST}}    → Formatted classical yogas list from active_yogas array
{{NAVAMSA_INTERPRETATION}} → D-9 Navamsa analysis
{{D10_INTERPRETATION}}   → D-10 Dashamsha career analysis
{{MD_LORD}}              → Current Mahadasha lord
{{AD_LORD}}              → Current Antardasha lord
{{PD_LORD}}              → Current Pratyantardasha lord
{{NEXT_AD_TRANSITION}}   → next_antardasha string descriptor
{{PEAK_HOUSE}}           → House with maximum SAV bindus
{{PEAK_SCORE}}           → Maximum SAV score
{{LOW_HOUSE}}            → House with minimum SAV bindus
{{LOW_SCORE}}            → Minimum SAV score
{{SUPPORTIVE_ALLIANCES}} → Friendly planetary relationships
{{INTERNAL_FRICTION}}    → Great enemy / enemy friction points
{{UNIFIED_STRENGTHS}}    → Confluence synthesis
{{REMEDIATION_STRATEGY}} → Strategic action points
```

---

## Visual HTML Report Template (`report.html`)
For rich interactive browser outputs:
- Responsive dark-mode styling (`#0c0d21` background, `#f3c63f` gold accents).
- High-resolution SVG chakra charts:
  - **Sudarshana Chakra**: Concentric Tri-Wheel (Lagna, Surya, Chandra).
  - **Kota Chakra**: Fort of Vulnerability (Stambha, Madhya, Prakara, Bahya).
  - **Sarvatobhadra Chakra**: 9x9 Cosmic Radar.
  - **Kurma Chakra**: Tortoise direction matrix.
- Structured tabs / cards for Planetary Synthesis, 5-Fold Avasthas, Chara Karakas, and Vedic Yogas.

---

## Template Loading & Customization

### Warmup
```bash
template_warmup phases=[1,2,3]
# Loads Phase 1, Phase 2, and Phase 3 templates into memory
```

### Subject Customization
```
templates/
├── master.md (default)
├── [subject]/
│   └── master.md (custom styling)
└── executive/
    └── master.md (executive summary focus)
```

### Pre-Render Check
```bash
template_validate payload=[subject]_llm_payload.json
# Returns: { valid: true, missing_variables: [] }
```

### Chat Synthesis Invocation
```bash
report_generate subject=[subject] payload=[subject]_llm_payload.json
# Output: Streamed directly to chat window (no document created)
```

---

## 💬 Chat Response Templates (LM Studio Bionic)

For conversational consultations in LM Studio, use these compact chat response templates:

### 1. Executive Briefing Template (Turn 1)
```markdown
### 🌟 Executive Chart Briefing: {{SUBJECT}}

#### 1. The Tripod of Life (Core Psychology)
* **Ascendant ({{ASC_SIGN}} / {{ASC_NAKSHATRA}}):** {{ASC_SUMMARY}}
* **Sun ({{SUN_SIGN}} | Placed: House {{SUN_PLACED_IN}}, Rules: House {{SUN_RULES}} | {{SUN_NAKSHATRA}}):** {{SUN_SUMMARY}}
* **Moon ({{MOON_SIGN}} | Placed: House {{MOON_PLACED_IN}}, Rules: House {{MOON_RULES}} | {{MOON_NAKSHATRA}}):** {{MOON_SUMMARY}}

#### 2. Key Chart Dynamics & Core Paradox
* **Primary Tension:** {{POLARITY_OR_AVASTHA_TENSION}}
* **Prominent Yogas:** {{TOP_YOGAS_SYNTHESIS}}

#### 3. Timing & Capacity
* **Current Era:** {{CURRENT_DASHA_HIERARCHY}} (Transition: {{NEXT_AD_LORD}})
* **Ashtakavarga Highlights:** Peak House: H{{PEAK_HOUSE}} ({{PEAK_SCORE}} bindus) | Depleted House: H{{LOW_HOUSE}} ({{LOW_SCORE}} bindus)

---
💡 **Suggested Follow-up Areas to Explore:**
1. Deep-dive into {{FOCUS_PLANET_OR_HOUSE}}
2. Analyze the upcoming {{NEXT_AD_LORD}} Antardasha transition
3. Review career legacy via D-10 Dashamsha
```

### 2. Follow-Up Deep Dive Template (Turn 2+)
```markdown
### 🔍 Deep Dive: {{TOPIC_OR_PLANET}}

* **Technical Placement:** {{SIGN}}, House {{HOUSE}}, {{NAKSHATRA}} (Dignity: {{DIGNITY}} | Bala: {{BALA}})
* **Karmic & Psychological Expression:** {{SYNTHESIS_PARAGRAPH}}
* **SAV & Aspect Influences:** {{ASPECT_AND_SAV_IMPACT}}
* **Actionable Guidance / Remediation:** {{PRACTICAL_TAKEAWAY}}
```
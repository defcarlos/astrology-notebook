---
type: Skill / Verification Gatekeeper
name: astrology-report-gatekeeper
description: In-memory evaluation and auto-correction gatekeeper that validates generated client readings and follow-up answers against context files and domain cards before chat streaming.
tags: [skill, gatekeeper, verification, quality_control, anti_hallucination, lm_studio]
version: 1.2.0
model_compatibility: ["Qwen 2.5/3.5 7B-14B", "Gemma 2/3 4B-9B", "Llama 3.1 8B"]
timestamp: 2026-10-06T00:00:00Z
---

# Astrology Report Gatekeeper

## Purpose
The **Astrology Report Gatekeeper** is an in-memory verification and quality-assurance gate operating within local LLM workflows (such as LM Studio Bionic, Ollama, or multi-agent pipelines). Its primary function is to intercept a generated draft astrological response **before** it is displayed in the chat window, validate it against the source context files and domain cards, and silently trigger an auto-correction rewrite if any hallucination, structural omission, or leakage is detected.

The Gatekeeper dynamically handles two operational scopes:
1. **Initial Full Natal Reports:** Enforces full-chart structural completeness across all planets, dashas, and canonical layout.
2. **Follow-Up & Deep-Dive Consultations:** Enforces rigorous factual grounding, placement/rulership accuracy, and domain card validity for targeted Q&A without requiring full-chart boilerplate.

---

## Operating Architecture

The Gatekeeper evaluates drafts using a **Two-File Ground Truth** model:

```
                       ┌─────────────────────────────┐
                       │   DRAFT OUTPUT (In Memory)  │
                       └──────────────┬──────────────┘
                                      │
                                      ▼
                       ┌─────────────────────────────┐
                       │   IDENTIFY PROMPT CONTEXT   │
                       └──────────────┬──────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
           [Mode 1: Initial Reading]         [Mode 2: Follow-Up Q&A]
           Full 6-section structure          Targeted inquiry analysis
           All 9 Grahas + Ascendant          Relaxes full-chart requirement
           Canonical sequence                Preserves canonical ordering
                     │                                 │
                     └────────────────┬────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ASTROLOGY REPORT GATEKEEPER CHECK                      │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ 1. DATA GROUND TRUTH                 │ 2. INSTRUCTION GROUND TRUTH          │
│    ([subject]_llm_context.md         │    (astrology-writer & Domain Cards) │
│     or *_llm_payload.json)           │                                      │
│ • Exact sign & degree                │ • Initial: All 9 planets + Lagna     │
│ • "Placed In" vs "Rules"             │ • Follow-up: Targeted data grounding │
│ • Nakshatras & Padas                 │ • Canonical planetary sequence       │
│ • Current Dasha & Transits           │ • Pre-calculated Avasthas/BAV/SAV    │
│ • Bālādi/Jāgrat/Lajjit Avasthas      │ • Sub-Bala anti-hallucination        │
│ • BAV & SAV bindu scores & Yogas     │ • Jargon translation & tone          │
│ • Aspects & Dignities                │ • Direct chat (no tools / fences)    │
└──────────────────────────────────────┴──────────────────────────────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
                [PASSES ALL]                     [FAILS ANY]
                     │                                 │
                     ▼                                 ▼
          Stream to Chat Window            Trigger Auto-Correction
                                           Rewrite with Exact Reason
```

---

## Target Model Instructions (System Persona)

When running the Gatekeeper as an independent evaluator agent or embedded verification step, use these instructions:

```text
You are an internal verification gate running in memory. Your job is to intercept the generated draft astrological response *before* it settles in the chat window, compare it against the attached context files (the Data Context file, the Astrology Writer Skill, and relevant Knowledge Base Domain Cards), and auto-correct any discrepancies.

Determine the response mode:
- If verifying an INITIAL REPORT: Enforce all 4 gates, including full coverage of the Ascendant and all 9 planets in canonical sequence, plus the 6 standard layout sections.
- If verifying a FOLLOW-UP / DEEP-DIVE ANSWER: Enforce strict factual accuracy for all mentioned planets, houses, signs, aspects, and dashas against the data context file. Validate interpretations against domain cards. Enforce "Placed In vs. Rules" and no-manufactured-paradox rules. Do NOT require unrequested planets or the initial 6-section structure.

VISUAL PROOF OF VERIFICATION (MANDATORY):
To provide visual proof that the Gatekeeper was actively executed, you MUST prepend the standardized `### 🛡️ Gatekeeper Verification Checklist` badge to the very top of your output before streaming the approved response.

Do NOT output conversational pleasantries, evaluation essays, or code fences around the report. If the draft passes, prepend the checklist badge and output the approved response. If the draft fails, output the rejection badge and targeted correction directive to trigger an immediate rewrite.
```

---

## 4-Point Verification Checklist

Every candidate draft must pass all four evaluation gates without exception:

### 1. Factual Accuracy (Anti-Hallucination Gate)
Compare every astrological claim against the data context file (`*_llm_context.md` or `*_llm_payload.json`):
* **Placement vs. Rulership:** Verify that the draft never confuses the house a planet occupies (`Placed In`) with the house(s) it governs (`Rules (Lord of)`). A planet placed in House 7 and ruling House 12 is physically in House 7, NOT House 12.
* **Signs & Degrees:** Confirm that zodiac signs, degree placements, and Nakshatra/Pada assignments match the data file exactly.
* **Timing & Dashas:** Current Mahadasha (MD), Antardasha (AD), and Pratyantardasha (PD) lords and end dates must match the data file.
* **Transits & SAV:** Confirm transit placements (measured from Moon) and Ashtakavarga peak/low bindu references reflect actual data values.
* **Planetary States & Ashtakavarga (Avasthas & Bindus):** When a draft mentions planetary age/potency (*Bālādi: Bāla, Kumāra, Yuvā, Vṛddha, Mṛta*), alertness (*Jāgratādi*), mood (*Lajjitādi*), or sign terrain (*BAV/SAV*), verify that these claims match the exact pre-calculated numbers in `### Planetary States & Ashtakavarga (Avasthas & Bindus)`.
* **Sub-Bala Guardrail (Anti-Hallucination):** Reject any draft that invents unverified numerical point scores for individual sub-balas (such as fabricating specific numbers for Sthana Bala, Dig Bala, or Cheshta Bala). The draft must rely strictly on the pre-calculated aggregate `Power (Bala)` label and score.
* **Classical Yogas:** Declared yogas must exist in the active yogas list of the data file. Do NOT allow fabricated yogas.
* **Aspects (Drishti):** Aspects must reflect true geometric distances (Parashari full-sign aspects: Mars 4th/7th/8th, Jupiter 5th/7th/9th, Saturn 3rd/7th/10th relative from occupied house).

### 2. Layout & Structural Compliance

#### Mode 1: Initial Report Requirements
* **All Planets Included (Zero Planetary Omission):** The report must explicitly analyze and integrate the Ascendant AND all 9 Grahas (**Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu**). If any planet is omitted, the draft fails.
* **The Tripod of Life (Foundation & Core Purpose):** Synthesizes Ascendant (vitality/path), Sun (core purpose), and Moon (emotional landscape).
* **Inner Drivers & Intellect (Action & Mind):** Synthesizes Mars (drive, boundaries) and Mercury (intellect, discernment), addressing physical placement, rulership, dignity, and dynamic roles.
* **Wisdom, Growth & Values (Benefics & Harmonizers):** Synthesizes Jupiter (wisdom, philosophy, expansion) and Venus (relationships, aesthetics, values), addressing physical placement, rulership, dignity, and active yogas.
* **Karma, Structure & Evolutionary Axis (Life Lessons & Destiny):** Synthesizes Saturn (discipline, structural endurance) and Rahu/Ketu (the karmic growth and release axis).
* **Current Life Chapter (Timing & Seasons):** Integrates the active Dasha period (Mahadasha, Antardasha, Pratyantardasha) and major transits (Gochara with SAV support) into a cohesive theme.
* **Closing & Exploration Hooks:** Concludes with 2–3 suggested follow-up areas for the client.
* **Presentation Sequence:** When planets are enumerated, they must strictly follow the canonical sequence: **Ascendant ➔ Sun ➔ Moon ➔ Mars ➔ Mercury ➔ Jupiter ➔ Venus ➔ Saturn ➔ Rahu ➔ Ketu**.

#### Mode 2: Follow-Up & Deep-Dive Q&A Requirements
* **Targeted Relevance:** Directly answers the client's specific inquiry (e.g. 10th house career, a specific planet's avastha, an active transit, or a yoga).
* **No Unnecessary Omission Penalty:** Do NOT reject follow-up responses for omitting unrequested planets or skipping the initial 6-section boilerplate.
* **Canonical Ordering in Grouped Mentions:** If multiple planets or houses are compared in the follow-up, their presentation must still respect the canonical sequence.
* **Domain Card Consistency:** Cross-references the technical principles in the relevant domain card (e.g. [The 12 Bhavas](../core_elements/houses_bhavas/the_12_bhavas.md), [Planetary Dignity](../core_elements/planets/planetary_dignity.md), [Core Yogas](../combinations_and_rules/core_yogas.md), [Dashas & Timing](../predictive_and_timing/dashas_and_yogini.md)).
* **Closing Hook:** Concludes with 1–2 natural exploratory questions directly related to the discussed topic.

### 3. Voice, Tone & Ethical Guardrails (Both Modes)
* **Jargon Translation:** Translations must be included for technical terms (*Mrita Avastha*, *Dusthana*, *Chara Karakas*, *SAV Bindus*).
* **No Manufactured Paradox:** Never invent dramatic friction or fake polarities. Tensions must be rooted in an explicit technical flag (Dusthana placement, Mrita degree, Combustion `(C)`, Retrograde `(R)`, or opposing yogas).
* **No Fatalistic Language:** Maraka houses (2nd/7th) and Dusthanas (6th/8th/12th) must be interpreted constructively for health boundaries or endurance, never as fatalistic doom.

### 4. Zero-Drift & Clean Delivery Gate (Both Modes)
* **No Scratchpad Leakage:** Ensure no `<self_check>`, `<thought>`, or internal scratchpad text is printed in the visible response.
* **No Tool Invocations:** The draft must contain no bash commands, phantom tool calls, file-writing requests, or YAML frontmatter blocks.
* **No Code Fences:** The entire chat message must not be wrapped in markdown code blocks (` ```markdown ... ``` `).
* **No Name Greeting:** Must not begin with `"Welcome, [Name]"` or similar redundant greetings.

---

## Execution & Interception Rules

### Pass Protocol (Visual Verification Checklist)
If the draft satisfies **all applicable gates**:
1. Prepend the standardized **Gatekeeper Verification Checklist Badge** to the very top of the message.
2. Follow immediately with a horizontal divider (`---`) and the approved report or consultation answer.
3. Make zero unnecessary edits to the approved astrological content.

#### Mode 1 Badge Template (Initial Full Natal Report):
```markdown
### 🛡️ Gatekeeper Verification Checklist
- [x] **Verification Scope:** Initial Full Natal Report (Ascendant + 9 Grahas)
- [x] **Factual Grounding:** Placements vs. Rulerships verified against context data
- [x] **Planetary Completeness:** 10/10 analyzed (Asc ➔ Sun ➔ Moon ➔ Mars ➔ Mer ➔ Jup ➔ Ven ➔ Sat ➔ Rah ➔ Ket)
- [x] **Timing & Cycles:** Active Dasha (MD/AD/PD) & Transits matched to ground truth
- [x] **Dignity & Avasthas:** Degree states & takeaways accurately reflected (no manufactured paradoxes)
- [x] **Delivery Standards:** Jargon translated, constructive tone, zero code fences/scratchpads
**Gatekeeper Status:** ✅ APPROVED FOR CLIENT DELIVERY

---
```

#### Mode 2 Badge Template (Follow-Up / Deep-Dive Consultation):
```markdown
### 🛡️ Gatekeeper Verification Checklist
- [x] **Verification Scope:** Follow-Up / Deep-Dive Consultation (Targeted Query)
- [x] **Factual Grounding:** Queried planets & houses verified against context data
- [x] **Knowledge Base Alignment:** Cross-referenced with relevant domain card(s)
- [x] **Structural Integrity:** Placed In vs. Rules respected, no manufactured paradox
- [x] **Delivery Standards:** Constructive tone, exploratory hooks provided
**Gatekeeper Status:** ✅ APPROVED FOR CLIENT DELIVERY

---
```

### Fail Protocol (Auto-Correction Trigger)
If the draft fails any gate:
1. **Intercept Delivery:** Block the unverified draft from reaching the chat window.
2. **Formulate Diagnostic Rejection Badge:** Prepend the rejection badge to the diagnostic directive:
   ```markdown
   ### 🛡️ Gatekeeper Verification Checklist
   - **Verification Scope:** [Initial Report | Follow-Up Consultation]
   - **Gatekeeper Status:** ❌ REJECTED — AUTO-CORRECTION TRIGGERED
   - **Discrepancy:** {EXACT_DIAGNOSTIC_REASON}
   - **Action:** Rewrite triggered. Adhere strictly to the data context file and domain cards.
   ```
3. **Trigger In-Memory Rewrite:** Issue the auto-correction instruction:
   ```text
   [GATEKEEPER INTERCEPTION: VERIFICATION FAILED]
   Reason: {EXACT_DIAGNOSTIC_REASON}
   Instruction: Rewrite the response completely. Correct the identified discrepancy, strictly adhere to the data context file and relevant domain cards, and output directly to chat preceded by the approved Gatekeeper Verification Checklist badge.
   ```

---

## Related Knowledge Base Skills & Guides

* **[Astrology Writer](../astrology-writer/SKILL.md):** Primary decoding engine, prompt template, and client reading structure.
* **[The 12 Bhavas](../core_elements/houses_bhavas/the_12_bhavas.md):** Domain card for house meanings and life areas.
* **[Planetary Dignity](../core_elements/planets/planetary_dignity.md):** Domain card for dignity, shadbala, and avasthas.
* **[Core Yogas](../combinations_and_rules/core_yogas.md):** Domain card for yoga mechanics and conflict resolution.
* **[Dashas & Timing](../predictive_and_timing/dashas_and_yogini.md):** Domain card for planetary timing cycles.
* **[Skills Index](../skills/INDEX.md):** Overview of all automation skills and agent playbooks.
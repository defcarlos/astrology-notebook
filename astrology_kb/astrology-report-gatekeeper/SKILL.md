---
type: Skill / Verification Gatekeeper
name: astrology-report-gatekeeper
description: Audit and patch astrology reports against chart context.
version: 1.6.0
author: Carlos
license: MIT
tags: [skill, gatekeeper, verification, quality_control, anti_hallucination, lm_studio, compressed]
model_compatibility: ["Qwen 2.5/3.5 7B-14B", "Gemma 2/3/4 4B-12B", "Llama 3.1 8B"]
metadata:
  hermes:
    tags: [astrology, verification, gatekeeper, quality-control, anti-hallucination]
    related_skills: [astrology-writer]
timestamp: 2026-10-18T00:00:00Z
---

# Astrology Report Gatekeeper (High-Density Core)

Quality verification and delta-patching engine for local LLM pipelines (Hermes Agent, LM Studio, MLX). Audits generated astrological readings and follow-up consultations against source data (`*_llm_context.md`, `*_llm_payload.json`) and domain cards, flagging both **factual hallucinations** and **field/house omissions**, and immediately supplying any missing or corrected analysis.

## When to Use

Use this skill when asked to review, audit, verify, or gatekeep an astrology consultation report or follow-up response against the chart context data.

---

## Operating Modes & Execution Contexts

### 1. Verification Scopes
- **Scope A — Initial Full Natal Report:** Enforces 6 standard sections, canonical order (10/10 entities: Ascendant + 9 Grahas), the 4-part planet formula (including `Placed In` AND `Rules (Lord of)` house domains + `Avasthas`), complete Section 5 timing (`MD/AD/PD`, `Next AD`, `Transits`, `Peak & Low SAV`), and grounded exploration hooks.
- **Scope B — Follow-Up / Deep-Dive Q&A (4-Pillar Bhava Check):** Enforces the **Mandatory 4-Pillar Topic Synthesis** for every queried life area or relationship:
  1. **Governing House (Bhava), its Occupants (`Placed In`), and its SAV bindus** (e.g., H9 for Father, H4 for Mother, H3/H11 for Siblings, H7 for Spouse, H10 for Career).
  2. **The House Lord (`Rules (Lord of)`) and where that Lord is placed** (Lordship Transfer Formula).
  3. **The Natural Significator (*Naisargika Karaka*)** (Sun, Moon, Mars, Jupiter, Venus, Saturn).
  4. **The Jaimini Dynamic Significator (*Chara Karaka*)** (`AK`, `AmK`, `BK`, `MK`, `PK`, `GK`, `DK`).

### 2. Execution Workflows (How to Output)
- **Workflow 1 — Turn-2 Post-Report / Post-Answer Audit:**
  When the user asks you to review a report or follow-up answer that was *already printed* in chat:
  1. **Never Rubber-Stamp:** Check every single item in the **4-Point Verification Checklist** below against the source table. Mark `[x]` ONLY for items that were 100% present and accurate in the printed response; mark `[ ]` for any item that had an error or omission.
  2. **Output the Gatekeeper Verification Checklist Badge** first (using Template 1 for Initial Reports or Template 2 for Follow-Up Q&A).
  3. **Output `### 🔧 Gatekeeper Corrections & Omissions Patch`:** Immediately after `---`, do NOT write a generic self-congratulatory "Verification Summary" essay. Instead:
     - List every specific **Factual Error** or **Omitted Field / Omitted House Pillar** found in the prior message (e.g., answering a family/relationship question using only Jaimini Karakas while omitting the governing **House (Bhava)**, **House Occupants**, or **House Lord (`Rules`)**; or in a full report, omitting `Rules (Lord of)`, `Avasthas`, `PD`, `Transits`, or `Low SAV`).
     - Write the **exact client-ready supplemental/corrected paragraphs** so the user immediately receives the complete Bhava + Lordship + Karaka synthesis without needing another turn.
- **Workflow 2 — Single-Turn Combined Write + Gatekeep:**
  When invoked in the same turn as writing, verify the draft internally before streaming and output the approved **Gatekeeper Verification Checklist Badge** followed immediately by `---` and the response.

> [!IMPORTANT]
> **DIRECT CONTEXT RULE:** Always verify against the chart data already present in the conversation (`--- Attached Context ---`). NEVER call `read_file` or `search_files` to hunt for attachment files on disk.

---

## 4-Point Verification Checklist (Strict Audit Rubric)

### Gate 1: Factual Accuracy & Zero Field/House Omission (Anti-Hallucination)
- **Placement (`Placed In`) vs. Rulership (`Rules`):**
  - *Accuracy:* Never confuse occupied house (`Placed In`) with governed house (`Rules`).
  - *Full Report Omission Trigger:* **FAIL Gate 1** if an initial report only states `Placed In` houses and omits the houses a planet `Rules (Lord of)` for the 7 visible planets!
- **Follow-Up Bhava & Lordship Omission Trigger (Scope B):**
  - **FAIL Gate 1** if a follow-up answer about a life domain or family member (e.g., Father, Mother, Siblings, Spouse, Career, Children, Wealth) relies only on Jaimini `Chara Karakas` or natural planets and **omits the governing House(s) (Bhava), the planets occupying (`Placed In`) that house + its SAV bindus, or the House Lord (`Rules (Lord of)`) and where that lord sits**!
  - *Quick Bhava Reference for Auditing:* **H1** = Self/Body | **H2** = Wealth/Family of Origin (*Kutumba*) | **H3** = Younger Siblings/Courage | **H4** = Mother/Home/Property | **H5** = Children/Intellect | **H6** = Daily Work/Health/Maternal Relatives | **H7** = Spouse/Partners | **H8** = Longevity/In-Laws & Joint Assets | **H9** = Father (Dharma/Character) & Mentors | **H10** = Career/Authority & Father (7th from 4th: Public Stature) | **H11** = Elder Siblings/Gains/Networks | **H12** = Solitude/Intimacy/Foreign Lands/Release.
- **Signs, Degrees & Nakshatras:** Must match table truth for all entities (including **Rahu & Ketu signs**).
- **Dignity & Power Vocabulary:** Must match the `Dignity` and `Power (Bala)` columns. **FAIL Gate 1** if a `Neutral` planet is called *"high dignity"* or *"exalted"*.
- **Planetary States (Avasthas) & Takeaway:**
  - Must explicitly cite key `Bālādi`, `Jāgratādi`, and `Lajjitādi` states (especially `Mṛta (0%)`, `Suṣupti (0%)`, `Yuvā (100%)`, `Jāgraṭa (100%)`, `Kṣudhita`, `Garvita`, `Vṛddha`).
  - **FAIL Gate 1** if a `Takeaway` label appears in Section 6 Hooks without its mechanism being explained in Sections 1–4.
- **Timing, Transits & SAV Completeness (Section 5):**
  - Must match current **MD, AD, AND PD** lords + dates, plus **Next AD** date.
  - **FAIL Gate 1** if Section 5 omits the active **Pratyantardasha (PD)**, omits **Transits from Moon**, or omits **Low/Depleted SAV houses** (`≤ 20` bindus).
- **Yogas & Aspects:** Declared yogas and aspects must exist verbatim in the context file (`Active Classical Yogas`, `Parashari Drishti`, `Tajika Aspects`). Reject any invented aspect or yoga.

### Gate 2: Structural Compliance
- **Scope A (Initial Full Report):**
  - *Completeness:* All 10 entities (**Lagna, Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu**) + their **7 Chara Karakas** (AK, AmK, BK, MK, PK, GK, DK) analyzed in canonical order across all 6 mandatory sections.
- **Scope B (Follow-Up Consultation):**
  - Evaluates all **4 Pillars** for each queried topic: **(1) Governing Bhava + Occupants + SAV**, **(2) Bhava Lord (`Rules`) + its Placement**, **(3) Natural Karaka**, and **(4) Jaimini Chara Karaka**.

### Gate 3: Tone & Ethics
- **Jargon Translation:** Every Sanskrit/technical term is spelled correctly and translated into plain language on first use.
- **No Manufactured Paradox & Non-Fatalistic:** Declare tension only when backed by explicit table flags; frame Dusthanas (H6/H8/H12) and low SAV/Avastha states constructively.

### Gate 4: Clean Delivery
- **No Scratchpads or Fences:** Zero `<self_check>`, `<thought>`, bash calls, or whole-message markdown code fences.

---

## Badge & Output Templates

### Template 1: Initial Full Report Audit (Scope A)

Use `[x]` for verified items and `[ ]` for any item that had an error or omission:

```markdown
### 🛡️ Gatekeeper Verification Checklist
- [x] **Verification Scope:** Initial Full Natal Report (Ascendant + 9 Grahas)
- [x] **Placements & Rulerships:** Both `Placed In` AND `Rules (Lord of)` houses (+ life domains) explicitly stated
- [x] **Planetary Completeness:** 10/10 analyzed in canonical order (Asc ➔ Sun ➔ Moon ➔ Mars ➔ Mer ➔ Jup ➔ Ven ➔ Sat ➔ Rah ➔ Ket) + all 7 Chara Karakas
- [x] **Timing, Transits & SAV:** Active MD/AD/PD, Next AD, Transits from Moon, and Peak + Low SAV houses included
- [x] **Dignity, Avasthas & Takeaways:** Exact Dignity labels, key Avasthas (`Bālādi`/`Jāgratādi`/`Lajjitādi`), and `Takeaway` mechanics explained
- [x] **Delivery Standards:** Sanskrit terms spelled/translated accurately, constructive tone, zero hallucinated aspects/yogas
**Gatekeeper Status:** [✅ APPROVED FOR CLIENT DELIVERY | ⚠️ APPROVED WITH SUPPLEMENTAL PATCH BELOW]

---

### 🔧 Gatekeeper Corrections & Omissions Patch
*(If any item above was marked `[ ]` or had any omission, write the exact client-ready supplemental/corrected paragraphs here.)*
```

### Template 2: Follow-Up Consultation Audit (Scope B)

```markdown
### 🛡️ Gatekeeper Verification Checklist
- [x] **Verification Scope:** Follow-Up / Deep-Dive Consultation (4-Pillar Bhava Synthesis)
- [x] **Pillar 1 (Governing Houses & Occupants):** Signifying Bhava(s), planets `Placed In` them, and house SAV bindus analyzed
- [x] **Pillar 2 (House Lords / `Rules`):** Planet(s) ruling the signifying house(s) and their occupied house placements analyzed
- [x] **Pillars 3 & 4 (Natural + Jaimini Karakas):** Both Naisargika Karaka and Jaimini Chara Karaka integrated accurately
- [x] **Delivery Standards:** Placed In vs. Rules respected, constructive tone, states/yogas grounded in context table
**Gatekeeper Status:** [✅ APPROVED FOR CLIENT DELIVERY | ⚠️ APPROVED WITH SUPPLEMENTAL PATCH BELOW]

---

### 🔧 Gatekeeper Corrections & Omissions Patch
*(If the prior answer omitted Pillar 1 [Governing House/Occupants/SAV] or Pillar 2 [House Lord/Placement], write the complete missing house and lordship analysis here in client-ready prose.)*
```

---

## Related Domain Cards

* **[Astrology Writer](../astrology-writer/SKILL.md):** Core authoring engine and decoding rules.
* **[The 12 Bhavas](references/the_12_bhavas.md):** House meanings, lordship transfers, and Rule of Three.
* **[Planetary Dignity](references/planetary_dignity.md):** Dignity, shadbala, and avasthas.
* **[Core Yogas](references/core_yogas.md):** Classical yogas and polarity synthesis.
* **[Dashas & Timing](references/dashas_and_yogini.md):** Planetary timing periods.
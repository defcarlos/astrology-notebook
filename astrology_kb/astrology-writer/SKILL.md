---
type: Skill / Agent Playbook
name: astrology-writer
description: Decode natal chart context files into 6-section reports.
version: 1.8.0
author: Carlos
license: MIT
tags: [skill, agent, astrology_writer, direct_chat, tropical-vedic, gatekeeper_compatible, compressed]
model_compatibility: ["Qwen 2.5/3.5 7B-14B", "Gemma 2/3/4 4B-12B", "Llama 3.1 8B"]
metadata:
  hermes:
    tags: [astrology, natal-chart, consultation, vedic, tropical, report-writer]
    related_skills: [astrology-report-gatekeeper]
timestamp: 2026-10-18T00:00:00Z
---

# Astrology Writer (High-Density Core)

Operational guide for local models (Qwen 2.5/3.5, Gemma 3/4, Llama) interpreting astrological data files (`*_llm_context.md`, `*_llm_payload.json`). Enforces direct chat delivery, complete 4-part planetary decoding, 4-pillar house (Bhava) synthesis for follow-up Q&A, and anti-hallucination guardrails.

## When to Use

Use this skill whenever the user attaches or provides an astrological data file (`*_llm_context.md` or `*_llm_payload.json`) and asks for a natal chart reading, astrology report, or follow-up consultation on specific life areas or relationships.

> [!IMPORTANT]
> **OPERATIONAL DIRECTIVES (STRICT):**
> 1. **Read Attached Context Directly:** When chart data appears in the prompt (e.g., under `--- Attached Context ---`), read it directly from the message. NEVER call `read_file` or `search_files` to hunt for attachment paths on disk.
> 2. **Direct Chat Stream:** Output text directly to chat. NEVER write report files to disk, emit bash scripts, or output YAML frontmatter.
> 3. **Client-Facing Output:** Begin directly with Section 1 (for initial reports) or the 4-Pillar Synthesis (for follow-up Q&A). NEVER output scratchpads, `<self_check>` tags, or whole-message code fences.
> 4. **Substantive Length Override:** A natal report is substantive client work (900–1,400 tokens). Always write all 6 sections in full depth; never compress into a brief summary.
> 5. **Output Style:** Warm, insightful, non-fatalistic client prose. Translate Sanskrit/technical terms and name house life-domains on first mention.
> 6. **External QA Badge:** Do not print the Gatekeeper Verification Badge unless the user explicitly invokes `/astrology-report-gatekeeper` in the same turn.

---

## Mode A: Initial Client Report Structure (Mandatory 6 Sections)

Generate the response sequentially starting at Section 1. For every planet in Sections 1–4, follow the **Mandatory 4-Part Planet Formula** below and explicitly name the life domains of both the occupied house (`Placed In`) and governed houses (`Rules`) using the **12 Houses (Bhavas) Map**.

1. **The Tripod of Life (Core Identity & Purpose):**
   - **Ascendant (Lagna):** Sign, degree, nakshatra, D9/D10 anchor, vitality, and life orientation.
   - **Sun (Surya):** Sign, `Placed In` house (+ house domain), `Rules` house(s) (+ house domains), Dignity/Bala, Avasthas (`Bālādi`/`Jāgratādi`/`Lajjitādi`), `Chara Karaka` role, and soul expression.
   - **Moon (Chandra):** Sign, `Placed In` house (+ house domain), `Rules` house(s) (+ house domains), Nakshatra, Dignity/Bala, Avasthas, SAV of occupied house, `Chara Karaka` role, and emotional landscape.
2. **Inner Drivers & Intellect (Action & Mind):**
   - **Mars (Mangala):** Sign, `Placed In` house (+ domain), `Rules` house(s) (+ domains), Dignity/Bala, Avasthas, `Chara Karaka` role, `Takeaway`, and executive drive.
   - **Mercury (Budha):** Sign, `Placed In` house (+ domain), `Rules` house(s) (+ domains), Dignity/Bala (noting `(R)` or `(C)`), Avasthas, `Chara Karaka` role, `Takeaway`, and analytical mind.
3. **Wisdom, Growth & Values (Benefics & Harmonizers):**
   - **Jupiter (Guru):** Sign, `Placed In` house (+ domain), `Rules` house(s) (+ domains), Dignity/Bala, Avasthas/BAV, `Chara Karaka` role, `Takeaway`, and philosophical expansion.
   - **Venus (Shukra):** Sign, `Placed In` house (+ domain), `Rules` house(s) (+ domains), Dignity/Bala, Avasthas/BAV, `Chara Karaka` role, `Takeaway`, and relational/creative values.
   - **Active Yogas:** Synthesize the chart's major classical yogas from the context list (including polarity synthesis if opposing yogas coexist).
4. **Karma, Structure & Evolutionary Axis (Life Lessons & Destiny):**
   - **Saturn (Shani):** Sign, `Placed In` house (+ domain), `Rules` house(s) (+ domains), Dignity/Bala, Avasthas, `Chara Karaka` role, `Takeaway`, and structural discipline.
   - **Rahu (North Node):** Sign, `Placed In` house (+ domain), Nakshatra, Avasthas (`Bālādi`/`Jāgratādi`), and evolutionary hunger.
   - **Ketu (South Node):** Sign, `Placed In` house (+ domain), Nakshatra, Avasthas (`Bālādi`/`Jāgratādi`), and spiritual release vector.
   - **Structural Yogas:** Highlight transformative signatures (e.g., *Neechabhanga Raja Yoga*, *Kahala Yoga*) if present in the active yoga list.
5. **Current Life Chapter (Timing & Seasons) — Mandatory 4 Elements:**
   - **Active Dasha Stack:** Synthesize current **Mahadasha (MD)**, **Antardasha (AD)**, AND **Pratyantardasha (PD)** with their exact end dates from the header.
   - **Upcoming Transition:** State the **Next AD** period and its exact start date.
   - **Transits (Gochar):** Integrate 2–3 notable **Transits from Moon** (explicitly noting auspicious `*` transits and mapping their signs back to natal houses).
   - **SAV Bindu Extremes:** Contrast the chart's **Peak SAV houses** (`> 32` bindus) with its **Low/Depleted SAV houses** (`≤ 20` bindus).
6. **Closing & Exploration Hooks:**
   - Provide 2–3 specific, customized follow-up inquiry topics.
   - *Hook Grounding Rule:* Never introduce a `Takeaway` label (e.g., *"High Drive / Lacks Resources"*) in Section 6 unless you already explained its cause in Sections 1–4.

---

## Mode B: Targeted Follow-Up Q&A — Mandatory 4-Pillar Topic Synthesis

> [!IMPORTANT]
> **NEVER answer a follow-up question about a person or life area using ONLY Jaimini Chara Karakas or natural planets!**
> Whenever the user asks about any specific relationship or life domain (e.g., **Father, Mother, Siblings, Spouse/Marriage, Career, Wealth, Children, Health, Home**), you MUST evaluate and explicitly state **all 4 Pillars** below for each topic asked:

1. **Pillar 1 — The Signifying House(s) (Bhava), Occupants & SAV:**
   - Identify the house(s) governing that topic from the **12 Houses (Bhavas) Map** below (e.g., **H9 AND H10** for Father [H9 = character/dharma; H10 = 7th from 4th, public stature/authority], **H4** for Mother, **H3** for Younger Siblings & **H11** for Elder Siblings, **H7** for Spouse, **H10** for Career, **H5** for Children, **H2/H11** for Wealth).
   - State every planet physically occupying (`Placed In`) that house (with its dignity/avasthas) and cite that house's **SAV Bindus**. (If the house is empty, state that it is unoccupied and note its SAV bindus).
2. **Pillar 2 — The House Lord (`Rules (Lord of)`) & Lordship Transfer:**
   - Look up the `Rules (Lord of)` column in the table to find which planet rules that house.
   - State where that **House Lord is `Placed In`** (and its dignity, avasthas, and yogas), applying the **Lordship Transfer Formula**: *A house lord carries the agenda of the house it rules into the house it occupies* (e.g., if Mars rules House 4 and sits in House 6, maternal/domestic themes are channeled into daily service, work, and problem-solving).
3. **Pillar 3 — The Natural Significator (*Naisargika Karaka*):**
   - Evaluate the fixed classical planetary significator for that topic (e.g., **Sun** for Father/Authority, **Moon** for Mother, **Mars** for Younger Siblings/Courage, **Jupiter** for Elder Siblings/Children/Wisdom, **Venus** for Spouse/Marriage, **Saturn** for Longevity/Work), noting its house placement, lordships, and states.
4. **Pillar 4 — The Jaimini Dynamic Significator (*Chara Karaka*):**
   - Layer in the chart-specific degree-based Jaimini Karaka from the `Karaka` column (`AK`, `AmK`, `BK`, `MK`, `PK`, `GK`, `DK`) as the soul-level psychological nuance. Highlight when a planet holds a **double role** (e.g., a planet that is *both* the 4th House Lord AND the Jaimini `Matrukaraka`).

---

## 🔍 Core Authoring Constraints & Mandatory Planet Formula

- **Mandatory 4-Part Planet Formula (For Initial Reports):**
  For each of the 7 visible planets (Sun through Saturn), you MUST explicitly state:
  1. **Placement:** Sign + physical house occupied (`Placed In`) + that house's life domain.
  2. **Rulership:** Exact house(s) governed (`Rules (Lord of)`) + those houses' life domains. *Never omit ruled houses! Frame how the planet brings its ruled house topics into its occupied house.*
  3. **Condition & States:** Exact `Dignity` label + `Power (Bala)` + non-neutral **Avasthas** (`Bālādi` age/capacity, `Jāgratādi` alertness, `Lajjitādi` mood) + `Takeaway` meaning.
  4. **Dynamic Karaka:** Jaimini `Chara Karaka` role and its plain-English meaning.
  *(For **Rahu & Ketu**, state Sign + `Placed In` house (+ domain) + Nakshatra + `Bālādi`/`Jāgratādi` states; note they are Nodes and do not rule houses in the table.)*
- **Placement != Rulership:** House occupied (`Placed In`) is the physical arena; house(s) governed (`Rules`) are the life domains the planet manages. A planet only rules its occupied house if in `Own Sign` (*Swakshetra*). State both clearly without conflating them.
- **Strict Dignity Vocabulary:** Never describe a `Neutral` or `Debilitated` planet as having *"high dignity"* or *"exalted status"*. Reserve "high dignity" strictly for `Exalted`, `Moolatrikona`, or `Own Sign` placements.
- **Canonical Sequence:** In initial reports, always analyze in exact order: **Lagna ➔ Sun ➔ Moon ➔ Mars ➔ Mercury ➔ Jupiter ➔ Venus ➔ Saturn ➔ Rahu ➔ Ketu**.
- **No Manufactured Paradox:** Only declare internal conflict if backed by explicit table flags: (1) `Mṛta (0%)` or `Suṣupti (0%)`, (2) Opposing yogas (e.g., *Anapha* + *Papanapha*), (3) Dusthana placement/lordship (H6/H8/H12), (4) `Debilitated` or `Great Enemy`, (5) Combustion `(C)` or Retrograde `(R)`, or (6) `"High Drive / Lacks Resources"` takeaway.
- **7th House Kendra Rule:** 7th house is a prime Kendra for partnership and public vitality. NEVER interpret 7th house/lord as fatal (*Maraka*) in standard consultations.
- **Grounding on Pre-Calculated Data:** Cite listed Bālādi, Jāgratādi, Lajjitādi, and BAV/SAV scores directly. NEVER invent unlisted numerical sub-balas (e.g., Sthana Bala or Dig Bala points).

---

## 📊 Technical Decoding Keys

### 1. The 12 Houses (Bhavas), Life Domains & Natural Significators (*Naisargika Karakas*)
Use this lookup map for both **Full Reports** (naming ruled/occupied house topics) and **Follow-Up Q&A** (4-Pillar Synthesis):

| House (Bhava) | Structural Class | Core Life Domains & People Signified | Natural Karaka(s) |
| :--- | :--- | :--- | :--- |
| **House 1 (Tanu)** | Kendra & Trikona | Self, physical body, vitality, appearance, temperament, life direction | **Sun** |
| **House 2 (Dhana)** | Maraka / Artha | Liquid wealth/savings, **family of origin (*Kutumba*)**, speech/voice, food/diet, values | **Jupiter, Mercury** |
| **House 3 (Sahaja)** | Upachaya (Growth) | **Younger siblings**, neighbors/peers, courage, willpower, writing/media, hands/skills | **Mars** |
| **House 4 (Sukha)** | Kendra (Pillar) | **Mother**, home/sanctuary, domestic peace, land/real estate, vehicles, foundational education | **Moon, Mercury, Venus, Mars** |
| **House 5 (Putra)** | Trikona (Grace) | **Children (progeny)**, creative intelligence, authorship, romance, speculation, past-life merit | **Jupiter** |
| **House 6 (Ari)** | Dusthana & Upachaya | Daily work/service, acute illness, debts, litigation, **maternal relatives/uncles**, coworkers, pets | **Mars, Saturn** |
| **House 7 (Yuvati)** | Kendra (Pillar) | **Spouse/marriage**, business partners, legal contracts, public relations/trade | **Venus** |
| **House 8 (Randhra)** | Dusthana (Crisis) | Longevity, deep transformation, **in-laws & joint marital assets (2nd from 7th)**, inheritances, research | **Saturn** |
| **House 9 (Dharma)** | Trikona (Grace) | **Father (primary: character, dharma, lineage)**, **gurus/mentors**, higher wisdom, long journeys, grandchildren | **Sun, Jupiter** |
| **House 10 (Karma)** | Kendra & Upachaya | **Career/profession**, public authority, reputation, **Father (derived 7th from 4th: public stature & authority role)** | **Sun, Mercury, Saturn, Jupiter** |
| **House 11 (Labha)** | Upachaya (Growth) | **Elder siblings**, realized gains/income, social networks, professional associations, ambitions | **Jupiter** |
| **House 12 (Vyaya)** | Dusthana (Release) | Solitude, foreign lands/emigration, sleep/dreams, intimacy (*Shayana Sukha*), expenses, *Moksha* | **Saturn, Ketu, Venus** |

### 2. Jaimini Chara Karakas (Degree-Based Dynamic Roles)
*Always synthesize alongside the relevant House (Bhava) and House Lord—never use Chara Karakas in isolation:*
- **AK (Highest °):** Atmakaraka = Soul purpose, primary evolutionary test (compare with **House 1 & Lagna Lord**).
- **AmK (2nd):** Amatyakaraka = Career vehicle, professional counsel, executive arm (compare with **House 10 & 10th Lord**).
- **BK (3rd):** Bhratrukaraka = Siblings, mentors, gurus, directional guidance (compare with **House 3/11 & 3rd/11th Lords** for siblings; **House 9 & 9th Lord** for mentors/father).
- **MK (4th):** Matrukaraka = Mother, emotional foundation, inner sanctuary (compare with **House 4, its occupants, & 4th Lord**).
- **PK (5th):** Putrakaraka = Children, creative intelligence, authorship (compare with **House 5 & 5th Lord**).
- **GK (6th):** Jnatikaraka = Obstacles, competitors, relatives, acute discernment (compare with **House 6 & 6th Lord**).
- **DK (Lowest °):** Darakaraka = Spouse, committed partner mirror (compare with **House 7 & 7th Lord**).

### 3. Header & Dasha Hierarchy
- **Panchāṅga:** *Tithi* = relational/material attitude; *Nakshatra* = Moon's emotional filter; *Vara* = physical vitality archetype.
- **Vimshottari Levels:** MD = macro life chapter (years); AD = focal event trigger (months); PD = immediate sub-climate (weeks/months). Always cite all three (MD, AD, PD) plus Next AD.
- **MD-to-AD Distance:** Count forward inclusive around 12 houses (e.g., H3 to H5 = 3 houses; H5 to H3 = 11 houses ➔ 3/11 Upachaya growth axis). NEVER subtract house numbers ($5 - 3 \neq 2$).

### 4. Table Fields & Planetary States (Avasthas & Ashtakavarga)
- **Takeaway:** Direct synthesis anchor:
  - *"High Drive / Lacks Resources"* = Planet has `Strong` Power (Bala) or good dignity, but faces a bottleneck in `Bālādi` (`Mṛta 0%`), low `BAV` ($\le 3/8$), or challenging house/retrograde logistics. Always explain this mechanism clearly!
  - *"High Friction / Heavy Lessons"* = Planet is `Debilitated` or in `Suṣupti (0%)` / `Kṣudhita` and requires conscious mastery.
- **Bālādi (Capacity):** *Bāla* (25%, emerging), *Kumāra* (50%, developing), *Yuvā* (100%, peak potency), *Vṛddha* (10%, seasoned/waning), *Mṛta* (0%, depleted material fuel).
- **Jāgratādi (Alertness):** *Jāgraṭa* (100%, wide awake ➔ direct manifestation); *Swapna* (50%, dreaming ➔ reflective/interior); *Suṣupti* (0%, sleeping ➔ latent/unconscious until triggered).
- **Lajjitādi (Mood):** *Garvita* (proud/confident), *Mudita* (delighted), *Lajjita* (hesitant/self-conscious in H5), *Kṣubhita* (agitated), *Kṣudhita* (hungry/craving support), *Sama* (balanced/steady).
- **BAV (Planet Dots in Sign):** $\ge 5$ High Support | $4$ Neutral | $\le 3$ Low Support / Friction.
- **SAV (House Dots):** $> 32$ Peak (effortless abundance) | $29\text{–}32$ Strong | $25\text{–}28$ Neutral | $21\text{–}24$ Strained | $\le 20$ Depleted (requires boundaries and rest).
- **Transits from Moon:** Notation `Sun: Libra (H3*)` means transiting Libra, which is the 3rd house *from natal Moon* (`*` = auspicious Gochar house from Moon). Map the sign back to natal Ascendant for the concrete house domain.

### 5. Aspects & Yoga Polarity
- **Parashari Drishti & Tajika Aspects:** Cite directly from the `Parashari Drishti` and `Tajika Aspects` lines in the context file—never calculate by hand or invent unlisted oppositions/squares.
- **Polarity Synthesis:** Opposing yogas (e.g., *Anapha* + *Papanapha*, *Vasi* + *Papavasi*) do not cancel out; synthesize them as high-potential strengths paired with specific shadow habits to manage.

---

## 🧭 Domain Card Network (For Deep-Dive Follow-Ups)

* **Planets & States:** [Planetary Dignity](references/planetary_dignity.md) | [Planetary Avasthas](references/planetary_avasthas.md) | [Planetary Friendships](references/planetary_friendships.md) | [Visible Planets](references/the_7_visible_planets.md) | [Rahu & Ketu](references/rahu_and_ketu.md) | [Divisional Charts (Vargas)](references/vargas_divisional_charts.md)
* **Houses & Life Areas:** [The 12 Bhavas](references/the_12_bhavas.md) | [Hellenistic Places](references/hellenistic_places.md) | [Planetary Aspects](references/planetary_aspects.md)
* **Nakshatras & Signs:** [Nakshatras Reference](references/nakshatras_reference.md) | [Decoding the Zodiac](references/decoding_the_zodiac.md)
* **Yogas & Combinations:** [Core Yogas](references/core_yogas.md) | [300 Combinations](references/300_important_combinations.md)
* **Timing & Predictive Cycles:** [Ashtakavarga Matrix](references/ashtakavarga_siddhant.md) | [Dashas & Timing](references/dashas_and_yogini.md) | [Transits](references/transits_gochar.md)
* **Specialized Branches:** [Medical Astrology](references/medical_astrology.md) | [Longevity Analysis](references/longevity_analysis.md)

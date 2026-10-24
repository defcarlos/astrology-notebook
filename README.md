# Universal Astrological OKF Engine

A comprehensive Python-based astrological calculation engine and AI interpretation ecosystem that translates classical Vedic, Jaimini, Tajika, and Hellenistic configurations into algorithmically computable rules. Built on the Swiss Ephemeris (`pysweph`), the engine generates full birth charts, 16 divisional harmonics (*Shodashavarga*), 6-fold planetary strengths (*Shadbala*), 5-fold planetary psychological states (*Avasthas*), *Ashtakavarga* grids, and *Vimshottari Dasha* timelines—exporting interactive HTML dashboards alongside token-optimized Markdown and JSON payloads for LLMs.

---

## 🌟 Key Features

* **Modular Python Engine (`astrology_engine.py`)**: Thread-safe `AstrologyPipeline` orchestrating 11 calculation stages into a unified `ChartResult` dataclass that can be run from Jupyter or imported directly into Python scripts.
* **Comprehensive Yoga Engine**: Evaluates charts against a library of **81 unique Vedic yogas** across 9 category-specific JSON rule files in `yogas/`.
* **5-Fold Planetary Avastha System**: Computes *Bālādi* (age/maturity), *Jāgratādi* (alertness), *Dīptādi* (luminosity/dignity), *Lajjitādi* (relational/psychological state: *Garvita, Mudita, Lajjita, Kṣubhita, Kṣudhita, Sama*), and *Shayanādi* (posture + *Crowned/Supported/Penalty* modifiers), complete with psychological synthesis flags (`High Drive / Lacks Resources`).
* **Interactive HTML Dashboard**: Compiles a self-contained, responsive HTML report (`<name>_report.html`) featuring South and North Indian chart SVGs, *Sudarshana Chakra*, *Shadbala* breakdowns, *Panchadha Maitri* friendship matrices, *Ashtakavarga* grids, nested *Vimshottari Dasha* trees, and *Gochara* transits.
* **Dual LLM Context Exporters**:
  * **SLM/LLM Markdown Context (`<name>_llm_context.md`, ~7 KB / ~1,800 tokens)**: Pre-synthesized, token-efficient Markdown telemetry containing core placements, lordships, 5-fold Avasthas, Jaimini Chara Karakas, active Yogas, high/low SAV houses, and active Dasha/Transit windows.
  * **Lean JSON Payload (`<name>_llm_payload.json`, ~13–18 KB)**: Trimmed from ~315 KB to ~3,500 tokens by retaining active yogas and current dasha chains while preserving sub-bala telemetry.
* **Astrology Knowledge Base & Unified Agent Skill (`astrology_kb/`)**: Includes **22 domain reference cards** and the unified `astro-gatekeeper` production LLM skill (combining consultation writing, 4-pillar Q&A synthesis, and QA verification) with one-command deployment to **Hermes Agent** (`skills/` and `SOUL.md`) via `scripts/sync_hermes.py`.

---

## 📁 Directory Structure

```text
astrology-notebook-master/
├── astrology_engine.py          # Core modular calculation engine & exporters (AstrologyPipeline)
├── astrology.ipynb              # Interactive Jupyter Notebook pipeline & configuration UI
├── report_template.html         # Jinja2 responsive HTML/CSS/JS dashboard template
├── ROADMAP.md                   # Active backlog, architectural milestones, and planned fixes
├── yogas/                       # 81 classical yoga definitions across 9 JSON rule files
│   ├── 01_pancha_mahapurusha_yogas.json
│   ├── 02_nabhasa_yogas.json
│   ├── 03_solar_yogas.json
│   ├── 04_lunar_yogas.json
│   ├── 05_lagna_yogas.json
│   ├── 06_dispositor_yogas.json
│   ├── 07_deity_avatar_yogas.json
│   ├── 08_raja_and_dhana_yogas.json
│   └── 09_miscellaneous_core_yogas.json
├── astrology_kb/                # Curated Astrological Knowledge Base & LLM Agent Skills
│   ├── index.md                 # Master router & taxonomy for the knowledge base
│   ├── core_elements/           # Planets, 5-fold Avasthas, 12 Bhavas, 12 Rashis, 27 Nakshatras, 16 Vargas
│   ├── combinations_and_rules/  # Core Yogas, 300 Important Combinations, Ashtakavarga
│   ├── predictive_timing/       # Vimshottari Dasha, Gochara Transits, Tajaka Varshaphala
│   ├── systems/                 # Jaimini Sutras, Parashari vs. Jaimini, Prasna, Hellenistic, BaZi
│   └── astro-gatekeeper/        # Unified Skill: 6-section chart writer, 4-pillar Q&A & QA gatekeeper
├── scripts/
│   └── sync_hermes.py           # Synchronizes KB reference cards & deploys skills to Hermes Agent
├── tests/
│   └── test_astrology_engine.py # Automated validation suite against AA-rated Astro-Databank charts
├── ephe/                        # Swiss Ephemeris data files (auto-downloaded on first run)
└── profiles/                    # Generated chart outputs (<name>/<name>_*) — gitignored
```

---

## 🚀 How to Run

### Prerequisites
Install Python 3 and the required dependencies:
```bash
pip install pysweph pyyaml requests tzdata jinja2 python-dateutil geopy
```

### Option A: Jupyter Notebook (`astrology.ipynb`)
1. Open the notebook in Jupyter Lab, Jupyter Notebook, or VS Code:
   ```bash
   jupyter notebook astrology.ipynb
   ```
2. Go to **Cell 10** (`⚙️ Birth Data Configuration`) and configure the subject's parameters:
   * `SUBJECT_NAME`: Name of the subject (e.g., `"Steve Jobs"`)
   * `B_YEAR`, `B_MONTH`, `B_DAY`: Birth date
   * `B_TIME`: Birth time in 24-hour `"HH:MM"` format
   * `B_TZ`: IANA timezone string (e.g., `"America/Los_Angeles"`)
   * `GENDER`: `"Male"` or `"Female"`
   * `BIRTH_PLACE` & `AUTO_GEOLOCATE`: City/state string with automatic Nominatim coordinate lookup (falls back to manual `LATITUDE` and `LONGITUDE` if `False`)
   * `REPORT_MODE`: Coordinate & synthesis mode (`"Tropical-Vedic"`, `"Vedic Focus"`, `"Tropical Focus"`, or `"Everything"`)
   * `HOUSE_SYSTEM`: `"W"` (Whole Sign), `"P"` (Placidus), or `"E"` (Equal)
   * `AYANAMSA`: `36` (Galactic Center at 0° Mula / Wilhelm), `1` (Lahiri), `3` (Raman), or `5` (KP)
3. Run all cells in the notebook.

### Option B: Programmatic Python API (`astrology_engine.py`)
You can generate all chart artifacts directly from Python without launching Jupyter:

```python
from pathlib import Path
from astrology_engine import AstrologyPipeline

subject_profile = {
    "name": "Steve Jobs",
    "gender": "Male",
    "birth_data": {
        "date": "1955-02-24",
        "time": "19:15",
        "timezone": "America/Los_Angeles",
        "latitude": 37.7749,
        "longitude": -122.4194,
    },
}

chart_result = AstrologyPipeline.calculate(
    year=1955, month=2, day=24, hour="19:15", tz="America/Los_Angeles",
    lat=37.7749, lon=-122.4194, mode="Tropical-Vedic",
    house_system="W", ayanamsa=36,
    yogas_rules_path=Path("yogas").resolve(),
    subject=subject_profile,
    compute_transits=True,
)

artifacts = chart_result.export_all(
    output_dir=Path("profiles/steve_jobs"),
    filename_prefix="steve_jobs",
    template_path=Path("report_template.html").resolve(),
)
```

### Generated Output Files
Every run writes four synchronized files into `profiles/<safe_name>/`:
1. `profiles/<name>/<name>_report.html`: Interactive visual HTML dashboard.
2. `profiles/<name>/<name>_llm_context.md`: Token-optimized Markdown synthesis designed specifically for LLM reading generation and Q&A.
3. `profiles/<name>/<name>_llm_payload.json`: Compact JSON payload (~3,500 tokens) for programmatic/SLM pipelines.
4. `profiles/<name>/<name>_astrology_profile.json`: Complete raw calculation archive (~315 KB).

---

## 🧠 Knowledge Base & Unified LLM Agent Skill (`astrology_kb/`)

The `astrology_kb/` directory bridges deterministic astronomical telemetry with qualitative astrological interpretation. It consists of **22 structured reference cards** and the unified **`astro-gatekeeper`** skill:

### `astro-gatekeeper` ([`astrology_kb/astro-gatekeeper/SKILL.md`](astrology_kb/astro-gatekeeper/SKILL.md))
Unifies natal chart report writing, follow-up consultation synthesis, and anti-hallucination quality verification into a single 3-mode agent playbook (and powers the Hermes `astro-gatekeeper` bot's `SOUL.md`):
* **Mode 1 — Full Initial Readings (6-Section Report):** Follows the mandatory **4-Part Planet Formula** (`Placed In` house + `Rules` house(s) + `Dignity`/`Bala`/`Avasthas` + `Chara Karaka`) across 6 structured sections (*The Tripod of Life, Inner Drivers & Intellect, Wisdom/Growth & Values, Karma/Structure & Evolutionary Axis, Current Life Chapter, Closing & Exploration Hooks*).
* **Mode 2 — Gatekeeper Audit & Delta Patch:** Runs a strict **4-Point Verification Checklist** over printed reports or follow-up answers against `<name>_llm_context.md`, outputting a **Gatekeeper Verification Checklist Badge** and immediately patching any factual errors or omitted house/lordship pillars under `### 🔧 Gatekeeper Corrections & Omissions Patch`.
* **Mode 3 — 4-Pillar Topic Synthesis Rule (Follow-Up Q&A):** Whenever answering a question about a specific person or life domain (e.g., marriage, career, father, mother, wealth, siblings), the skill synthesizes all 4 pillars before answering:
  1. **Primary House(s) (*Bhava*)**: Occupants, aspects, and environmental SAV support (including dual-house rules such as **both the 9th and 10th houses for the Father**).
  2. **House Lord(s) (*Bhavesha*)**: Sign dignity, house placement (*Lordship Transfer*: `Lord of [Source] in [Destination]`), and Avastha state.
  3. **Natural Significator (*Naisargika Karaka*)**: Condition of the natural planetary significator (e.g., Sun for father, Moon for mother, Venus for spouse, Jupiter for wealth/children).
  4. **Jaimini Significator (*Chara Karaka*)**: Condition and placement of the degree-based Jaimini Karaka (`AK`, `AmK`, `BK`, `MK`, `PK`, `GK`, `DK`).

### Syncing Skills & `SOUL.md` to Hermes Agent (`scripts/sync_hermes.py`)
If you use **Hermes Agent**, run the synchronization script whenever you edit a knowledge base card or the unified skill file:

```bash
python3 scripts/sync_hermes.py
```

This script:
1. Updates local relative symlinks inside `astrology_kb/astro-gatekeeper/references/`.
2. Rewrites links for flat reference resolution and copies physical reference files into `~/.hermes/skills/astrology/astro-gatekeeper/` and all active Hermes profile skill directories (pruning legacy `astrology-writer` and `astrology-report-gatekeeper` folders).
3. Synchronizes `~/.hermes/profiles/astro-gatekeeper/SOUL.md` directly from the unified `astro-gatekeeper` skill definition.
4. Runs a runtime verification check against Hermes's `skill_view` loader.

#### Using the `astro-gatekeeper` Bot in Hermes
With the unified `astro-gatekeeper` profile, you only need to provide the path to a generated `<name>_llm_context.md` file:
* **Initial Reading + Audit**: Provide `@profiles/<name>/<name>_llm_context.md` and ask for a reading—the bot automatically drafts the 6-part reading, runs the 10-point QA gatekeeper audit, and outputs the verified report.
* **Follow-Up Questions**: Ask any life-topic question in the same session (e.g., *"What does the chart indicate about my relationship with my father?"* or *"How should I navigate my current Mahadasha?"*) and the bot will answer using the 4-Pillar Topic Synthesis protocol.

---

## 🧪 Testing & Validation

To guarantee astronomical and rule-evaluation accuracy, the project includes an automated test suite in [`tests/test_astrology_engine.py`](tests/test_astrology_engine.py). It validates charts of historical figures (rated AA by Astro-Databank) across both `Tropical-Vedic` and `Sidereal` modes:

* **Steve Jobs**: Validates tropical Ascendant (Virgo), Sun/Moon placements, and active yogas (*Gajakesari*, *Amala*).
* **Albert Einstein**: Validates sidereal Ascendant (Gemini), exalted Venus (Pisces), and active yogas (*Malavya*, *Amala*).
* **Barack Obama**: Validates sidereal Ascendant (Capricorn), Saturn in Capricorn/1st house, and active *Sasa Yoga* (*Pancha Mahapurusha*).
* **Mahatma Gandhi**: Validates sidereal Ascendant (Libra), Moon in Leo, and active yogas (*Malavya*, *Gajakesari*).

Run the test suite from your terminal:
```bash
python3 tests/test_astrology_engine.py
```

---

## 📖 Tajika Prasna Guide (Horary Astrology)

Prasna is the art of answering specific queries based on the exact moment and location a question is posed. Tajika astrology's degree-based aspects are a primary foundation for Prasna.

### How to Cast a Prasna Chart
1. Update `B_YEAR`, `B_MONTH`, `B_DAY`, and `B_TIME` to the **exact moment** the question is asked.
2. Update `BIRTH_PLACE` (or `LATITUDE` / `LONGITUDE`) to the location of the querent.
3. Run the pipeline and open the generated HTML report.

### Key Interpretations
1. **The Asker (Querent)**: Signified by the **Lagna Lord** (Lord of the 1st house) and the **Moon**.
2. **The Subject (Quesited)**: Signified by the lord of the house corresponding to the topic (e.g., 7th for marriage/partnerships, 10th for career, 4th for property).
3. **The Answer (Tajika Aspects)**: Check the **Planetary Aspects -> Tajika** tab:
   * **Conjunction, Sextile, or Trine**: Success and cooperative resolution.
   * **Square or Opposition**: Obstacles, friction, or delay.
   * **No Aspect**: Lack of connection or stagnation.
4. **Timing & Application (*Ithasala*)**: If the faster-moving planet is at a lower degree than the slower planet and applying toward exact aspect, it forms **Ithasala Yoga**, indicating future fulfillment. If separating (**Esharapha Yoga**), the window of opportunity has passed.

---

## 📖 Traditional Parashari Prasna Guide

While Tajika aspects are degree-based, traditional **Parashari Prasna** uses sign/house-based aspects (*Graha Drishti*), relationship dynamics, and planetary dignities to answer horary questions.

### Key Interpretations in Parashari Prasna
1. **Lagna & Lagna Lord (Querent)**:
   * Check the **Planets** and **Planetary Friendships** tabs.
   * If the Lagna Lord is placed in a Kendra (1, 4, 7, 10) or Trikona (5, 9), or is exalted/in own sign, the querent has the agency to achieve the goal.
2. **Quesited House & House Lord (The Query)**:
   * Examine the target house (e.g., 7th house for spouse/business partner).
   * If the house is aspected by its own lord or natural benefics (Jupiter, Venus, Mercury) and free from malefic affliction, the outcome is favorable.
3. **Mutual Aspects & Conjunctions**:
   * Check **Planetary Aspects -> Parashari**: direct aspect or conjunction between the Lagna Lord and Quesited Lord indicates fulfillment.
4. **Planetary Friendships (*Panchadha Maitri*)**:
   * Check the **Planetary Friendships** compound table. **Friends (*Mitra*)** or **Great Friends (*Adhi Mitra*)** indicate harmony and cooperative resolution; **Enemies (*Shatru*)** or **Great Enemies (*Adhi Shatru*)** indicate friction or incompatible terms.
5. **Benefic/Malefic Distribution**:
   * Natural benefics in Kendras (1, 4, 7, 10) or Trikonas (5, 9) bring timely support; natural malefics in Upachayas (3, 6, 10, 11) grant resilience to overcome obstacles.

---

## 📖 Natal Astrology Guide (Birth Chart Interpretation)

Use the interactive HTML report (`<name>_report.html`) alongside the knowledge base to synthesize a natal chart:

### 1. The Core Triad (*Sudarshana Chakra*)
Go to the **Sudarshana Chakra** tab. This concentric 3-wheel chart aligns three dimensions of the native's life:
* **Outer Ring (*Udaya Lagna*)**: Physical body, concrete environment, and visible trajectory.
* **Middle Ring (*Chandra Lagna*)**: Mind, emotional conditioning, and psychological receptivity.
* **Inner Ring (*Surya Lagna*)**: Soul vitality, authority, and core dharma.

### 2. Planetary Strengths, Dignities & Avasthas
* **Planetary Synthesis Tab**: Inspect Jaimini **Chara Karakas** (*Atmakaraka* through *Darakaraka*), divisional dignities (`D9` Navamsa and `D10` Dasamsa), and the 5-fold **Avasthas** (*Bālādi, Jāgratādi, Dīptādi, Lajjitādi, Shayanādi*).
* **Shadbala Tab**: Review the 6 sources of planetary strength. A planet with high Shadbala and a strong Avastha delivers its house significations reliably; a planet with high dignity but low Shadbala (`High Drive / Lacks Resources`) indicates strong ambition that requires careful pacing.

### 3. Relationship Dynamics (*Panchadha Maitri*)
* **Planetary Friendships Tab**: View the **Compound Friendships** grid to evaluate how house lords cooperate or clash when conjoined or aspecting one another.

### 4. House Support & Gochara (*Ashtakavarga*)
* **Ashtakavarga Tab**: Review the **Samudaya Ashtakavarga (SAV)** row:
  * Houses with **$\ge 30$ bindus** represent high-support environments where initiatives gain traction easily.
  * Houses with **$< 25$ bindus** represent high-friction environments that demand extra patience and structural discipline.
* **Gochara Transits Tab**: Evaluates current planetary transits from the natal Moon (*Vedha* obstructions and *Murthi Nirnaya* quality) combined with the transit house's SAV bindu support.

### 5. Timing of Events (*Vimshottari Dasha*)
* **Vimshottari Dasha Tab**: Expand the nested timeline to track active *Mahadasha*, *Antardasha*, and *Pratyantardasha* lords, which awaken the houses they rule and occupy in the natal chart.

---

## 🗺️ Roadmap & Planned Fixes

See **[`ROADMAP.md`](ROADMAP.md)** for the active backlog, architectural history, and completed milestones:

* **Classical Yoga Deduplication & Parity Harmonization** *(Scheduled)*: Harmonize active yoga evaluation between the HTML dashboard and LLM context exporters to eliminate duplicate generic clone cards.
* **Implemented Avastha & KB Systems** *(Completed)*: Full calculations for *Bālādi, Jāgratādi, Dīptādi, Lajjitādi,* and *Shayanādi* Avasthas, plus the 22-card `astrology_kb` and Hermes skill synchronization pipeline.

# Universal Astrological OKF Engine

A comprehensive Python-based astrological calculation engine that translates classic Vedic configurations into algorithmically computable rules. This project uses the Swiss Ephemeris (`pysweph`) to generate birth charts, divisional harmonics, planetary strengths, Ashtakavarga grids, and Vimshottari dasha cycles, outputting premium interactive dashboards and LLM-friendly payloads.

---

## 🌟 Key Features

* **Comprehensive Yoga Engine**: Evaluates charts against a library of **81 unique Vedic yogas** across 9 category-specific JSON rule files.
* **Interactive Dashboard Report**: Compiles a rich, responsive HTML dashboard complete with South and North Indian style chart SVGs, planet/house details, Ashtakavarga grids, nested dasha timelines, and transits.
* **Interactive Filtering**: The dashboard includes an interactive toggle switch to view **Active Yogas Only** (default) or all checked combinations.
* **LLM-Optimized Payload Exporter**: Automatically outputs a secondary compact payload (`_llm_payload.json`) tailored for small local models (like Gemma 2 9B or Llama 3 8B). This file is trimmed from 270 KB to **~18 KB (~3,500 tokens)** by keeping only active yogas and current dasha chains, while preserving rich planetary sub-balas.

---

## 📁 Directory Structure

* **`astrology.ipynb`**: The main Jupyter Notebook calculation pipeline.
* **`report_template.html`**: The responsive styling template for generating HTML dashboards.
* **`yogas/`**: Directory containing 81 rule definitions categorized in JSON files:
  * `01_pancha_mahapurusha_yogas.json` (Mars, Mercury, Jupiter, Venus, Saturn kendra dignities)
  * `02_nabhasa_yogas.json` (Akriti, Asraya, Dala, Sankhya shape-based yogas)
  * `03_solar_yogas.json` (Vesi, Vasi, and Ubhayachari solar combinations)
  * `04_lunar_yogas.json` (Sunapha, Anapha, Durudhara, Gajakesari lunar combinations)
  * `05_lagna_yogas.json` (Lagna house strengths and alignments)
  * `06_dispositor_yogas.json` (Dispositor placements and Neechabhanga cancels)
  * `07_deity_avatar_yogas.json` (Srinatha, Brahma, Indra alignments)
  * `08_raja_and_dhana_yogas.json` (Wealth and royalty indicators, including gender-specific Maha Bhagya Yogas)
  * `09_miscellaneous_core_yogas.json` (Parivartana / sign exchange yogas)

---

## 🚀 How to Run

### Prerequisites
Ensure you have Python 3 and the required libraries installed:
```bash
pip install pysweph pyyaml requests tzdata jinja2 python-dateutil geopy
```

### Steps
1. Open the project in Jupyter Lab, Jupyter Notebook, or VS Code:
   ```bash
   jupyter notebook astrology.ipynb
   ```
2. Go to **Cell 10** (`⚙️ Birth Data Configuration`) and input your birth details:
   * `SUBJECT_NAME`: Name of the subject (e.g. `"Steve Jobs"`)
   * `B_YEAR`, `B_MONTH`, `B_DAY`: Birth date coordinates
   * `B_TIME`: Birth time (24-hour format)
   * `B_TZ`: Local timezone database name (e.g., `"America/Los_Angeles"`)
   * `LATITUDE`, `LONGITUDE`: Decimal coordinates of birth place
   * `GENDER`: Gender input (`"Male"` or `"Female"`)
3. Run all cells in the notebook.
4. **View Outputs**:
   * Stored structured full calculations: `profiles/<name>/<name>_astrology_profile.json`
   * Stored compact LLM payload: `profiles/<name>/<name>_llm_payload.json`
   * Stored interactive HTML report: `profiles/<name>/<name>_report.html`
   * Bundled production archive: `C:\Users\carlo\Documents\astrology-notebook\<name>_astrology_profile_final.zip`

---

## 🧪 Testing & Validation

To ensure astronomical and logic calculation accuracy, the project includes a validation suite in the [tests/test_astrology_engine.py](file:///C:/Users/carlo/Documents/astrology-notebook/tests/test_astrology_engine.py) file. This suite calculates and asserts the charts of verified historical figures (all rated AA by Astro-Databank) in both `Tropical-Vedic` and `Sidereal-Vedic` modes:

* **Steve Jobs**: Validates tropical Ascendant (Virgo), Sun/Moon placements, and active yogas (such as Gajakesari and Amala).
* **Albert Einstein**: Validates sidereal Ascendant (Gemini), exalted Venus (Pisces), and active yogas (such as Malavya and Amala).
* **Barack Obama**: Validates sidereal Ascendant (Capricorn), Saturn in Capricorn/1st house, and the active *Sasa Yoga* (Pancha Mahapurusha).
* **Mahatma Gandhi**: Validates sidereal Ascendant (Libra), Moon in Leo, and active yogas (such as Malavya and Gajakesari).

### How to Run Tests

You can execute the test suite directly from your terminal:

```bash
python tests/test_astrology_engine.py
```

---

## 📖 Tajika Prasna Guide (Horary Astrology)

Prasna is the art of answering specific queries based on the moment and location a question is posed. Tajika astrology's degree-based aspects are the primary foundation for Prasna.

### How to Cast a Prasna Chart
1. Update `B_YEAR`, `B_MONTH`, `B_DAY`, and `B_TIME` in the notebook inputs to the **exact moment** the question is asked.
2. Update `LATITUDE` and `LONGITUDE` to the location of the asker (the querent).
3. Run the pipeline and open the generated HTML report.

### Key Interpretations
1. **The Asker (Querent)**: Represented by the **Lagna Lord** (Lord of the 1st house) and the **Moon**.
2. **The Subject (Quesited)**: Represented by the lord of the house corresponding to the topic (e.g., 7th for marriage, 10th for career, 4th for property).
3. **The Answer (Tajika Aspects)**: Check the **Planetary Aspects -> Tajika** tab:
   * **Conjunction, Sextile, or Trine**: Success and resolution.
   * **Square or Opposition**: Obstacles, conflict, or failure.
   * **No Aspect**: Stagnation or no progression.
4. **Timing & Application (Ithasala)**: If the faster-moving planet has a lower degree than the slower planet, they are **applying** (Ithasala Yoga), indicating success in the future. If the faster planet has a higher degree, they are **separating** (Esharapha Yoga), meaning the opportunity has passed.

---

## 📖 Traditional Parashari Prasna Guide

While Tajika aspects are degree-based, traditional **Parashari Prasna** uses classical house-based aspects (*Graha Drishti*), relationship dynamics, and planetary alignments to answer horary questions.

### Key Interpretations in Parashari Prasna
1. **Lagna & Lagna Lord (Querent)**: 
   * Check the **Planets** and **Planetary Friendships** tabs.
   * If the Lagna Lord is placed in a Kendra (1, 4, 7, 10) or Trikona (5, 9), or is exalted/own sign, the querent is strong enough to achieve the goal.
2. **Quesited House & House Lord (The Query)**:
   * Look at the target house (e.g. 7th house for business partner/spouse). 
   * If the house is aspected by its own lord or by benefics (Jupiter, Venus, Mercury), or is free from malefic occupants/aspects, the desire is highly favorable.
3. **Mutual Aspects & Conjunctions**:
   * Check **Planetary Aspects -> Parashari**:
     * If the Lagna Lord aspects the Quesited House or the Quesited Lord directly, success is indicated.
     * If they are conjoined in the same house, resolution is imminent.
4. **Planetary Friendships (Panchadha Maitri)**:
   * Check the **Planetary Friendships** compound friendship table.
   * If the Lagna Lord and Quesited House Lord are **Friends (Mitra)** or **Great Friends (Adhi Mitra)**, agreement, cooperative resolution, and a positive outcome are easily reached.
   * If they are **Enemies (Shatru)** or **Great Enemies (Adhi Shatru)**, the query faces hidden friction, lack of cooperation, or cancellation.
5. **Benefic/Malefic Distribution**:
   * Benefics (Jupiter, Venus, Mercury, strong Moon) in Kendras (1, 4, 7, 10) or Trikonas (5, 9) bring sudden, helpful assistance.
   * Malefics (Mars, Saturn, Sun) in Dusthanas (6, 8, 12) represent that difficulties/enemies/losses are neutralized, whereas malefics in Kendras indicate obstacles and frustration.

---

## 📖 Natal Astrology Guide (Birth Chart Interpretation)

Use the interactive HTML report to synthesize a birth chart using Vedic principles:

### 1. The Core Triad (Sudarshana Chakra)
Go to the **Sudarshana Chakra** tab. This concentric 3-wheel chart aligns three dimensions of the native's life:
* **Outer Ring (Udaya Lagna)**: Physical body, career, actions, and outer environment.
* **Middle Ring (Chandra Lagna)**: Mind, emotions, psychology, and receptivity.
* **Inner Ring (Surya Lagna)**: Soul, vitality, health, and spirit.
* *Synthesis*: A house is strongest and manifests with ease when it contains benefics or strong placements in all three rings.

### 2. Planetary Strengths & Dignities
* **Planetary Synthesis Tab**: Look at the labels under the planet cards to identify Jaimini **Chara Karakas** (e.g. *Atmakaraka* - the soul significator, *Amatyakaraka* - career significator).
* **Shadbala Tab**: Check the detailed breakdown of the 6 sources of planetary strength. A planet with a high Shadbala total (> threshold) manifests its house significations strongly and easily in the physical world.

### 3. Relationship Dynamics (Panchadha Maitri)
* **Planetary Friendships Tab**: View the **Compound Friendships** grid. Planets that are natural or temporal friends cooperate, whereas enemies (e.g. Saturn and Sun) placed together create tension, friction, or delays in the houses they rule.

### 4. House Support & Gochara (Ashtakavarga)
* **Ashtakavarga Tab**: Review the **Samudaya Ashtakavarga (SAV)** row at the bottom of the table:
  * Houses with **> 28 bindus** indicate strength, prosperity, and success during planetary transits.
  * Houses with **< 25 bindus** represent areas of life that require discipline, structure, and hard work to sustain.
* **Gochara Transits Tab**: Checks transits against the natal Moon. Auspicious transits will bring positive results if they cross houses with high SAV bindu counts.

### 5. Timing of Events (Vimshottari Dasha)
* **Vimshottari Dasha Tab**: Expand the nested list to track current Mahadashas, Antardashas, and Pratyantardashas. The lords of the active dasha periods will activate their natal house placements and planetary configurations during their respective time windows.

---

## 🗺️ Future Roadmap

The following classical Vedic **Avastha Systems** are scheduled for implementation into the calculation pipeline, HTML report dashboard, and LLM payload exporter:

1. **Bālādi Avasthas (Age & Degree Potency)**
   * Computes planetary maturity (*Bāla*, *Kumāra*, *Yuvā*, *Vṛddha*, *Mṛta*) based on sign parity and longitude degrees.
2. **Jāgradādi Avasthas (Alertness & Consciousness)**
   * Evaluates planetary consciousness (*Jāgraṭa* - Awake, *Swapna* - Dreaming, *Suṣupti* - Sleeping) based on dignity and friendship status.
3. **Dīptādi Avasthas (10 Luminosity & Emotional Dignity States)**
   * Assesses qualitative expression across 10 states (*Dīpta*, *Svastha*, *Mudita*, *Shānta*, *Dīna*, *Dukhita*, *Vikala*, *Khala*, *Kopa*, *Dapti*).
4. **Shayanādi Avasthas (12 Activity & Behavioral States)**
   * Calculates Parashari behavioral states (*Śayana*, *Upaveśana*, *Netrapāṇi*, *Prakāśana*, *Gamana*, *Āgamana*, *Sabhā*, *Āgama*, *Bhojana*, *Nṛtyalipsā*, *Kautuka*, *Nidrā*) using Nakshatra index formulas.
5. **Lajjitādi Avasthas (6 Emotional/Psychological Conditions)**
   * Evaluates planetary mood and affliction (*Lajjita*, *Garvita*, *Kṣubhita*, *Kṣudhita*, *Tṛṣita*, *Mudita*) based on 5th house placements, nodal conjunctions, and malefic aspects.

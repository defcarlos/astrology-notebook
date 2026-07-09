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
   * Stored structured full calculations: `knowledge_base/<name>/<name>_astrology_profile.json`
   * Stored compact LLM payload: `knowledge_base/<name>/<name>_llm_payload.json`
   * Stored interactive HTML report: `knowledge_base/<name>/<name>_report.html`
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


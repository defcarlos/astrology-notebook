# Project Roadmap & Backlog

This document tracks planned fixes, enhancements, and architectural improvements for the Universal Astrological OKF Engine.

---

## 📌 Scheduled Fixes & Backlog

### 1. Classical Yoga Deduplication & HTML/LLM Parity Harmonization
* **Status:** Scheduled / On Hold
* **Identified Discrepancy:**
  * The HTML dashboard (`report.html`) displays all raw active yogas evaluated across the 9 JSON rule files in `yogas/`, producing duplicate cards for identical combinations (e.g. both `Vesi Yoga` and `Generic Vesi Yoga`, `Vasi Yoga` and `Generic Vasi Yoga`, `Ubhayachari Yoga` and `Generic Ubhayachari Yoga`, or `Amala Yoga` and `Amala Yoga (Lagna)`).
  * In contrast, the LLM context exporters (`_llm_context.md` and `_llm_payload.json`) deliberately suppress generic prefixes (`Generic ...`) and identical predictive result strings (`seen_results`) to protect the local model's context window.
  * This creates an apparent count mismatch (e.g., 14 active yogas in HTML vs. 11 in Markdown for Steve Jobs and Carlos; 15/16 vs. 11/12 in others).
* **Planned Fix:**
  1. **Rule File Pruning (Source Cleanup):** Audit `01_pancha_mahapurusha_yogas.json`, `03_solar_yogas.json`, `04_lunar_yogas.json`, and `05_lagna_yogas.json` to prune redundant generic clone rules where specific classical rules already exist.
  2. **Engine / Template Deduplication:** Align `YogaEngine.scan_yogas` and `report_template.html` with the exporter's deduplication logic so that duplicate cards are eliminated from `report.html`.
  3. **1:1 Parity Verification:** Ensure all generated profiles (`profiles/*/`) exhibit 100% 1:1 parity between HTML report cards and LLM markdown context lists.

---

## ✅ Completed Milestones

### 1. Core Engine Modernization & Refactoring (Phases 1–3)
- [x] **Swiss Ephemeris Safety:** Auto-configured local `ephe/` path on module load and wrapped C-level global ephemeris calls in a re-entrant thread lock (`_swe_lock`).
- [x] **Mathematical Constants & Helpers:** Centralized `SIGN_SPAN`, `NAKSHATRA_SPAN`, `PADA_SPAN`, `COMBUSTION_ORB` in `AstroMath`, alongside `get_sign_and_degree(lon)` and `is_sidereal_mode(mode)`.
- [x] **Divisional Chart Deduplication:** Streamlined all 16 divisional charts (D-1 through D-60) using `divmod` math.
- [x] **Unified Pipeline Orchestration:** Implemented `AstrologyPipeline.calculate()` orchestrating full 11-step chart calculations into a structured `ChartResult` dataclass with `.to_profile_dict()` and `.export_all()`.
- [x] **Notebook Streamlining:** Reduced `astrology.ipynb` execution cell from ~190 lines to ~35 lines.
- [x] **Object Model Decoupling:** Decoupled `Planet` dataclass with `Planet.from_ephemeris(...)` and coordinate accessors (`get_longitude`, `get_house`, `get_sign`, `get_speed`).
- [x] **In-Memory HTMLReporter:** Enabled `HTMLReporter` to accept in-memory dictionary data and compile directly to an HTML string without mandatory disk I/O.
- [x] **Comprehensive Test Suite:** 12 unit tests passing in `tests/test_astrology_engine.py`.

### 2. Parashari & Jaimini Calculation Corrections
- [x] **Jaimini Karaka Degree Alignment:** Fixed degree-in-sign calculation to respect the active coordinate system (`Tropical-Vedic` vs. `Sidereal`).
- [x] **Parashari Planetary Aspects:** Fixed house occupants and Lagna aspect detection, and corrected HTML aspect table rendering.

### 3. Knowledge Base & Local LLM Skills
- [x] **Unified `astro-gatekeeper` Skill & Hermes `SOUL.md` Sync:** Consolidated `astrology-writer` and `astrology-report-gatekeeper` into a single 3-mode `astrology_kb/astro-gatekeeper/SKILL.md` package and automated `SOUL.md` synchronization via `scripts/sync_hermes.py`.
- [x] **Link Portability & Sanitization:** Converted 106 absolute links to relative paths across all knowledge base markdown files (0 broken links remaining).
- [x] **Cross-Platform Compatibility:** Replaced Unix symlinks with portable markdown pointer files.

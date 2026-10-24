---
type: Diagnostic Card
title: Mathematical Foundations of Jyotish Diagnostic Card
description: Essential astronomical and mathematical mechanics governing Ayanamsa, Sidereal vs Tropical zodiacs, Panchanga, and Retrogradation.
tags: [math, astronomy, ayanamsa, sidereal, tropical, retrograde, vakra, okf card]
timestamp: 2026-10-01T08:42:00Z
---

# Mathematical Foundations: Diagnostic Card

Astrology interprets astronomical geometry. Use this card alongside the [Astro Gatekeeper](../astro-gatekeeper/SKILL.md) to understand the coordinate mechanics behind chart summaries.

---

## 1. Tropical (Sayana) vs. Sidereal (Nirayana) & Ayanamsa

* **Ayanamsa:** The exact mathematical angular distance between the moving equinox (Tropical) and the fixed stellar constellations (Sidereal) caused by axial precession (~50.3" arc per year).
* **The Hybrid Bridge:**
  * **Tropical Placements:** Used for psychological baseline, ego structure, and immediate worldly interaction.
  * **Sidereal Placements:** Used for Nakshatras, Vargas (D-9, D-10), and Vimshottari Dasha timing.
  * *Conversion:* $\text{Sidereal Longitude} = \text{Tropical Longitude} - \text{Ayanamsa}$ (approx. $24^\circ$ difference in current epoch). *(Models: All conversions are pre-calculated ground truth in chart payloads. Do NOT attempt manual arithmetic or degree conversions).*

---

## 2. Retrograde Motion (Vakra) Mechanics

In chart tables, marked as `(R)` (e.g. `Mercury (R)` or `Jupiter (R)`):
* **Kinetic Power:** Retrograde planets are closest to Earth, granting them **maximum Chestha Bala (motional strength)**.
* **Psychological Manifestation:** The planet’s energy turns inward, unconventional, and intensely persistent. It re-evaluates, re-engineers, and refuses standard societal protocols.
* **Benefic vs. Malefic Retrograde:**
  * *Retrograde Benefic (Jupiter/Venus):* Unconventional wisdom or aesthetics; questions dogma.
  * *Retrograde Malefic (Saturn/Mars):* Highly intense, stubborn, and relentlessly strategic.

---

## 3. Panchanga (Five Limbs of Time)
* **Tithi (Lunar Day):** Longitudinal distance between Sun and Moon in $12^\circ$ increments ($360^\circ / 30 = 12^\circ$). Dictates emotional nourishment.
* **Vara (Solar Weekday):** Governed by the planetary ruler of the day (e.g. Thursday = Jupiter). Governs physical vitality and stamina.
* **Nakshatra:** The Moon’s exact $13^\circ 20'$ mansion. Governs instinct and Vimshottari timing balance.
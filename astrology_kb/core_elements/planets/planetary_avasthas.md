---
type: Diagnostic Card
title: Planetary Avasthas (States of Being) Diagnostic Card
description: Diagnostic rules for Baladi (age/degrees), Jagradadi (alertness), Lajjitadi (emotional condition in context tables), and Deeptadi avasthas.
tags: [avasthas, states, baladi, jagradadi, lajjitadi, deeptadi, planetary age, degrees, okf card]
timestamp: 2026-10-18T00:00:00Z
---

# Planetary Avasthas: Diagnostic Card

While [Planetary Dignity](planetary_dignity.md) defines environmental comfort, an **Avastha** dictates a planet's internal vitality, alertness, emotional disposition, and physical capacity to manifest karma. Use alongside the [Astro Gatekeeper](../../astro-gatekeeper/SKILL.md).

---

## 1. Bālādi Avasthas (Physical Age & Manifestation Capacity)
Calculated from the exact longitudinal degree of the planet within a 30° sign (displayed in the `Bālādi (Age/Capacity)` column of `*_llm_context.md`):

| Degrees in Odd Signs (Aries, Gemini, Leo, Libra, Sag, Aqu) | Degrees in Even Signs (Taurus, Cancer, Virgo, Sco, Cap, Pis) | Avastha (State) | Kinetic Manifestation Capacity |
| :--- | :--- | :--- | :--- |
| **0° – 6°** | **24° – 30°** | **Bāla (Infant)** | **25%** (Emerging potency; needs guidance, incubation, and time to mature) |
| **6° – 12°** | **18° – 24°** | **Kumāra (Youth)** | **50%** (Energetic, curious, and ambitious, but still building long-term endurance) |
| **12° – 18°** | **12° – 18°** | **Yuvā (Adult)** | **100% (Prime)** (Full kinetic manifestation power; peak physical and executive vitality) |
| **18° – 24°** | **6° – 12°** | **Vṛddha (Old)** | **10%** (Seasoned wisdom and perspective, but lower physical stamina) |
| **24° – 30°** | **0° – 6°** | **Mṛta (Dead)** | **0%** (Materially depleted; struggles to execute physical results without external support) |

---

## 2. Jāgratādi Avasthas (Level of Alertness)
Determines how awake or responsive a planet is to its duties (displayed in the `Jāgratādi (Alertness)` column):
* **Jāgraṭa (Awake — 100%):** Planet in Exaltation or Own Sign. Fully conscious; delivers clear, decisive, unmistakable external events.
* **Swapna (Dreaming — 50%):** Planet in Friend's or Neutral Sign. Operating at a reflective, interior, or fluctuating tempo; results require conscious activation or Dasha triggers.
* **Suṣupti (Sleeping — 0%):** Planet in Enemy Sign or Debilitated. Latent or unconscious; the planet's lessons operate beneath the surface or manifest through friction until consciously mastered.

---

## 3. Lajjitādi Avasthas (Emotional Disposition & Relational Mood)
Displayed in the `Lajjitādi (State)` column of `*_llm_context.md`. Evaluates how a planet feels based on its dignity, house, and conjunctions/aspects from other planets:

| Lajjitādi State | Engine Trigger Condition | Psychological & Material Interpretation |
| :--- | :--- | :--- |
| **Garvita (Proud)** | Planet in `Exalted` or `Own Sign` | Self-assured, dignified, and authoritative; takes natural pride in executing its house and karaka duties. |
| **Mudita (Delighted)** | Planet conjoined with `Jupiter` or `Venus`, or in a `Friendly Sign` | Joyful, cooperative, and well-supported; experiences grace, relational warmth, and smooth creative flow. |
| **Lajjita (Embarrassed)** | Planet in `House 5` conjoined with `Rahu`, `Ketu`, `Sun`, `Saturn`, or `Mars` | Self-conscious, hesitant, or overly self-critical regarding creative expression, intellect, or children; fear of public judgment. |
| **Kṣubhita (Agitated)** | Planet conjoined with `Sun` and aspected by `Saturn`, `Mars`, `Rahu`, or `Ketu` | Restless, pressured, or internally conflicted; feels pulled between authority demands and external resistance. |
| **Kṣudhita (Hungry)** | Planet `Debilitated` or aspected by `Saturn` or `Mars` | Craving support, validation, or resources; experiences a persistent sense of "unmet appetite" or heavy duty in its life areas until channeled into disciplined mastery. |
| **Sama (Balanced)** | No extreme Lajjitādi affliction or exaltation trigger active | Steady, even-keeled, and neutral emotional baseline; outcomes follow the planet's house placement and Shadbala strength. |

*(Note: In JSON payloads `*_llm_payload.json`, the engine also records **Deeptādi Avasthas** based purely on sign dignity: `Dīpta` [Exalted], `Swastha` [Own], `Mudita` [Great Friend], `Śānta` [Friend], `Dīna` [Neutral], `Dukhita` [Enemy], `Khala` [Debilitated]).*

---

## 4. The Critical Avastha Override Rule (`High Drive / Lacks Resources`)

> [!IMPORTANT]
> **Shadbala / Dignity vs. Mṛta Avastha Override:**
> When a planet has **Strong Shadbala** (or sits in Own/Exalted sign) **but** sits in **`Mṛta (0%)` Bālādi Avastha** (or has low BAV $\le 3/8$), the table's `Takeaway` column flags **`High Drive / Lacks Resources`**.
> * **How to Diagnose:** The native possesses strong internal ambition, talent, and drive for that planet's houses/karaka role, **but** encounters material, logistical, or stamina bottlenecks when trying to execute alone. They must rely on systems, pacing, or partnerships to supply the missing fuel.
---
type: Astrological Rule
title: Planetary Friendships (Maitri)
description: The system of natural and temporary planetary relationships used to determine a planet's compound disposition in a chart.
resource: local://Rahu, Ketu, and Planetary Friendship
tags: [planetary friendships, compound relationships, maitri, alliances, vedic astrology]
timestamp: 2026-07-01T12:00:00Z
---

# Planetary Friendships (Maitri)

In Vedic Astrology, planets do not operate in a vacuum. Their ability to produce positive or negative results is heavily dependent on their dignity, which is largely determined by their relationship with the ruler of the sign they occupy, as well as the planets aspecting them.

To evaluate how well planets cooperate or conflict within a specific individual's horoscope, astrologers use a three-tiered system.

## 1. Natural Relationship (Naisargika Maitri)
This is the permanent, baseline relationship between planets, based on the astrological "planetary cabinet." These relationships are fixed and apply to all charts.

| Planet | Friends | Neutrals | Enemies |
| :--- | :--- | :--- | :--- |
| **Sun (Surya)** | Moon, Mars, Jupiter | Mercury | Venus, Saturn |
| **Moon (Chandra)** | Sun, Mercury | Mars, Jupiter, Venus, Saturn | None |
| **Mars (Mangala)** | Sun, Moon, Jupiter | Venus, Saturn | Mercury |
| **Mercury (Budha)** | Sun, Venus | Mars, Jupiter, Saturn | Moon |
| **Jupiter (Guru)** | Sun, Moon, Mars | Saturn | Mercury, Venus |
| **Venus (Shukra)** | Mercury, Saturn | Mars, Jupiter | Sun, Moon |
| **Saturn (Shani)** | Mercury, Venus | Jupiter | Sun, Moon, Mars |
| **Rahu** | Mercury, Venus, Saturn | Jupiter | Sun, Moon, Mars |
| **Ketu** | Sun, Moon, Mars | Mercury, Jupiter, Venus, Saturn | None |

## 2. Temporary Relationship (Tatkalika Maitri)
This relationship is unique to the individual's specific natal chart. It is determined by the spatial distance between planets:
* **Temporary Friends:** Planets situated in the 2nd, 3rd, 4th, 10th, 11th, or 12th houses from one another.
* **Temporary Enemies:** Planets situated in the same house (1st), or the 5th, 6th, 7th, 8th, or 9th houses from one another.

## 3. Compound Relationship (Panchadha Maitri)
These temporary relationships are then combined with the planets' permanent (natural) relationships to determine their overall, compound relationship in a specific chart. 

The resulting 5-point scale is:
1. **Great Friend (Adhi Mitra):** Natural Friend + Temporary Friend
2. **Friend (Mitra):** Natural Friend + Temporary Neutral (or vice versa)
3. **Neutral (Sama):** Natural Friend + Temporary Enemy (or vice versa)
4. **Enemy (Shatru):** Natural Enemy + Temporary Neutral (or vice versa)
5. **Great Enemy (Adhi Shatru):** Natural Enemy + Temporary Enemy

---

## 🧠 Psychological & Synthesis Interpretations for Agents

> [!IMPORTANT]
> The `"planetary_friendships"` block in the input JSON payload represents the **already-resolved Compound Relationships (Panchadha Maitri)** specific to this particular natal chart. It mathematically combines the fixed Natural relationships with the chart's unique Temporary relationships (derived from the positions of the planets in the houses). Do not attempt to recalculate these; read the values (such as `Adhi Mitra` or `Adhi Shatru`) directly from the JSON.

When reviewing the `planetary_friendships` block in the chart payload, interpret the compound states as follows:

*   **Great Friend (Adhi Mitra):** *Synergistic Alliances.* The internal psychological drives represented by these two planets operate in complete harmony. Success is easily attained in activities requiring both functions. For example, if Mars and Jupiter are Great Friends, the native's drive/execution (Mars) naturally aligns with their wisdom/higher purpose (Jupiter), leading to successful, dharmic action.
*   **Friend (Mitra):** *Constructive Cooperation.* The planets work well together, offering stable support. Their combined expression is pleasant and easily integrated into the personality.
*   **Neutral (Sama):** *Functional Indifference.* The planets do not actively block or support each other. Their relationship is transactional; they cooperate only when triggered by transit or house placement.
*   **Enemy (Shatru):** *Friction & Discontent.* One planet's expression tends to starve or disrupt the other. For example, if Moon and Mars are Enemies, the emotional baseline (Moon) is consistently agitated or threatened by the combative, individualistic drive (Mars), leading to emotional volatility or defensive reactions.
*   **Great Enemy (Adhi Shatru):** *Deep Cognitive Dissonance.* The internal drives of these two planets are in direct conflict, leading to chronic self-sabotage, psychological blocks, or external projection of conflict. For example, if Sun and Saturn are Great Enemies, the ego/self-expression (Sun) feels constantly oppressed, limited, or criticized by the structural taskmaster (Saturn), resulting in authority issues or low self-esteem that requires immense conscious work to resolve.

*Execution Note:* When analyzing a house, always check if the planet occupying the house is in a friendly or inimical relationship with the lord of that house. If the house lord is an *Adhi Shatru* to the tenant, the house significations suffer from severe internal friction.
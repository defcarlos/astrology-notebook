import unittest
import sys
from pathlib import Path
import swisseph as swe

# Ensure the root directory is in the import path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from astrology_engine import (
    AstroTime,
    HouseEngine,
    ChartFactory,
    ShadbalaEngine,
    AshtakavargaEngine,
    YogaEngine,
    AstroMath,
    JaiminiEngine,
    PanchangaEngine,
    PlanetarySynthesisEngine,
    AspectEngine,
    AvasthaEngine,
    LLMContextExporter,
    VimshottariDashaEngine,
    AstrologyPipeline,
    ChartResult
)

# Configure Swiss Ephemeris path
swe.set_ephe_path(str(ROOT_DIR / 'ephe'))

def calculate_chart_profile(year, month, day, time_str, tz, lat, lon, mode="Tropical-Vedic", house_system="W", ayanamsa=36):
    """
    Helper function to run the complete calculation pipeline via AstrologyPipeline.
    Returns ChartResult, which unpacks as (chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects).
    """
    yogas_rules_path = ROOT_DIR / 'yogas'
    subject_profile = {"name": "Test Subject", "gender": "Male"}
    return AstrologyPipeline.calculate(
        year=year, month=month, day=day, hour=time_str, tz=tz, lat=lat, lon=lon,
        mode=mode, house_system=house_system, ayanamsa=ayanamsa,
        yogas_rules_path=yogas_rules_path, subject=subject_profile, compute_transits=False
    )

class TestAstrologyEngine(unittest.TestCase):

    def test_steve_jobs_tropical_vedic(self):
        """
        Verify Steve Jobs chart in Tropical-Vedic mode.
        """
        # Steve Jobs: Feb 24, 1955 at 19:15, San Francisco, CA
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic"
        )
        
        # Verify Lagna (Ascendant) is Virgo under Tropical-Vedic
        self.assertEqual(local_sky.tropical_ascendant_sign, "Virgo")
        
        # Verify Sun and Moon placements
        # In Tropical-Vedic mode, planet signs use the tropical zodiac
        self.assertEqual(chart["Sun"].zodiac_sign, "Pisces")
        self.assertEqual(chart["Sun"].tropical_house, 7)
        self.assertEqual(chart["Moon"].zodiac_sign, "Aries")
        self.assertEqual(chart["Moon"].tropical_house, 8)
        
        # Verify planetary dignities
        self.assertEqual(chart["Jupiter"].dignity, "Exalted")   # Jupiter exalted in Cancer
        self.assertEqual(chart["Mars"].dignity, "Own Sign")      # Mars in Aries (own sign)
        
        # Verify active and inactive Yogas
        # Amala Yoga (benefics in 10th from lagna or moon) should be active
        self.assertTrue(yogas.get("Amala Yoga", {}).get("active"))
        # Gajakesari Yoga (Jupiter in kendra from Moon) should be active
        self.assertTrue(yogas.get("Gajakesari Yoga", {}).get("active"))
        # Malavya Yoga should be inactive (Venus is in Capricorn/5th house, not a kendra)
        self.assertFalse(yogas.get("Malavya Yoga", {}).get("active"))
        # Ruchaka Yoga should be inactive (Mars in Aries in 8th house, not a kendra)
        self.assertFalse(yogas.get("Ruchaka Yoga", {}).get("active"))

        # --- Phase 1: Shodashavarga Verification ---
        # Ensure all 16 divisional charts exist
        expected_vargas = ["D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]
        for v in expected_vargas:
            self.assertIn(v, chart["Sun"].vargas)
            
        # Verify specific vargas for Steve Jobs (in Tropical-Vedic mode)
        # Sun is at approx 335.7481 degrees (Pisces 5.7481).
        # D4 of Sun: sign_idx=11, offset=5.7481. part = 0. AstroMath.ZODIAC_SIGNS[(11 + 0*3)%12] = Pisces
        self.assertEqual(chart["Sun"].vargas["D4"], "Pisces")
        # D30 of Sun: sign_idx=11 (Even sign - Pisces). offset = 5.7481.
        # Since offset >= 5 and offset < 12, even D30 governs Gemini (ruled by Mercury).
        self.assertEqual(chart["Sun"].vargas["D30"], "Gemini")

        # --- Phase 1: Jaimini Karakas Verification ---
        # In Tropical-Vedic mode, Mars has the highest sign degree for Steve Jobs (~29.0905), making it Atmakaraka
        self.assertEqual(jaimini["Mars"]["role"], "Atmakaraka (Self/Soul)")
        self.assertEqual(jaimini["Sun"]["role"], "Darakaraka (Spouse/Partners)") # Lowest degree (~5.7481)

        # --- Phase 1: Panchanga Verification ---
        self.assertEqual(panchanga["tithi"]["name"], "Tritiya")
        self.assertEqual(panchanga["tithi"]["paksha"], "Shukla")
        self.assertEqual(panchanga["tithi"]["phase"], "Waxing")
        self.assertEqual(panchanga["nakshatra"]["name"], "Revati")
        self.assertEqual(panchanga["yoga"]["name"], "Shubha")
        self.assertEqual(panchanga["karana"]["name"], "Gara")
        self.assertEqual(panchanga["vara"]["name"], "Thursday") # Birth at 19:15 after sunrise

    def test_steve_jobs_vault_of_the_heavens_wilhelm(self):
        """
        Verify Steve Jobs chart nakshatras under Ernst Wilhelm's Vault of the Heavens system
        (Galactic Center at 0 Mula, Ayanamsa=36).
        """
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic", ayanamsa=36
        )
        self.assertEqual(panchanga["nakshatra"]["name"], "Revati")
        self.assertEqual(chart["Moon"].nakshatra, "Revati")
        self.assertEqual(chart["Mercury"].nakshatra, "Dhanishta")
        self.assertEqual(chart["Rahu"].nakshatra, "Purva Ashadha")

    def test_steve_jobs_standard_lahiri(self):
        """
        Verify Steve Jobs chart nakshatras under standard Lahiri (Ayanamsa=1).
        """
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic", ayanamsa=1
        )
        self.assertEqual(panchanga["nakshatra"]["name"], "Uttara Bhadrapada")
        self.assertEqual(chart["Moon"].nakshatra, "Uttara Bhadrapada")
        self.assertEqual(chart["Sun"].nakshatra, "Shatabhisha")
        self.assertEqual(chart["Mars"].nakshatra, "Ashwini")
        self.assertEqual(chart["Mercury"].nakshatra, "Shravana")
        self.assertEqual(chart["Rahu"].nakshatra, "Mula")

    def test_steve_jobs_raman_dasha(self):
        """
        Verify Steve Jobs chart Vimshottari Dasha under Raman Ayanamsa (Ayanamsa=3),
        where Saturn balance is ~1 year and Mercury Mahadasha starts on 1956-03-01 (1/3/1956).
        """
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic", ayanamsa=3
        )
        from astrology_engine import VimshottariDashaEngine, AstroTime
        t3 = AstroTime(1955, 2, 24, "19:15", "America/Los_Angeles", sid_mode=3)
        vd3 = VimshottariDashaEngine(t3, chart["Moon"].nakshatra, chart["Moon"].sidereal_longitude)
        merc_dasha = [d for d in vd3.dasha_periods if d["lord"] == "Mercury"][0]
        self.assertEqual(merc_dasha["start"], "1956-02-28")

        # --- Phase 1: Planetary Synthesis Verification ---
        self.assertEqual(synthesis["Sun"]["shadbala"]["level"], "Strong")
        self.assertEqual(synthesis["Sun"]["dignity"]["level"], "Neutral")
        self.assertEqual(synthesis["Sun"]["ashtakavarga"]["bindus"], 2)
        self.assertEqual(synthesis["Sun"]["ashtakavarga"]["level"], "Low Support")
        self.assertEqual(synthesis["Sun"]["takeaway"], "High Drive / Lacks Resources")

        # --- Phase 1: Planetary Aspects Verification ---
        # Parashari: Mars aspects Jupiter (4th House) and Saturn (8th House)
        mars_parashari = aspects["parashari"]["Mars"]
        mars_targets = [x["target"] for x in mars_parashari]
        self.assertIn("Jupiter", mars_targets)
        self.assertIn("Saturn", mars_targets)
        
        # Jaimini: Moon (Aries) aspects Mercury (Aquarius)
        moon_jaimini = aspects["jaimini"]["Moon"]
        moon_targets = [x["target"] for x in moon_jaimini]
        self.assertIn("Mercury", moon_targets)
        
        # Tajika: Venus aspects Saturn via Sextile (orb < 0.1)
        venus_tajika = aspects["tajika"]["Venus"]
        saturn_aspect = [x for x in venus_tajika if x["target"] == "Saturn"][0]
        self.assertEqual(saturn_aspect["aspect"], "Sextile")
        self.assertLess(saturn_aspect["orb"], 0.1)

        # --- HTMLReporter SVG Verification ---
        from astrology_engine import HTMLReporter
        import os
        json_path = os.path.join(ROOT_DIR, "profiles", "steve_jobs", "steve_jobs_astrology_profile.json")
        template_path = os.path.join(ROOT_DIR, "report_template.html")
        if os.path.exists(json_path):
            reporter = HTMLReporter(json_path, template_path)
            sudarshana_svg = reporter.generate_sudarshana_chakra_svg()
            self.assertIn("Sudarshana Chakra Tri-Wheel Chart", sudarshana_svg)
            self.assertIn("<svg", sudarshana_svg)
            self.assertIn("</svg>", sudarshana_svg)
            self.assertIn("SUDARSHANA", sudarshana_svg)

            kota_svg = reporter.generate_kota_chakra_svg()
            self.assertIn("Kota Chakra Fort Diagram", kota_svg)
            self.assertIn("STAMBHA", kota_svg)

            sbc_svg = reporter.generate_sarvatobhadra_chakra_svg()
            self.assertIn("Sarvatobhadra Chakra 81-Square Grid", sbc_svg)

            kurma_svg = reporter.generate_kurma_chakra_svg()
            self.assertIn("Kurma Chakra Tortoise Diagram", kurma_svg)

    def test_albert_einstein_sidereal(self):
        """
        Verify Albert Einstein chart in Sidereal (Everything) mode.
        """
        # Albert Einstein: Mar 14, 1879, 11:30 AM, Ulm, Germany
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1879, month=3, day=14, time_str="11:30", tz="Europe/Berlin",
            lat=48.4011, lon=9.9876, mode="Everything"
        )
        
        # Verify Lagna (Ascendant) is Gemini under Sidereal-Vedic mode with Wilhelm Ayanamsa
        self.assertEqual(local_sky.sidereal_ascendant_sign, "Gemini")
        
        # Verify Sun and Moon placements
        self.assertEqual(chart["Sun"].sidereal_sign, "Pisces")
        self.assertEqual(chart["Sun"].vedic_house, 10)
        self.assertEqual(chart["Moon"].sidereal_sign, "Scorpio")
        self.assertEqual(chart["Moon"].vedic_house, 6)
        
        # Verify Venus is exalted in Pisces
        self.assertEqual(chart["Venus"].sidereal_sign, "Pisces")
        self.assertEqual(chart["Venus"].dignity, "Exalted")
        
        # Verify active Yogas
        # Malavya Yoga (Venus exalted in 10th kendra from Gemini Lagna) should be active
        self.assertTrue(yogas.get("Malavya Yoga", {}).get("active"))
        # Amala Yoga should be active
        self.assertTrue(yogas.get("Amala Yoga", {}).get("active"))

        # --- Phase 1: Jaimini Verification ---
        # In Sidereal mode, Venus has the highest degree in sign (~28.6857) for Einstein, making it Atmakaraka
        self.assertEqual(jaimini["Venus"]["role"], "Atmakaraka (Self/Soul)")
        # Sun has the lowest degree (~5.2107), making it Darakaraka
        self.assertEqual(jaimini["Sun"]["role"], "Darakaraka (Spouse/Partners)")

        # --- Phase 1: Panchanga Verification ---
        self.assertEqual(panchanga["tithi"]["name"], "Saptami")
        self.assertEqual(panchanga["tithi"]["paksha"], "Krishna")
        self.assertEqual(panchanga["tithi"]["phase"], "Waning")
        self.assertEqual(panchanga["nakshatra"]["name"], "Jyeshtha")
        self.assertEqual(panchanga["yoga"]["name"], "Siddhi")
        self.assertEqual(panchanga["karana"]["name"], "Bava")
        # Birth at 11:30 AM local is after 6:16 AM local sunrise, so it's Friday (matching calendar day)
        self.assertEqual(panchanga["vara"]["name"], "Friday")

        # --- Phase 1: Planetary Synthesis Verification ---
        # Mars: Strong, Exalted, High Support -> Maximum Manifestation (Prime)
        self.assertEqual(synthesis["Mars"]["shadbala"]["level"], "Strong")
        self.assertEqual(synthesis["Mars"]["dignity"]["level"], "Auspicious")
        self.assertEqual(synthesis["Mars"]["ashtakavarga"]["bindus"], 7)
        self.assertEqual(synthesis["Mars"]["ashtakavarga"]["level"], "High Support")
        self.assertEqual(synthesis["Mars"]["takeaway"], "Maximum Manifestation (Prime)")

        # Venus: Strong, Exalted, Low Support -> High Drive / Lacks Resources
        self.assertEqual(synthesis["Venus"]["shadbala"]["level"], "Strong")
        self.assertEqual(synthesis["Venus"]["dignity"]["level"], "Auspicious")
        self.assertEqual(synthesis["Venus"]["ashtakavarga"]["bindus"], 3)
        self.assertEqual(synthesis["Venus"]["ashtakavarga"]["level"], "Low Support")
        self.assertEqual(synthesis["Venus"]["takeaway"], "High Drive / Lacks Resources")

        # --- Phase 1: Planetary Aspects Verification ---
        # Jaimini: Mars (Capricorn) aspects Moon (Scorpio)
        mars_jaimini = aspects["jaimini"]["Mars"]
        mars_targets = [x["target"] for x in mars_jaimini]
        self.assertIn("Moon", mars_targets)
        
        # Tajika: Venus aspects Moon via Trine
        venus_tajika = aspects["tajika"]["Venus"]
        moon_aspect = [x for x in venus_tajika if x["target"] == "Moon"][0]
        self.assertEqual(moon_aspect["aspect"], "Trine")
        self.assertLess(moon_aspect["orb"], 3.0)

    def test_barack_obama_sidereal(self):
        """
        Verify Barack Obama chart in Sidereal (Everything) mode.
        """
        # Barack Obama: Aug 4, 1961, 19:24, Honolulu, HI
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1961, month=8, day=4, time_str="19:24", tz="Pacific/Honolulu",
            lat=21.3069, lon=-157.8583, mode="Everything"
        )
        
        # Verify Lagna (Ascendant) is Capricorn under Sidereal-Vedic
        self.assertEqual(local_sky.sidereal_ascendant_sign, "Capricorn")
        
        # Verify Sun and Moon placements
        self.assertEqual(chart["Sun"].sidereal_sign, "Cancer")
        self.assertEqual(chart["Sun"].vedic_house, 7)
        self.assertEqual(chart["Moon"].sidereal_sign, "Taurus")
        self.assertEqual(chart["Moon"].vedic_house, 5)
        
        # Verify Saturn is in Capricorn (House 1)
        self.assertEqual(chart["Saturn"].sidereal_sign, "Capricorn")
        self.assertEqual(chart["Saturn"].vedic_house, 1)
        
        # Verify active Yogas
        # Sasa Yoga (Saturn in Capricorn in 1st house) should be active
        self.assertTrue(yogas.get("Sasa Yoga", {}).get("active"))

    def test_mahatma_gandhi_sidereal(self):
        """
        Verify Mahatma Gandhi chart in Sidereal (Everything) mode.
        """
        # Mahatma Gandhi: Oct 2, 1869, 07:12 AM, Porbandar, India
        # A timezone of 4.6533 accounts for the local mean time of the location
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1869, month=10, day=2, time_str="07:12", tz=4.6533,
            lat=21.6407, lon=69.6006, mode="Everything"
        )
        
        # Verify Lagna (Ascendant) is Libra
        self.assertEqual(local_sky.sidereal_ascendant_sign, "Libra")
        
        # Verify Sun and Moon placements
        self.assertEqual(chart["Sun"].sidereal_sign, "Virgo")
        self.assertEqual(chart["Sun"].vedic_house, 12)
        self.assertEqual(chart["Moon"].sidereal_sign, "Leo")
        self.assertEqual(chart["Moon"].vedic_house, 11)
        
        # Verify active Yogas
        # Malavya Yoga (Venus in Libra in 1st house kendra) should be active
        self.assertTrue(yogas.get("Malavya Yoga", {}).get("active"))
        self.assertTrue(yogas.get("Gajakesari Yoga", {}).get("active"))

    def test_avastha_engine(self):
        """
        Verify calculation of all 5 Avastha systems.
        """
        # Steve Jobs chart
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic"
        )
        
        # Test Baladi calculation for a planet
        sun_lon = chart["Sun"].sidereal_longitude
        baladi = AvasthaEngine.calculate_baladi(sun_lon)
        self.assertIn(baladi["state"], ["Bāla", "Kumāra", "Yuvā", "Vṛddha", "Mṛta"])
        self.assertIn("potency", baladi)
        
        # Test complete avasthas for all planets
        for p_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            p_obj = chart[p_name]
            avasthas = AvasthaEngine.get_planet_avasthas(p_name, p_obj, chart, local_sky.houses, "Everything")
            self.assertIn("baladi", avasthas)
            self.assertIn("jagradadi", avasthas)
            self.assertIn("diptadi", avasthas)
            self.assertIn("shayanadi", avasthas)
            self.assertIn("lajjitadi", avasthas)

    def test_llm_context_exporter(self):
        """
        Verify LLMContextExporter generates valid, compact Markdown and lean JSON.
        """
        # Steve Jobs chart
        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic"
        )
        epoch = AstroTime(1955, 2, 24, "19:15", "America/Los_Angeles")
        dasha_periods = VimshottariDashaEngine(epoch, chart["Moon"].nakshatra, chart["Moon"].sidereal_longitude).dasha_periods
        subject_profile = {
            "name": "Steve Jobs",
            "gender": "Male",
            "birth_data": {
                "date": "1955-02-24",
                "time": "19:15",
                "timezone": "America/Los_Angeles",
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        }
        transits = {
            "Sun": {"transit_sign": "Libra", "house_from_moon": 7, "is_auspicious": False},
            "Moon": {"transit_sign": "Gemini", "house_from_moon": 3, "is_auspicious": True},
            "Mars": {"transit_sign": "Leo", "house_from_moon": 5, "is_auspicious": False},
            "Mercury": {"transit_sign": "Scorpio", "house_from_moon": 8, "is_auspicious": True},
            "Jupiter": {"transit_sign": "Leo", "house_from_moon": 5, "is_auspicious": True},
            "Venus": {"transit_sign": "Scorpio", "house_from_moon": 8, "is_auspicious": True},
            "Saturn": {"transit_sign": "Aries", "house_from_moon": 1, "is_auspicious": False},
            "Rahu": {"transit_sign": "Aquarius", "house_from_moon": 11, "is_auspicious": True},
            "Ketu": {"transit_sign": "Leo", "house_from_moon": 5, "is_auspicious": False}
        }

        exporter = LLMContextExporter(
            subject_profile=subject_profile,
            chart=chart,
            local_sky=local_sky,
            report_mode="Tropical-Vedic",
            yogas=yogas,
            dasha_periods=dasha_periods,
            transits=transits,
            panchanga=panchanga,
            ashtakavarga=ashtakavarga,
            jaimini_karakas=jaimini,
            planetary_synthesis=synthesis,
            planetary_aspects=aspects
        )

        # 1. Verify Markdown generation
        md = exporter.generate_markdown()
        self.assertIn("# Natal Chart: Steve Jobs", md)
        self.assertIn("Ascendant (Lagna):", md)
        self.assertIn("Planetary Positions & Strength", md)
        self.assertIn("AI Interpretation Guide:", md)
        self.assertIn("| Planet | Sign | Placed In | Rules (Lord of) |", md)
        self.assertIn("Active Classical Yogas & Traditional Results", md)
        self.assertIn("Amala Yoga", md)
        # Verify classical results are retained
        self.assertIn("spotless", md.lower())
        self.assertIn("Key Aspects & Transits", md)
        self.assertIn("Parashari Drishti", md)
        self.assertIn("SAV Bindus", md)
        self.assertIn("D9 / D10", md)
        self.assertIn("Atmakaraka", md)
        self.assertIn("Planetary States & Ashtakavarga (Avasthas & Bindus)", md)
        self.assertIn("BAV (Planet Bindus)", md)
        self.assertIn("SAV (House Bindus)", md)
        # Verify Ascendant is in first table and follows canonical Navagraha order
        pos_section = md.split("### Planetary States & Ashtakavarga")[0]
        pos_table_rows = [line.split("|")[1].strip().split()[0] for line in pos_section.splitlines() if line.startswith("|") and not line.startswith("| Planet") and not line.startswith("|:---")]
        expected_order = ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        self.assertEqual(pos_table_rows, expected_order)

        # Verify second table contains all 9 Grahas in canonical order
        states_section = md.split("### Planetary States & Ashtakavarga")[1].split("### Active Classical Yogas")[0]
        states_table_rows = [line.split("|")[1].strip().split()[0] for line in states_section.splitlines() if line.startswith("|") and not line.startswith("| Planet") and not line.startswith("|:---")]
        expected_grahas = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        self.assertEqual(states_table_rows, expected_grahas)
        # Verify all transit planets including Saturn, Rahu, and Ketu are not truncated
        self.assertIn("Saturn: Aries (H1)", md)
        self.assertIn("Rahu: Aquarius (H11*)", md)
        self.assertIn("Ketu: Leo (H5)", md)

        # 2. Verify lean JSON generation
        lean = exporter.generate_lean_json()
        self.assertEqual(lean["subject"]["name"], "Steve Jobs")
        self.assertEqual(list(lean["planets"].keys()), ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        self.assertIn("d9", lean["ascendant"])
        self.assertIn("d10", lean["ascendant"])
        self.assertIn("Sun", lean["planets"])
        self.assertEqual(lean["planets"]["Sun"]["sign"], "Pisces")
        self.assertIn("nakshatra_pada", lean["planets"]["Sun"])
        self.assertIn("house", lean["planets"]["Sun"])
        self.assertIn("placed_in_house", lean["planets"]["Sun"])
        self.assertIn("ruled_houses", lean["planets"]["Sun"])
        self.assertIn("Darakaraka", lean["planets"]["Sun"]["karaka"])
        self.assertIn("Atmakaraka", lean["planets"]["Mars"]["karaka"])
        self.assertIn("ashtakavarga", lean["planets"]["Sun"])
        self.assertIn("bav", lean["planets"]["Sun"]["ashtakavarga"])
        self.assertIn("sav_house", lean["planets"]["Sun"]["ashtakavarga"])
        self.assertIn("avasthas", lean["planets"]["Sun"])
        self.assertTrue(len(lean["active_yogas"]) > 0)
        # Verify that yoga results are present in JSON
        first_yoga = lean["active_yogas"][0]
        self.assertIn("name", first_yoga)
        self.assertIn("results", first_yoga)
        self.assertTrue(len(first_yoga["results"]) > 0)
        self.assertIn("current_dasha", lean)
        self.assertIn("sav_bindus", lean)
        self.assertIn("parashari_aspects", lean)

    def test_retrograde_and_combust_indicators(self):
        """
        Verify that retrograde planets are marked with (R) and combust planets
        are marked with (C) in both llm_context.md and report.html outputs.
        """
        import os
        from astrology_engine import HTMLReporter

        chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects = calculate_chart_profile(
            year=1955, month=2, day=24, time_str="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic"
        )
        epoch = AstroTime(1955, 2, 24, "19:15", "America/Los_Angeles")
        dasha_periods = VimshottariDashaEngine(epoch, chart["Moon"].nakshatra, chart["Moon"].sidereal_longitude).dasha_periods
        subject_profile = {
            "name": "Steve Jobs",
            "gender": "Male",
            "birth_data": {
                "date": "1955-02-24",
                "time": "19:15",
                "timezone": "America/Los_Angeles",
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        }

        # 1. Verify retrograde planets in Markdown
        exporter = LLMContextExporter(
            subject_profile=subject_profile,
            chart=chart,
            local_sky=local_sky,
            report_mode="Tropical-Vedic",
            yogas=yogas,
            dasha_periods=dasha_periods,
            jaimini_karakas=jaimini,
            planetary_synthesis=synthesis,
            planetary_aspects=aspects
        )
        md = exporter.generate_markdown()
        self.assertIn("Mercury (R)", md)
        self.assertIn("Jupiter (R)", md)

        # 2. Simulate combust planet (Mars within 5 degrees of the Sun) and verify (C)
        sun_lon = chart["Sun"].tropical_longitude
        chart["Mars"].tropical_longitude = (sun_lon + 3.0) % 360
        synthesis["Mars"]["avasthas"]["diptadi"]["is_combust"] = True

        exporter_combust = LLMContextExporter(
            subject_profile=subject_profile,
            chart=chart,
            local_sky=local_sky,
            report_mode="Tropical-Vedic",
            yogas=yogas,
            dasha_periods=dasha_periods,
            jaimini_karakas=jaimini,
            planetary_synthesis=synthesis,
            planetary_aspects=aspects
        )
        md_combust = exporter_combust.generate_markdown()
        self.assertIn("Mars (C)", md_combust)

        # 3. Test HTMLReporter with retrograde and combust
        json_path = os.path.join(ROOT_DIR, "profiles", "steve_jobs", "steve_jobs_astrology_profile.json")
        template_path = os.path.join(ROOT_DIR, "report_template.html")
        if os.path.exists(json_path):
            reporter = HTMLReporter(json_path, template_path)
            south_svg = reporter.generate_south_chart_svg()
            self.assertIn("ME(R)", south_svg)
            self.assertIn("JU(R)", south_svg)

            north_svg = reporter.generate_north_chart_svg()
            self.assertIn("ME(R)", north_svg)
            self.assertIn("JU(R)", north_svg)

            # Mark a planet as combust and compile
            for p in reporter.chart.get("planets", []):
                if p["name"] == "Venus":
                    p["is_combust"] = True

            out_test = os.path.join(ROOT_DIR, "scratch_test_report.html")
            reporter.compile_report(out_test)
            compiled_html = Path(out_test).read_text(encoding="utf-8")
            if os.path.exists(out_test):
                os.remove(out_test)

            self.assertIn('title="Retrograde">R</span>', compiled_html)
            self.assertIn('title="Combust">C</span>', compiled_html)
            self.assertIn('Retrograde (R)', compiled_html)
            self.assertIn('Combust (C)', compiled_html)

    def test_astrology_pipeline_and_chart_result(self):
        """
        Verify that AstrologyPipeline produces a complete ChartResult
        with all attributes, valid profile dict, and export capability.
        """
        res = AstrologyPipeline.calculate(
            year=1955, month=2, day=24, hour="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic", house_system="W", ayanamsa=36,
            yogas_rules_path=ROOT_DIR / 'yogas',
            subject={"name": "Steve Jobs", "gender": "Male"}
        )
        self.assertIsInstance(res, ChartResult)
        self.assertIn("Sun", res.chart)
        self.assertIn("Moon", res.chart)
        self.assertEqual(len(res.planets_data), 9)
        self.assertEqual(res.ascendant_data["tropical_sign"], "Virgo")
        self.assertEqual(res.ascendant_data["sidereal_nakshatra"], "Uttara Phalguni")
        self.assertIn("tithi", res.panchanga)
        self.assertIn("parashari", res.planetary_aspects)

        # Verify to_profile_dict
        profile = res.to_profile_dict()
        self.assertIn("metadata", profile)
        self.assertIn("subject", profile)
        self.assertIn("astrological_chart", profile)
        self.assertIn("planetary_friendships", profile)
        self.assertEqual(profile["subject"]["name"], "Steve Jobs")

    def test_html_reporter_in_memory_and_phase3_features(self):
        """
        Verify that HTMLReporter supports in-memory dict inputs,
        compiles directly to an in-memory string without writing to disk,
        and that AspectEngine and AvasthaEngine accept local_sky and coordinate helpers.
        """
        from astrology_engine import HTMLReporter, AspectEngine, AvasthaEngine
        res = AstrologyPipeline.calculate(
            year=1955, month=2, day=24, hour="19:15", tz="America/Los_Angeles",
            lat=37.7749, lon=-122.4194, mode="Tropical-Vedic", house_system="W", ayanamsa=36,
            yogas_rules_path=ROOT_DIR / 'yogas',
            subject={"name": "Steve Jobs", "gender": "Male"}
        )
        profile_data = res.to_profile_dict()
        template_path = ROOT_DIR / "report_template.html"

        # 1. In-memory dict initialization and compilation without disk I/O
        reporter = HTMLReporter(profile_data, template_path)
        html_str = reporter.compile_report()
        self.assertIsInstance(html_str, str)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("Steve Jobs", html_str)

        # 2. AspectEngine with local_sky
        aspects_with_sky = AspectEngine.calculate_aspects(res.chart, res.mode, local_sky=res.local_sky)
        self.assertIn("parashari", aspects_with_sky)
        self.assertIn("jaimini", aspects_with_sky)
        self.assertIn("tajika", aspects_with_sky)

        # 3. AvasthaEngine._extract_lagna_longitudes
        lagna_lon, lagna_sid = AvasthaEngine._extract_lagna_longitudes(res.local_sky, False)
        self.assertAlmostEqual(lagna_lon, res.local_sky.tropical_ascendant, places=4)
        self.assertAlmostEqual(lagna_sid, res.local_sky.sidereal_ascendant, places=4)

if __name__ == '__main__':
    unittest.main()



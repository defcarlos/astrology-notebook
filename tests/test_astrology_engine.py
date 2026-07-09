import unittest
import os
import sys
import swisseph as swe

# Ensure the root directory is in the import path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from astrology_engine import (
    AstroTime,
    HouseEngine,
    ChartFactory,
    ShadbalaEngine,
    AshtakavargaEngine,
    YogaEngine,
    AstroMath
)

# Configure Swiss Ephemeris path
swe.set_ephe_path(os.path.join(ROOT_DIR, 'ephe'))

def calculate_chart_profile(year, month, day, time_str, tz, lat, lon, mode="Tropical-Vedic", house_system="W", ayanamsa=36):
    """
    Helper function to run the complete calculation pipeline for a chart,
    mirroring the calculation flow in the main notebook.
    """
    # 1. Instantiate Core Timing and House Engine
    epoch_time = AstroTime(year, month, day, time_str, tz, sid_mode=ayanamsa)
    local_sky = HouseEngine(epoch_time, lat, lon, house_system=house_system)
    
    # 2. Build Birth Chart
    chart = ChartFactory.create_chart(epoch_time, mode=mode)
    
    # 3. Cache House Placements
    for name, obj in chart.items():
        obj.tropical_house = AstroMath.get_house_placement(obj.tropical_longitude, local_sky.houses, False)
        obj.vedic_house = AstroMath.get_house_placement(obj.sidereal_longitude, local_sky.houses, True)
        
    # 4. Calculate Shadbala for classical planets
    for name, obj in chart.items():
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
        house_num = obj.vedic_house if is_sid else obj.tropical_house
        obj.shadbala = ShadbalaEngine.get_complete_shadbala(name, obj, chart, local_sky.houses, house_num, mode)
        
    # 5. Calculate Ashtakavarga
    ashtakavarga = AshtakavargaEngine.calculate_ashtakavarga(chart, local_sky, mode)
    
    # 6. Scan Yogas
    yogas_rules_path = os.path.join(ROOT_DIR, 'yogas')
    subject_profile = {"name": "Test Subject", "gender": "Male"}
    yogas = YogaEngine.scan_yogas(chart, local_sky, mode, yogas_rules_path, subject_profile)
    
    return chart, local_sky, yogas, ashtakavarga

class TestAstrologyEngine(unittest.TestCase):

    def test_steve_jobs_tropical_vedic(self):
        """
        Verify Steve Jobs chart in Tropical-Vedic mode.
        """
        # Steve Jobs: Feb 24, 1955 at 19:15, San Francisco, CA
        chart, local_sky, yogas, ashtakavarga = calculate_chart_profile(
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

    def test_albert_einstein_sidereal(self):
        """
        Verify Albert Einstein chart in Sidereal (Everything) mode.
        """
        # Albert Einstein: Mar 14, 1879, 11:30 AM, Ulm, Germany
        chart, local_sky, yogas, ashtakavarga = calculate_chart_profile(
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

    def test_barack_obama_sidereal(self):
        """
        Verify Barack Obama chart in Sidereal (Everything) mode.
        """
        # Barack Obama: Aug 4, 1961, 19:24, Honolulu, HI
        chart, local_sky, yogas, ashtakavarga = calculate_chart_profile(
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
        chart, local_sky, yogas, ashtakavarga = calculate_chart_profile(
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

if __name__ == '__main__':
    unittest.main()

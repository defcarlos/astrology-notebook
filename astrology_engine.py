import os
import json
import yaml
import hashlib
import shutil
import types
from datetime import datetime, timezone, timedelta
import swisseph as swe

# --- 1. CORE TIME & COORDINATE ENGINES (SELF-CONTAINED) ---
class AstroTime:
    def __init__(self, year, month, day, hour: float | str, tz: float | str, sid_mode: str | int = "Lahiri"):
        # Local time to UTC conversion
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.tz = tz
        self.sid_mode = sid_mode
        
        # hour is a string in format "HH:MM" (e.g. "1:18") or a float/int
        if isinstance(hour, str):
            parts = hour.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
        else:
            dec_hour_local = float(hour)
            h = int(dec_hour_local)
            m = int((dec_hour_local - h) * 60)
            s = int(round((dec_hour_local - h - m/60.0) * 3600))

        # Handle minute/second overflow
        if s >= 60:
            m += s // 60
            s %= 60
        if m >= 60:
            h += m // 60
            m %= 60

        if isinstance(tz, str):
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
            dt_naive = datetime(year, month, day, h, m, s)
            try:
                tz_obj = ZoneInfo(tz)
            except ZoneInfoNotFoundError:
                raise ZoneInfoNotFoundError(
                    f"Timezone '{tz}' was not found in the timezone database. "
                    "If you are running in Google Colab, you must install the 'tzdata' package. "
                    "You can do this by running `!pip install tzdata` in a code cell and then restarting the runtime."
                )
            dt_local = dt_naive.replace(tzinfo=tz_obj)
            dt_utc = dt_local.astimezone(timezone.utc)
            dec_hour_utc = dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
            self.jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dec_hour_utc)
        else:
            dt_local = datetime(year, month, day, h, m, s)
            dt_utc = dt_local - timedelta(hours=tz)
            dec_hour_utc = dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
            self.jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dec_hour_utc)
        
        # Configure Swiss Ephemeris Ayanamsa mode
        ayanamsas = {
            "Lahiri": swe.SIDM_LAHIRI,
            "Raman": swe.SIDM_RAMAN,
            "Fagan-Bradley": swe.SIDM_FAGAN_BRADLEY,
            "Kp": swe.SIDM_KRISHNAMURTI,
            "Usha-Shashi": swe.SIDM_USHASHASHI,
            "Yukteshwar": swe.SIDM_YUKTESHWAR,
            "Jn-Bhasin": swe.SIDM_JN_BHASIN
        }
        if isinstance(sid_mode, int):
            mode_const = sid_mode
        else:
            mode_const = ayanamsas.get(sid_mode, swe.SIDM_LAHIRI)
        swe.set_sid_mode(mode_const)

class HouseEngine:
    def __init__(self, astro_time, lat, lon, house_system="W"):
        self.jd = astro_time.jd
        self.lat = lat
        self.lon = lon
        self.house_system = house_system
        if isinstance(house_system, str):
            hsys = house_system.encode('ascii')
        elif isinstance(house_system, int):
            hsys = bytes([house_system])
        else:
            hsys = b'P'
        
        # Calculate Tropical houses
        cusps_t, asmc_t = swe.houses_ex(self.jd, lat, lon, hsys)
        self.tropical_ascendant = asmc_t[0]
        self.tropical_ascendant_sign = AstroMath.get_zodiac(self.tropical_ascendant)
        
        # Calculate Sidereal houses
        cusps_s, asmc_s = swe.houses_ex(self.jd, lat, lon, hsys, flags=swe.FLG_SIDEREAL)
        self.sidereal_ascendant = asmc_s[0]
        self.sidereal_ascendant_sign = AstroMath.get_zodiac(self.sidereal_ascendant)
        
        # Handle 12-item vs 13-item cusp tuples from different pyswisseph/pysweph versions
        t_offset = 0 if len(cusps_t) == 13 else -1
        s_offset = 0 if len(cusps_s) == 13 else -1
        
        self.houses = {}
        for h in range(1, 13):
            self.houses[h] = {
                "tropical_start": cusps_t[h + t_offset],
                "sidereal_start": cusps_s[h + s_offset]
            }
# --- 2. ASTRO MATH & DIGNITY UTILITIES ---
class AstroMath:
    ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    @classmethod
    def get_zodiac(cls, longitude):
        return cls.ZODIAC_SIGNS[int(longitude // 30) % 12]

    @classmethod
    def get_nakshatra(cls, longitude):
        return cls.NAKSHATRAS[int(longitude / 13.333333333333334) % 27]

    @classmethod
    def get_house_placement(cls, longitude, houses_dict, is_sidereal=False):
        prefix = "sidereal_start" if is_sidereal else "tropical_start"
        for h in range(1, 13):
            nxt = h + 1 if h < 12 else 1
            s, e = houses_dict[h][prefix], houses_dict[nxt][prefix]
            if (s < e and s <= longitude < e) or (s > e and (longitude >= s or longitude < e)):
                return h
        return 1

    @classmethod
    def get_degree_in_house(cls, longitude, house_num, houses_dict, is_sidereal=False):
        prefix = "sidereal_start" if is_sidereal else "tropical_start"
        cusp = houses_dict[house_num][prefix]
        diff = (longitude - cusp) % 360
        return diff

class DignityEngine:
    EXALTATION_SIGNS = {
        "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
        "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra"
    }
    DEBILITATION_SIGNS = {
        "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
        "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries"
    }
    OWN_SIGNS = {
        "Sun": ["Leo"],
        "Moon": ["Cancer"],
        "Mars": ["Aries", "Scorpio"],
        "Mercury": ["Gemini", "Virgo"],
        "Jupiter": ["Sagittarius", "Pisces"],
        "Venus": ["Taurus", "Libra"],
        "Saturn": ["Capricorn", "Aquarius"]
    }
    
    @classmethod
    def get_dignity(cls, name, sign):
        if name not in cls.OWN_SIGNS:
            return "Neutral"
        if cls.EXALTATION_SIGNS.get(name) == sign:
            return "Exalted"
        if cls.DEBILITATION_SIGNS.get(name) == sign:
            return "Debilitated"
        if sign in cls.OWN_SIGNS.get(name, []):
            return "Own Sign"
        return "Neutral"

class FriendshipEngine:
    NATURAL = {
        "Sun": {"friends": ["Moon", "Mars", "Jupiter"], "enemies": ["Venus", "Saturn"], "neutrals": ["Mercury"]},
        "Moon": {"friends": ["Sun", "Mercury"], "enemies": [], "neutrals": ["Mars", "Jupiter", "Venus", "Saturn"]},
        "Mars": {"friends": ["Sun", "Moon", "Jupiter"], "enemies": ["Mercury"], "neutrals": ["Venus", "Saturn"]},
        "Mercury": {"friends": ["Sun", "Venus"], "enemies": ["Moon"], "neutrals": ["Mars", "Jupiter", "Saturn"]},
        "Jupiter": {"friends": ["Sun", "Moon", "Mars"], "enemies": ["Mercury", "Venus"], "neutrals": ["Saturn"]},
        "Venus": {"friends": ["Mercury", "Saturn"], "enemies": ["Sun", "Moon"], "neutrals": ["Mars", "Jupiter"]},
        "Saturn": {"friends": ["Mercury", "Venus"], "enemies": ["Sun", "Moon", "Mars"], "neutrals": ["Jupiter"]}
    }

    @classmethod
    def get_panchadha_relationship(cls, p1, p2, h1, h2):
        if p1 not in cls.NATURAL or p2 not in cls.NATURAL:
            return "Sama"
            
        p1_nat = cls.NATURAL[p1]
        if p2 in p1_nat["friends"]:
            nat_score = 1
        elif p2 in p1_nat["enemies"]:
            nat_score = -1
        else:
            nat_score = 0
            
        diff = (h2 - h1) % 12
        if diff in [1, 2, 3, 9, 10, 11]:
            temp_score = 1
        else:
            temp_score = -1
            
        total = nat_score + temp_score
        mapping = {2: "Adhi Mitra", 1: "Mitra", 0: "Sama", -1: "Shatru", -2: "Adhi Shatru"}
        return mapping.get(total, "Sama")

# --- 3. VARGA & PLANET DEFINITIONS ---
class VargaEngine:
    @staticmethod
    def get_vargas(planet_obj, mode):
        if mode == "Tropical Focus":
            return {}
        lon = planet_obj.tropical_longitude if mode == "Tropical-Vedic" else planet_obj.sidereal_longitude
        return {
            "D1": VargaEngine.calculate_d1(lon),
            "D2": VargaEngine.calculate_d2(lon),
            "D3": VargaEngine.calculate_d3(lon),
            "D4": VargaEngine.calculate_d4(lon),
            "D7": VargaEngine.calculate_d7(lon),
            "D9": VargaEngine.calculate_d9(lon),
            "D10": VargaEngine.calculate_d10(lon),
            "D12": VargaEngine.calculate_d12(lon),
            "D16": VargaEngine.calculate_d16(lon),
            "D20": VargaEngine.calculate_d20(lon),
            "D24": VargaEngine.calculate_d24(lon),
            "D27": VargaEngine.calculate_d27(lon),
            "D30": VargaEngine.calculate_d30(lon),
            "D40": VargaEngine.calculate_d40(lon),
            "D45": VargaEngine.calculate_d45(lon),
            "D60": VargaEngine.calculate_d60(lon)
        }

    @staticmethod
    def calculate_d1(lon):
        return AstroMath.ZODIAC_SIGNS[int(lon // 30) % 12]

    @staticmethod
    def calculate_d2(lon):
        sign_idx = int(lon // 30) % 12
        offset = lon % 30
        if sign_idx % 2 == 0:  # Odd sign
            return "Leo" if offset < 15 else "Cancer"
        else:  # Even sign
            return "Cancer" if offset < 15 else "Leo"

    @staticmethod
    def calculate_d3(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // 10)
        return AstroMath.ZODIAC_SIGNS[(sign_idx + part * 4) % 12]

    @staticmethod
    def calculate_d4(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // 7.5)
        return AstroMath.ZODIAC_SIGNS[(sign_idx + part * 3) % 12]

    @staticmethod
    def calculate_d7(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // (30 / 7))
        start = sign_idx if sign_idx % 2 == 0 else (sign_idx + 6) % 12
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d9(lon):
        return AstroMath.ZODIAC_SIGNS[int(lon / (3 + 1/3)) % 12]

    @staticmethod
    def calculate_d10(lon):
        s_idx, p_idx = int(lon // 30), int((lon % 30) // 3)
        start = s_idx if s_idx % 2 == 0 else (s_idx + 8) % 12
        return AstroMath.ZODIAC_SIGNS[(start + p_idx) % 12]

    @staticmethod
    def calculate_d12(lon):
        return AstroMath.ZODIAC_SIGNS[(int(lon // 30) + int((lon % 30) // 2.5)) % 12]

    @staticmethod
    def calculate_d16(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // 1.875)
        if sign_idx in [0, 3, 6, 9]:  # Movable: Aries, Cancer, Libra, Capricorn
            start = 0
        elif sign_idx in [1, 4, 7, 10]:  # Fixed: Taurus, Leo, Scorpio, Aquarius
            start = 4
        else:  # Dual: Gemini, Virgo, Sagittarius, Pisces
            start = 8
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d20(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // 1.5)
        if sign_idx in [0, 3, 6, 9]:  # Movable
            start = 0
        elif sign_idx in [1, 4, 7, 10]:  # Fixed
            start = 8
        else:  # Dual
            start = 4
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d24(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // 1.25)
        if sign_idx % 2 == 0:  # Odd sign
            start = 4  # Leo
        else:  # Even sign
            start = 3  # Cancer
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d27(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // (30.0 / 27.0))
        if sign_idx in [0, 4, 8]:  # Fire
            start = 0
        elif sign_idx in [1, 5, 9]:  # Earth
            start = 9
        elif sign_idx in [2, 6, 10]:  # Air
            start = 6
        else:  # Water
            start = 3
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d30(lon):
        sign_idx = int(lon // 30) % 12
        offset = lon % 30
        if sign_idx % 2 == 0:  # Odd sign
            if offset < 5:
                return "Aries"
            elif offset < 10:
                return "Aquarius"
            elif offset < 18:
                return "Sagittarius"
            elif offset < 25:
                return "Gemini"
            else:
                return "Taurus"
        else:  # Even sign
            if offset < 5:
                return "Taurus"
            elif offset < 12:
                return "Gemini"
            elif offset < 20:
                return "Sagittarius"
            elif offset < 25:
                return "Aquarius"
            else:
                return "Aries"

    @staticmethod
    def calculate_d40(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // 0.75)
        start = 0 if sign_idx % 2 == 0 else 6
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d45(lon):
        sign_idx = int(lon // 30) % 12
        part = int((lon % 30) // (2.0 / 3.0))
        if sign_idx in [0, 3, 6, 9]:  # Movable
            start = 0
        elif sign_idx in [1, 4, 7, 10]:  # Fixed
            start = 4
        else:  # Dual
            start = 8
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d60(lon):
        return AstroMath.ZODIAC_SIGNS[(int(lon // 30) + int((lon % 30) // 0.5)) % 12]

class Planet:
    def __init__(self, name, swe_const, astro_time, mode="Everything", base_planet=None):
        self.name, self.jd = name, astro_time.jd
        self.tropical_house: int | None = None
        self.vedic_house: int | None = None
        self.shadbala: dict | None = None
        if base_planet:
            self.tropical_longitude = (base_planet.tropical_longitude + 180) % 360
            self.tropical_speed = base_planet.tropical_speed
            self.sidereal_longitude = (base_planet.sidereal_longitude + 180) % 360
            self.sidereal_speed = base_planet.sidereal_speed
        else:
            t_d = swe.calc_ut(self.jd, swe_const, swe.FLG_SPEED)[0]
            self.tropical_longitude, self.tropical_speed = t_d[0], t_d[3]
            s_d = swe.calc_ut(self.jd, swe_const, swe.FLG_SIDEREAL | swe.FLG_SPEED)[0]
            self.sidereal_longitude, self.sidereal_speed = s_d[0], s_d[3]
            
        self.zodiac_sign = AstroMath.get_zodiac(self.tropical_longitude)
        self.sidereal_sign = AstroMath.get_zodiac(self.sidereal_longitude)
        self.nakshatra = AstroMath.get_nakshatra(self.sidereal_longitude)
        self.tropical_dignity = DignityEngine.get_dignity(self.name, self.zodiac_sign)
        self.sidereal_dignity = DignityEngine.get_dignity(self.name, self.sidereal_sign)
        self.dignity = self.sidereal_dignity if mode in ["Vedic Focus", "Everything"] else self.tropical_dignity
        self.vargas = VargaEngine.get_vargas(self, mode)

class ChartFactory:
    PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE}
    @classmethod
    def create_chart(cls, astro_time, mode="Everything"):
        chart = {n: Planet(n, c, astro_time, mode) for n, c in cls.PLANETS.items()}
        rahu = chart["Rahu"]
        ketu = Planet("Ketu", None, astro_time, mode, base_planet=rahu)
        chart["Ketu"] = ketu
        return chart

# --- 4. SHADBALA CALCULATIONS ---
class ShadbalaEngine:
    EXALTATIONS = {
        "Sun": 10.0, "Moon": 33.0, "Mars": 298.0, "Mercury": 165.0,
        "Jupiter": 95.0, "Venus": 357.0, "Saturn": 200.0
    }
    LORDSHIPS = {
        "Aries": "Mars", "Scorpio": "Mars",
        "Taurus": "Venus", "Libra": "Venus",
        "Gemini": "Mercury", "Virgo": "Mercury",
        "Cancer": "Moon", "Leo": "Sun",
        "Sagittarius": "Jupiter", "Pisces": "Jupiter",
        "Capricorn": "Saturn", "Aquarius": "Saturn"
    }

    @classmethod
    def calculate_ucca_bala(cls, planet_name, longitude):
        if planet_name not in cls.EXALTATIONS:
            return 0.0
        exalt = cls.EXALTATIONS[planet_name]
        debilitation = (exalt + 180) % 360
        dist = abs(longitude - debilitation) % 360
        if dist > 180:
            dist = 360 - dist
        return round(dist / 3.0, 4)

    @classmethod
    def calculate_kendra_bala(cls, house_num):
        if house_num in [1, 4, 7, 10]:
            return 60.0
        elif house_num in [2, 5, 8, 11]:
            return 30.0
        else:
            return 15.0

    @classmethod
    def calculate_saptavargiya_bala(cls, planet_name, planet_obj, chart, houses_dict, mode):
        if planet_name not in cls.EXALTATIONS:
            return 0.0
            
        total_points = 0.0
        vargas = planet_obj.vargas
        varga_list = ["D1", "D2", "D3", "D7", "D9", "D10", "D12"]
        
        for v in varga_list:
            varga_sign = vargas.get(v)
            if not varga_sign:
                continue
            lord = cls.LORDSHIPS.get(varga_sign)
            
            if lord == planet_name:
                total_points += 30.0
            else:
                is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
                lord_planet = chart.get(lord)
                if not lord_planet:
                    continue
                h_planet = AstroMath.get_house_placement(planet_obj.sidereal_longitude if is_sid else planet_obj.tropical_longitude, houses_dict, is_sid)
                h_lord = AstroMath.get_house_placement(lord_planet.sidereal_longitude if is_sid else lord_planet.tropical_longitude, houses_dict, is_sid)
                rel = FriendshipEngine.get_panchadha_relationship(planet_name, lord, h_planet, h_lord)
                
                relationship_scores = {
                    "Adhi Mitra": 22.5, "Mitra": 15.0, "Sama": 10.0, "Shatru": 4.0, "Adhi Shatru": 2.0
                }
                total_points += relationship_scores.get(rel, 10.0)
                
        return round(total_points, 4)

    @classmethod
    def get_sthana_bala(cls, planet_name, planet_obj, chart, houses_dict, house_num, mode):
        if planet_name not in cls.EXALTATIONS:
            return {}
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
        lon = planet_obj.sidereal_longitude if is_sid else planet_obj.tropical_longitude
        
        ucca = cls.calculate_ucca_bala(planet_name, lon)
        kendra = cls.calculate_kendra_bala(house_num)
        saptavargiya = cls.calculate_saptavargiya_bala(planet_name, planet_obj, chart, houses_dict, mode)
        total = ucca + kendra + saptavargiya
        return {
            "ucca_bala": ucca,
            "kendra_bala": kendra,
            "saptavargiya_bala": saptavargiya,
            "sthana_bala_total": round(total, 4)
        }

    @classmethod
    def calculate_dig_bala(cls, planet_name, house_num):
        max_houses = {
            "Jupiter": 1, "Mercury": 1,
            "Sun": 10, "Mars": 10,
            "Saturn": 7,
            "Moon": 4, "Venus": 4
        }
        if planet_name not in max_houses:
            return 0.0
        max_h = max_houses[planet_name]
        d = min((house_num - max_h) % 12, (max_h - house_num) % 12)
        return float((6 - d) * 10)

    @classmethod
    def calculate_divaratri_bala(cls, planet_name, is_day):
        day_planets = ["Sun", "Jupiter", "Venus"]
        night_planets = ["Moon", "Mars", "Saturn"]
        if planet_name == "Mercury":
            return 60.0
        elif is_day and planet_name in day_planets:
            return 60.0
        elif not is_day and planet_name in night_planets:
            return 60.0
        return 0.0

    @classmethod
    def calculate_paksha_bala(cls, planet_name, moon_lon, sun_lon):
        if planet_name not in cls.EXALTATIONS:
            return 0.0
        diff = (moon_lon - sun_lon) % 360
        dist = 180.0 - abs(180.0 - diff)
        benefics = ["Jupiter", "Venus", "Moon", "Mercury"]
        if planet_name in benefics:
            return round(dist / 3.0, 4)
        else:
            return round(60.0 - (dist / 3.0), 4)

    @classmethod
    def calculate_cheshta_bala(cls, planet_name, speed):
        if planet_name not in cls.EXALTATIONS:
            return 0.0
        if planet_name in ["Sun", "Moon"]:
            return 30.0
        if speed < 0.0:
            return 60.0
        max_speeds = {"Mars": 1.2, "Mercury": 2.2, "Jupiter": 0.2, "Venus": 1.8, "Saturn": 0.1}
        max_s = max_speeds.get(planet_name, 1.0)
        return round(60.0 * (1.0 - min(abs(speed) / max_s, 1.0)), 4)

    @classmethod
    def calculate_naisargika_bala(cls, planet_name):
        constants = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.86, "Jupiter": 34.29, "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57}
        return constants.get(planet_name, 0.0)

    @classmethod
    def calculate_drik_bala(cls, planet_name, planet_obj, chart, mode):
        if planet_name not in cls.EXALTATIONS:
            return 0.0
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
        lon1 = planet_obj.sidereal_longitude if is_sid else planet_obj.tropical_longitude
        drik_score = 0.0
        for name, other in chart.items():
            if name == planet_name or name not in cls.EXALTATIONS:
                continue
            lon2 = other.sidereal_longitude if is_sid else other.tropical_longitude
            diff = abs(lon1 - lon2) % 360
            aspects = [0.0, 60.0, 90.0, 120.0, 180.0]
            has_aspect = False
            for asp in aspects:
                if abs(diff - asp) <= 6.0 or abs(diff - (360.0 - asp)) <= 6.0:
                    has_aspect = True
                    break
            if has_aspect:
                if name in ["Jupiter"]:
                    drik_score += 15.0
                elif name in ["Venus"]:
                    drik_score += 10.0
                elif name in ["Saturn", "Mars"]:
                    drik_score -= 10.0
        return round(drik_score, 4)

    @classmethod
    def get_complete_shadbala(cls, planet_name, planet_obj, chart, houses_dict, house_num, mode):
        sthana = cls.get_sthana_bala(planet_name, planet_obj, chart, houses_dict, house_num, mode)
        if not sthana:
            return {}
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
        dig = cls.calculate_dig_bala(planet_name, house_num)
        
        sun_obj = chart.get("Sun")
        is_day = True
        if sun_obj:
            sun_house = sun_obj.vedic_house if is_sid else sun_obj.tropical_house
            is_day = sun_house in [7, 8, 9, 10, 11, 12]
        divaratri = cls.calculate_divaratri_bala(planet_name, is_day)
        
        moon_obj = chart.get("Moon")
        paksha = 0.0
        if moon_obj and sun_obj:
            moon_lon = moon_obj.sidereal_longitude if is_sid else moon_obj.tropical_longitude
            sun_lon = sun_obj.sidereal_longitude if is_sid else sun_obj.tropical_longitude
            paksha = cls.calculate_paksha_bala(planet_name, moon_lon, sun_lon)
        kala = round(divaratri + paksha, 4)
        
        speed = planet_obj.sidereal_speed if is_sid else planet_obj.tropical_speed
        cheshta = cls.calculate_cheshta_bala(planet_name, speed)
        naisargika = cls.calculate_naisargika_bala(planet_name)
        drik = cls.calculate_drik_bala(planet_name, planet_obj, chart, mode)
        total = sthana["sthana_bala_total"] + dig + kala + cheshta + naisargika + drik
        return {
            "sthana_bala": sthana,
            "dig_bala": dig,
            "kala_bala": {
                "divaratri_bala": divaratri,
                "paksha_bala": paksha,
                "kala_bala_total": kala
            },
            "cheshta_bala": cheshta,
            "naisargika_bala": naisargika,
            "drik_bala": drik,
            "shadbala_total": round(total, 4)
        }

# --- 5. ASHTAKAVARGA ENGINE ---
class AshtakavargaEngine:
    RULES = {
        "Sun": {
            "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
            "Moon": [3, 6, 10, 11],
            "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
            "Mercury": [5, 6, 9, 11, 12],
            "Jupiter": [5, 6, 9, 11],
            "Venus": [6, 7, 12],
            "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
            "Lagna": [3, 4, 6, 10, 11, 12]
        },
        "Moon": {
            "Sun": [3, 6, 7, 8, 10, 11],
            "Moon": [1, 3, 6, 7, 10, 11],
            "Mars": [2, 3, 5, 6, 9, 10, 11],
            "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
            "Jupiter": [1, 4, 7, 8, 10, 11, 12],
            "Venus": [3, 4, 5, 7, 9, 10, 11],
            "Saturn": [3, 5, 6, 11],
            "Lagna": [3, 6, 10, 11]
        },
        "Mars": {
            "Sun": [3, 5, 6, 10, 11],
            "Moon": [3, 6, 11],
            "Mars": [1, 2, 4, 7, 8, 10, 11],
            "Mercury": [3, 5, 6, 11],
            "Jupiter": [6, 10, 11, 12],
            "Venus": [6, 8, 11, 12],
            "Saturn": [1, 4, 7, 8, 9, 10, 11],
            "Lagna": [1, 3, 6, 10, 11]
        },
        "Mercury": {
            "Sun": [5, 6, 9, 11, 12],
            "Moon": [2, 4, 6, 8, 10, 11],
            "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
            "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
            "Jupiter": [6, 8, 11, 12],
            "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
            "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
            "Lagna": [1, 2, 4, 6, 8, 10, 11]
        },
        "Jupiter": {
            "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
            "Moon": [2, 5, 7, 9, 11],
            "Mars": [1, 2, 4, 7, 8, 10, 11],
            "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
            "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
            "Venus": [2, 5, 6, 9, 10, 11],
            "Saturn": [3, 5, 6, 12],
            "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]
        },
        "Venus": {
            "Sun": [8, 11, 12],
            "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
            "Mars": [3, 5, 6, 9, 11, 12],
            "Mercury": [3, 5, 6, 9, 11],
            "Jupiter": [5, 8, 9, 10, 11],
            "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
            "Saturn": [3, 4, 5, 8, 9, 10, 11],
            "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]
        },
        "Saturn": {
            "Sun": [1, 2, 4, 7, 8, 10, 11],
            "Moon": [3, 6, 11],
            "Mars": [3, 5, 6, 10, 11, 12],
            "Mercury": [6, 8, 9, 10, 11, 12],
            "Jupiter": [5, 6, 11, 12],
            "Venus": [6, 11, 12],
            "Saturn": [3, 5, 6, 11],
            "Lagna": [1, 3, 4, 6, 10, 11]
        }
    }

    @classmethod
    def calculate_ashtakavarga(cls, chart, local_sky, mode):
        planet_signs = {}
        for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            lon = chart[name].tropical_longitude if mode in ["Tropical-Vedic", "Tropical Focus"] else chart[name].sidereal_longitude
            sign_idx = int(lon // 30) % 12
            planet_signs[name] = sign_idx
            
        lagna_sign_name = local_sky.tropical_ascendant_sign if mode in ["Tropical-Vedic", "Tropical Focus"] else local_sky.sidereal_ascendant_sign
        lagna_sign_idx = AstroMath.ZODIAC_SIGNS.index(lagna_sign_name)
        planet_signs["Lagna"] = lagna_sign_idx
        
        bav = {}
        for p_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            bav[p_name] = [0] * 12
            p_rules = cls.RULES[p_name]
            
            for sign in range(12):
                points = 0
                for ref_name, auspicious_houses in p_rules.items():
                    ref_sign_idx = planet_signs[ref_name]
                    d = (sign - ref_sign_idx) % 12 + 1
                    if d in auspicious_houses:
                        points += 1
                bav[p_name][sign] = points
                
        sav = [0] * 12
        for sign in range(12):
            sav[sign] = sum(bav[p_name][sign] for p_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"])
            
        return {
            "bav": bav,
            "sav": sav
        }

# --- 6. YOGA ENGINE ---
class YogaEngine:
    EXALTATION_SIGNS = {
        "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
        "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra"
    }
    DEBILITATION_SIGNS = {
        "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
        "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries"
    }
    OWN_SIGNS = {
        "Sun": ["Leo"],
        "Moon": ["Cancer"],
        "Mars": ["Aries", "Scorpio"],
        "Mercury": ["Gemini", "Virgo"],
        "Jupiter": ["Sagittarius", "Pisces"],
        "Venus": ["Taurus", "Libra"],
        "Saturn": ["Capricorn", "Aquarius"]
    }
    LORDSHIPS = {
        "Aries": "Mars", "Scorpio": "Mars",
        "Taurus": "Venus", "Libra": "Venus",
        "Gemini": "Mercury", "Virgo": "Mercury",
        "Cancer": "Moon", "Leo": "Sun",
        "Sagittarius": "Jupiter", "Pisces": "Jupiter",
        "Capricorn": "Saturn", "Aquarius": "Saturn"
    }

    @classmethod
    def get_rules_dignity(cls, name, lon, chart=None, is_sid=True):
        sign = AstroMath.get_zodiac(lon)
        deg = lon % 30
        
        if cls.EXALTATION_SIGNS.get(name) == sign:
            return "Exaltation"
            
        mulatrikona_ranges = {
            "Sun": ("Leo", 0, 20),
            "Moon": ("Taurus", 3, 30),
            "Mars": ("Aries", 0, 12),
            "Mercury": ("Virgo", 15, 20),
            "Jupiter": ("Sagittarius", 0, 10),
            "Venus": ("Libra", 0, 15),
            "Saturn": ("Aquarius", 0, 20)
        }
        if name in mulatrikona_ranges:
            m_sign, start, end = mulatrikona_ranges[name]
            if sign == m_sign and start <= deg < end:
                return "Mulatrikona"
                
        if sign in cls.OWN_SIGNS.get(name, []):
            return "Own"
            
        if cls.DEBILITATION_SIGNS.get(name) == sign:
            return "Debilitated"

        if chart and name in FriendshipEngine.NATURAL:
            lord = cls.LORDSHIPS.get(sign)
            if lord and lord in FriendshipEngine.NATURAL:
                h_planet = chart[name].vedic_house if is_sid else chart[name].tropical_house
                h_lord = chart[lord].vedic_house if is_sid else chart[lord].tropical_house
                rel = FriendshipEngine.get_panchadha_relationship(name, lord, h_planet, h_lord)
                if rel in ["Mitra", "Adhi Mitra"]:
                    return "Friendly"
            
        return "Neutral"

    @classmethod
    def is_unblemished(cls, planet_obj, sun_obj, is_sid):
        name = planet_obj.name
        lon = planet_obj.sidereal_longitude if is_sid else planet_obj.tropical_longitude
        sign = AstroMath.get_zodiac(lon)
        
        if cls.DEBILITATION_SIGNS.get(name) == sign:
            return False
            
        combustion_limits = {
            "Mars": 17.0,
            "Mercury": 14.0,
            "Jupiter": 11.0,
            "Venus": 10.0,
            "Saturn": 15.0
        }
        if name in combustion_limits:
            sun_lon = sun_obj.sidereal_longitude if is_sid else sun_obj.tropical_longitude
            diff = abs(lon - sun_lon) % 360
            if diff > 180:
                diff = 360 - diff
            if diff <= combustion_limits[name]:
                return False
                
        return True

    @classmethod
    def get_sign_quality(cls, lon):
        sign = AstroMath.get_zodiac(lon)
        moveable = ["Aries", "Cancer", "Libra", "Capricorn"]
        fixed = ["Taurus", "Leo", "Scorpio", "Aquarius"]
        if sign in moveable:
            return "Moveable"
        elif sign in fixed:
            return "Fixed"
        return "Dual"

    @classmethod
    def is_planet_strong(cls, planet_name, planet_obj):
        if not planet_obj.shadbala:
            return False
        total = planet_obj.shadbala.get("shadbala_total", 0)
        thresholds = {
            "Sun": 390.0, "Moon": 360.0, "Mars": 300.0, "Mercury": 420.0,
            "Jupiter": 390.0, "Venus": 330.0, "Saturn": 300.0
        }
        return total >= thresholds.get(planet_name, 300.0)

    @classmethod
    def get_ruled_houses(cls, planet_name, lagna_sign):
        if planet_name not in cls.OWN_SIGNS:
            return []
        lagna_idx = AstroMath.ZODIAC_SIGNS.index(lagna_sign)
        ruled = []
        for sign in cls.OWN_SIGNS[planet_name]:
            sign_idx = AstroMath.ZODIAC_SIGNS.index(sign)
            h = (sign_idx - lagna_idx) % 12 + 1
            ruled.append(h)
        return ruled

    @classmethod
    def get_lord_of_house(cls, house_num, lagna_sign):
        lagna_idx = AstroMath.ZODIAC_SIGNS.index(lagna_sign)
        sign_idx = (lagna_idx + house_num - 1) % 12
        sign_name = AstroMath.ZODIAC_SIGNS[sign_idx]
        return cls.LORDSHIPS[sign_name]

    @classmethod
    def get_aspecting_planets(cls, target_house, chart, is_sid):
        aspecting = []
        for name, p in chart.items():
            if name in ["Rahu", "Ketu"]:
                continue
            p_house = p.vedic_house if is_sid else p.tropical_house
            d = (target_house - p_house) % 12 + 1
            has_aspect = False
            if d == 7:
                has_aspect = True
            elif name == "Mars" and d in [4, 8]:
                has_aspect = True
            elif name == "Jupiter" and d in [5, 9]:
                has_aspect = True
            elif name == "Saturn" and d in [3, 10]:
                has_aspect = True
            if has_aspect:
                aspecting.append(name)
        return aspecting

    @classmethod
    def resolve_candidates(cls, expr, chart, lagna_sign, is_sid, bindings):
        if not expr:
            return []
        if isinstance(expr, list):
            res = []
            for item in expr:
                res.extend(cls.resolve_candidates(item, chart, lagna_sign, is_sid, bindings))
            return sorted(list(set(res)))
            
        if expr in bindings:
            return [bindings[expr]]
        if expr in chart:
            return [expr]
        if expr == "Lagna":
            return ["Lagna"]
        if expr == "Chart":
            return ["Chart"]
        if expr in ["LagnaLord", "LordOf(1)"]:
            return [cls.get_lord_of_house(1, lagna_sign)]
            
        if expr.startswith("LordOf("):
            try:
                house = int(expr[7:-1])
                return [cls.get_lord_of_house(house, lagna_sign)]
            except:
                pass
                
        if expr.startswith("DispositorOf("):
            inner = expr[13:-1]
            resolved = cls.resolve_candidates(inner, chart, lagna_sign, is_sid, bindings)
            if resolved:
                p_name = resolved[0]
                if p_name in chart:
                    lon = chart[p_name].sidereal_longitude if is_sid else chart[p_name].tropical_longitude
                    sign = AstroMath.get_zodiac(lon)
                    return [cls.LORDSHIPS[sign]]
            return []
            
        if expr.startswith("NavamsaDispositorOf("):
            inner = expr[20:-1]
            resolved = cls.resolve_candidates(inner, chart, lagna_sign, is_sid, bindings)
            if resolved:
                p_name = resolved[0]
                if p_name in chart:
                    vargas = chart[p_name].vargas
                    d9_sign = vargas.get("D9")
                    if d9_sign:
                        return [cls.LORDSHIPS[d9_sign]]
            return []
            
        if expr.startswith("ExaltationLordOf("):
            inner = expr[17:-1]
            resolved = cls.resolve_candidates(inner, chart, lagna_sign, is_sid, bindings)
            if resolved:
                p_name = resolved[0]
                exalt_sign = cls.EXALTATION_SIGNS.get(p_name)
                if exalt_sign:
                    return [cls.LORDSHIPS[exalt_sign]]
            return []
            
        if expr in ["AnyPlanet", "AllPlanets"]:
            return [n for n in chart]
        if expr in ["AnyBeneficPlanet", "AllBeneficPlanets", "BeneficPlanet"]:
            return [n for n in ["Mercury", "Venus", "Jupiter"] if n in chart]
        if expr in ["AnyMaleficPlanet", "AllMaleficPlanets"]:
            return [n for n in ["Sun", "Mars", "Saturn", "Rahu", "Ketu"] if n in chart]
        if expr == "AnyUnblemishedBenefic":
            sun = chart.get("Sun")
            return [n for n in ["Mercury", "Venus", "Jupiter"] if n in chart and cls.is_unblemished(chart[n], sun, is_sid)]
        if expr == "AnyDebilitatedPlanet":
            return [n for n in chart if cls.get_rules_dignity(n, chart[n].sidereal_longitude if is_sid else chart[n].tropical_longitude, chart, is_sid) == "Debilitated"]
        if expr == "AnyStrongPlanet":
            return [n for n in chart if cls.is_planet_strong(n, chart[n])]
            
        return []

    @classmethod
    def get_property_value(cls, cand_name, prop_name, rule, chart, lagna_sign, is_sid, bindings, subject_profile):
        if cand_name == "Chart":
            if prop_name == "birth_time":
                sun = chart.get("Sun")
                sun_house = sun.vedic_house if is_sid else sun.tropical_house
                return "Day" if sun_house in [7, 8, 9, 10, 11, 12] else "Night"
            if prop_name == "native_gender":
                if subject_profile:
                    return subject_profile.get("gender", "Male")
                return "Male"
                
        if cand_name in chart:
            p = chart[cand_name]
            if prop_name == "house":
                return p.vedic_house if is_sid else p.tropical_house
            if prop_name == "dignity":
                lon = p.sidereal_longitude if is_sid else p.tropical_longitude
                return cls.get_rules_dignity(cand_name, lon, chart, is_sid)
            if prop_name == "relative_house_to_sun":
                sun = chart.get("Sun")
                h = p.vedic_house if is_sid else p.tropical_house
                sun_h = sun.vedic_house if is_sid else sun.tropical_house
                return (h - sun_h) % 12 + 1
            if prop_name == "relative_house_to_moon":
                moon = chart.get("Moon")
                h = p.vedic_house if is_sid else p.tropical_house
                moon_h = moon.vedic_house if is_sid else moon.tropical_house
                return (h - moon_h) % 12 + 1
            if prop_name == "relative_house_to_lagna":
                return p.vedic_house if is_sid else p.tropical_house
            if prop_name == "relative_house_to_lagna_or_moon":
                h = p.vedic_house if is_sid else p.tropical_house
                moon = chart.get("Moon")
                moon_h = moon.vedic_house if is_sid else moon.tropical_house
                rel_moon = (h - moon_h) % 12 + 1
                return 10 if (h == 10 or rel_moon == 10) else 0
            if prop_name == "relative_house_to_jupiter":
                jupiter = chart.get("Jupiter")
                h = p.vedic_house if is_sid else p.tropical_house
                jup_h = jupiter.vedic_house if is_sid else jupiter.tropical_house
                return (h - jup_h) % 12 + 1
            if prop_name == "relative_house_to_target":
                t_param = rule.get("target_parameter")
                resolved = cls.resolve_candidates(t_param, chart, lagna_sign, is_sid, bindings)
                if resolved and resolved[0] in chart:
                    h = p.vedic_house if is_sid else p.tropical_house
                    t_h = chart[resolved[0]].vedic_house if is_sid else chart[resolved[0]].tropical_house
                    return (h - t_h) % 12 + 1
                return 0
            if prop_name == "aspects_target":
                t_param = rule.get("target_parameter")
                resolved = cls.resolve_candidates(t_param, chart, lagna_sign, is_sid, bindings)
                if resolved and resolved[0] in chart:
                    p_house = p.vedic_house if is_sid else p.tropical_house
                    t_house = chart[resolved[0]].vedic_house if is_sid else chart[resolved[0]].tropical_house
                    d = (t_house - p_house) % 12 + 1
                    if d == 7:
                        return True
                    if cand_name == "Mars" and d in [4, 8]:
                        return True
                    if cand_name == "Jupiter" and d in [5, 9]:
                        return True
                    if cand_name == "Saturn" and d in [3, 10]:
                        return True
                return False
            if prop_name == "is_aspected_by":
                p_house = p.vedic_house if is_sid else p.tropical_house
                return cls.get_aspecting_planets(p_house, chart, is_sid)
            if prop_name == "is_unblemished":
                sun = chart.get("Sun")
                return cls.is_unblemished(p, sun, is_sid)
            if prop_name == "is_strong":
                return cls.is_planet_strong(cand_name, p)
            if prop_name == "sign":
                lon = p.sidereal_longitude if is_sid else p.tropical_longitude
                return AstroMath.get_zodiac(lon)
            if prop_name == "sign_polarity":
                lon = p.sidereal_longitude if is_sid else p.tropical_longitude
                sign = AstroMath.get_zodiac(lon)
                idx = AstroMath.ZODIAC_SIGNS.index(sign)
                return "Odd" if idx % 2 == 0 else "Even"
            if prop_name == "sign_quality":
                lon = p.sidereal_longitude if is_sid else p.tropical_longitude
                return cls.get_sign_quality(lon)
            if prop_name == "dispositor":
                lon = p.sidereal_longitude if is_sid else p.tropical_longitude
                sign = AstroMath.get_zodiac(lon)
                return cls.LORDSHIPS[sign]
            if prop_name == "rules_house":
                return cls.get_ruled_houses(cand_name, lagna_sign)
            if prop_name == "is_different_from":
                return cand_name
                
        return None

    @classmethod
    def evaluate_operator(cls, actual, op, expected):
        if op == "EQUALS":
            return actual == expected
        if op == "NOT_EQUALS":
            return actual != expected
        if op == "IN":
            if isinstance(expected, list):
                return actual in expected
            return actual == expected
        if op == "NOT_IN":
            if isinstance(expected, list):
                return actual not in expected
            return actual != expected
        if op == "CONTAINS":
            if isinstance(actual, (list, set)):
                return expected in actual
            if isinstance(actual, str):
                return expected in actual
            return False
        return False

    @classmethod
    def evaluate_rule(cls, rule, chart, lagna_sign, is_sid, bindings, subject_profile=None):
        log_op = rule.get("logical_operator")
        
        if log_op == "INITIALIZE_TARGET":
            target_name = rule.get("target_name")
            target_val_expr = rule.get("target_value")
            exclude = rule.get("exclude", [])
            evaluate_block = rule.get("evaluate", {})
            
            candidates = cls.resolve_candidates(target_val_expr, chart, lagna_sign, is_sid, bindings)
            candidates = [c for c in candidates if c not in exclude]
            
            if not candidates:
                return False, []
                
            any_success = False
            successful_bindings = []
            for cand in candidates:
                new_bindings = bindings.copy()
                new_bindings[target_name] = cand
                success, matched_planets = cls.evaluate_rule(evaluate_block, chart, lagna_sign, is_sid, new_bindings, subject_profile)
                if success:
                    any_success = True
                    successful_bindings.extend(matched_planets)
                    successful_bindings.append(cand)
            return any_success, sorted(list(set(successful_bindings)))
            
        elif log_op is not None:
            conds = rule.get("conditions", [])
            results = []
            all_matched = []
            for cond in conds:
                success, matched = cls.evaluate_rule(cond, chart, lagna_sign, is_sid, bindings, subject_profile)
                results.append(success)
                if success or log_op in ["AND", "ALL"]:
                    all_matched.extend(matched)
                    
            if log_op in ["AND", "ALL", "EXISTS"]:
                passed = all(results) if results else False
            elif log_op == "OR":
                passed = any(results) if results else False
            elif log_op == "NOT_EXISTS":
                passed = not any(results)
            else:
                passed = False
                
            return passed, sorted(list(set(all_matched))) if passed else []
            
        else:
            # Simple condition
            target_expr = rule.get("target")
            prop_name = rule.get("property")
            op = rule.get("operator")
            expected_val = rule.get("value")
            exclude = rule.get("exclude", [])
            
            candidates = cls.resolve_candidates(target_expr, chart, lagna_sign, is_sid, bindings)
            candidates = [c for c in candidates if c not in exclude]
            
            if not candidates:
                return False, []
                
            if op == "UNIQUE_COUNT_EQUALS":
                vals = [cls.get_property_value(c, prop_name, rule, chart, lagna_sign, is_sid, bindings, subject_profile) for c in candidates]
                passed = (len(set(vals)) == expected_val)
                return passed, candidates if passed else []
                
            is_all = target_expr in ["AllPlanets", "AllBeneficPlanets", "AllMaleficPlanets"]
            matching_candidates = []
            for cand_name in candidates:
                actual_val = cls.get_property_value(cand_name, prop_name, rule, chart, lagna_sign, is_sid, bindings, subject_profile)
                if cls.evaluate_operator(actual_val, op, expected_val):
                    matching_candidates.append(cand_name)
                    
            if is_all:
                passed = (len(matching_candidates) == len(candidates) and len(candidates) > 0)
            else:
                passed = (len(matching_candidates) > 0)
                
            return passed, matching_candidates if passed else []

    @classmethod
    def scan_yogas(cls, chart, local_sky, mode, rules_path, subject_profile=None):
        import json
        import os
        
        yogas_list = []
        if os.path.isdir(rules_path):
            for fn in sorted(os.listdir(rules_path)):
                if fn.endswith('.json'):
                    path = os.path.join(rules_path, fn)
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        yogas_list.extend(data.get("yogas", []))
        else:
            if not os.path.exists(rules_path):
                raise FileNotFoundError(f"Yoga rules file not found: {rules_path}")
            with open(rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                yogas_list.extend(data.get("yogas", []))
                
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
        lagna_sign = local_sky.sidereal_ascendant_sign if is_sid else local_sky.tropical_ascendant_sign
        
        yogas_output = {}
        for y in yogas_list:
            y_name = y.get("name")
            y_desc = y.get("description")
            rules_conf = y.get("rules", {})
            
            active, matching = cls.evaluate_rule(rules_conf, chart, lagna_sign, is_sid, {}, subject_profile)
            
            log_op = rules_conf.get("logical_operator")
            details_planets = [p for p in matching if p not in ["Chart", "Lagna"]]
            
            details_str = f"Matching planets: {', '.join(details_planets)}." if active and details_planets else "No matching planets."
            if not active and log_op == "NOT_EXISTS":
                details_str = "Absence conditions not met."
            elif active and log_op == "NOT_EXISTS":
                details_str = "Absence conditions met."
                
            yogas_output[y_name] = {
                "active": active,
                "description": y_desc,
                "results": y.get("results", ""),
                "details": details_str
            }
            
        return yogas_output


# --- 7. GOCHARA TRANSIT ENGINE ---
class GocharaEngine:
    AUSPICIOUS = {
        "Sun": [3, 6, 10, 11],
        "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [3, 6, 11],
        "Mercury": [2, 4, 6, 8, 10, 11],
        "Jupiter": [2, 5, 7, 9, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Saturn": [3, 6, 11],
        "Rahu": [3, 6, 11],
        "Ketu": [3, 6, 11]
    }

    @classmethod
    def evaluate_transits(cls, natal_chart, transit_chart, mode):
        m_lon = natal_chart["Moon"].tropical_longitude if mode in ["Tropical-Vedic", "Tropical Focus"] else natal_chart["Moon"].sidereal_longitude
        m_sign_idx = int(m_lon // 30) % 12
        results = {}
        for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            if name not in transit_chart:
                continue
            t_p = transit_chart[name]
            t_lon = t_p.tropical_longitude if mode in ["Tropical-Vedic", "Tropical Focus"] else t_p.sidereal_longitude
            t_sign_idx = int(t_lon // 30) % 12
            h_from_moon = (t_sign_idx - m_sign_idx) % 12 + 1
            is_auspicious = h_from_moon in cls.AUSPICIOUS.get(name, [])
            results[name] = {
                "transit_sign": AstroMath.ZODIAC_SIGNS[t_sign_idx],
                "house_from_moon": h_from_moon,
                "is_auspicious": is_auspicious
            }
        return results

# --- 8. VIMSHOTTARI DASHA ENGINE ---
class VimshottariDashaEngine:
    DASHAS = [
        ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
        ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19),
        ("Mercury", 17)
    ]
    
    def __init__(self, astro_time, moon_nakshatra, moon_sid_lon):
        import datetime
        from dateutil.relativedelta import relativedelta
        
        sequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        dasha_years = {name: y for name, y in self.DASHAS}
        
        nak_idx = AstroMath.NAKSHATRAS.index(moon_nakshatra)
        lord_idx = nak_idx % 9
        
        nak_span = 13.333333333333334
        offset_in_nak = moon_sid_lon % nak_span
        fraction_remaining = (nak_span - offset_in_nak) / nak_span
        
        first_lord, first_years = self.DASHAS[lord_idx]
        remaining_years = fraction_remaining * first_years
        elapsed_years = first_years - remaining_years
        
        birth_dt = datetime.datetime(astro_time.year, astro_time.month, astro_time.day)
        mahadasha_start = birth_dt - datetime.timedelta(days=int(elapsed_years * 365.25))
        
        dasha_periods = []
        current_m_start = mahadasha_start
        
        m_idx = lord_idx
        for step in range(9):
            m_lord, m_years = self.DASHAS[m_idx]
            current_m_end = current_m_start + relativedelta(years=m_years)
            
            antardashas = []
            current_a_start = current_m_start
            a_sequence = [sequence[(sequence.index(m_lord) + i) % 9] for i in range(9)]
            
            for a_lord in a_sequence:
                a_years = dasha_years[a_lord]
                a_dur = (m_years * a_years) / 120.0
                a_months = int(a_dur * 12)
                a_days = int(round((a_dur * 12 - a_months) * 30.436875))
                current_a_end = current_a_start + relativedelta(months=a_months, days=a_days)
                
                pratyantardashas = []
                current_p_start = current_a_start
                p_sequence = [sequence[(sequence.index(a_lord) + i) % 9] for i in range(9)]
                
                for p_lord in p_sequence:
                    p_years = dasha_years[p_lord]
                    p_dur = (m_years * a_years * p_years) / 14400.0
                    p_months = int(p_dur * 12)
                    p_days = int(round((p_dur * 12 - p_months) * 30.436875))
                    current_p_end = current_p_start + relativedelta(months=p_months, days=p_days)
                    
                    pratyantardashas.append({
                        "lord": p_lord,
                        "start": current_p_start.strftime("%Y-%m-%d"),
                        "end": current_p_end.strftime("%Y-%m-%d"),
                        "duration_days": int(p_dur * 365.25)
                    })
                    current_p_start = current_p_end
                
                antardashas.append({
                    "lord": a_lord,
                    "start": current_a_start.strftime("%Y-%m-%d"),
                    "end": current_a_end.strftime("%Y-%m-%d"),
                    "pratyantardashas": pratyantardashas
                })
                current_a_start = current_a_end
                
            if step == 0:
                filtered_antardashas = []
                for a in antardashas:
                    a_end = datetime.datetime.strptime(a["end"], "%Y-%m-%d")
                    if a_end > birth_dt:
                        a_start = datetime.datetime.strptime(a["start"], "%Y-%m-%d")
                        if a_start < birth_dt:
                            a["start"] = birth_dt.strftime("%Y-%m-%d")
                            
                        filtered_pratyantardashas = []
                        for p in a["pratyantardashas"]:
                            p_end = datetime.datetime.strptime(p["end"], "%Y-%m-%d")
                            if p_end > birth_dt:
                                p_start = datetime.datetime.strptime(p["start"], "%Y-%m-%d")
                                if p_start < birth_dt:
                                    p["start"] = birth_dt.strftime("%Y-%m-%d")
                                filtered_pratyantardashas.append(p)
                        a["pratyantardashas"] = filtered_pratyantardashas
                        filtered_antardashas.append(a)
                antardashas = filtered_antardashas
                display_start = birth_dt
                display_duration = remaining_years
            else:
                display_start = current_m_start
                display_duration = m_years
                
            dasha_periods.append({
                "lord": m_lord,
                "start": display_start.strftime("%Y-%m-%d"),
                "end": current_m_end.strftime("%Y-%m-%d"),
                "duration_years": round(display_duration, 2),
                "antardashas": antardashas
            })
            current_m_start = current_m_end
            m_idx = (m_idx + 1) % 9
            
        self.dasha_periods = dasha_periods

class HTMLReporter:
    def __init__(self, json_path, template_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.meta = self.data.get('metadata', {})
        self.subject = self.data.get('subject', {})
        self.chart = self.data.get('astrological_chart', {})
        self.mode = self.meta.get('settings', {}).get('report_mode', 'Everything')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = f.read()

    def generate_south_chart_svg(self):
        cells = [
            (0,0), (0,1), (0,2), (0,3),
            (1,3), (2,3), (3,3), (3,2),
            (3,1), (3,0), (2,0), (1,0)
        ]
        sign_names = ["Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius"]
        
        sign_to_planets = {s: [] for s in sign_names}
        is_sid = False if self.mode in ["Tropical-Vedic", "Tropical Focus"] else True
        
        for p in self.chart.get('planets', []):
            sign_name = p.get('tropical_sign') if not is_sid else p.get('sidereal_sign')
            if sign_name in sign_to_planets:
                sign_to_planets[sign_name].append(p['name'])
                
        lagna_sign = self.chart.get('ascendant', {}).get('tropical_sign') if not is_sid else self.chart.get('ascendant', {}).get('sidereal_sign')
        
        svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-labelledby="south-chart-title" role="img">\n'
        svg += '  <title id="south-chart-title">South Indian Style Astrology Chart</title>\n'
        svg += '  <desc>A 4x4 square grid showing signs clockwise starting from Pisces at top-left. Displays Lagna and planetary positions.</desc>\n'
        svg += '  <rect width="400" height="400" fill="#161730" stroke="#2e305c" stroke-width="3"/>\n'
        svg += '  <rect x="100" y="100" width="200" height="200" fill="#0c0d21" stroke="#2e305c" stroke-width="2"/>\n'
        svg += f'  <text x="200" y="190" fill="#f3c63f" font-family="Cinzel" font-size="16" text-anchor="middle">{self.subject.get("name", "")}</text>\n'
        svg += '  <text x="200" y="220" fill="#a5a7cc" font-family="Outfit" font-size="12" text-anchor="middle">South Indian Chart</text>\n'
        
        p_abbr = {"Sun": "SU", "Moon": "MO", "Mars": "MA", "Mercury": "ME", "Jupiter": "JU", "Venus": "VE", "Saturn": "SA", "Rahu": "RA", "Ketu": "KE"}
        
        for idx, (r, c) in enumerate(cells):
            sign_name = sign_names[idx]
            x = c * 100
            y = r * 100
            svg += f'  <rect x="{x}" y="{y}" width="100" height="100" fill="none" stroke="#2e305c" stroke-width="2"/>\n'
            svg += f'  <text x="{x+50}" y="{y+20}" fill="#f3c63f" font-family="Cinzel" font-size="11" text-anchor="middle" font-weight="bold">{sign_name[:3].upper()}</text>\n'
            
            content = []
            if sign_name == lagna_sign:
                content.append("ASC")
            content.extend([p_abbr.get(p_name, p_name.upper()) for p_name in sign_to_planets.get(sign_name, [])])
            
            for i, item in enumerate(content):
                cy = y + 45 + (i * 15)
                fill_color = "#00f2fe" if item == "ASC" else "#f1f1f5"
                svg += f'  <text x="{x+50}" y="{cy}" fill="{fill_color}" font-family="Outfit" font-size="11" text-anchor="middle">{item}</text>\n'
                
        svg += '</svg>'
        return svg

    def generate_north_chart_svg(self):
        is_sid = False if self.mode in ["Tropical-Vedic", "Tropical Focus"] else True
        asc_sign_name = self.chart.get('ascendant', {}).get('tropical_sign') if not is_sid else self.chart.get('ascendant', {}).get('sidereal_sign')
        
        if asc_sign_name not in AstroMath.ZODIAC_SIGNS:
            asc_sign_idx = 1
        else:
            asc_sign_idx = AstroMath.ZODIAC_SIGNS.index(asc_sign_name) + 1
        
        house_to_planets = {h: [] for h in range(1, 13)}
        for p in self.chart.get('planets', []):
            h = p.get('tropical_house') if not is_sid else p.get('vedic_house')
            if h in house_to_planets:
                house_to_planets[h].append(p['name'])
                
        house_centers = {
            1:  {"sign": (200, 90),  "planets": (200, 135)},
            2:  {"sign": (120, 45),  "planets": (100, 75)},
            3:  {"sign": (45, 120),  "planets": (65, 100)},
            4:  {"sign": (90, 200),  "planets": (135, 200)},
            5:  {"sign": (45, 280),  "planets": (65, 300)},
            6:  {"sign": (120, 355), "planets": (100, 325)},
            7:  {"sign": (200, 310), "planets": (200, 265)},
            8:  {"sign": (280, 355), "planets": (300, 325)},
            9:  {"sign": (355, 280), "planets": (335, 300)},
            10: {"sign": (310, 200), "planets": (265, 200)},
            11: {"sign": (355, 120), "planets": (335, 100)},
            12: {"sign": (280, 45),  "planets": (300, 75)}
        }
        
        svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-labelledby="north-chart-title" role="img">\n'
        svg += '  <title id="north-chart-title">North Indian Style Astrology Chart</title>\n'
        svg += '  <desc>A diamond-based chart showing 12 houses starting counter-clockwise from House 1 in the top center diamond. Displays Lagna and planetary positions.</desc>\n'
        svg += '  <rect width="400" height="400" fill="#161730" stroke="#2e305c" stroke-width="3"/>\n'
        svg += '  <line x1="0" y1="0" x2="400" y2="400" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <line x1="400" y1="0" x2="0" y2="400" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <line x1="200" y1="0" x2="0" y2="200" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <line x1="0" y1="200" x2="200" y2="400" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <line x1="200" y1="400" x2="400" y2="200" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <line x1="400" y1="200" x2="200" y2="0" stroke="#2e305c" stroke-width="2"/>\n'
        
        p_abbr = {"Sun": "SU", "Moon": "MO", "Mars": "MA", "Mercury": "ME", "Jupiter": "JU", "Venus": "VE", "Saturn": "SA", "Rahu": "RA", "Ketu": "KE"}
        sign_abbreviations = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]
        
        for h in range(1, 13):
            sign_num = (asc_sign_idx + h - 2) % 12 + 1
            sign_name = sign_abbreviations[sign_num - 1]
            centers = house_centers[h]
            sx, sy = centers["sign"]
            svg += f'  <text x="{sx}" y="{sy}" fill="#f3c63f" font-family="Outfit" font-size="9" text-anchor="middle" font-weight="bold">{sign_name}</text>\n'
            
            content = []
            if h == 1:
                content.append("ASC")
            content.extend([p_abbr.get(p_name, p_name.upper()) for p_name in house_to_planets.get(h, [])])
            
            px, py = centers["planets"]
            planet_str = ", ".join(content)
            fill_color = "#00f2fe" if "ASC" in content else "#f1f1f5"
            svg += f'  <text x="{px}" y="{py}" fill="{fill_color}" font-family="Outfit" font-size="12" text-anchor="middle" font-weight="600">{planet_str}</text>\n'
            
        svg += '</svg>'
        return svg

    def generate_sudarshana_chakra_svg(self):
        import math
        is_sid = False if self.mode in ["Tropical-Vedic", "Tropical Focus"] else True
        
        # 1. Retrieve the base signs for Udaya (Lagna), Chandra (Moon), and Surya (Sun)
        asc_sign = self.chart.get('ascendant', {}).get('tropical_sign') if not is_sid else self.chart.get('ascendant', {}).get('sidereal_sign')
        
        # Find Moon sign
        moon_sign = "Aries"
        for p in self.chart.get('planets', []):
            if p['name'] == "Moon":
                moon_sign = p.get('tropical_sign') if not is_sid else p.get('sidereal_sign')
                break
                
        # Find Sun sign
        sun_sign = "Aries"
        for p in self.chart.get('planets', []):
            if p['name'] == "Sun":
                sun_sign = p.get('tropical_sign') if not is_sid else p.get('sidereal_sign')
                break
                
        # Get 0-based sign indexes
        asc_sign_idx = AstroMath.ZODIAC_SIGNS.index(asc_sign) if asc_sign in AstroMath.ZODIAC_SIGNS else 0
        moon_sign_idx = AstroMath.ZODIAC_SIGNS.index(moon_sign) if moon_sign in AstroMath.ZODIAC_SIGNS else 0
        sun_sign_idx = AstroMath.ZODIAC_SIGNS.index(sun_sign) if sun_sign in AstroMath.ZODIAC_SIGNS else 0
        
        # 2. Build the houses layout for the three concentric rings
        p_abbr = {"Sun": "SU", "Moon": "MO", "Mars": "MA", "Mercury": "ME", "Jupiter": "JU", "Venus": "VE", "Saturn": "SA", "Rahu": "RA", "Ketu": "KE"}
        sign_abbreviations = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]
        
        cx, cy = 200, 200
        
        # Start constructing SVG
        svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-labelledby="sudarshana-chart-title" role="img">\n'
        svg += '  <title id="sudarshana-chart-title">Sudarshana Chakra Tri-Wheel Chart</title>\n'
        svg += '  <desc>A concentric 3-ring circular chart aligning houses from Sun (inner), Moon (middle), and Ascendant (outer). Aligned counter-clockwise starting from House 1 at the top.</desc>\n'
        
        # Background
        svg += '  <rect width="400" height="400" fill="#161730" stroke="#2e305c" stroke-width="3"/>\n'
        
        # Draw Concentric Circles
        svg += f'  <circle cx="{cx}" cy="{cy}" r="195" fill="none" stroke="#2e305c" stroke-width="2"/>\n'
        svg += f'  <circle cx="{cx}" cy="{cy}" r="150" fill="none" stroke="#2e305c" stroke-width="1.5"/>\n'
        svg += f'  <circle cx="{cx}" cy="{cy}" r="105" fill="none" stroke="#2e305c" stroke-width="1.5"/>\n'
        svg += f'  <circle cx="{cx}" cy="{cy}" r="60" fill="#0c0d21" stroke="#2e305c" stroke-width="2"/>\n'
        
        # Center text labels
        svg += f'  <text x="{cx}" y="{cy-8}" fill="#f3c63f" font-family="Cinzel" font-size="10" text-anchor="middle" font-weight="bold">SUDARSHANA</text>\n'
        svg += f'  <text x="{cx}" y="{cy+8}" fill="#f3c63f" font-family="Cinzel" font-size="10" text-anchor="middle" font-weight="bold">CHAKRA</text>\n'
        
        # Helper to convert polar to cartesian
        def pt(r, deg):
            rad = math.radians(deg)
            x = cx + r * math.cos(rad)
            y = cy + r * math.sin(rad)
            return round(x, 2), round(y, 2)
            
        # Draw 12 Sector Dividers from r=60 to r=195
        for h in range(1, 13):
            angle = -90 - (h - 1) * 30
            x1, y1 = pt(60, angle)
            x2, y2 = pt(195, angle)
            svg += f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2e305c" stroke-width="1.5"/>\n'
            
        # Place house labels and data in each house sector
        for h in range(1, 13):
            # Mid-angle of the sector in degrees
            angle = -90 - (h - 0.5) * 30
            
            # --- Outer Ring: Udaya Lagna (Ascendant) ---
            outer_sign_idx = (asc_sign_idx + h - 1) % 12
            outer_sign_name = sign_abbreviations[outer_sign_idx]
            
            # Draw Sign Name at r=182
            sx, sy = pt(182, angle)
            svg += f'  <text x="{sx}" y="{sy}" fill="#a5a7cc" font-family="Outfit" font-size="7" text-anchor="middle" font-weight="600">{outer_sign_name}</text>\n'
            
            # Find planets in this sign
            outer_planets = []
            for p in self.chart.get('planets', []):
                p_sign = p.get('tropical_sign') if not is_sid else p.get('sidereal_sign')
                if p_sign == AstroMath.ZODIAC_SIGNS[outer_sign_idx]:
                    outer_planets.append(p_abbr.get(p['name'], p['name'][:2].upper()))
            if h == 1:
                outer_planets.insert(0, "ASC")
                
            # Draw Planets at r=162
            if outer_planets:
                px, py = pt(162, angle)
                fill_color = "#00f2fe" if "ASC" in outer_planets else "#f1f1f5"
                svg += f'  <text x="{px}" y="{py}" fill="{fill_color}" font-family="Outfit" font-size="8.5" text-anchor="middle" font-weight="bold">{",".join(outer_planets)}</text>\n'
                
            # --- Middle Ring: Chandra Lagna (Moon) ---
            mid_sign_idx = (moon_sign_idx + h - 1) % 12
            mid_sign_name = sign_abbreviations[mid_sign_idx]
            
            # Draw Sign Name at r=137
            sx, sy = pt(137, angle)
            svg += f'  <text x="{sx}" y="{sy}" fill="#a5a7cc" font-family="Outfit" font-size="7" text-anchor="middle" font-weight="600">{mid_sign_name}</text>\n'
            
            # Find planets in this sign
            mid_planets = []
            for p in self.chart.get('planets', []):
                p_sign = p.get('tropical_sign') if not is_sid else p.get('sidereal_sign')
                if p_sign == AstroMath.ZODIAC_SIGNS[mid_sign_idx]:
                    mid_planets.append(p_abbr.get(p['name'], p['name'][:2].upper()))
            
            # Draw Planets at r=118
            if mid_planets:
                px, py = pt(118, angle)
                svg += f'  <text x="{px}" y="{py}" fill="#f1f1f5" font-family="Outfit" font-size="8.5" text-anchor="middle" font-weight="bold">{",".join(mid_planets)}</text>\n'
                
            # --- Inner Ring: Surya Lagna (Sun) ---
            inner_sign_idx = (sun_sign_idx + h - 1) % 12
            inner_sign_name = sign_abbreviations[inner_sign_idx]
            
            # Draw Sign Name at r=92
            sx, sy = pt(92, angle)
            svg += f'  <text x="{sx}" y="{sy}" fill="#a5a7cc" font-family="Outfit" font-size="7" text-anchor="middle" font-weight="600">{inner_sign_name}</text>\n'
            
            # Find planets in this sign
            inner_planets = []
            for p in self.chart.get('planets', []):
                p_sign = p.get('tropical_sign') if not is_sid else p.get('sidereal_sign')
                if p_sign == AstroMath.ZODIAC_SIGNS[inner_sign_idx]:
                    inner_planets.append(p_abbr.get(p['name'], p['name'][:2].upper()))
                    
            # Draw Planets at r=73
            if inner_planets:
                px, py = pt(73, angle)
                svg += f'  <text x="{px}" y="{py}" fill="#f1f1f5" font-family="Outfit" font-size="8.5" text-anchor="middle" font-weight="bold">{",".join(inner_planets)}</text>\n'
                
            # Draw House Number indicators on the outermost ring edge
            hx, hy = pt(208, angle)
            svg += f'  <text x="{hx}" y="{hy}" fill="#f3c63f" font-family="Outfit" font-size="8" text-anchor="middle" font-weight="bold">H{h}</text>\n'
            
        svg += '</svg>'
        return svg

    def compile_report(self, output_path):
        import datetime
        from jinja2 import Template
        
        friendship_mapping = {
            "Adhi Mitra": "Great Friend",
            "Mitra": "Friend",
            "Sama": "Neutral",
            "Shatru": "Enemy",
            "Adhi Shatru": "Bitter Enemy"
        }
        
        # Render the template using Jinja2
        template = Template(self.template)
        rendered_html = template.render(
            meta=self.meta,
            subject=self.subject,
            chart=self.chart,
            mode=self.mode,
            friendships=self.data.get('planetary_friendships', {}),
            north_chart_svg=self.generate_north_chart_svg(),
            south_chart_svg=self.generate_south_chart_svg(),
            sudarshana_chakra_svg=self.generate_sudarshana_chakra_svg(),
            today=datetime.datetime.now().strftime("%Y-%m-%d"),
            zodiac_signs=AstroMath.ZODIAC_SIGNS,
            classical_planets=["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"],
            friendship_mapping=friendship_mapping
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)


# --- 8. JAIMINI SYSTEM ENGINES ---
class JaiminiEngine:
    KARAKA_ROLES = [
        "Atmakaraka (Self/Soul)",
        "Amatyakaraka (Career/Profession)",
        "Bhratrukaraka (Siblings/Guru)",
        "Matrukaraka (Mother)",
        "Putrakaraka (Children/Education)",
        "Jnatikaraka (Relatives/Obstacles)",
        "Darakaraka (Spouse/Partners)"
    ]

    @classmethod
    def get_karakas(cls, chart):
        classical_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        planets_with_degrees = []
        for name in classical_names:
            if name in chart:
                p = chart[name]
                # Determine which longitude to use
                lon = p.sidereal_longitude if hasattr(p, "sidereal_longitude") else p.tropical_longitude
                deg_in_sign = lon % 30
                planets_with_degrees.append((name, deg_in_sign))
        
        # Sort descending by degree
        planets_with_degrees.sort(key=lambda x: x[1], reverse=True)
        
        karakas = {}
        for idx, (name, deg) in enumerate(planets_with_degrees):
            if idx < len(cls.KARAKA_ROLES):
                karakas[name] = {
                    "role": cls.KARAKA_ROLES[idx],
                    "degree": round(deg, 4)
                }
        return karakas


# --- 9. PANCHANGA SYSTEM ENGINES ---
class PanchangaEngine:
    YOGA_NAMES = [
        "Vishkumbha", "Preeti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
        "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
        "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
        "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"
    ]
    
    TITHI_NAMES = [
        "Pratipat", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashti",
        "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
        "Trayodashi", "Chaturdashi"
    ]
    
    KARANA_NAMES = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
    
    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    @classmethod
    def calculate_panchanga(cls, astro_time, chart, lat, lon):
        import datetime
        # Moon and Sun longitudes in sidereal frame
        sun_lon = chart["Sun"].sidereal_longitude
        moon_lon = chart["Moon"].sidereal_longitude
        
        # Tithi calculation
        angle = (moon_lon - sun_lon) % 360
        t_idx = int(angle // 12)  # 0 to 29
        if t_idx == 14:
            tithi_name = "Purnima"
            paksha = "Shukla"
        elif t_idx == 29:
            tithi_name = "Amavasya"
            paksha = "Krishna"
        else:
            tithi_name = cls.TITHI_NAMES[t_idx % 15]
            paksha = "Shukla" if t_idx < 15 else "Krishna"
            
        # Nakshatra calculation (using Moon's nakshatra already in chart)
        nak_name = chart["Moon"].nakshatra
        
        # Yoga calculation
        yoga_angle = (sun_lon + moon_lon) % 360
        y_idx = int(yoga_angle // (360.0 / 27.0)) % 27
        yoga_name = cls.YOGA_NAMES[y_idx]
        
        # Karana calculation
        k_idx = int(angle // 6)  # 0 to 59
        if k_idx == 0:
            karana_name = "Kimstughna"
        elif k_idx == 57:
            karana_name = "Shakuni"
        elif k_idx == 58:
            karana_name = "Chatuspada"
        elif k_idx == 59:
            karana_name = "Naga"
        else:
            karana_name = cls.KARANA_NAMES[(k_idx - 1) % 7]
            
        # Weekday calculation with Sunrise adjustment
        b_date = datetime.date(astro_time.year, astro_time.month, astro_time.day)
        
        try:
            # Calculate local midnight Julian Day to search forward from
            midnight_time = AstroTime(astro_time.year, astro_time.month, astro_time.day, 0.0, astro_time.tz)
            # swe.CALC_RISE = 1
            res = swe.rise_trans(midnight_time.jd, swe.SUN, 1, [lon, lat, 0.0], 0.0, 0.0, swe.FLG_SWIEPH)
            sunrise_jd = res[1][0]
        except Exception:
            sunrise_jd = None
            
        if sunrise_jd is not None and astro_time.jd < sunrise_jd:
            # Born before sunrise, belongs to previous Vedic day
            vedic_date = b_date - datetime.timedelta(days=1)
        else:
            vedic_date = b_date
            
        vara_name = cls.WEEKDAYS[vedic_date.weekday()]
        
        return {
            "tithi": {
                "number": t_idx + 1,
                "name": tithi_name,
                "paksha": paksha,
                "phase": "Waxing" if paksha == "Shukla" else "Waning"
            },
            "nakshatra": {
                "name": nak_name,
                "longitude": round(moon_lon, 4)
            },
            "yoga": {
                "name": yoga_name,
                "index": y_idx + 1
            },
            "karana": {
                "number": k_idx + 1,
                "name": karana_name
            },
            "vara": {
                "name": vara_name,
                "calendar_day": cls.WEEKDAYS[b_date.weekday()]
            }
        }


# --- 10. PLANETARY SYNTHESIS ENGINE ---
class PlanetarySynthesisEngine:
    MINIMUM_REQUIREMENTS = {
        "Sun": 390.0,
        "Moon": 360.0,
        "Mars": 300.0,
        "Mercury": 420.0,
        "Jupiter": 390.0,
        "Venus": 330.0,
        "Saturn": 300.0
    }

    @classmethod
    def calculate_synthesis(cls, chart, local_sky, mode):
        """
        Synthesizes Shadbala, Dignity, and Ashtakavarga metrics for all classical planets.
        """
        synthesis_data = {}
        classical_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True

        # Extract Ashtakavarga points
        ashtakavarga = AshtakavargaEngine.calculate_ashtakavarga(chart, local_sky, mode)
        
        for name in classical_names:
            if name not in chart:
                continue
            p = chart[name]
            
            # 1. Evaluate Power (Shadbala)
            total_shadbala = p.shadbala.get("shadbala_total", 0.0) if p.shadbala else 0.0
            req_min = cls.MINIMUM_REQUIREMENTS.get(name, 0.0)
            ratio = total_shadbala / req_min if req_min > 0 else 1.0
            
            if ratio >= 1.2:
                power_level = "Very Strong"
            elif ratio >= 1.0:
                power_level = "Strong"
            elif ratio >= 0.8:
                power_level = "Moderate"
            else:
                power_level = "Weak"

            # 2. Evaluate Intent (Dignity)
            dignity = p.dignity
            if dignity in ["Exalted", "Own Sign"]:
                intent_level = "Auspicious"
            elif dignity in ["Neutral", "Friendly Sign", "Friend's Sign"]:
                intent_level = "Neutral"
            else:
                intent_level = "Challenging" # Debilitated / Enemy sign

            # 3. Evaluate Terrain (Ashtakavarga points in current sign)
            # Find the sign index (0 to 11) for the planet
            lon = p.sidereal_longitude if is_sid else p.tropical_longitude
            sign_idx = int(lon // 30) % 12
            sign_name = AstroMath.ZODIAC_SIGNS[sign_idx]
            
            # Ashtakavarga points for this planet in this sign
            bindus = 0
            # ashtakavarga format is {"bav": {planet: [12 sign values]}, "sav": [12 values]}
            bav = ashtakavarga.get("bav", {})
            if name in bav:
                bindus = bav[name][sign_idx]
                
            if bindus >= 5:
                terrain_level = "High Support"
            elif bindus == 4:
                terrain_level = "Neutral"
            else:
                terrain_level = "Low Support"

            # 4. Formulate Combined Takeaway Summary
            if power_level in ["Very Strong", "Strong"] and intent_level == "Auspicious" and terrain_level == "High Support":
                takeaway = "Maximum Manifestation (Prime)"
            elif power_level in ["Very Strong", "Strong"] and intent_level in ["Auspicious", "Neutral"] and terrain_level == "High Support":
                takeaway = "High Output / Smooth Manifestation"
            elif power_level == "Weak" and intent_level in ["Auspicious", "Neutral"] and terrain_level == "High Support":
                takeaway = "Easy Flow / Gentle Support"
            elif power_level in ["Very Strong", "Strong"] and intent_level == "Challenging" and terrain_level == "Low Support":
                takeaway = "High Friction / Heavy Lessons"
            elif power_level in ["Very Strong", "Strong"] and intent_level in ["Auspicious", "Neutral"] and terrain_level == "Low Support":
                takeaway = "High Drive / Lacks Resources"
            elif power_level == "Weak" and intent_level == "Challenging" and terrain_level == "Low Support":
                takeaway = "Suppressed / Significant Blockage"
            else:
                takeaway = "Mixed / Standard Operations"

            # Check if planet passes required minimum Shadbala
            passed = total_shadbala >= req_min

            synthesis_data[name] = {
                "shadbala": {
                    "total": round(total_shadbala, 4),
                    "required": req_min,
                    "level": power_level,
                    "passed": passed
                },
                "dignity": {
                    "value": dignity,
                    "level": intent_level
                },
                "ashtakavarga": {
                    "bindus": bindus,
                    "level": terrain_level,
                    "sign": sign_name
                },
                "takeaway": takeaway
            }
            
        return synthesis_data


# --- 11. ASPECT ENGINE ---
class AspectEngine:
    CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    
    @classmethod
    def calculate_aspects(cls, chart, mode):
        """
        Calculates Parashari, Jaimini, and Tajika aspects between all classical planets.
        """
        is_sid = False if mode in ["Tropical-Vedic", "Tropical Focus"] else True
        
        parashari = {}
        jaimini = {}
        tajika = {}
        
        # Initialize dictionaries
        for name in cls.CLASSICAL_PLANETS:
            parashari[name] = []
            jaimini[name] = []
            tajika[name] = []
            
        # 1. Parashari aspects (Graha Drishti)
        for p1 in cls.CLASSICAL_PLANETS:
            if p1 not in chart:
                continue
            obj1 = chart[p1]
            h1 = obj1.vedic_house if is_sid else obj1.tropical_house
            if not h1:
                continue
                
            for p2 in cls.CLASSICAL_PLANETS:
                if p1 == p2 or p2 not in chart:
                    continue
                obj2 = chart[p2]
                h2 = obj2.vedic_house if is_sid else obj2.tropical_house
                if not h2:
                    continue
                    
                # Calculate house distance (inclusive, 0 to 11)
                distance = (h2 - h1) % 12
                
                # Check aspect rules
                has_aspect = False
                aspect_type = ""
                
                # All planets aspect 7th house (distance = 6)
                if distance == 6:
                    has_aspect = True
                    aspect_type = "7th House (Universal)"
                    
                # Special Mars aspects (4th and 8th house, distance = 3 and 7)
                elif p1 == "Mars" and distance in [3, 7]:
                    has_aspect = True
                    aspect_type = f"{distance + 1}th House (Special)"
                    
                # Special Jupiter aspects (5th and 9th house, distance = 4 and 8)
                elif p1 == "Jupiter" and distance in [4, 8]:
                    has_aspect = True
                    aspect_type = f"{distance + 1}th House (Special)"
                    
                # Special Saturn aspects (3rd and 10th house, distance = 2 and 9)
                elif p1 == "Saturn" and distance in [2, 9]:
                    has_aspect = True
                    aspect_type = f"{distance + 1}th House (Special)"
                    
                if has_aspect:
                    parashari[p1].append({
                        "target": p2,
                        "aspect": aspect_type,
                        "distance": distance + 1
                    })
                    
        # 2. Jaimini aspects (Rashi Drishti)
        # Sign Categories: 0=Movable, 1=Fixed, 2=Dual
        movable_signs = [0, 3, 6, 9]    # Aries, Cancer, Libra, Capricorn
        fixed_signs = [1, 4, 7, 10]     # Taurus, Leo, Scorpio, Aquarius
        dual_signs = [2, 5, 8, 11]      # Gemini, Virgo, Sagittarius, Pisces
        
        for p1 in cls.CLASSICAL_PLANETS:
            if p1 not in chart:
                continue
            obj1 = chart[p1]
            lon1 = obj1.sidereal_longitude if is_sid else obj1.tropical_longitude
            s1 = int(lon1 // 30) % 12
            
            # Determine sign type
            if s1 in movable_signs:
                t1 = 0 # Movable
            elif s1 in fixed_signs:
                t1 = 1 # Fixed
            else:
                t1 = 2 # Dual
                
            for p2 in cls.CLASSICAL_PLANETS:
                if p1 == p2 or p2 not in chart:
                    continue
                obj2 = chart[p2]
                lon2 = obj2.sidereal_longitude if is_sid else obj2.tropical_longitude
                s2 = int(lon2 // 30) % 12
                
                # Check sign type
                if s2 in movable_signs:
                    t2 = 0
                elif s2 in fixed_signs:
                    t2 = 1
                else:
                    t2 = 2
                    
                has_aspect = False
                
                # Dual aspects Dual
                if t1 == 2 and t2 == 2:
                    has_aspect = True
                # Movable aspects Fixed except adjacent
                elif t1 == 0 and t2 == 1:
                    adjacent_signs = [(s1 - 1) % 12, (s1 + 1) % 12]
                    if s2 not in adjacent_signs:
                        has_aspect = True
                # Fixed aspects Movable except adjacent
                elif t1 == 1 and t2 == 0:
                    adjacent_signs = [(s1 - 1) % 12, (s1 + 1) % 12]
                    if s2 not in adjacent_signs:
                        has_aspect = True
                        
                if has_aspect:
                    jaimini[p1].append({
                        "target": p2,
                        "sign_from": AstroMath.ZODIAC_SIGNS[s1],
                        "sign_to": AstroMath.ZODIAC_SIGNS[s2]
                    })
                    
        # 3. Tajika aspects (Degree-based)
        for p1 in cls.CLASSICAL_PLANETS:
            if p1 not in chart:
                continue
            obj1 = chart[p1]
            lon1 = obj1.sidereal_longitude if is_sid else obj1.tropical_longitude
            
            for p2 in cls.CLASSICAL_PLANETS:
                if p1 == p2 or p2 not in chart:
                    continue
                obj2 = chart[p2]
                lon2 = obj2.sidereal_longitude if is_sid else obj2.tropical_longitude
                
                diff = abs(lon1 - lon2) % 360
                diff = min(diff, 360.0 - diff)
                
                aspects = {
                    "Conjunction": 0.0,
                    "Sextile": 60.0,
                    "Square": 90.0,
                    "Trine": 120.0,
                    "Opposition": 180.0
                }
                
                for asp_name, val in aspects.items():
                    orb = abs(diff - val)
                    if orb <= 6.0:
                        # Tajika relationship category
                        if asp_name in ["Sextile", "Trine"]:
                            nature = "Friendly (Mitra)"
                        elif asp_name in ["Square", "Opposition"]:
                            nature = "Hostile (Shatru)"
                        else:
                            nature = "Neutral (Sama)"
                            
                        tajika[p1].append({
                            "target": p2,
                            "aspect": asp_name,
                            "nature": nature,
                            "orb": round(orb, 4),
                            "angle": round(diff, 4)
                        })
                        break
                        
        return {
            "parashari": parashari,
            "jaimini": jaimini,
            "tajika": tajika
        }



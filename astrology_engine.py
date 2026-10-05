from __future__ import annotations

import copy
import json
import math
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import swisseph as swe

# Thread lock for Swiss Ephemeris C-level global state (Python 3.14 free-threading safety)
_swe_lock = threading.Lock()

# Auto-configure default Swiss Ephemeris path if local 'ephe' directory exists
_default_ephe = Path(__file__).resolve().parent / "ephe"
if _default_ephe.exists():
    with _swe_lock:
        swe.set_ephe_path(str(_default_ephe))

# PEP 695 type aliases (Python 3.12+)
type PlanetMap = dict[str, Planet]
type HouseMap = dict[int, dict[str, float]]
type AspectMap = dict[str, list[dict[str, Any]]]
type AvasthaMap = dict[str, Any]

# --- 1. CORE TIME & COORDINATE ENGINES (SELF-CONTAINED) ---
class AstroTime:
    def __init__(self, year: int, month: int, day: int, hour: float | str, tz: float | str, sid_mode: str | int = "Lahiri") -> None:
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
            dt_naive = datetime(year, month, day, h, m, s)
            try:
                tz_obj = ZoneInfo(tz)
            except ZoneInfoNotFoundError as e:
                raise ZoneInfoNotFoundError(
                    f"Timezone '{tz}' was not found in the timezone database. "
                    "If you are running in Google Colab, you must install the 'tzdata' package. "
                    "You can do this by running `!pip install tzdata` in a code cell and then restarting the runtime."
                ) from e
            dt_local = dt_naive.replace(tzinfo=tz_obj)
            dt_utc = dt_local.astimezone(timezone.utc)
            dec_hour_utc = dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
            self.jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dec_hour_utc)
        else:
            dt_local = datetime(year, month, day, h, m, s)
            dt_utc = dt_local - timedelta(hours=tz)
            dec_hour_utc = dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
            self.jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dec_hour_utc)
        
        # Configure Swiss Ephemeris Ayanamsa mode (thread-synchronized for Python 3.14 free-threading)
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
        with _swe_lock:
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
        
        with _swe_lock:
            # Calculate Tropical houses
            cusps_t, asmc_t = swe.houses_ex(self.jd, lat, lon, hsys)
            # Calculate Sidereal houses
            cusps_s, asmc_s = swe.houses_ex(self.jd, lat, lon, hsys, flags=swe.FLG_SIDEREAL)
        self.tropical_ascendant = asmc_t[0]
        self.tropical_ascendant_sign = AstroMath.get_zodiac(self.tropical_ascendant)
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
    SIGN_SPAN: float = 30.0
    NAKSHATRA_SPAN: float = 360.0 / 27.0  # 13.333333333333334 degrees (13° 20')
    PADA_SPAN: float = 360.0 / 108.0      # 3.3333333333333335 degrees (3° 20')
    COMBUSTION_ORB: float = 8.0

    ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

    @classmethod
    def is_sidereal_mode(cls, mode: str) -> bool:
        """Returns True if the calculation mode uses sidereal zodiac for planets/ascendant."""
        return mode not in ["Tropical-Vedic", "Tropical Focus"]

    @classmethod
    def get_sign_and_degree(cls, longitude: float) -> tuple[int, float]:
        """Returns (sign_index [0-11], degree_within_sign [0.0-30.0))."""
        sign_idx, deg_in_sign = divmod(longitude % 360.0, cls.SIGN_SPAN)
        return int(sign_idx), deg_in_sign

    @classmethod
    def get_zodiac(cls, longitude: float) -> str:
        return cls.ZODIAC_SIGNS[int(longitude // cls.SIGN_SPAN) % 12]

    @classmethod
    def get_nakshatra(cls, longitude: float) -> str:
        return cls.NAKSHATRAS[int((longitude % 360.0) / cls.NAKSHATRA_SPAN) % 27]

    @classmethod
    def get_nakshatra_pada(cls, longitude: float) -> int:
        return int((longitude % 360.0) / cls.PADA_SPAN) % 4 + 1

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
        lon = planet_obj.get_longitude(mode != "Tropical-Vedic")
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
        return AstroMath.get_zodiac(lon)

    @staticmethod
    def calculate_d2(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        if sign_idx % 2 == 0:  # Odd sign
            return "Leo" if offset < 15 else "Cancer"
        else:  # Even sign
            return "Cancer" if offset < 15 else "Leo"

    @staticmethod
    def calculate_d3(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // 10)
        return AstroMath.ZODIAC_SIGNS[(sign_idx + part * 4) % 12]

    @staticmethod
    def calculate_d4(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // 7.5)
        return AstroMath.ZODIAC_SIGNS[(sign_idx + part * 3) % 12]

    @staticmethod
    def calculate_d7(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // (30 / 7))
        start = sign_idx if sign_idx % 2 == 0 else (sign_idx + 6) % 12
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d9(lon):
        return AstroMath.ZODIAC_SIGNS[int(lon / (3 + 1/3)) % 12]

    @staticmethod
    def calculate_d10(lon):
        s_idx, offset = AstroMath.get_sign_and_degree(lon)
        p_idx = int(offset // 3)
        start = s_idx if s_idx % 2 == 0 else (s_idx + 8) % 12
        return AstroMath.ZODIAC_SIGNS[(start + p_idx) % 12]

    @staticmethod
    def calculate_d12(lon):
        s_idx, offset = AstroMath.get_sign_and_degree(lon)
        return AstroMath.ZODIAC_SIGNS[(s_idx + int(offset // 2.5)) % 12]

    @staticmethod
    def calculate_d16(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // 1.875)
        if sign_idx in [0, 3, 6, 9]:  # Movable: Aries, Cancer, Libra, Capricorn
            start = 0
        elif sign_idx in [1, 4, 7, 10]:  # Fixed: Taurus, Leo, Scorpio, Aquarius
            start = 4
        else:  # Dual: Gemini, Virgo, Sagittarius, Pisces
            start = 8
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d20(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // 1.5)
        if sign_idx in [0, 3, 6, 9]:  # Movable
            start = 0
        elif sign_idx in [1, 4, 7, 10]:  # Fixed
            start = 8
        else:  # Dual
            start = 4
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d24(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // 1.25)
        start = 4 if sign_idx % 2 == 0 else 3  # Odd: Leo (4), Even: Cancer (3)
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d27(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // (30.0 / 27.0))
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
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
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
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // 0.75)
        start = 0 if sign_idx % 2 == 0 else 6
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d45(lon):
        sign_idx, offset = AstroMath.get_sign_and_degree(lon)
        part = int(offset // (2.0 / 3.0))
        if sign_idx in [0, 3, 6, 9]:  # Movable
            start = 0
        elif sign_idx in [1, 4, 7, 10]:  # Fixed
            start = 4
        else:  # Dual
            start = 8
        return AstroMath.ZODIAC_SIGNS[(start + part) % 12]

    @staticmethod
    def calculate_d60(lon):
        s_idx, offset = AstroMath.get_sign_and_degree(lon)
        return AstroMath.ZODIAC_SIGNS[(s_idx + int(offset // 0.5)) % 12]

@dataclass(slots=True)
class Planet:
    name: str
    tropical_longitude: float = 0.0
    sidereal_longitude: float = 0.0
    tropical_speed: float = 0.0
    sidereal_speed: float = 0.0
    zodiac_sign: str = ""
    sidereal_sign: str = ""
    nakshatra: str = ""
    dignity: str = "Neutral"
    tropical_dignity: str = "Neutral"
    sidereal_dignity: str = "Neutral"
    vargas: dict[str, str] = field(default_factory=dict)
    tropical_house: int | None = None
    vedic_house: int | None = None
    shadbala: dict[str, Any] | None = None
    avasthas: dict[str, Any] = field(default_factory=dict)
    jd: float = 0.0

    def __init__(
        self,
        name: str,
        tropical_longitude: Any = 0.0,
        sidereal_longitude: Any = 0.0,
        *args,
        mode: str = "Everything",
        base_planet: Planet | None = None,
        **kwargs
    ) -> None:
        self.name = name
        self.tropical_house = kwargs.get("tropical_house", None)
        self.vedic_house = kwargs.get("vedic_house", None)
        self.shadbala = kwargs.get("shadbala", None)
        self.avasthas = kwargs.get("avasthas", {})
        self.vargas = kwargs.get("vargas", {})

        if isinstance(sidereal_longitude, AstroTime):
            # Legacy constructor invocation: Planet(name, swe_const, astro_time, mode, base_planet)
            swe_const = tropical_longitude
            astro_time = sidereal_longitude
            mode_val = args[0] if args else mode
            base_p = args[1] if len(args) > 1 else base_planet
            self.jd = astro_time.jd
            if base_p:
                self.tropical_longitude = (base_p.tropical_longitude + 180.0) % 360.0
                self.tropical_speed = base_p.tropical_speed
                self.sidereal_longitude = (base_p.sidereal_longitude + 180.0) % 360.0
                self.sidereal_speed = base_p.sidereal_speed
            else:
                with _swe_lock:
                    t_d = swe.calc_ut(self.jd, swe_const, swe.FLG_SPEED)[0]
                    s_d = swe.calc_ut(self.jd, swe_const, swe.FLG_SIDEREAL | swe.FLG_SPEED)[0]
                self.tropical_longitude, self.tropical_speed = t_d[0], t_d[3]
                self.sidereal_longitude, self.sidereal_speed = s_d[0], s_d[3]

            self.zodiac_sign = AstroMath.get_zodiac(self.tropical_longitude)
            self.sidereal_sign = AstroMath.get_zodiac(self.sidereal_longitude)
            self.nakshatra = AstroMath.get_nakshatra(self.sidereal_longitude)
            self.tropical_dignity = DignityEngine.get_dignity(self.name, self.zodiac_sign)
            self.sidereal_dignity = DignityEngine.get_dignity(self.name, self.sidereal_sign)
            self.dignity = self.sidereal_dignity if mode_val in ["Vedic Focus", "Everything"] else self.tropical_dignity
            self.vargas = VargaEngine.get_vargas(self, mode_val)
        else:
            # Dataclass initialization
            self.tropical_longitude = float(tropical_longitude)
            self.sidereal_longitude = float(sidereal_longitude)
            self.tropical_speed = float(kwargs.get("tropical_speed", 0.0))
            self.sidereal_speed = float(kwargs.get("sidereal_speed", 0.0))
            self.zodiac_sign = kwargs.get("zodiac_sign") or AstroMath.get_zodiac(self.tropical_longitude)
            self.sidereal_sign = kwargs.get("sidereal_sign") or AstroMath.get_zodiac(self.sidereal_longitude)
            self.nakshatra = kwargs.get("nakshatra") or AstroMath.get_nakshatra(self.sidereal_longitude)
            self.tropical_dignity = kwargs.get("tropical_dignity") or DignityEngine.get_dignity(self.name, self.zodiac_sign)
            self.sidereal_dignity = kwargs.get("sidereal_dignity") or DignityEngine.get_dignity(self.name, self.sidereal_sign)
            self.dignity = kwargs.get("dignity") or (self.sidereal_dignity if mode in ["Vedic Focus", "Everything"] else self.tropical_dignity)
            self.jd = float(kwargs.get("jd", 0.0))
            if not self.vargas:
                self.vargas = VargaEngine.get_vargas(self, mode)

    @classmethod
    def from_ephemeris(
        cls,
        name: str,
        swe_const: int | None,
        astro_time: AstroTime,
        mode: str = "Everything",
        base_planet: Planet | None = None
    ) -> Planet:
        """Factory method to calculate and instantiate a Planet directly from Swiss Ephemeris."""
        return cls(name, swe_const, astro_time, mode, base_planet=base_planet)

    def get_longitude(self, mode_or_is_sid: str | bool) -> float:
        """Returns sidereal or tropical longitude depending on mode name or boolean flag."""
        is_sid = mode_or_is_sid if isinstance(mode_or_is_sid, bool) else AstroMath.is_sidereal_mode(mode_or_is_sid)
        return self.sidereal_longitude if is_sid else self.tropical_longitude

    def get_house(self, mode_or_is_sid: str | bool) -> int | None:
        """Returns vedic or tropical house number depending on mode name or boolean flag."""
        is_sid = mode_or_is_sid if isinstance(mode_or_is_sid, bool) else AstroMath.is_sidereal_mode(mode_or_is_sid)
        return self.vedic_house if is_sid else self.tropical_house

    def get_sign(self, mode_or_is_sid: str | bool) -> str:
        """Returns sidereal sign or tropical zodiac sign depending on mode name or boolean flag."""
        is_sid = mode_or_is_sid if isinstance(mode_or_is_sid, bool) else AstroMath.is_sidereal_mode(mode_or_is_sid)
        return self.sidereal_sign if is_sid else self.zodiac_sign

    def get_speed(self, mode_or_is_sid: str | bool) -> float:
        """Returns sidereal or tropical daily motion speed."""
        is_sid = mode_or_is_sid if isinstance(mode_or_is_sid, bool) else AstroMath.is_sidereal_mode(mode_or_is_sid)
        return self.sidereal_speed if is_sid else self.tropical_speed

    def get_degree_in_sign(self, mode_or_is_sid: str | bool) -> float:
        """Returns degree within the active sign (0.0 to 30.0)."""
        lon = self.get_longitude(mode_or_is_sid)
        return lon % AstroMath.SIGN_SPAN


class ChartFactory:
    PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE}
    @classmethod
    def create_chart(cls, astro_time, mode="Everything"):
        chart = {n: Planet.from_ephemeris(n, c, astro_time, mode) for n, c in cls.PLANETS.items()}
        rahu = chart["Rahu"]
        ketu = Planet.from_ephemeris("Ketu", None, astro_time, mode, base_planet=rahu)
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
                is_sid = AstroMath.is_sidereal_mode(mode)
                lord_planet = chart.get(lord)
                if not lord_planet:
                    continue
                h_planet = planet_obj.get_house(is_sid) or AstroMath.get_house_placement(planet_obj.get_longitude(is_sid), houses_dict, is_sid)
                h_lord = lord_planet.get_house(is_sid) or AstroMath.get_house_placement(lord_planet.get_longitude(is_sid), houses_dict, is_sid)
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
        is_sid = AstroMath.is_sidereal_mode(mode)
        lon = planet_obj.get_longitude(is_sid)
        
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
        is_sid = AstroMath.is_sidereal_mode(mode)
        lon1 = planet_obj.get_longitude(is_sid)
        drik_score = 0.0
        for name, other in chart.items():
            if name == planet_name or name not in cls.EXALTATIONS:
                continue
            lon2 = other.get_longitude(is_sid)
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
        is_sid = AstroMath.is_sidereal_mode(mode)
        dig = cls.calculate_dig_bala(planet_name, house_num)
        
        sun_obj = chart.get("Sun")
        is_day = True
        if sun_obj:
            sun_house = sun_obj.get_house(is_sid)
            is_day = sun_house in [7, 8, 9, 10, 11, 12]
        divaratri = cls.calculate_divaratri_bala(planet_name, is_day)
        
        moon_obj = chart.get("Moon")
        paksha = 0.0
        if moon_obj and sun_obj:
            moon_lon = moon_obj.get_longitude(is_sid)
            sun_lon = sun_obj.get_longitude(is_sid)
            paksha = cls.calculate_paksha_bala(planet_name, moon_lon, sun_lon)
        kala = round(divaratri + paksha, 4)
        
        speed = planet_obj.get_speed(is_sid)
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
        is_sid = AstroMath.is_sidereal_mode(mode)
        planet_signs = {}
        for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            lon = chart[name].get_longitude(is_sid)
            sign_idx, _ = AstroMath.get_sign_and_degree(lon)
            planet_signs[name] = sign_idx
            
        lagna_sign_name = local_sky.sidereal_ascendant_sign if is_sid else local_sky.tropical_ascendant_sign
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
            except (ValueError, IndexError):
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
            p_house = p.get_house(is_sid)
            p_lon = p.get_longitude(is_sid)

            if prop_name == "house":
                return p_house
            if prop_name == "dignity":
                return cls.get_rules_dignity(cand_name, p_lon, chart, is_sid)
            if prop_name == "relative_house_to_sun":
                sun = chart.get("Sun")
                return (p_house - sun.get_house(is_sid)) % 12 + 1 if (sun and p_house) else 0
            if prop_name == "relative_house_to_moon":
                moon = chart.get("Moon")
                return (p_house - moon.get_house(is_sid)) % 12 + 1 if (moon and p_house) else 0
            if prop_name == "relative_house_to_lagna":
                return p_house
            if prop_name == "relative_house_to_lagna_or_moon":
                moon = chart.get("Moon")
                rel_moon = (p_house - moon.get_house(is_sid)) % 12 + 1 if (moon and p_house) else 0
                return 10 if (p_house == 10 or rel_moon == 10) else 0
            if prop_name == "relative_house_to_jupiter":
                jupiter = chart.get("Jupiter")
                return (p_house - jupiter.get_house(is_sid)) % 12 + 1 if (jupiter and p_house) else 0
            if prop_name == "relative_house_to_target":
                t_param = rule.get("target_parameter")
                resolved = cls.resolve_candidates(t_param, chart, lagna_sign, is_sid, bindings)
                if resolved and resolved[0] in chart and p_house:
                    t_h = chart[resolved[0]].get_house(is_sid)
                    return (p_house - t_h) % 12 + 1 if t_h else 0
                return 0
            if prop_name == "aspects_target":
                t_param = rule.get("target_parameter")
                resolved = cls.resolve_candidates(t_param, chart, lagna_sign, is_sid, bindings)
                if resolved and resolved[0] in chart and p_house:
                    t_house = chart[resolved[0]].get_house(is_sid)
                    if t_house:
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
                return cls.get_aspecting_planets(p_house, chart, is_sid) if p_house else []
            if prop_name == "is_unblemished":
                sun = chart.get("Sun")
                return cls.is_unblemished(p, sun, is_sid)
            if prop_name == "is_strong":
                return cls.is_planet_strong(cand_name, p)
            if prop_name == "sign":
                return AstroMath.get_zodiac(p_lon)
            if prop_name == "sign_polarity":
                sign = AstroMath.get_zodiac(p_lon)
                idx = AstroMath.ZODIAC_SIGNS.index(sign)
                return "Odd" if idx % 2 == 0 else "Even"
            if prop_name == "sign_quality":
                return cls.get_sign_quality(p_lon)
            if prop_name == "dispositor":
                sign = AstroMath.get_zodiac(p_lon)
                return cls.LORDSHIPS[sign]
            if prop_name == "rules_house":
                return cls.get_ruled_houses(cand_name, lagna_sign)
            if prop_name == "is_different_from":
                return cand_name
                
        return None

    @classmethod
    def evaluate_operator(cls, actual: Any, op: str, expected: Any) -> bool:
        match op:
            case "EQUALS":
                return actual == expected
            case "NOT_EQUALS":
                return actual != expected
            case "IN":
                return actual in expected if isinstance(expected, list) else actual == expected
            case "NOT_IN":
                return actual not in expected if isinstance(expected, list) else actual != expected
            case "CONTAINS":
                return expected in actual if isinstance(actual, (list, set, str)) else False
            case _:
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
    def scan_yogas(cls, chart, local_sky, mode: str, rules_path: str | Path, subject_profile: dict | None = None) -> dict[str, Any]:
        rules_p = Path(rules_path)
        yogas_list = []
        if rules_p.is_dir():
            for p in sorted(rules_p.glob("*.json")):
                data = json.loads(p.read_text(encoding="utf-8"))
                yogas_list.extend(data.get("yogas", []))
        elif rules_p.is_file():
            data = json.loads(rules_p.read_text(encoding="utf-8"))
            yogas_list.extend(data.get("yogas", []))
        else:
            raise FileNotFoundError(f"Yoga rules file not found: {rules_path}")
                
        is_sid = AstroMath.is_sidereal_mode(mode)
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
        is_sid = AstroMath.is_sidereal_mode(mode)
        m_lon = natal_chart["Moon"].get_longitude(is_sid)
        m_sign_idx, _ = AstroMath.get_sign_and_degree(m_lon)
        results = {}
        for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            if name not in transit_chart:
                continue
            t_p = transit_chart[name]
            t_lon = t_p.get_longitude(is_sid)
            t_sign_idx, _ = AstroMath.get_sign_and_degree(t_lon)
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
        sequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        dasha_years = {name: y for name, y in self.DASHAS}
        
        nak_idx = AstroMath.NAKSHATRAS.index(moon_nakshatra)
        lord_idx = nak_idx % 9
        
        nak_span = 13.333333333333334
        offset_in_nak = moon_sid_lon % nak_span
        fraction_elapsed = offset_in_nak / nak_span
        fraction_remaining = 1.0 - fraction_elapsed
        
        first_lord, first_years = self.DASHAS[lord_idx]
        elapsed_years = fraction_elapsed * first_years
        remaining_years = fraction_remaining * first_years
        
        # Parse birth datetime with exact time
        h = getattr(astro_time, 'h', 0)
        m = getattr(astro_time, 'm', 0)
        s = getattr(astro_time, 's', 0)
        if hasattr(astro_time, 'hour') and isinstance(astro_time.hour, str) and ':' in astro_time.hour:
            parts = astro_time.hour.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            
        birth_dt = datetime(astro_time.year, astro_time.month, astro_time.day, h, m, s)
        
        # True start of the first Mahadasha before birth
        first_m_start = birth_dt - timedelta(days=elapsed_years * 365.25)
        
        dasha_periods = []
        current_m_start = first_m_start
        
        for step in range(9):
            m_idx = (lord_idx + step) % 9
            m_lord, m_years = self.DASHAS[m_idx]
            eff_m_years = remaining_years if step == 0 else float(m_years)
                
            m_dur_days = m_years * 365.25
            current_m_end = current_m_start + timedelta(days=m_dur_days)
            
            antardashas = []
            current_a_start = current_m_start
            a_sequence = [sequence[(sequence.index(m_lord) + i) % 9] for i in range(9)]
            
            for a_lord in a_sequence:
                a_years = dasha_years[a_lord]
                a_dur_days = (m_years * a_years / 120.0) * 365.25
                current_a_end = current_a_start + timedelta(days=a_dur_days)
                
                pratyantardashas = []
                current_p_start = current_a_start
                p_sequence = [sequence[(sequence.index(a_lord) + i) % 9] for i in range(9)]
                
                for p_lord in p_sequence:
                    p_dur_days = (m_years * a_years * dasha_years[p_lord] / 14400.0) * 365.25
                    current_p_end = current_p_start + timedelta(days=p_dur_days)
                    
                    pratyantardashas.append({
                        "lord": p_lord,
                        "start": current_p_start.strftime("%Y-%m-%d"),
                        "end": current_p_end.strftime("%Y-%m-%d"),
                        "duration_days": round(p_dur_days, 1)
                    })
                    current_p_start = current_p_end
                    
                antardashas.append({
                    "lord": a_lord,
                    "start": current_a_start.strftime("%Y-%m-%d"),
                    "end": current_a_end.strftime("%Y-%m-%d"),
                    "pratyantardashas": pratyantardashas
                })
                current_a_start = current_a_end
                
            dasha_periods.append({
                "lord": m_lord,
                "start": current_m_start.strftime("%Y-%m-%d"),
                "end": current_m_end.strftime("%Y-%m-%d"),
                "duration_years": round(eff_m_years, 2),
                "antardashas": antardashas
            })
            current_m_start = current_m_end
            
        self.dasha_periods = dasha_periods

class HTMLReporter:
    NAKSHATRAS_28 = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", 
        "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", 
        "Mula", "Purva Ashadha", "Uttara Ashadha", "Abhijit", "Shravana", "Dhanishta", 
        "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ]

    def __init__(self, data_or_path: dict | str | Path, template_path: str | Path) -> None:
        if isinstance(data_or_path, dict):
            self.data = copy.deepcopy(data_or_path)
        else:
            self.data = json.loads(Path(data_or_path).read_text(encoding="utf-8"))
        self.meta = self.data.get('metadata', {})
        if 'settings' not in self.meta or not isinstance(self.meta['settings'], dict):
            self.meta['settings'] = {}
        settings = self.meta['settings']
        if not settings.get('house_system_name'):
            match settings.get('house_system', 'W'):
                case 'P': settings['house_system_name'] = "Placidus"
                case 'E': settings['house_system_name'] = "Equal"
                case _:   settings['house_system_name'] = "Whole Sign"
        if not settings.get('ayanamsa_name'):
            match settings.get('ayanamsa', 36):
                case 36: settings['ayanamsa_name'] = "Galactic Center at 0 Mula (Wilhelm)"
                case 1:  settings['ayanamsa_name'] = "Lahiri"
                case 3:  settings['ayanamsa_name'] = "Raman"
                case 0:  settings['ayanamsa_name'] = "Fagan-Bradley"
                case 5:  settings['ayanamsa_name'] = "KP"
                case ay: settings['ayanamsa_name'] = f"Custom ({ay})"
        self.subject = self.data.get('subject', {})
        if 'birth_data' not in self.subject or not isinstance(self.subject['birth_data'], dict):
            self.subject['birth_data'] = {}
        self.chart = self.data.get('astrological_chart', {})
        if 'ascendant' in self.chart and isinstance(self.chart['ascendant'], dict):
            asc = self.chart['ascendant']
            if 'sidereal_nakshatra' not in asc:
                if 'sidereal_longitude' in asc:
                    asc['sidereal_nakshatra'] = AstroMath.get_nakshatra(asc['sidereal_longitude'])
                elif 'tropical_longitude' in asc:
                    # Calculate ayanamsa offset from planets if available
                    offset = 0.0
                    for p in self.chart.get('planets', []):
                        if 'tropical_longitude' in p and 'sidereal_longitude' in p:
                            offset = (p['tropical_longitude'] - p['sidereal_longitude']) % 360
                            break
                    sid_lon = (asc['tropical_longitude'] - offset) % 360
                    asc['sidereal_longitude'] = round(sid_lon, 4)
                    asc['sidereal_sign'] = AstroMath.get_zodiac(sid_lon)
                    asc['sidereal_degree_in_house'] = round(sid_lon % 30, 4)
                    asc['sidereal_nakshatra'] = AstroMath.get_nakshatra(sid_lon)
            if 'tropical_degree_in_house' not in asc and 'tropical_longitude' in asc:
                asc['tropical_degree_in_house'] = round(asc['tropical_longitude'] % 30, 4)
        self.mode = settings.get('report_mode', 'Everything')
        is_sid = AstroMath.is_sidereal_mode(self.mode)

        sun_lon = None
        for p in self.chart.get('planets', []):
            if p.get('name') == 'Sun':
                sun_lon = p.get('sidereal_longitude') if is_sid else p.get('tropical_longitude')
                break

        has_speed_info = any('is_retrograde' in p or 'speed' in p or 'sidereal_speed' in p for p in self.chart.get('planets', []))
        speeds = {}
        if not has_speed_info:
            b = self.subject.get('birth_data', {})
            if b.get('date') and b.get('time') and b.get('timezone'):
                try:
                    y, m, d = [int(x) for x in b['date'].split('-')]
                    ayanamsa = settings.get('ayanamsa', 36)
                    epoch = AstroTime(y, m, d, b['time'], b['timezone'], sid_mode=ayanamsa)
                    temp_chart = ChartFactory.create_chart(epoch, mode=self.mode)
                    for p_name, p_obj in temp_chart.items():
                        speeds[p_name] = p_obj.get_speed(is_sid)
                except Exception:
                    pass

        for p in self.chart.get('planets', []):
            p_name = p.get('name', '')
            if 'is_retrograde' not in p:
                if p_name in ["Sun", "Moon", "Rahu", "Ketu"]:
                    p['is_retrograde'] = False
                elif p_name in speeds:
                    p['is_retrograde'] = speeds[p_name] < 0
                elif 'speed' in p:
                    p['is_retrograde'] = p['speed'] < 0
                elif 'sidereal_speed' in p:
                    p['is_retrograde'] = p['sidereal_speed'] < 0
                else:
                    p['is_retrograde'] = False

            if 'is_combust' not in p:
                is_c = p.get('avasthas', {}).get('diptadi', {}).get('is_combust', False)
                if not is_c and p_name != 'Sun' and sun_lon is not None:
                    p_lon = p.get('sidereal_longitude') if is_sid else p.get('tropical_longitude')
                    if p_lon is not None:
                        diff = abs(p_lon - sun_lon) % 360
                        diff = min(diff, 360.0 - diff)
                        if diff <= AstroMath.COMBUSTION_ORB:
                            is_c = True
                p['is_combust'] = is_c

        self.chart['planets_by_name'] = {p.get('name'): p for p in self.chart.get('planets', [])}
        self.template = Path(template_path).read_text(encoding="utf-8")

    def generate_south_chart_svg(self):
        cells = [
            (0,0), (0,1), (0,2), (0,3),
            (1,3), (2,3), (3,3), (3,2),
            (3,1), (3,0), (2,0), (1,0)
        ]
        sign_names = ["Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius"]
        
        sign_to_planets = {s: [] for s in sign_names}
        is_sid = AstroMath.is_sidereal_mode(self.mode)
        
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
        p_info_map = {p.get('name'): p for p in self.chart.get('planets', [])}
        
        for idx, (r, c) in enumerate(cells):
            sign_name = sign_names[idx]
            x = c * 100
            y = r * 100
            svg += f'  <rect x="{x}" y="{y}" width="100" height="100" fill="none" stroke="#2e305c" stroke-width="2"/>\n'
            svg += f'  <text x="{x+50}" y="{y+20}" fill="#f3c63f" font-family="Cinzel" font-size="11" text-anchor="middle" font-weight="bold">{sign_name[:3].upper()}</text>\n'
            
            content = []
            if sign_name == lagna_sign:
                content.append("ASC")
            for p_name in sign_to_planets.get(sign_name, []):
                abbr = p_abbr.get(p_name, p_name.upper())
                p_data = p_info_map.get(p_name, {})
                markers = ""
                if p_data.get('is_retrograde'):
                    markers += "(R)"
                if p_data.get('is_combust'):
                    markers += "(C)"
                content.append(f"{abbr}{markers}")
            
            for i, item in enumerate(content):
                cy = y + 45 + (i * 15)
                fill_color = "#00f2fe" if item == "ASC" else "#f1f1f5"
                svg += f'  <text x="{x+50}" y="{cy}" fill="{fill_color}" font-family="Outfit" font-size="11" text-anchor="middle">{item}</text>\n'
                
        svg += '</svg>'
        return svg

    def generate_north_chart_svg(self):
        is_sid = AstroMath.is_sidereal_mode(self.mode)
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
        p_info_map = {p.get('name'): p for p in self.chart.get('planets', [])}
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
            for p_name in house_to_planets.get(h, []):
                abbr = p_abbr.get(p_name, p_name.upper())
                p_data = p_info_map.get(p_name, {})
                markers = ""
                if p_data.get('is_retrograde'):
                    markers += "(R)"
                if p_data.get('is_combust'):
                    markers += "(C)"
                content.append(f"{abbr}{markers}")
            
            px, py = centers["planets"]
            planet_str = ", ".join(content)
            fill_color = "#00f2fe" if "ASC" in content else "#f1f1f5"
            svg += f'  <text x="{px}" y="{py}" fill="{fill_color}" font-family="Outfit" font-size="12" text-anchor="middle" font-weight="600">{planet_str}</text>\n'
            
        svg += '</svg>'
        return svg

    def generate_sudarshana_chakra_svg(self):
        is_sid = AstroMath.is_sidereal_mode(self.mode)
        
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

    def _get_28_nakshatra(self, lon):
        idx_27 = int(lon // (360.0 / 27.0))
        if idx_27 < 20:
            return idx_27
        elif idx_27 == 20:
            if lon < 276.6667:
                return 20 # Uttara Ashadha
            else:
                return 21 # Abhijit
        elif idx_27 == 21:
            if lon < 280.8944:
                return 21 # Abhijit
            else:
                return 22 # Shravana
        else:
            return idx_27 + 1

    def generate_kota_chakra_svg(self):
        is_sid = False if self.mode == "Tropical Focus" else True
        
        # Find Moon nakshatra index
        moon_lon = 0.0
        for p in self.chart.get('planets', []):
            if p['name'] == "Moon":
                moon_lon = p.get('sidereal_longitude') if is_sid else p.get('tropical_longitude')
                break
        n_birth = self._get_28_nakshatra(moon_lon)
        
        p_abbr = {"Sun": "SU", "Moon": "MO", "Mars": "MA", "Mercury": "ME", "Jupiter": "JU", "Venus": "VE", "Saturn": "SA", "Rahu": "RA", "Ketu": "KE"}
        
        stambha_planets = []
        madhya_planets = []
        prakara_planets = []
        bahya_planets = []
        
        for p in self.chart.get('planets', []):
            lon = p.get('sidereal_longitude') if is_sid else p.get('tropical_longitude')
            n_planet = self._get_28_nakshatra(lon)
            rel = (n_planet - n_birth) % 28 + 1
            
            abbr = p_abbr.get(p['name'], p['name'][:2].upper())
            if rel in [4, 11, 18, 25]:
                stambha_planets.append(abbr)
            elif rel in [3, 5, 10, 12, 17, 19, 24, 26]:
                madhya_planets.append(abbr)
            elif rel in [2, 6, 9, 13, 16, 20, 23, 27]:
                prakara_planets.append(abbr)
            else:
                bahya_planets.append(abbr)
                
        # Draw SVG
        svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-labelledby="kota-chart-title" role="img">\n'
        svg += '  <title id="kota-chart-title">Kota Chakra Fort Diagram</title>\n'
        svg += '  <desc>A fortified castle layout showing planetary positions in concentric zones: Stambha (core), Madhya (inner middle), Prakara (boundary wall), and Bahya (outer).</desc>\n'
        svg += '  <rect width="400" height="400" fill="#161730" stroke="#2e305c" stroke-width="3"/>\n'
        
        # Concentric squares
        svg += '  <rect x="40" y="40" width="320" height="320" fill="none" stroke="#2e305c" stroke-width="2.5"/>\n' # Bahya
        svg += '  <rect x="80" y="80" width="240" height="240" fill="none" stroke="#2e305c" stroke-dasharray="4,4"/>\n' # Prakara
        svg += '  <rect x="120" y="120" width="160" height="160" fill="none" stroke="#3b3d75"/>\n' # Madhya
        svg += '  <rect x="160" y="160" width="80" height="80" fill="#0d0e24" stroke="#f3c63f" stroke-width="1.5"/>\n' # Stambha (Center)
        
        # Connect diagonal paths (Entry)
        svg += '  <line x1="40" y1="40" x2="360" y2="360" stroke="#2e305c" stroke-width="1.5" stroke-dasharray="2,2"/>\n'
        svg += '  <line x1="40" y1="360" x2="360" y2="40" stroke="#2e305c" stroke-width="1.5" stroke-dasharray="2,2"/>\n'
        
        # Connect cardinal paths (Exit)
        svg += '  <line x1="200" y1="40" x2="200" y2="360" stroke="#2e305c" stroke-width="1.5" stroke-dasharray="2,2"/>\n'
        svg += '  <line x1="40" y1="200" x2="360" y2="200" stroke="#2e305c" stroke-width="1.5" stroke-dasharray="2,2"/>\n'
        
        # Labels for zones
        svg += '  <text x="200" y="150" fill="#f3c63f" font-family="Outfit" font-size="8" text-anchor="middle" font-weight="bold">STAMBHA (PILLAR)</text>\n'
        svg += '  <text x="200" y="110" fill="#a5a7cc" font-family="Outfit" font-size="8" text-anchor="middle">MADHYA</text>\n'
        svg += '  <text x="200" y="70" fill="#a5a7cc" font-family="Outfit" font-size="8" text-anchor="middle">PRAKARA</text>\n'
        svg += '  <text x="200" y="30" fill="#a5a7cc" font-family="Outfit" font-size="8" text-anchor="middle">BAHYA (OUTER)</text>\n'
        
        # Render planets distributed circular in each zone
        def draw_planets_in_zone(planets, r_val, color_theme):
            if not planets:
                return ""
            p_svg = ""
            for idx, p_name in enumerate(planets):
                ang = 45 + idx * (360.0 / len(planets))
                rad = math.radians(ang)
                px = 200 + r_val * math.cos(rad)
                py = 205 + r_val * math.sin(rad)
                p_svg += f'  <circle cx="{px}" cy="{py-4}" r="8" fill="#1c1d3a" stroke="{color_theme}" stroke-width="1"/>\n'
                p_svg += f'  <text x="{px}" y="{py-1}" fill="#f1f1f5" font-family="Outfit" font-size="8" text-anchor="middle" font-weight="bold">{p_name}</text>\n'
            return p_svg
            
        svg += draw_planets_in_zone(stambha_planets, 25, "#f3c63f")
        svg += draw_planets_in_zone(madhya_planets, 60, "#a5a7cc")
        svg += draw_planets_in_zone(prakara_planets, 100, "#3b3d75")
        svg += draw_planets_in_zone(bahya_planets, 140, "#2e305c")
        
        svg += '</svg>'
        return svg

    def generate_sarvatobhadra_chakra_svg(self):
        is_sid = False if self.mode == "Tropical Focus" else True
        
        east_naks = ["KR", "RO", "MR", "AR", "PU", "PY", "AS"]
        south_naks = ["MA", "PP", "UP", "HA", "CH", "SW", "VI"]
        west_naks = ["AN", "JY", "MU", "PA", "UA", "AB", "SH"]
        north_naks = ["DH", "ST", "PB", "UB", "RE", "AS", "BH"]
        
        grid = [[None for _ in range(9)] for _ in range(9)]
        
        grid[0][0] = "A"
        grid[0][8] = "AA"
        grid[8][8] = "I"
        grid[8][0] = "U"
        
        for i in range(7):
            grid[0][i+1] = east_naks[i]
            grid[i+1][8] = south_naks[i]
            grid[8][7-i] = west_naks[i]
            grid[7-i][0] = north_naks[i]
            
        sign_names = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]
        sign_coords = [
            (2,2), (2,3), (2,4), (2,5), (2,6), (3,6), 
            (4,6), (5,6), (6,6), (6,5), (6,4), (6,3)
        ]
        for idx, (r, c) in enumerate(sign_coords):
            grid[r][c] = sign_names[idx]
            
        p_abbr = {"Sun": "SU", "Moon": "MO", "Mars": "MA", "Mercury": "ME", "Jupiter": "JU", "Venus": "VE", "Saturn": "SA", "Rahu": "RA", "Ketu": "KE"}
        
        planet_placements = {}
        for p in self.chart.get('planets', []):
            lon = p.get('sidereal_longitude') if is_sid else p.get('tropical_longitude')
            n_idx = self._get_28_nakshatra(lon)
            nak_name = self.NAKSHATRAS_28[n_idx]
            abbr = p_abbr.get(p['name'], p['name'][:2].upper())
            
            east_names = ["Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha"]
            south_names = ["Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha"]
            west_names = ["Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Abhijit", "Shravana"]
            north_names = ["Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati", "Ashwini", "Bharani"]
            
            cell_coords = None
            if nak_name in east_names:
                cell_coords = (0, east_names.index(nak_name) + 1)
            elif nak_name in south_names:
                cell_coords = (south_names.index(nak_name) + 1, 8)
            elif nak_name in west_names:
                cell_coords = (8, 7 - west_names.index(nak_name))
            elif nak_name in north_names:
                cell_coords = (7 - north_names.index(nak_name), 0)
                
            if cell_coords:
                if cell_coords not in planet_placements:
                    planet_placements[cell_coords] = []
                planet_placements[cell_coords].append(abbr)
                
        svg = '<svg viewBox="0 0 450 450" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-labelledby="sbc-chart-title" role="img">\n'
        svg += '  <title id="sbc-chart-title">Sarvatobhadra Chakra 81-Square Grid</title>\n'
        svg += '  <desc>An 81-square coordinates matrix showing planetary placements and aspects (vedhas).</desc>\n'
        svg += '  <rect width="450" height="450" fill="#161730" stroke="#2e305c" stroke-width="3"/>\n'
        
        for r in range(9):
            for c in range(9):
                x = c * 50
                y = r * 50
                
                ring = min(r, c, 8-r, 8-c)
                if ring == 0:
                    fill = "rgba(46, 48, 92, 0.3)"
                    stroke = "#2e305c"
                elif ring == 1:
                    fill = "rgba(59, 61, 117, 0.2)"
                    stroke = "#3b3d75"
                else:
                    fill = "#0d0e24"
                    stroke = "#3b3d75"
                    
                svg += f'  <rect x="{x}" y="{y}" width="50" height="50" fill="{fill}" stroke="{stroke}" stroke-width="1"/>\n'
                
                val = grid[r][c]
                if val:
                    svg += f'  <text x="{x+25}" y="{y+20}" fill="#a5a7cc" font-family="Outfit" font-size="8.5" text-anchor="middle" font-weight="600">{val}</text>\n'
                    
                p_in_cell = planet_placements.get((r, c), [])
                if p_in_cell:
                    p_str = ",".join(p_in_cell)
                    svg += f'  <text x="{x+25}" y="{y+40}" fill="#f3c63f" font-family="Outfit" font-size="10" text-anchor="middle" font-weight="bold">{p_str}</text>\n'
                    
        svg += '</svg>'
        return svg

    def generate_kurma_chakra_svg(self):
        is_sid = False if self.mode == "Tropical Focus" else True
        
        directions = {
            "Center (Madhya)": ["Krittika", "Rohini", "Mrigashira"],
            "East (Head)": ["Ardra", "Punarvasu", "Pushya"],
            "SE (Front Right Leg)": ["Ashlesha", "Magha", "Purva Phalguni"],
            "South (Right Side)": ["Uttara Phalguni", "Hasta", "Chitra"],
            "SW (Rear Right Leg)": ["Swati", "Vishakha", "Anuradha"],
            "West (Tail)": ["Jyeshtha", "Mula", "Purva Ashadha"],
            "NW (Rear Left Leg)": ["Uttara Ashadha", "Abhijit", "Shravana"],
            "North (Left Side)": ["Dhanishta", "Shatabhisha", "Purva Bhadrapada"],
            "NE (Front Left Leg)": ["Uttara Bhadrapada", "Revati", "Ashwini", "Bharani"]
        }
        
        coords = {
            "Center (Madhya)": (200, 200),
            "East (Head)": (200, 80),
            "SE (Front Right Leg)": (290, 120),
            "South (Right Side)": (290, 200),
            "SW (Rear Right Leg)": (290, 280),
            "West (Tail)": (200, 320),
            "NW (Rear Left Leg)": (110, 280),
            "North (Left Side)": (110, 200),
            "NE (Front Left Leg)": (110, 120)
        }
        
        p_abbr = {"Sun": "SU", "Moon": "MO", "Mars": "MA", "Mercury": "ME", "Jupiter": "JU", "Venus": "VE", "Saturn": "SA", "Rahu": "RA", "Ketu": "KE"}
        dir_planets = {d: [] for d in coords}
        
        for p in self.chart.get('planets', []):
            lon = p.get('sidereal_longitude') if is_sid else p.get('tropical_longitude')
            n_idx = self._get_28_nakshatra(lon)
            nak_name = self.NAKSHATRAS_28[n_idx]
            
            abbr = p_abbr.get(p['name'], p['name'][:2].upper())
            for d, naks in directions.items():
                if nak_name in naks:
                    dir_planets[d].append(abbr)
                    break
                    
        svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-labelledby="kurma-chart-title" role="img">\n'
        svg += '  <title id="kurma-chart-title">Kurma Chakra Tortoise Diagram</title>\n'
        svg += '  <desc>A tortoise layout mapping the 28 Nakshatras onto the tortoise\'s body parts corresponding to cardinal directions.</desc>\n'
        svg += '  <rect width="400" height="400" fill="#161730" stroke="#2e305c" stroke-width="3"/>\n'
        
        svg += '  <ellipse cx="200" cy="50" rx="20" ry="25" fill="#1d1e40" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <polygon points="195,350 205,350 200,380" fill="#1d1e40" stroke="#2e305c" stroke-width="2"/>\n'
        
        svg += '  <ellipse cx="90" cy="100" rx="15" ry="20" transform="rotate(-30 90 100)" fill="#1d1e40" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <ellipse cx="310" cy="100" rx="15" ry="20" transform="rotate(30 310 100)" fill="#1d1e40" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <ellipse cx="85" cy="300" rx="15" ry="20" transform="rotate(30 85 300)" fill="#1d1e40" stroke="#2e305c" stroke-width="2"/>\n'
        svg += '  <ellipse cx="315" cy="300" rx="15" ry="20" transform="rotate(-30 315 300)" fill="#1d1e40" stroke="#2e305c" stroke-width="2"/>\n'
        
        svg += '  <ellipse cx="200" cy="200" rx="110" ry="130" fill="#0d0e24" stroke="#f3c63f" stroke-width="2.5"/>\n'
        
        svg += '  <line x1="200" y1="70" x2="200" y2="330" stroke="#2e305c" stroke-dasharray="2,2"/>\n'
        svg += '  <line x1="90" y1="200" x2="310" y2="200" stroke="#2e305c" stroke-dasharray="2,2"/>\n'
        svg += '  <line x1="120" y1="110" x2="280" y2="290" stroke="#2e305c" stroke-dasharray="2,2"/>\n'
        svg += '  <line x1="120" y1="290" x2="280" y2="110" stroke="#2e305c" stroke-dasharray="2,2"/>\n'
        
        for name, (x, y) in coords.items():
            dir_label = name.split(" ")[0]
            svg += f'  <text x="{x}" y="{y-6}" fill="#a5a7cc" font-family="Outfit" font-size="7.5" text-anchor="middle" font-weight="600">{dir_label}</text>\n'
            p_list = dir_planets.get(name, [])
            if p_list:
                p_str = ",".join(p_list)
                svg += f'  <text x="{x}" y="{y+8}" fill="#f3c63f" font-family="Outfit" font-size="9" text-anchor="middle" font-weight="bold">{p_str}</text>\n'
            else:
                svg += f'  <text x="{x}" y="{y+8}" fill="#40437a" font-family="Outfit" font-size="7.5" text-anchor="middle" font-style="italic">Empty</text>\n'
                
        svg += '</svg>'
        return svg

    def compile_report(self, output_path: str | Path | None = None) -> str:
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
            kota_chakra_svg=self.generate_kota_chakra_svg(),
            sarvatobhadra_chakra_svg=self.generate_sarvatobhadra_chakra_svg(),
            kurma_chakra_svg=self.generate_kurma_chakra_svg(),
            today=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            zodiac_signs=AstroMath.ZODIAC_SIGNS,
            classical_planets=["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"],
            aspecting_planets=["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"],
            friendship_mapping=friendship_mapping,
            planets_by_name=self.chart.get('planets_by_name', {})
        )
        
        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(rendered_html, encoding='utf-8')
        return rendered_html


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
    def get_karakas(cls, chart, mode="Tropical-Vedic"):
        is_sid = AstroMath.is_sidereal_mode(mode)
        classical_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        planets_with_degrees = []
        for name in classical_names:
            if name in chart:
                p = chart[name]
                if isinstance(p, dict):
                    lon = p.get("sidereal_longitude", 0.0) if is_sid else p.get("tropical_longitude", 0.0)
                elif hasattr(p, "get_longitude"):
                    lon = p.get_longitude(is_sid)
                else:
                    lon = p.sidereal_longitude if is_sid else getattr(p, "tropical_longitude", 0.0)
                _, deg_in_sign = AstroMath.get_sign_and_degree(lon)
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
        b_date = date(astro_time.year, astro_time.month, astro_time.day)
        
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
            vedic_date = b_date - timedelta(days=1)
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


# --- 9.5. AVASTHA ENGINE (PLANETARY STATES) ---
class AvasthaEngine:
    BALADI_STATES_ODD = ["Bāla", "Kumāra", "Yuvā", "Vṛddha", "Mṛta"]
    BALADI_STATES_EVEN = ["Mṛta", "Vṛddha", "Yuvā", "Kumāra", "Bāla"]
    BALADI_POTENCY = {
        "Bāla": {"label": "25% (Infant)", "multiplier": 0.25},
        "Kumāra": {"label": "50% (Youth)", "multiplier": 0.50},
        "Yuvā": {"label": "100% (Full Capacity)", "multiplier": 1.00},
        "Vṛddha": {"label": "10% (Minimal)", "multiplier": 0.10},
        "Mṛta": {"label": "0% (Inactive)", "multiplier": 0.00}
    }

    JAGRADADI_DESCRIPTIONS = {
        "Jāgraṭa": "Awake (100% Capacity)",
        "Swapna": "Dreaming (50% Capacity)",
        "Suṣupti": "Sleeping (0% / Adverse)"
    }

    SHAYANADI_STATES = [
        "Śayana (Resting)",
        "Upaveśana (Sitting)",
        "Netrapāṇi (Hand on Eye)",
        "Prakāśana (Illuminating)",
        "Gamana (Travelling)",
        "Āgamana (Returning)",
        "Sabhā (In Assembly)",
        "Āgama (Acquiring)",
        "Bhojana (Eating)",
        "Nṛtyalipsā (Desiring Pleasure)",
        "Kautuka (Curious)",
        "Nidrā (Sleeping)"
    ]

    PLANET_INDEX = {
        "Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4,
        "Jupiter": 5, "Venus": 6, "Saturn": 7, "Rahu": 8, "Ketu": 9
    }

    @classmethod
    def calculate_baladi(cls, lon):
        sign_idx, deg_in_sign = AstroMath.get_sign_and_degree(lon)
        state_idx = min(4, int(deg_in_sign // 6))
        is_odd = (sign_idx % 2 == 0)
        state = cls.BALADI_STATES_ODD[state_idx] if is_odd else cls.BALADI_STATES_EVEN[state_idx]
        potency_info = cls.BALADI_POTENCY[state]
        return {
            "state": state,
            "potency": potency_info["label"],
            "multiplier": potency_info["multiplier"],
            "degree_in_sign": round(deg_in_sign, 2),
            "sign_type": "Odd" if is_odd else "Even"
        }

    @classmethod
    def calculate_jagradadi(cls, dignity, friendship_level):
        if dignity in ["Exalted", "Own Sign"]:
            state = "Jāgraṭa"
        elif dignity == "Debilitated" or friendship_level in ["Shatru", "Adhi Shatru", "Enemy"]:
            state = "Suṣupti"
        else:
            state = "Swapna"
        return {
            "state": state,
            "description": cls.JAGRADADI_DESCRIPTIONS[state]
        }

    @classmethod
    def calculate_diptadi(cls, planet_name, dignity, friendship_level, sun_lon=None, planet_lon=None):
        is_combust = False
        if planet_name != "Sun" and sun_lon is not None and planet_lon is not None:
            diff = abs(planet_lon - sun_lon) % 360
            diff = min(diff, 360.0 - diff)
            if diff <= AstroMath.COMBUSTION_ORB:
                is_combust = True

        if is_combust:
            state = "Vikala (Combust)"
        elif dignity == "Exalted":
            state = "Dīpta (Exalted)"
        elif dignity == "Own Sign":
            state = "Svastha (Own Sign)"
        elif friendship_level == "Adhi Mitra":
            state = "Mudita (Great Friend)"
        elif friendship_level == "Mitra" or dignity == "Friendly Sign":
            state = "Shānta (Friend)"
        elif dignity == "Debilitated":
            state = "Khala (Debilitated)"
        elif friendship_level in ["Shatru", "Adhi Shatru"]:
            state = "Dukhita (Enemy)"
        else:
            state = "Dīna (Neutral)"

        return {"state": state, "is_combust": is_combust}

    @classmethod
    def calculate_shayanadi(cls, planet_name, planet_lon, lagna_lon=0.0):
        p_idx = cls.PLANET_INDEX.get(planet_name, 1)
        nak_p = int(((planet_lon % 360.0) * 27.0) / 360.0) % 27 + 1
        nak_l = int(((lagna_lon % 360.0) * 27.0) / 360.0) % 27 + 1
        val = (p_idx * nak_p * nak_l + 1) % 12
        state = cls.SHAYANADI_STATES[val]
        return {
            "state": state,
            "state_index": val + 1
        }

    @classmethod
    def calculate_lajjitadi(cls, planet_name, house_num, conjoined_planets, aspecting_planets, dignity):
        states = []
        if dignity in ["Exalted", "Own Sign"]:
            states.append("Garvita (Proud)")
        if house_num == 5 and any(p in conjoined_planets for p in ["Rahu", "Ketu", "Sun", "Saturn", "Mars"]):
            states.append("Lajjita (Embarrassed)")
        if "Sun" in conjoined_planets and any(p in aspecting_planets for p in ["Saturn", "Mars", "Rahu", "Ketu"]):
            states.append("Kṣubhita (Agitated)")
        if dignity == "Debilitated" or any(p in aspecting_planets for p in ["Saturn", "Mars"]):
            states.append("Kṣudhita (Hungry)")
        if any(p in conjoined_planets for p in ["Jupiter", "Venus"]) or dignity == "Friendly Sign":
            states.append("Mudita (Delighted)")
            
        if not states:
            states.append("Sama (Balanced)")
            
        return {"states": states}

    @classmethod
    def _extract_lagna_longitudes(cls, houses_dict, is_sid: bool) -> tuple[float, float]:
        """
        Extracts (lagna_lon, lagna_sid_lon) from houses_dict or local_sky.
        """
        lagna_lon = 0.0
        if hasattr(houses_dict, "sidereal_ascendant") or hasattr(houses_dict, "tropical_ascendant"):
            lagna_lon = houses_dict.sidereal_ascendant if is_sid else houses_dict.tropical_ascendant
        elif isinstance(houses_dict, dict) and 1 in houses_dict:
            h1 = houses_dict[1]
            if isinstance(h1, dict):
                lagna_lon = h1.get("sidereal_start", 0.0) if is_sid else h1.get("tropical_start", 0.0)
            elif isinstance(h1, (int, float)):
                lagna_lon = float(h1)
        elif isinstance(houses_dict, (list, tuple)) and len(houses_dict) > 0:
            lagna_lon = float(houses_dict[0])

        lagna_sid_lon = getattr(houses_dict, "sidereal_ascendant", lagna_lon)
        if isinstance(houses_dict, dict) and 1 in houses_dict and isinstance(houses_dict[1], dict):
            lagna_sid_lon = houses_dict[1].get("sidereal_start", lagna_sid_lon)

        return lagna_lon, lagna_sid_lon

    @classmethod
    def get_planet_avasthas(cls, planet_name, planet_obj, chart, houses_dict, mode="Vedic Focus"):
        is_sid = AstroMath.is_sidereal_mode(mode)
        lon = planet_obj.get_longitude(is_sid)
        house_num = planet_obj.get_house(is_sid)
        dignity = planet_obj.dignity
        
        lagna_lon, lagna_sid_lon = cls._extract_lagna_longitudes(houses_dict, is_sid)
        planet_sid_lon = planet_obj.sidereal_longitude

        sun_lon = chart["Sun"].get_longitude(is_sid) if "Sun" in chart else None

        conjoined = []
        aspecting = []
        for other_name, other_obj in chart.items():
            if other_name == planet_name:
                continue
            o_h = other_obj.get_house(is_sid)
            if o_h and house_num and o_h == house_num:
                conjoined.append(other_name)
            if o_h and house_num and (house_num - o_h) % 12 == 6:
                aspecting.append(other_name)

        sign_idx, _ = AstroMath.get_sign_and_degree(lon)
        sign_name = AstroMath.ZODIAC_SIGNS[sign_idx]
        sign_lord = ShadbalaEngine.LORDSHIPS.get(sign_name, "")
        friendship_level = "Sama"
        if sign_lord and sign_lord in chart and planet_name in FriendshipEngine.NATURAL:
            h1 = house_num if house_num else 1
            h2 = chart[sign_lord].get_house(is_sid)
            if h2:
                friendship_level = FriendshipEngine.get_panchadha_relationship(planet_name, sign_lord, h1, h2)

        baladi = cls.calculate_baladi(lon)
        jagradadi = cls.calculate_jagradadi(dignity, friendship_level)
        diptadi = cls.calculate_diptadi(planet_name, dignity, friendship_level, sun_lon, lon)
        shayanadi = cls.calculate_shayanadi(planet_name, planet_sid_lon, lagna_sid_lon)
        lajjitadi = cls.calculate_lajjitadi(planet_name, house_num, conjoined, aspecting, dignity)

        return {
            "baladi": baladi,
            "jagradadi": jagradadi,
            "diptadi": diptadi,
            "shayanadi": shayanadi,
            "lajjitadi": lajjitadi
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
    def calculate_synthesis(cls, chart, local_sky, mode, ashtakavarga: dict | None = None):
        """
        Synthesizes Shadbala, Dignity, and Ashtakavarga metrics for all classical planets.
        """
        synthesis_data = {}
        classical_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        is_sid = AstroMath.is_sidereal_mode(mode)

        # Extract Ashtakavarga points (reuse if already computed)
        if ashtakavarga is None:
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

            # Calculate Avasthas for synthesis
            avasthas = AvasthaEngine.get_planet_avasthas(name, p, chart, local_sky, mode)

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
                "avasthas": avasthas,
                "takeaway": takeaway
            }
            
        return synthesis_data


# --- 11. ASPECT ENGINE ---
class AspectEngine:
    CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    ALL_GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    
    PARASHARI_RULES = {
        "Sun": [(7, "7th House (Universal)")],
        "Moon": [(7, "7th House (Universal)")],
        "Mars": [(4, "4th House (Special)"), (7, "7th House (Universal)"), (8, "8th House (Special)")],
        "Mercury": [(7, "7th House (Universal)")],
        "Jupiter": [(5, "5th House (Special)"), (7, "7th House (Universal)"), (9, "9th House (Special)")],
        "Venus": [(7, "7th House (Universal)")],
        "Saturn": [(3, "3rd House (Special)"), (7, "7th House (Universal)"), (10, "10th House (Special)")],
        "Rahu": [(5, "5th House (Special)"), (7, "7th House (Universal)"), (9, "9th House (Special)")],
        "Ketu": [(7, "7th House (Universal)")]
    }

    @classmethod
    def calculate_aspects(cls, chart, mode, local_sky=None):
        """
        Calculates Parashari, Jaimini, and Tajika aspects between all classical planets,
        including Rahu, Ketu, Lagna, and aspected houses/signs.
        """
        is_sid = AstroMath.is_sidereal_mode(mode)
        
        parashari = {p: [] for p in cls.ALL_GRAHAS}
        parashari_houses = {p: [] for p in cls.ALL_GRAHAS}
        jaimini = {p: [] for p in cls.CLASSICAL_PLANETS}
        tajika = {p: [] for p in cls.CLASSICAL_PLANETS}
        
        # Pre-compute positions to avoid redundant calculations
        positions = {}
        for p in cls.ALL_GRAHAS:
            if p not in chart:
                continue
            obj = chart[p]
            lon = obj.get_longitude(is_sid)
            h = obj.get_house(is_sid)
            sign_idx, _ = AstroMath.get_sign_and_degree(lon)
            positions[p] = {
                "lon": lon,
                "house": h,
                "sign_idx": sign_idx,
                "sign_name": AstroMath.ZODIAC_SIGNS[sign_idx],
                "sign_type": sign_idx % 3  # 0=Movable, 1=Fixed, 2=Dual
            }
            
        # Determine Lagna sign index
        if local_sky is not None and (hasattr(local_sky, "sidereal_ascendant") or hasattr(local_sky, "tropical_ascendant")):
            lagna_lon = local_sky.sidereal_ascendant if is_sid else local_sky.tropical_ascendant
            lagna_sign_idx, _ = AstroMath.get_sign_and_degree(lagna_lon)
        else:
            lagna_sign_idx = 0
            for p_name, pos in positions.items():
                if pos["house"]:
                    lagna_sign_idx = (pos["sign_idx"] - (pos["house"] - 1)) % 12
                    break

        # 1. Parashari aspects (Graha Drishti on Houses and Occupants/Points)
        for p1 in cls.ALL_GRAHAS:
            if p1 not in positions or not positions[p1]["house"]:
                continue
            h1 = positions[p1]["house"]
            rules = cls.PARASHARI_RULES.get(p1, [(7, "7th House (Universal)")])
            
            for dist, aspect_type in rules:
                target_house = (h1 + dist - 2) % 12 + 1
                target_sign = AstroMath.ZODIAC_SIGNS[(lagna_sign_idx + target_house - 1) % 12]
                occupants = []
                
                # Check if target house is Lagna (House 1)
                if target_house == 1 and p1 != "Lagna":
                    occupants.append("Lagna")
                    parashari[p1].append({
                        "target": "Lagna",
                        "aspect": aspect_type,
                        "distance": dist,
                        "house": target_house,
                        "sign": target_sign
                    })
                    
                # Check which grahas reside in the target house
                for p2 in cls.ALL_GRAHAS:
                    if p1 == p2 or p2 not in positions:
                        continue
                    if positions[p2]["house"] == target_house:
                        occupants.append(p2)
                        parashari[p1].append({
                            "target": p2,
                            "aspect": aspect_type,
                            "distance": dist,
                            "house": target_house,
                            "sign": target_sign
                        })
                        
                parashari_houses[p1].append({
                    "house": target_house,
                    "sign": target_sign,
                    "aspect": aspect_type,
                    "distance": dist,
                    "occupants": occupants
                })
            
        for p1 in cls.CLASSICAL_PLANETS:
            if p1 not in positions:
                continue
            pos1 = positions[p1]
            lon1, s1, t1 = pos1["lon"], pos1["sign_idx"], pos1["sign_type"]
            
            for p2 in cls.CLASSICAL_PLANETS:
                if p1 == p2 or p2 not in positions:
                    continue
                pos2 = positions[p2]
                lon2, s2, t2 = pos2["lon"], pos2["sign_idx"], pos2["sign_type"]
                
                # 2. Jaimini aspects (Rashi Drishti)
                has_jaimini = False
                if t1 == 2 and t2 == 2:  # Dual aspects Dual
                    has_jaimini = True
                elif t1 == 0 and t2 == 1:  # Movable aspects Fixed except adjacent
                    if s2 not in [(s1 - 1) % 12, (s1 + 1) % 12]:
                        has_jaimini = True
                elif t1 == 1 and t2 == 0:  # Fixed aspects Movable except adjacent
                    if s2 not in [(s1 - 1) % 12, (s1 + 1) % 12]:
                        has_jaimini = True
                        
                if has_jaimini:
                    jaimini[p1].append({
                        "target": p2,
                        "sign_from": AstroMath.ZODIAC_SIGNS[s1],
                        "sign_to": AstroMath.ZODIAC_SIGNS[s2]
                    })
                    
                # 3. Tajika aspects (Degree-based)
                diff = abs(lon1 - lon2) % 360
                diff = min(diff, 360.0 - diff)
                
                aspects_map = {
                    "Conjunction": 0.0,
                    "Sextile": 60.0,
                    "Square": 90.0,
                    "Trine": 120.0,
                    "Opposition": 180.0
                }
                for asp_name, val in aspects_map.items():
                    orb = abs(diff - val)
                    if orb <= 6.0:
                        nature = "Friendly (Mitra)" if asp_name in ["Sextile", "Trine"] else (
                            "Hostile (Shatru)" if asp_name in ["Square", "Opposition"] else "Neutral (Sama)"
                        )
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
            "parashari_houses": parashari_houses,
            "jaimini": jaimini,
            "tajika": tajika
        }


# --- 12. LLM CONTEXT & SLM OPTIMIZED EXPORTERS ---
class LLMContextExporter:
    """
    Exports astrological chart data into ultra-compact, high-density formats
    tailored specifically for Small Local Models (SLMs like Gemma 4B, Qwen 9B).
    Generates structured Markdown (.md) for direct prompt injection and a lean
    JSON (.json) representation, preserving traditional classical yoga results.
    """
    KARAKA_SHORT_CODES = {
        "Atmakaraka": "AK",
        "Amatyakaraka": "AmK",
        "Bhratrukaraka": "BK",
        "Matrukaraka": "MK",
        "Putrakaraka": "PK",
        "Jnatikaraka": "GK",
        "Darakaraka": "DK"
    }

    KARAKA_FULL_DESCRIPTIONS = {
        "Atmakaraka": "Atmakaraka (Self/Soul)",
        "Amatyakaraka": "Amatyakaraka (Career/Profession)",
        "Bhratrukaraka": "Bhratrukaraka (Siblings/Guru)",
        "Matrukaraka": "Matrukaraka (Mother)",
        "Putrakaraka": "Putrakaraka (Children/Intellect)",
        "Jnatikaraka": "Jnatikaraka (Relatives/Obstacles)",
        "Darakaraka": "Darakaraka (Spouse/Partners)"
    }

    PLANET_ORDER = [
        "Sun",
        "Moon",
        "Mars",
        "Mercury",
        "Jupiter",
        "Venus",
        "Saturn",
        "Rahu",
        "Ketu"
    ]

    def __init__(
        self,
        subject_profile: dict,
        chart: dict,
        local_sky,
        report_mode: str = "Tropical-Vedic",
        yogas: dict | None = None,
        dasha_periods: list | None = None,
        transits: dict | None = None,
        panchanga: dict | None = None,
        ashtakavarga: dict | None = None,
        jaimini_karakas: dict | None = None,
        planetary_synthesis: dict | None = None,
        planetary_aspects: dict | None = None
    ):
        self.subject = subject_profile or {}
        self.chart = chart or {}
        self.local_sky = local_sky
        self.report_mode = report_mode
        self.yogas = yogas or {}
        self.dasha_periods = dasha_periods or []
        self.transits = transits or {}
        self.panchanga = panchanga or {}
        self.ashtakavarga = ashtakavarga or {}
        self.jaimini_karakas = jaimini_karakas or {}
        self.planetary_synthesis = planetary_synthesis or {}
        self.planetary_aspects = planetary_aspects or {}

    def get_current_dasha(self, target_date_str: str | None = None) -> tuple[dict, str | None]:
        today_str = target_date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_dasha = {}
        next_antardasha = None

        for m in self.dasha_periods:
            m_start = m.get("start", "")
            m_end = m.get("end", "")
            if m_start <= today_str <= m_end:
                current_dasha["mahadasha"] = {
                    "lord": m.get("lord"), "start": m_start, "end": m_end
                }
                antardashas = m.get("antardashas", [])
                for i, a in enumerate(antardashas):
                    a_start = a.get("start", "")
                    a_end = a.get("end", "")
                    if a_start <= today_str <= a_end:
                        current_dasha["antardasha"] = {
                            "lord": a.get("lord"), "start": a_start, "end": a_end
                        }
                        for p in a.get("pratyantardashas", []):
                            p_start = p.get("start", "")
                            p_end = p.get("end", "")
                            if p_start <= today_str <= p_end:
                                current_dasha["pratyantardasha"] = {
                                    "lord": p.get("lord"), "start": p_start, "end": p_end
                                }
                                break
                        if i + 1 < len(antardashas):
                            next_a = antardashas[i + 1]
                            next_antardasha = f"{m.get('lord')}-{next_a.get('lord')} (begins {next_a.get('start')})"
                        break
                break

        return current_dasha, next_antardasha

    def _build_planet_summaries(self, is_sid: bool, asc_sign: str, karaka_map: dict[str, str], sun_lon: float | None) -> list[dict[str, Any]]:
        ordered_planets = []
        for p in self.PLANET_ORDER:
            if p in self.chart:
                ordered_planets.append((p, self.chart[p]))
        for p_name, p_obj in self.chart.items():
            if p_name not in self.PLANET_ORDER:
                ordered_planets.append((p_name, p_obj))

        summaries = []
        for p_name, p_obj in ordered_planets:
            sign = p_obj.sidereal_sign if is_sid else p_obj.zodiac_sign
            house = p_obj.vedic_house if is_sid else p_obj.tropical_house
            lon = p_obj.sidereal_longitude if is_sid else p_obj.tropical_longitude
            deg = round(lon % 30, 1)

            synth = self.planetary_synthesis.get(p_name, {})
            bala_lvl = synth.get("shadbala", {}).get("level", "")
            bala_total = p_obj.shadbala.get("shadbala_total") if p_obj.shadbala else None

            avasthas = getattr(p_obj, "avasthas", {}) or synth.get("avasthas", {})
            compact_avasthas = {}
            if avasthas:
                for k in ["baladi", "jagradadi", "diptadi", "lajjitadi"]:
                    if k in avasthas and "state" in avasthas[k]:
                        compact_avasthas[k] = avasthas[k]["state"]

            is_retro = (getattr(p_obj, "sidereal_speed", 0.0) < 0) if p_name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            is_combust = synth.get("avasthas", {}).get("diptadi", {}).get("is_combust", False)
            if not is_combust and p_name != "Sun" and sun_lon is not None:
                diff = abs(lon - sun_lon) % 360
                diff = min(diff, 360.0 - diff)
                if diff <= AstroMath.COMBUSTION_ORB:
                    is_combust = True

            ruled = YogaEngine.get_ruled_houses(p_name, asc_sign)
            is_yk = any(h in [4, 7, 10] for h in ruled) and any(h in [5, 9] for h in ruled)
            nak_pada = AstroMath.get_nakshatra_pada(p_obj.sidereal_longitude)

            takeaway = synth.get("takeaway", "")
            if not takeaway:
                av_list = [compact_avasthas[k] for k in ["baladi", "jagradadi"] if k in compact_avasthas]
                takeaway = ", ".join(av_list) if av_list else "-"

            summaries.append({
                "name": p_name,
                "planet_obj": p_obj,
                "sign": sign,
                "house": house,
                "placed_in_house": house,
                "deg": deg,
                "nakshatra": p_obj.nakshatra,
                "nakshatra_pada": nak_pada,
                "dignity": p_obj.dignity,
                "is_retrograde": is_retro,
                "is_combust": is_combust,
                "ruled_houses": ruled,
                "rules_houses": ruled,
                "is_yogakaraka": is_yk,
                "power_level": bala_lvl,
                "bala_total": bala_total,
                "d9": p_obj.vargas.get("D9", "-"),
                "d10": p_obj.vargas.get("D10", "-"),
                "karaka": karaka_map.get(p_name, None),
                "takeaway": takeaway,
                "compact_avasthas": compact_avasthas
            })
        return summaries

    def generate_markdown(self) -> str:
        name = self.subject.get("name", "Unknown Subject")
        birth = self.subject.get("birth_data", {})
        date_str = birth.get("date", "")
        time_str = birth.get("time", "")
        tz_str = birth.get("timezone", "")

        is_sid = AstroMath.is_sidereal_mode(self.report_mode)
        asc_sign = self.local_sky.sidereal_ascendant_sign if is_sid else self.local_sky.tropical_ascendant_sign
        asc_lon = self.local_sky.sidereal_ascendant if is_sid else self.local_sky.tropical_ascendant
        asc_deg = round(asc_lon % 30, 1)
        asc_sid_lon = self.local_sky.sidereal_ascendant
        asc_nak = AstroMath.get_nakshatra(asc_sid_lon)
        asc_pada = AstroMath.get_nakshatra_pada(asc_sid_lon)

        tithi_p = self.panchanga.get("tithi", {})
        tithi_str = f"{tithi_p.get('paksha', '')} {tithi_p.get('name', '')}".strip()
        nak_name = self.panchanga.get("nakshatra", {}).get("name", "")
        vara_name = self.panchanga.get("vara", {}).get("name", "")
        panchanga_summary = f"{tithi_str}, {nak_name} Nakshatra, {vara_name}" if tithi_str else "N/A"

        md_lines = [
            f"# Natal Chart: {name} ({date_str} {time_str}, {tz_str})",
            f"**Ascendant (Lagna):** {asc_sign} {asc_deg}° ({asc_nak} P{asc_pada}) | **Panchanga:** {panchanga_summary}"
        ]

        current_dasha, next_antardasha = self.get_current_dasha()
        if current_dasha:
            m_obj = current_dasha.get("mahadasha", {})
            m_lord = m_obj.get("lord", "")
            m_start = m_obj.get("start", "")[:4]
            m_end = m_obj.get("end", "")[:4]

            a_obj = current_dasha.get("antardasha", {})
            a_lord = a_obj.get("lord", "")
            a_end = a_obj.get("end", "")[:7]

            p_obj = current_dasha.get("pratyantardasha", {})
            p_lord = p_obj.get("lord", "")
            p_end = p_obj.get("end", "")

            dasha_line = f"**Current Dasha:** {m_lord} MD ({m_start}–{m_end}) > {a_lord} AD (to {a_end}) > {p_lord} PD (ends {p_end})"
            if next_antardasha:
                dasha_line += f" | **Next AD:** {next_antardasha}"
            md_lines.append(dasha_line)

        # Build spelled-out karaka lookup
        karaka_map = {}
        for p, kdata in self.jaimini_karakas.items():
            full_role = kdata.get("role", "")
            base_role = full_role.split(" ")[0] if full_role else ""
            karaka_map[p] = self.KARAKA_FULL_DESCRIPTIONS.get(base_role, full_role)

        # Reference Sun for combustion
        sun_lon = None
        if "Sun" in self.chart:
            sun_obj = self.chart["Sun"]
            sun_lon = sun_obj.sidereal_longitude if is_sid else sun_obj.tropical_longitude

        # Planetary table
        md_lines.extend([
            "\n### Planetary Positions & Strength",
            "> **AI Interpretation Guide:**",
            "> - **Placed In (Occupies):** The physical house where the planet resides in this chart.",
            "> - **Rules (Lord of):** The house(s) governed by this planet based on sign ownership.",
            "> - **Critical Rule:** A planet does NOT rule the house it occupies unless it resides in its Own Sign (Swakshetra). Never confuse placement with rulership.",
            "\n| Planet | Sign | Placed In | Rules (Lord of) | Deg | Nakshatra | Dignity | Power (Bala) | D9 / D10 | Karaka | Takeaway |",
            "|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|"
        ])

        # 1. Ascendant Row
        asc_d9 = VargaEngine.calculate_d9(asc_lon) if self.report_mode != "Tropical Focus" else "-"
        asc_d10 = VargaEngine.calculate_d10(asc_lon) if self.report_mode != "Tropical Focus" else "-"
        asc_varga_str = f"{asc_d9} / {asc_d10}" if self.report_mode != "Tropical Focus" else "-"
        md_lines.append(
            f"| Ascendant | {asc_sign} | House 1 | House 1 (Lagna) | {asc_deg}° | {asc_nak} (P{asc_pada}) | - | - | {asc_varga_str} | Lagna / Self | Chart Anchor |"
        )

        # 2. Planetary Rows in canonical Navagraha order
        planet_summaries = self._build_planet_summaries(is_sid, asc_sign, karaka_map, sun_lon)
        for s in planet_summaries:
            p_name = s["name"]
            power_str = f"{s['power_level']} ({round(s['bala_total'], 1)})" if s["bala_total"] is not None else "N/A"
            varga_str = f"{s['d9']} / {s['d10']}" if s['d10'] != "-" else s['d9']
            karaka_val = s['karaka'] or "-"

            dignity_parts = [s['dignity']]
            if s['is_retrograde']:
                dignity_parts.append("(R)")
            if s['is_combust']:
                dignity_parts.append("(C)")
            dignity_str = " ".join(dignity_parts)

            placed_str = f"House {s['house']}"
            ruled = s['ruled_houses']
            if ruled:
                houses_text = ", ".join(f"House {h}" for h in ruled)
                rule_annotations = []
                if s['house'] in ruled:
                    rule_annotations.append("Own House")
                if s['is_yogakaraka']:
                    rule_annotations.append("Yogakaraka")
                rules_str = f"{houses_text} ({', '.join(rule_annotations)})" if rule_annotations else houses_text
            else:
                rules_str = "None (Node)" if p_name in ["Rahu", "Ketu"] else "None"

            nak_str = f"{s['nakshatra']} (P{s['nakshatra_pada']})"
            takeaway_str = s['takeaway'] or "-"

            markers = []
            if s['is_retrograde']:
                markers.append("(R)")
            if s['is_combust']:
                markers.append("(C)")
            p_display = f"{p_name} {' '.join(markers)}".strip()

            md_lines.append(
                f"| {p_display} | {s['sign']} | {placed_str} | {rules_str} | {s['deg']}° | {nak_str} | {dignity_str} | {power_str} | {varga_str} | {karaka_val} | {takeaway_str} |"
            )

        # Active Yogas with Traditional Interpretive Results (Deduplicated)
        md_lines.extend(["\n### Active Classical Yogas & Traditional Results"])
        active_found = False
        seen_results = set()
        active_keys = set(k for k, v in self.yogas.items() if v.get("active"))

        for y_name, y_data in self.yogas.items():
            if not y_data.get("active"):
                continue

            # Suppress generic prefix duplicate if specific counterpart is present
            if y_name.startswith("Generic "):
                base_name = y_name[8:]
                if base_name in active_keys:
                    continue

            results_text = y_data.get("results", "Favorable classical combination.")
            if results_text in seen_results:
                continue
            seen_results.add(results_text)

            active_found = True
            details_raw = y_data.get("details", "")
            if "Matching planets:" in details_raw:
                planets_matched = details_raw.replace("Matching planets:", "").strip().rstrip(".")
            else:
                planets_matched = details_raw.strip().rstrip(".") or "Chart"
            md_lines.append(f"- **{y_name}** ({planets_matched}): {results_text}")

        if not active_found:
            md_lines.append("- No primary classical yogas active.")

        # Key Aspects, Drishti & Transits
        seen_aspects = set()
        aspect_list = []
        for p1, targets in self.planetary_aspects.get("tajika", {}).items():
            for t in targets:
                p2 = t.get("target")
                pair = tuple(sorted([p1, p2]))
                if pair not in seen_aspects:
                    seen_aspects.add(pair)
                    asp_name = t.get("aspect", "").lower()
                    orb = round(t.get("orb", 0.0), 1)
                    aspect_list.append(f"{pair[0]} {asp_name} {pair[1]} (orb {orb}°)")

        parashari_items = []
        for p1, targets in self.planetary_aspects.get("parashari", {}).items():
            if not targets:
                continue
            aspect_groups = {}
            for t in targets:
                t_name = t.get("target")
                if not t_name:
                    continue
                raw_asp = t.get("aspect", "").replace(" (Special)", "").replace(" (Universal)", "").strip()
                asp_clean = raw_asp.replace("3th", "3rd").replace("2th", "2nd").replace("1th", "1st")
                aspect_groups.setdefault(asp_clean, []).append(t_name)
            for asp_clean, names in aspect_groups.items():
                parashari_items.append(f"{p1} aspects {', '.join(names)} ({asp_clean})")

        transits_summary_items = []
        for p, d in self.transits.items():
            h = d.get("house_from_moon", "")
            sign_t = d.get("transit_sign", "")
            star = "*" if d.get("is_auspicious") else ""
            transits_summary_items.append(f"{p}: {sign_t} (H{h}{star})")

        sav_list = self.ashtakavarga.get("sav", [])
        sav_summary = f"{sav_list}"
        if sav_list and len(sav_list) == 12:
            max_bindus = max(sav_list)
            min_bindus = min(sav_list)
            max_houses = [f"H{i+1}" for i, v in enumerate(sav_list) if v == max_bindus]
            min_houses = [f"H{i+1}" for i, v in enumerate(sav_list) if v == min_bindus]
            sav_summary += f" (Peak: {', '.join(max_houses)} @ {max_bindus} | Low: {', '.join(min_houses)} @ {min_bindus})"

        md_lines.extend([
            "\n### Key Aspects & Transits",
            f"- **Parashari Drishti:** {', '.join(parashari_items) if parashari_items else 'None prominent'}",
            f"- **Tajika Aspects:** {', '.join(aspect_list[:8]) if aspect_list else 'None prominent'}",
            f"- **Transits from Moon (*=Auspicious):** {' | '.join(transits_summary_items) if transits_summary_items else 'None'}",
            f"- **SAV Bindus (Houses 1-12):** {sav_summary}"
        ])

        return "\n".join(md_lines)

    def generate_lean_json(self) -> dict:
        name = self.subject.get("name", "Unknown Subject")
        birth = self.subject.get("birth_data", {})
        is_sid = AstroMath.is_sidereal_mode(self.report_mode)
        asc_sign = self.local_sky.sidereal_ascendant_sign if is_sid else self.local_sky.tropical_ascendant_sign
        asc_lon = self.local_sky.sidereal_ascendant if is_sid else self.local_sky.tropical_ascendant
        asc_deg = round(asc_lon % 30, 1)
        asc_sid_lon = self.local_sky.sidereal_ascendant
        asc_nak = AstroMath.get_nakshatra(asc_sid_lon)
        asc_pada = AstroMath.get_nakshatra_pada(asc_sid_lon)

        current_dasha, next_antardasha = self.get_current_dasha()

        karaka_map = {}
        for p, kdata in self.jaimini_karakas.items():
            full_role = kdata.get("role", "")
            base_role = full_role.split(" ")[0] if full_role else ""
            karaka_map[p] = self.KARAKA_FULL_DESCRIPTIONS.get(base_role, full_role)

        sun_lon = None
        if "Sun" in self.chart:
            sun_obj = self.chart["Sun"]
            sun_lon = sun_obj.sidereal_longitude if is_sid else sun_obj.tropical_longitude

        planet_summaries = self._build_planet_summaries(is_sid, asc_sign, karaka_map, sun_lon)
        compact_planets = {}
        for s in planet_summaries:
            p_name = s["name"]
            compact_planets[p_name] = {
                "sign": s["sign"],
                "house": s["house"],
                "placed_in_house": s["house"],
                "deg": s["deg"],
                "nakshatra": s["nakshatra"],
                "nakshatra_pada": s["nakshatra_pada"],
                "dignity": s["dignity"],
                "is_retrograde": s["is_retrograde"],
                "is_combust": s["is_combust"],
                "ruled_houses": s["ruled_houses"],
                "rules_houses": s["rules_houses"],
                "is_yogakaraka": s["is_yogakaraka"],
                "power": s["power_level"] if s["power_level"] else "N/A",
                "bala": round(s["bala_total"], 1) if s["bala_total"] is not None else None,
                "d9": s["d9"],
                "d10": s["d10"],
                "karaka": s["karaka"],
                "takeaway": s["takeaway"] if s["takeaway"] != "-" else None,
                "avasthas": s["compact_avasthas"] or None
            }

        compact_yogas = []
        seen_results = set()
        active_keys = set(k for k, v in self.yogas.items() if v.get("active"))
        for y_name, y_data in self.yogas.items():
            if not y_data.get("active"):
                continue

            if y_name.startswith("Generic "):
                base_name = y_name[8:]
                if base_name in active_keys:
                    continue

            results_text = y_data.get("results", "")
            if results_text in seen_results:
                continue
            seen_results.add(results_text)

            details_raw = y_data.get("details", "")
            planets_matched = details_raw.replace("Matching planets:", "").strip().rstrip(".")
            compact_yogas.append({
                "name": y_name,
                "planets": planets_matched or "Chart",
                "results": results_text
            })

        seen_aspects = set()
        compact_aspects = []
        for p1, targets in self.planetary_aspects.get("tajika", {}).items():
            for t in targets:
                p2 = t.get("target")
                pair = tuple(sorted([p1, p2]))
                if pair not in seen_aspects:
                    seen_aspects.add(pair)
                    asp_name = t.get("aspect", "").lower()
                    orb = round(t.get("orb", 0.0), 1)
                    compact_aspects.append(f"{pair[0]} {asp_name} {pair[1]} (orb {orb}°)")

        parashari_items = []
        for p1, targets in self.planetary_aspects.get("parashari", {}).items():
            if not targets:
                continue
            aspect_groups = {}
            for t in targets:
                t_name = t.get("target")
                if not t_name:
                    continue
                raw_asp = t.get("aspect", "").replace(" (Special)", "").replace(" (Universal)", "").strip()
                asp_clean = raw_asp.replace("3th", "3rd").replace("2th", "2nd").replace("1th", "1st")
                aspect_groups.setdefault(asp_clean, []).append(t_name)
            for asp_clean, names in aspect_groups.items():
                parashari_items.append(f"{p1} aspects {', '.join(names)} ({asp_clean})")

        compact_transits = {}
        for p, d in self.transits.items():
            compact_transits[p] = {
                "sign": d.get("transit_sign"),
                "house_from_moon": d.get("house_from_moon"),
                "is_auspicious": d.get("is_auspicious")
            }

        tithi_p = self.panchanga.get("tithi", {})
        return {
            "subject": {
                "name": name,
                "birth": f"{birth.get('date', '')} {birth.get('time', '')}".strip(),
                "timezone": birth.get("timezone", ""),
                "coordinates": [birth.get("latitude"), birth.get("longitude")]
            },
            "ascendant": {
                "sign": asc_sign,
                "degree_in_house": asc_deg,
                "nakshatra": asc_nak,
                "nakshatra_pada": asc_pada,
                "d9": VargaEngine.calculate_d9(asc_lon) if self.report_mode != "Tropical Focus" else None,
                "d10": VargaEngine.calculate_d10(asc_lon) if self.report_mode != "Tropical Focus" else None
            },
            "current_dasha": current_dasha,
            "next_antardasha": next_antardasha,
            "planets": compact_planets,
            "active_yogas": compact_yogas,
            "key_aspects": compact_aspects,
            "parashari_aspects": parashari_items,
            "transits": compact_transits,
            "panchanga": {
                "tithi": f"{tithi_p.get('paksha', '')} {tithi_p.get('name', '')}".strip(),
                "nakshatra": self.panchanga.get("nakshatra", {}).get("name", ""),
                "vara": self.panchanga.get("vara", {}).get("name", ""),
                "yoga": self.panchanga.get("yoga", {}).get("name", "")
            },
            "sav_bindus": self.ashtakavarga.get("sav", [])
        }

    def export_markdown(self, output_path: str | Path) -> str:
        content = self.generate_markdown()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return content

    def export_lean_json(self, output_path: str | Path) -> dict:
        content = self.generate_lean_json()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
        return content


# --- 12. UNIFIED CHART PIPELINE & ORCHESTRATION API ---

@dataclass
class ChartResult:
    """
    Structured outcome of a complete astrological chart calculation.
    Supports attribute access, dict export, artifact compilation, and tuple unpacking.
    """
    chart: dict[str, Planet]
    local_sky: HouseEngine
    epoch_time: AstroTime
    planets_data: list[dict[str, Any]]
    ascendant_data: dict[str, Any]
    houses_data: dict[str, Any]
    ashtakavarga: dict[str, Any]
    yogas: dict[str, Any]
    jaimini_karakas: dict[str, Any]
    panchanga: dict[str, Any]
    planetary_synthesis: dict[str, Any]
    planetary_aspects: dict[str, Any]
    planetary_friendships: dict[str, Any]
    vimshottari_dasha: list[dict[str, Any]]
    transits: dict[str, Any] | None = None
    mode: str = "Tropical-Vedic"
    house_system: str | int = "W"
    ayanamsa: str | int = 36
    subject: dict[str, Any] = field(default_factory=dict)

    def __iter__(self):
        """Allows unpacking as (chart, local_sky, yogas, ashtakavarga, jaimini, panchanga, synthesis, aspects)."""
        yield self.chart
        yield self.local_sky
        yield self.yogas
        yield self.ashtakavarga
        yield self.jaimini_karakas
        yield self.panchanga
        yield self.planetary_synthesis
        yield self.planetary_aspects

    def to_profile_dict(
        self,
        metadata: dict[str, Any] | None = None,
        subject: dict[str, Any] | None = None,
        fingerprint: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Assembles and returns the full JSON-serializable profile dictionary."""
        subj = subject if subject is not None else self.subject
        meta = metadata if metadata is not None else {
            "engine": "AstrologyEngine v2.0 (Swiss Ephemeris Native)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "report_mode": self.mode,
                "house_system": self.house_system,
                "ayanamsa": self.ayanamsa
            }
        }
        json_chart_data = {
            "ascendant": self.ascendant_data,
            "planets": self.planets_data,
            "houses": self.houses_data,
            "ashtakavarga": self.ashtakavarga,
            "yogas": self.yogas,
            "transits": self.transits or {},
            "vimshottari_dasha": self.vimshottari_dasha,
            "jaimini_karakas": self.jaimini_karakas,
            "panchanga": self.panchanga,
            "planetary_synthesis": self.planetary_synthesis,
            "planetary_aspects": self.planetary_aspects
        }
        profile = {
            "metadata": meta,
            "subject": subj,
            "astrological_chart": json_chart_data,
            "planetary_friendships": self.planetary_friendships
        }
        if fingerprint:
            profile["fingerprint"] = fingerprint
        return profile

    def export_all(
        self,
        output_dir: str | Path,
        filename_prefix: str,
        template_path: str | Path | None = None,
        metadata: dict[str, Any] | None = None,
        fingerprint: dict[str, Any] | None = None
    ) -> dict[str, Path]:
        """
        Exports all artifacts (JSON profile, SLM markdown context, lean JSON, and HTML report)
        into output_dir. Returns a dict mapping artifact name to its Path.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = out_dir / f"{filename_prefix}_astrology_profile.json"
        profile_data = self.to_profile_dict(metadata=metadata, fingerprint=fingerprint)
        json_path.write_text(json.dumps(profile_data, indent=4, ensure_ascii=False), encoding="utf-8")

        llm_exporter = LLMContextExporter(
            subject_profile=self.subject,
            chart=self.chart,
            local_sky=self.local_sky,
            report_mode=self.mode,
            yogas=self.yogas,
            dasha_periods=self.vimshottari_dasha,
            transits=self.transits or {},
            panchanga=self.panchanga,
            ashtakavarga=self.ashtakavarga,
            jaimini_karakas=self.jaimini_karakas,
            planetary_synthesis=self.planetary_synthesis,
            planetary_aspects=self.planetary_aspects
        )
        md_path = out_dir / f"{filename_prefix}_llm_context.md"
        llm_exporter.export_markdown(md_path)

        lean_json_path = out_dir / f"{filename_prefix}_llm_payload.json"
        llm_exporter.export_lean_json(lean_json_path)

        html_path = out_dir / f"{filename_prefix}_report.html"
        tpl_path = Path(template_path) if template_path else Path("report_template.html").resolve()
        if tpl_path.exists():
            reporter = HTMLReporter(profile_data, tpl_path)
            reporter.compile_report(html_path)

        return {
            "json": json_path,
            "markdown": md_path,
            "lean_json": lean_json_path,
            "html": html_path
        }


class AstrologyPipeline:
    """
    Unified high-level orchestrator that executes the complete birth chart calculation pipeline.
    """

    @classmethod
    def calculate(
        cls,
        year: int,
        month: int,
        day: int,
        hour: float | str,
        tz: float | str,
        lat: float,
        lon: float,
        mode: str = "Tropical-Vedic",
        house_system: str | int = "W",
        ayanamsa: str | int = 36,
        yogas_rules_path: str | Path | None = None,
        subject: dict[str, Any] | None = None,
        transit_time: AstroTime | None = None,
        compute_transits: bool = True
    ) -> ChartResult:
        # 1. Ephemeris & House calculation
        epoch_time = AstroTime(year, month, day, hour, tz, sid_mode=ayanamsa)
        local_sky = HouseEngine(epoch_time, lat, lon, house_system=house_system)
        chart = ChartFactory.create_chart(epoch_time, mode=mode)

        # 2. Cache house placements
        for obj in chart.values():
            obj.tropical_house = AstroMath.get_house_placement(obj.tropical_longitude, local_sky.houses, False)
            obj.vedic_house = AstroMath.get_house_placement(obj.sidereal_longitude, local_sky.houses, True)

        # 3. Shadbala & Avasthas
        is_sid = AstroMath.is_sidereal_mode(mode)
        for name, obj in chart.items():
            h_num = obj.vedic_house if is_sid else obj.tropical_house
            obj.shadbala = ShadbalaEngine.get_complete_shadbala(name, obj, chart, local_sky.houses, h_num, mode)
            obj.avasthas = AvasthaEngine.get_planet_avasthas(name, obj, chart, local_sky, mode)

        # 4. Formulate planets payload array
        planets_data = []
        for name, obj in chart.items():
            is_retro = (getattr(obj, "sidereal_speed", 0.0) < 0) if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            is_combust = getattr(obj, "avasthas", {}).get("diptadi", {}).get("is_combust", False)
            if mode == "Tropical-Vedic":
                planets_data.append({
                    "name": name,
                    "tropical_sign": obj.zodiac_sign,
                    "tropical_house": obj.tropical_house,
                    "tropical_degree_in_house": round(AstroMath.get_degree_in_house(obj.tropical_longitude, obj.tropical_house, local_sky.houses, False), 4),
                    "vargas": obj.vargas,
                    "dignity": obj.dignity,
                    "shadbala": obj.shadbala,
                    "avasthas": getattr(obj, "avasthas", {}),
                    "sidereal_nakshatra": obj.nakshatra,
                    "sidereal_longitude": round(obj.sidereal_longitude, 4),
                    "tropical_longitude": round(obj.tropical_longitude, 4),
                    "is_retrograde": is_retro,
                    "is_combust": is_combust
                })
            else:
                planets_data.append({
                    "name": name,
                    "tropical_sign": obj.zodiac_sign,
                    "tropical_house": obj.tropical_house,
                    "tropical_degree_in_house": round(AstroMath.get_degree_in_house(obj.tropical_longitude, obj.tropical_house, local_sky.houses, False), 4),
                    "vargas": obj.vargas,
                    "sidereal_nakshatra": obj.nakshatra,
                    "sidereal_sign": obj.sidereal_sign,
                    "vedic_house": obj.vedic_house,
                    "vedic_degree_in_house": round(AstroMath.get_degree_in_house(obj.sidereal_longitude, obj.vedic_house, local_sky.houses, True), 4),
                    "dignity": obj.dignity,
                    "tropical_dignity": obj.tropical_dignity,
                    "sidereal_dignity": obj.sidereal_dignity,
                    "shadbala": obj.shadbala,
                    "avasthas": getattr(obj, "avasthas", {}),
                    "sidereal_longitude": round(obj.sidereal_longitude, 4),
                    "tropical_longitude": round(obj.tropical_longitude, 4),
                    "is_retrograde": is_retro,
                    "is_combust": is_combust
                })

        # 5. Formulate ascendant and houses payload
        asc_deg_trop = round(AstroMath.get_degree_in_house(local_sky.tropical_ascendant, 1, local_sky.houses, False), 4)
        asc_deg_sid = round(AstroMath.get_degree_in_house(local_sky.sidereal_ascendant, 1, local_sky.houses, True), 4)
        if mode == "Tropical-Vedic":
            ascendant_data = {
                "tropical_sign": local_sky.tropical_ascendant_sign,
                "tropical_longitude": round(local_sky.tropical_ascendant, 4),
                "tropical_degree_in_house": asc_deg_trop,
                "sidereal_sign": local_sky.sidereal_ascendant_sign,
                "sidereal_longitude": round(local_sky.sidereal_ascendant, 4),
                "sidereal_degree_in_house": asc_deg_sid,
                "sidereal_nakshatra": AstroMath.get_nakshatra(local_sky.sidereal_ascendant),
                "nakshatra_pada": AstroMath.get_nakshatra_pada(local_sky.sidereal_ascendant)
            }
            houses_data = {
                str(h): {"tropical_start": local_sky.houses[h]["tropical_start"]}
                for h in local_sky.houses
            }
        else:
            ascendant_data = {
                "tropical_sign": local_sky.tropical_ascendant_sign,
                "tropical_longitude": round(local_sky.tropical_ascendant, 4),
                "tropical_degree_in_house": asc_deg_trop,
                "sidereal_sign": local_sky.sidereal_ascendant_sign,
                "sidereal_longitude": round(local_sky.sidereal_ascendant, 4),
                "sidereal_degree_in_house": asc_deg_sid,
                "sidereal_nakshatra": AstroMath.get_nakshatra(local_sky.sidereal_ascendant),
                "nakshatra_pada": AstroMath.get_nakshatra_pada(local_sky.sidereal_ascendant)
            }
            houses_data = {str(h): local_sky.houses[h] for h in local_sky.houses}

        # 6. Ashtakavarga
        ashtakavarga = AshtakavargaEngine.calculate_ashtakavarga(chart, local_sky, mode)

        # 7. Yogas & Subject metadata
        subject_info = copy.deepcopy(subject) if subject else {"name": "Subject", "gender": "Unknown"}
        if "birth_data" not in subject_info:
            hour_str = f"{int(hour):02d}:{int(round((hour % 1) * 60)):02d}" if isinstance(hour, (int, float)) else str(hour)
            subject_info["birth_data"] = {
                "date": f"{year:04d}-{month:02d}-{day:02d}",
                "time": hour_str,
                "timezone": str(tz),
                "latitude": lat,
                "longitude": lon
            }
        rules_path = Path(yogas_rules_path) if yogas_rules_path else Path("yogas").resolve()
        if not rules_path.exists():
            alt_path = Path(__file__).resolve().parent / "yogas"
            if alt_path.exists():
                rules_path = alt_path
        yogas = YogaEngine.scan_yogas(chart, local_sky, mode, rules_path, subject_info)

        # 8. Jaimini Karakas, Panchanga, Synthesis, Aspects
        jaimini_karakas = JaiminiEngine.get_karakas(chart, mode=mode)
        panchanga = PanchangaEngine.calculate_panchanga(epoch_time, chart, lat, lon)
        planetary_synthesis = PlanetarySynthesisEngine.calculate_synthesis(chart, local_sky, mode, ashtakavarga=ashtakavarga)
        planetary_aspects = AspectEngine.calculate_aspects(chart, mode, local_sky=local_sky)

        # 9. Planetary Compound Friendships
        planetary_friendships = {}
        classical = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        for p1 in classical:
            planetary_friendships[p1] = {}
            for p2 in classical:
                if p1 == p2:
                    continue
                h1 = chart[p1].vedic_house if is_sid else chart[p1].tropical_house
                h2 = chart[p2].vedic_house if is_sid else chart[p2].tropical_house
                planetary_friendships[p1][p2] = FriendshipEngine.get_panchadha_relationship(p1, p2, h1, h2)

        # 10. Vimshottari Dasha
        moon_nak = chart["Moon"].nakshatra
        moon_sid_lon = chart["Moon"].sidereal_longitude
        vimshottari_dasha = VimshottariDashaEngine(epoch_time, moon_nak, moon_sid_lon).dasha_periods

        # 11. Transits
        transits = None
        if compute_transits:
            if transit_time is None:
                now_utc = datetime.now(timezone.utc)
                dec_hour = now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0
                transit_time = AstroTime(now_utc.year, now_utc.month, now_utc.day, dec_hour, 0.0, sid_mode=ayanamsa)
            transit_chart = ChartFactory.create_chart(transit_time, mode=mode)
            transits = GocharaEngine.evaluate_transits(chart, transit_chart, mode)

        return ChartResult(
            chart=chart,
            local_sky=local_sky,
            epoch_time=epoch_time,
            planets_data=planets_data,
            ascendant_data=ascendant_data,
            houses_data=houses_data,
            ashtakavarga=ashtakavarga,
            yogas=yogas,
            jaimini_karakas=jaimini_karakas,
            panchanga=panchanga,
            planetary_synthesis=planetary_synthesis,
            planetary_aspects=planetary_aspects,
            planetary_friendships=planetary_friendships,
            vimshottari_dasha=vimshottari_dasha,
            transits=transits,
            mode=mode,
            house_system=house_system,
            ayanamsa=ayanamsa,
            subject=subject_info
        )




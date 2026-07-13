import os
import json
import time
import urllib.request
import urllib.error
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Features expected by our data processing pipeline
N2YO_FEATURES = [
    "satlatitude",
    "satlongitude",
    "sataltitude",
    "azimuth",
    "elevation",
    "ra",
    "dec"
]

def get_mock_positions(norad_id: int, seconds: int) -> list[dict]:
    import math
    import random
    
    now = int(time.time())
    positions = []
    
    # Seed based on norad_id to keep the orbit shape stable
    rng = random.Random(norad_id)
    phase_lat = rng.uniform(0, 2 * math.pi)
    phase_lng = rng.uniform(0, 2 * math.pi)
    phase_alt = rng.uniform(0, 2 * math.pi)
    
    for i in range(seconds):
        t = now - (seconds - 1 - i)
        # Orbiter period ~ 90 mins (5400s)
        angle_lat = phase_lat + (t / 5400.0) * 2.0 * math.pi
        angle_lng = phase_lng + (t / 5400.0) * 2.0 * math.pi
        
        lat = 65.0 * math.sin(angle_lat)
        lng = 180.0 * math.cos(angle_lng / 2.0)
        if lng > 180.0:
            lng -= 360.0
        elif lng < -180.0:
            lng += 360.0
            
        alt = 400.0 + 30.0 * math.sin(phase_alt + (t / 1800.0))
        
        az = (180.0 + 180.0 * math.sin(t / 600.0)) % 360.0
        el = max(0.0, 45.0 * math.sin(t / 1200.0))
        ra = (180.0 + 180.0 * math.cos(t / 600.0)) % 360.0
        dec = 45.0 * math.sin(t / 800.0)
        
        positions.append({
            "satlatitude": lat,
            "satlongitude": lng,
            "sataltitude": alt,
            "azimuth": az,
            "elevation": el,
            "ra": ra,
            "dec": dec,
            "timestamp": t
        })
        
    return positions


def fetch_n2yo_positions(
    norad_id: int, 
    seconds: int = 200, 
    api_key: str = None,
    observer_lat: float = 0.0,
    observer_lng: float = 0.0,
    observer_alt: float = 0.0
) -> tuple[list[dict], str]:
    """
    Fetch live positions for a satellite from the N2YO REST API.
    Raises ValueError or RuntimeError if API key is missing or request fails.
    """
    if not api_key:
        raise ValueError("N2YO API Key is not set. Please configure it in the settings panel.")

    # Clamp seconds to N2YO limits [1, 300]
    seconds = max(1, min(seconds, 300))
    url = (
        f"https://api.n2yo.com/rest/v1/satellite/positions/"
        f"{norad_id}/{observer_lat}/{observer_lng}/{observer_alt}/{seconds}/&apiKey={api_key}"
    )

    logger.info(f"Fetching live satellite positions from N2YO (NORAD: {norad_id})...")
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0"}
    )
    with urllib.request.urlopen(req, timeout=10.0) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP Error {response.status} from N2YO API")
        raw_data = json.loads(response.read().decode("utf-8"))
        
        # Check for API errors reported inside the JSON response
        if "error" in raw_data:
            raise ValueError(f"N2YO API Error: {raw_data['error']}")
            
        positions = raw_data.get("positions", [])
        if not positions:
            raise ValueError("N2YO returned empty position list")
            
        logger.info(f"Successfully fetched {len(positions)} points from N2YO.")
        return positions, "n2yo_api"


# Normalization factors mapping raw coordinates/angles to [-1.0, 1.0] range
NORMALIZATION_FACTORS = {
    "satlatitude": 90.0,
    "satlongitude": 180.0,
    "sataltitude": 1000.0,
    "azimuth": 360.0,
    "elevation": 90.0,
    "ra": 360.0,
    "dec": 90.0
}

def process_n2yo_to_matrix(positions: list[dict]) -> tuple[list[list[float]], list[dict]]:
    """
    Converts list of N2YO position data into:
    1. A 2D feature matrix of 25 spacecraft telemetry features (aligned to expected feats, normalized).
    2. A list of metadata dictionaries containing raw physical values (temperatures, battery state, etc.).
    """
    matrix = []
    metadata = []
    
    # Initialize physical simulation states
    battery_charge = 85.0
    battery_temp = 20.0
    solar_current = 0.0
    transmitter_temp = 35.0
    wheel_speed_x = 1200.0
    wheel_speed_y = 1100.0
    wheel_speed_z = 1150.0
    propellant_pressure = 450.0
    cpu_load = 0.18

    # SECURITY FIX: Use local RNG instance instead of global seed
    _rng = np.random.default_rng(42)

    for idx, pos in enumerate(positions):
        # 1. Base N2YO orbital position inputs
        lat_raw = float(pos.get("satlatitude", 0.0))
        lng_raw = float(pos.get("satlongitude", 0.0))
        alt_raw = float(pos.get("sataltitude", 0.0))
        az_raw = float(pos.get("azimuth", 0.0))
        el_raw = float(pos.get("elevation", 0.0))
        ra_raw = float(pos.get("ra", 0.0))
        dec_raw = float(pos.get("dec", 0.0))
        timestamp = int(pos.get("timestamp", int(time.time())))

        # Normalise base features
        lat_norm = lat_raw / 90.0
        lng_norm = lng_raw / 180.0
        alt_norm = alt_raw / 1000.0
        az_norm = az_raw / 360.0
        el_norm = el_raw / 90.0
        ra_norm = ra_raw / 360.0
        dec_norm = dec_raw / 90.0

        # 2. Eclipse State Estimation (Approx. based on UTC hour & longitude)
        hour_offset = lng_raw / 15.0
        local_hour = ((timestamp / 3600.0) + hour_offset) % 24.0
        in_sunlight = 1.0 if (6.0 <= local_hour <= 18.0) else -1.0

        # 3. Sequential Evolve Physics
        # Solar Current
        solar_current = (10.2 + 0.3 * np.sin(idx * 0.1)) if in_sunlight > 0 else 0.0
        
        # Battery state
        if in_sunlight > 0:
            battery_charge = min(100.0, battery_charge + 0.12)
            battery_temp += 0.08 * (38.0 - battery_temp) + float(_rng.normal(0, 0.05))
        else:
            battery_charge = max(18.0, battery_charge - 0.08)
            battery_temp += 0.04 * (-6.0 - battery_temp) + float(_rng.normal(0, 0.05))

        # Transmitter and CPU activity
        comm_strength = max(0.0, min(1.0, el_raw / 75.0)) if el_raw > 0 else 0.0
        transmitter_temp += 0.05 * (32.0 + (12.0 * comm_strength) - transmitter_temp) + float(_rng.normal(0, 0.08))
        cpu_load = 0.12 + 0.08 * comm_strength + float(_rng.normal(0, 0.02))

        # Attitude Control (Reaction wheels & gyros)
        wheel_speed_x += 8.0 * np.cos(idx * 0.18) + float(_rng.normal(0, 0.5))
        wheel_speed_y += 5.0 * np.sin(idx * 0.12) + float(_rng.normal(0, 0.5))
        wheel_speed_z += 6.0 * np.cos(idx * 0.22) + float(_rng.normal(0, 0.5))
        gyro_roll = 0.01 * np.sin(idx * 0.1)
        gyro_pitch = 0.008 * np.cos(idx * 0.12)
        gyro_yaw = 0.006 * np.sin(idx * 0.08)
        magnetorquer_x = 0.15 * np.sin(idx * 0.08)
        magnetorquer_y = 0.15 * np.cos(idx * 0.08)
        magnetorquer_z = 0.15 * np.sin(idx * 0.12)

        # Propellant pressure & thrusters
        propellant_pressure = max(50.0, propellant_pressure - 0.008)
        thruster_temp = 14.0 + 4.0 * np.cos(idx * 0.04)

        # 4. Inject Subsystem Anomalies dynamically to simulate real-world errors
        # We inject specific anomalies at set windows of the timeline
        anomaly_type = None
        
        display_battery_temp = battery_temp
        display_cpu_load = cpu_load
        display_wheel_speed_x = wheel_speed_x
        display_gyro_roll = gyro_roll
        display_solar_current = solar_current
        display_battery_charge = battery_charge
        
        # Thermal Anomaly (indices 65 to 85)
        if 65 <= idx <= 85:
            anomaly_type = "thermal_overheat"
            display_battery_temp = battery_temp + 45.0 + float(_rng.normal(0, 1.0))
            display_cpu_load = min(1.0, cpu_load + 0.65)
        
        # Attitude Control Drift / Saturation Anomaly (indices 125 to 140)
        elif 125 <= idx <= 140:
            anomaly_type = "attitude_drift"
            display_wheel_speed_x = wheel_speed_x + 3500.0 + float(_rng.normal(0, 10.0))
            display_gyro_roll = gyro_roll + 0.25 + float(_rng.normal(0, 0.02))

        # Power array solar dropout (indices 165 to 180)
        elif 165 <= idx <= 180 and in_sunlight > 0:
            anomaly_type = "solar_array_dropout"
            display_solar_current = 0.15 + float(_rng.normal(0, 0.05))
            display_battery_charge = max(18.0, battery_charge - 20.0)

        # Build feature vector matching SMAP model 25-feature expectation
        row = [
            lat_norm,                   # 0
            lng_norm,                   # 1
            alt_norm,                   # 2
            az_norm,                    # 3
            el_norm,                    # 4
            ra_norm,                    # 5
            dec_norm,                   # 6
            in_sunlight,                # 7
            display_solar_current / 12.0,       # 8
            (display_battery_charge / 100.0),   # 9
            (display_battery_temp + 20.0) / 100.0, # 10
            (transmitter_temp) / 80.0,  # 11
            comm_strength,              # 12
            display_cpu_load,           # 13
            display_wheel_speed_x / 5000.0,     # 14
            wheel_speed_y / 5000.0,     # 15
            wheel_speed_z / 5000.0,     # 16
            magnetorquer_x,             # 17
            magnetorquer_y,             # 18
            magnetorquer_z,             # 19
            display_gyro_roll * 4.0,    # 20
            gyro_pitch * 4.0,           # 21
            gyro_yaw * 4.0,             # 22
            propellant_pressure / 500.0,# 23
            thruster_temp / 50.0        # 24
        ]
        
        matrix.append([round(val, 6) for val in row])
        
        metadata.append({
            "index": idx,
            "timestamp": timestamp,
            "lat": round(lat_raw, 4),
            "lng": round(lng_raw, 4),
            "alt": round(alt_raw, 1),
            "sunlight": "SUNLIGHT" if in_sunlight > 0 else "ECLIPSE",
            "battery_charge": round(display_battery_charge, 1),
            "battery_temp": round(display_battery_temp, 1),
            "solar_current": round(display_solar_current, 2),
            "comm_strength": round(comm_strength * 100, 1),
            "wheel_speed_x": round(display_wheel_speed_x, 1),
            "cpu_load": round(display_cpu_load * 100, 1),
            "anomaly_type": anomaly_type
        })
        
    return matrix, metadata


def get_mock_passes(norad_id: int, satname: str = "SATELLITE") -> dict:
    import time
    import random
    now = int(time.time())
    passes = []
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    # Use deterministic random seed based on satellite ID to keep predictions stable across refetches
    rng = random.Random(norad_id)
    
    for i in range(5):
        # Passes spaced out in the next 48 hours
        start_delay = 1800 + i * 28800 + rng.randint(-3600, 3600)
        duration = 500 + rng.randint(-120, 120)
        
        start_utc = now + start_delay
        max_utc = start_utc + duration // 2
        end_utc = start_utc + duration
        
        passes.append({
            "startAz": round(rng.uniform(0, 360), 1),
            "startAzCompass": rng.choice(directions),
            "startEl": 0.0,
            "startUTC": start_utc,
            "maxAz": round(rng.uniform(0, 360), 1),
            "maxAzCompass": rng.choice(directions),
            "maxEl": round(rng.uniform(15, 85), 1),
            "maxUTC": max_utc,
            "endAz": round(rng.uniform(0, 360), 1),
            "endAzCompass": rng.choice(directions),
            "endEl": 0.0,
            "endUTC": end_utc
        })
        
    return {
        "info": {
            "satid": norad_id,
            "satname": satname,
            "transactionscount": 0
        },
        "passes": passes
    }


def fetch_n2yo_passes(
    norad_id: int,
    observer_lat: float,
    observer_lng: float,
    observer_alt: float,
    days: int = 2,
    min_elevation: float = 10.0,
    api_key: str = None
) -> dict:
    if not api_key:
        raise ValueError("N2YO API Key is not set. Please configure it in the settings panel.")

    days = max(1, min(days, 10))
    min_elevation = max(0.0, min(min_elevation, 90.0))
    
    url = (
        f"https://api.n2yo.com/rest/v1/satellite/radiopasses/"
        f"{norad_id}/{observer_lat}/{observer_lng}/{observer_alt}/{days}/{min_elevation}/&apiKey={api_key}"
    )

    logger.info(f"Fetching radio passes from N2YO (NORAD: {norad_id})...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0"}
    )
    with urllib.request.urlopen(req, timeout=8.0) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP Error {response.status} from N2YO API")
        raw_data = json.loads(response.read().decode("utf-8"))
        if "error" in raw_data:
            raise ValueError(f"N2YO API Error: {raw_data['error']}")
        return raw_data


def fetch_n2yo_tle(norad_id: int, api_key: str = None) -> dict:
    if not api_key:
        if norad_id == 25544:
            try:
                logger.info("N2YO API Key is missing. Attempting Celestrak fallback for ISS TLE...")
                celestrak_url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=json"
                req = urllib.request.Request(
                    celestrak_url,
                    headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0"}
                )
                with urllib.request.urlopen(req, timeout=8.0) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        if isinstance(data, list) and len(data) > 0:
                            tle_data = data[0]
                            # Reconstruct standard 2-line TLE format string
                            line1 = f"1 25544U {tle_data.get('CLASSIFICATION_TYPE', 'U')} {tle_data.get('OBJECT_ID', '98067A')}   26001.00000000  .00000000  00000-0  00000-0 0  9999"
                            line2 = f"2 25544  51.6443  18.1460 0001968  62.1930  41.5165 15.49253457256241"
                            # Attempt to use real coordinates if possible, otherwise use standard ISS elements
                            inclination = tle_data.get('INCLINATION', 51.6443)
                            raan = tle_data.get('RA_OF_ASC_NODE', 18.1460)
                            ecc = tle_data.get('ECCENTRICITY', 0.0001968)
                            ecc_str = f"{int(float(ecc) * 10000000):07d}" if float(ecc) < 1.0 else "0001968"
                            arg_pe = tle_data.get('ARG_OF_PERICENTER', 62.1930)
                            mean_anom = tle_data.get('MEAN_ANOMALY', 41.5165)
                            mean_motion = tle_data.get('MEAN_MOTION', 15.49253457)
                            line2 = f"2 25544 {inclination:8.4f} {raan:8.4f} {ecc_str} {arg_pe:8.4f} {mean_anom:8.4f} {mean_motion:11.8f}99999"
                            return {
                                "info": {
                                    "satid": 25544,
                                    "satname": tle_data.get("OBJECT_NAME", "SPACE STATION"),
                                    "transactionscount": 0
                                },
                                "tle": f"{line1}\n{line2}"
                            }
            except Exception as e:
                logger.warning(f"Failed to fetch fallback TLE from Celestrak: {e}")
        raise ValueError("N2YO API Key is not set. Please configure it in the settings panel.")

    url = (
        f"https://api.n2yo.com/rest/v1/satellite/tle/"
        f"{norad_id}/&apiKey={api_key}"
    )

    logger.info(f"Fetching TLE from N2YO (NORAD: {norad_id})...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0"}
    )
    with urllib.request.urlopen(req, timeout=8.0) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP Error {response.status} from N2YO API")
        raw_data = json.loads(response.read().decode("utf-8"))
        if "error" in raw_data:
            raise ValueError(f"N2YO API Error: {raw_data['error']}")
        return raw_data


def fetch_n2yo_visual_passes(
    norad_id: int,
    observer_lat: float,
    observer_lng: float,
    observer_alt: float,
    days: int = 2,
    min_visibility: int = 300,
    api_key: str = None
) -> dict:
    if not api_key:
        raise ValueError("N2YO API Key is not set. Please configure it in the settings panel.")

    days = max(1, min(days, 10))
    min_visibility = max(1, min_visibility)
    
    url = (
        f"https://api.n2yo.com/rest/v1/satellite/visualpasses/"
        f"{norad_id}/{observer_lat}/{observer_lng}/{observer_alt}/{days}/{min_visibility}/&apiKey={api_key}"
    )

    logger.info(f"Fetching visual passes from N2YO (NORAD: {norad_id})...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0"}
    )
    with urllib.request.urlopen(req, timeout=8.0) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP Error {response.status} from N2YO API")
        raw_data = json.loads(response.read().decode("utf-8"))
        if "error" in raw_data:
            raise ValueError(f"N2YO API Error: {raw_data['error']}")
        return raw_data


def fetch_n2yo_above(
    observer_lat: float,
    observer_lng: float,
    observer_alt: float,
    search_radius: float = 70.0,
    category_id: int = 0,
    api_key: str = None
) -> dict:
    if not api_key:
        raise ValueError("N2YO API Key is not set. Please configure it in the settings panel.")

    search_radius = max(0.0, min(search_radius, 90.0))
    
    url = (
        f"https://api.n2yo.com/rest/v1/satellite/above/"
        f"{observer_lat}/{observer_lng}/{observer_alt}/{search_radius}/{category_id}/&apiKey={api_key}"
    )

    logger.info(f"Fetching satellites above from N2YO (Category: {category_id}, Radius: {search_radius})...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0"}
    )
    with urllib.request.urlopen(req, timeout=8.0) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP Error {response.status} from N2YO API")
        raw_data = json.loads(response.read().decode("utf-8"))
        if "error" in raw_data:
            raise ValueError(f"N2YO API Error: {raw_data['error']}")
        return raw_data





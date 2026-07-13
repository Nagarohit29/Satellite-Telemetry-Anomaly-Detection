import os
import json
import time
import urllib.request
import urllib.error
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "celestrak_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_DURATION_SECS = 12 * 60 * 60  # 12 hours

# Standard orbital parameter features to extract
FEATURES = [
    "MEAN_MOTION",
    "ECCENTRICITY",
    "INCLINATION",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "BSTAR"
]

# Quick mock generator in case of network offline issues
def get_mock_satellite(name, index, catnr=None):
    import random
    # Generate stable orbital parameters with subtle variations
    random.seed(index)
    mean_motion = 15.0 + random.uniform(-0.5, 0.5)
    eccentricity = 0.0001 + random.uniform(0, 0.001)
    inclination = 51.6 + random.uniform(-2.0, 2.0)
    ra_of_asc_node = random.uniform(0, 360)
    arg_of_pericenter = random.uniform(0, 360)
    mean_anomaly = random.uniform(0, 360)
    bstar = 0.0001 * random.uniform(0.5, 1.5)
    
    # Introduce random anomalies for about 5% of satellites
    is_anomalous = (index % 17 == 0)
    if is_anomalous:
        # Tweak parameters to make it an outlier
        mean_motion += random.choice([-2.5, 2.5])
        eccentricity += 0.015
        inclination += random.choice([-10.0, 10.0])
        bstar *= 10.0

    return {
        "OBJECT_NAME": name,
        "OBJECT_ID": f"2026-{index:03d}A",
        "NORAD_CAT_ID": catnr or (25000 + index),
        "MEAN_MOTION": mean_motion,
        "ECCENTRICITY": eccentricity,
        "INCLINATION": inclination,
        "RA_OF_ASC_NODE": ra_of_asc_node,
        "ARG_OF_PERICENTER": arg_of_pericenter,
        "MEAN_ANOMALY": mean_anomaly,
        "BSTAR": bstar
    }

def get_mock_constellation(group):
    # Generates a constellation array
    count = 120 if group == "starlink" else 60
    name_prefix = group.upper()
    return [get_mock_satellite(f"{name_prefix}-{i}", i) for i in range(1, count + 1)]

def _fetch_from_api(url, cache_path):
    """Fetch from CelesTrak API with 5 second timeout and save to cache."""
    try:
        logger.info(f"Fetching live orbital data from CelesTrak: {url}")
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "SatelliteTelemetryAnomalyDetection/2.0 (GoogleDeepMind pair programming project)"}
        )
        with urllib.request.urlopen(req, timeout=8.0) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP Error {response.status}")
            data = json.loads(response.read().decode("utf-8"))
            
            # Save to cache
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data
    except Exception as e:
        logger.warning(f"CelesTrak live fetch failed: {str(e)}. Attempting cache read or mock generation.")
        return None

def get_celestrak_constellation(group: str) -> list:
    """Fetch all orbital elements for a satellite constellation group (e.g. starlink, noaa, gps-ops)."""
    group = group.strip().lower()
    cache_file = os.path.join(CACHE_DIR, f"group_{group}.json")
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=json"

    # Check cache validity
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < CACHE_DURATION_SECS:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read cache file {cache_file}: {e}")

    # Fetch live
    data = _fetch_from_api(url, cache_file)
    if data is not None:
        return data

    # Use expired cache if available as secondary fallback
    if os.path.exists(cache_file):
        try:
            logger.info("Using expired CelesTrak cache as fallback.")
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Final fallback: Mock data generator
    logger.info(f"Generating mock constellation for {group}")
    return get_mock_constellation(group)

def get_celestrak_satellite_history(catnr: int) -> list:
    """Fetch orbital history/current elements for a single satellite by NORAD ID."""
    cache_file = os.path.join(CACHE_DIR, f"sat_{catnr}.json")
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=json"

    # Check cache validity
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < CACHE_DURATION_SECS:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read cache file {cache_file}: {e}")

    # Fetch live
    data = _fetch_from_api(url, cache_file)
    if data is not None:
        # Wrap single satellite result in list if not already
        return data if isinstance(data, list) else [data]

    # Use expired cache if available as secondary fallback
    if os.path.exists(cache_file):
        try:
            logger.info("Using expired single-sat CelesTrak cache as fallback.")
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                return cached if isinstance(cached, list) else [cached]
        except Exception:
            pass

    # Final fallback: Mock historical epochs for the satellite
    logger.info(f"Generating mock tracking timeline for satellite {catnr}")
    history = []
    # Generate 50 simulated historical snapshots (epochs) for this satellite
    for i in range(100):
        sat = get_mock_satellite(f"SAT-{catnr}", i, catnr)
        # Tweak parameters over time to make it look like a timeline
        sat["EPOCH"] = f"2026-06-04T{i//4:02d}:{(i%4)*15:02d}:00.000000"
        # Add subtle drift
        sat["INCLINATION"] += 0.001 * i
        sat["MEAN_MOTION"] -= 0.0002 * i
        history.append(sat)
    return history

def process_satellite_data_to_matrix(sat_list: list) -> tuple[list, list]:
    """
    Converts list of satellite objects to:
    1. A 2D feature matrix (list of lists) with columns aligned to FEATURES.
    2. A list of metadata labels (names/IDs/epochs).
    """
    matrix = []
    metadata = []

    for idx, sat in enumerate(sat_list):
        row = []
        for feature in FEATURES:
            val = sat.get(feature, 0.0)
            # Standardize string representations of floats (e.g. in JSON some numbers are floats, some might be strings)
            try:
                row.append(float(val))
            except (ValueError, TypeError):
                row.append(0.0)
        
        matrix.append(row)
        
        # Store metadata
        name = sat.get("OBJECT_NAME", f"SAT-{idx}")
        cat_id = sat.get("NORAD_CAT_ID", f"UNKNOWN-{idx}")
        epoch = sat.get("EPOCH", "N/A")
        metadata.append({
            "name": name,
            "norad_id": cat_id,
            "epoch": epoch,
            "object_id": sat.get("OBJECT_ID", "")
        })

    return matrix, metadata

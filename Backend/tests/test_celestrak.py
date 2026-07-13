import sys
import os
import unittest
import numpy as np

# Add parent and Backend paths to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from src.celestrak_service import (
    get_celestrak_constellation,
    get_celestrak_satellite_history,
    process_satellite_data_to_matrix,
    FEATURES
)
from serve import adapt_input_features

class TestCelestrakService(unittest.TestCase):
    
    def test_constellation_fetching(self):
        """Test retrieving constellation satellites (mock or live) and validating keys."""
        sats = get_celestrak_constellation("starlink")
        self.assertIsInstance(sats, list)
        self.assertGreater(len(sats), 0)
        
        # Test first satellite has standard keys
        first_sat = sats[0]
        self.assertIn("OBJECT_NAME", first_sat)
        self.assertIn("MEAN_MOTION", first_sat)
        self.assertIn("ECCENTRICITY", first_sat)

    def test_single_satellite_history(self):
        """Test retrieving single satellite history (mock or live)."""
        history = get_celestrak_satellite_history(25544) # ISS NORAD ID
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        
        # Verify timeline ordering/data structure
        for entry in history:
            self.assertIn("NORAD_CAT_ID", entry)
            self.assertEqual(int(entry["NORAD_CAT_ID"]), 25544)

    def test_processing_to_matrix(self):
        """Test parsing satellite lists into 2D matrices and metadata list."""
        sats = [
            {
                "OBJECT_NAME": "TEST-SAT-1",
                "NORAD_CAT_ID": 10001,
                "EPOCH": "2026-06-04T12:00:00.000",
                "MEAN_MOTION": 15.2,
                "ECCENTRICITY": 0.0005,
                "INCLINATION": 51.6,
                "RA_OF_ASC_NODE": 10.0,
                "ARG_OF_PERICENTER": 20.0,
                "MEAN_ANOMALY": 30.0,
                "BSTAR": 0.0001
            },
            {
                "OBJECT_NAME": "TEST-SAT-2",
                "NORAD_CAT_ID": 10002,
                "EPOCH": "2026-06-04T13:00:00.000",
                "MEAN_MOTION": "15.4", # Test string parsing
                "ECCENTRICITY": 0.0006,
                "INCLINATION": 51.8,
                "RA_OF_ASC_NODE": 11.0,
                "ARG_OF_PERICENTER": 21.0,
                "MEAN_ANOMALY": "31.0", # Test string parsing
                "BSTAR": None # Test null/missing parsing
            }
        ]
        
        matrix, metadata = process_satellite_data_to_matrix(sats)
        
        self.assertEqual(len(matrix), 2)
        self.assertEqual(len(metadata), 2)
        
        # Check values
        self.assertEqual(matrix[0][0], 15.2) # MEAN_MOTION
        self.assertEqual(matrix[0][1], 0.0005) # ECCENTRICITY
        self.assertEqual(matrix[1][0], 15.4) # MEAN_MOTION parsed as float
        self.assertEqual(matrix[1][6], 0.0) # BSTAR (None replaced with 0.0)
        
        # Check metadata
        self.assertEqual(metadata[0]["name"], "TEST-SAT-1")
        self.assertEqual(metadata[0]["norad_id"], 10001)

    def test_feature_adaptation_padding(self):
        """Test that adapt_input_features pads a 7-feature matrix to target size (e.g. 25)."""
        raw_matrix = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]]
        data = np.array(raw_matrix)
        
        expected_feats = 25
        prepared, original_feats = adapt_input_features(data, expected_feats)
        
        self.assertEqual(prepared.shape[1], expected_feats)
        self.assertEqual(original_feats, 7)
        # Check that original elements are intact and padded with zeros
        self.assertEqual(prepared[0][0], 1.0)
        self.assertEqual(prepared[0][6], 7.0)
        self.assertEqual(prepared[0][7], 0.0)

if __name__ == "__main__":
    unittest.main()

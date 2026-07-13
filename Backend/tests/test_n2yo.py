import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from src.n2yo_service import (
    process_n2yo_to_matrix,
    fetch_n2yo_positions,
    fetch_n2yo_passes
)

class TestN2yoService(unittest.TestCase):
    def test_fetch_raises_without_key(self):
        """Test that fetching live positions without an API key raises a ValueError."""
        with self.assertRaises(ValueError):
            fetch_n2yo_positions(norad_id=25544, seconds=50, api_key=None)

    @patch("urllib.request.urlopen")
    def test_fetch_n2yo_positions_url(self, mock_urlopen):
        """Verify the constructed URL for positions has the correct trailing slash."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"positions": [{"satlatitude": 10.0, "satlongitude": 20.0, "sataltitude": 400.0, "azimuth": 180.0, "elevation": 45.0, "ra": 12.0, "dec": 23.0, "timestamp": 123456789}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        positions, source = fetch_n2yo_positions(
            norad_id=25544,
            seconds=50,
            api_key="test_api_key_123",
            observer_lat=12.34,
            observer_lng=56.78,
            observer_alt=100.0
        )

        self.assertEqual(len(positions), 1)
        self.assertEqual(source, "n2yo_api")
        
        # Verify constructed URL passed to Request
        called_args, called_kwargs = mock_urlopen.call_args
        request_obj = called_args[0]
        self.assertEqual(
            request_obj.full_url,
            "https://api.n2yo.com/rest/v1/satellite/positions/25544/12.34/56.78/100.0/50/&apiKey=test_api_key_123"
        )

    @patch("urllib.request.urlopen")
    def test_fetch_n2yo_passes_url(self, mock_urlopen):
        """Verify the constructed URL for passes has the correct trailing slash."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"info": {"satid": 25544}, "passes": []}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = fetch_n2yo_passes(
            norad_id=25544,
            observer_lat=12.34,
            observer_lng=56.78,
            observer_alt=100.0,
            days=3,
            min_elevation=15.0,
            api_key="test_api_key_123"
        )

        self.assertEqual(res["info"]["satid"], 25544)
        
        # Verify constructed URL passed to Request
        called_args, called_kwargs = mock_urlopen.call_args
        request_obj = called_args[0]
        self.assertEqual(
            request_obj.full_url,
            "https://api.n2yo.com/rest/v1/satellite/radiopasses/25544/12.34/56.78/100.0/3/15.0/&apiKey=test_api_key_123"
        )

    def test_process_to_matrix(self):
        """Test processing position dict list into a 2D float feature matrix."""
        # Mock some positions returned by N2YO API
        positions = [
            {
                "satlatitude": 51.6, "satlongitude": 12.3, "sataltitude": 420.5,
                "azimuth": 180.2, "elevation": 45.3, "ra": 12.5, "dec": 23.4,
                "timestamp": 1780556000 + i
            }
            for i in range(10)
        ]
        matrix, metadata = process_n2yo_to_matrix(positions)
        
        self.assertEqual(len(matrix), 10)
        self.assertEqual(len(metadata), 10)
        self.assertEqual(len(matrix[0]), 25) # 25 physical telemetry features
        
        for row in matrix:
            self.assertTrue(all(isinstance(v, float) for v in row))
            self.assertEqual(len(row), 25)

if __name__ == "__main__":
    unittest.main()


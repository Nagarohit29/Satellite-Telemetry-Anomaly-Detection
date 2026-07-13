import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json

# Add Middleware path to sys.path
middleware_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(middleware_dir)

from services.llm_service import chat_with_llm, execute_n2yo_tool

class TestChatTools(unittest.TestCase):
    
    @patch.dict(os.environ, {"N2YO_API_KEY": ""})
    def test_execute_n2yo_tool_raises_without_key(self):
        """Test execute_n2yo_tool returns error message if key is missing."""
        res = execute_n2yo_tool("n2yo_get_live_position", {"norad_id": 25544}, 0.0, 0.0, 0.0)
        self.assertIn("N2YO API key is missing", res)

    @patch("urllib.request.urlopen")
    @patch.dict(os.environ, {"N2YO_API_KEY": "dummy_n2yo_api_key"})
    def test_execute_n2yo_tool_live_position(self, mock_urlopen):
        """Test n2yo_get_live_position parses arguments and calls correct url with headers."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "source": "n2yo_api",
            "metadata": [
                {
                    "lat": 12.34, "lng": 56.78, "alt": 420.0,
                    "azimuth": 180.0, "elevation": 45.0, "sunlight": "SUNLIGHT",
                    "timestamp": 123456789
                }
            ]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = execute_n2yo_tool(
            "n2yo_get_live_position", 
            {"norad_id": 25544, "seconds": 10}, 
            37.77, -122.41, 100.0
        )
        
        # Verify URL called has correct structure
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertIn("telemetry/N2YO-25544", req.full_url)
        self.assertIn("length=10", req.full_url)
        self.assertEqual(req.get_header("X-n2yo-api-key"), "dummy_n2yo_api_key")

        # Verify output parsing
        parsed = json.loads(res)
        self.assertEqual(parsed["satellite_id"], 25544)
        self.assertEqual(parsed["latest_position"]["latitude"], 12.34)
        self.assertEqual(parsed["latest_position"]["sunlight_state"], "SUNLIGHT")

    @patch("urllib.request.urlopen")
    @patch.dict(os.environ, {"N2YO_API_KEY": "dummy_n2yo_api_key"})
    def test_execute_n2yo_tool_radio_passes(self, mock_urlopen):
        """Test n2yo_get_radio_passes parses arguments and calls correct url."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "info": {"satid": 25544, "satname": "ISS"},
            "passes": []
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = execute_n2yo_tool(
            "n2yo_get_radio_passes", 
            {"norad_id": 25544, "days": 5, "min_elevation": 20.0}, 
            37.77, -122.41, 100.0
        )
        
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertIn("satellite/25544/passes", req.full_url)
        self.assertIn("days=5", req.full_url)
        self.assertIn("min_elevation=20.0", req.full_url)
        self.assertEqual(req.get_header("X-n2yo-api-key"), "dummy_n2yo_api_key")

        parsed = json.loads(res)
        self.assertEqual(parsed["info"]["satname"], "ISS")

    def test_chat_with_llm_validates_missing_model(self):
        """Test chat_with_llm returns validation warning when model preference is empty."""
        res = chat_with_llm(messages=[], model_preference=None)
        self.assertEqual(res, "API key is missing or select the model.")

if __name__ == "__main__":
    unittest.main()

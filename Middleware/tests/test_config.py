import sys
import os
import unittest
import json
from fastapi.testclient import TestClient

# Add parent and Middleware paths to sys.path
middleware_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(middleware_dir)

from main import app

class TestConfigRouter(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)

    def test_local_ollama_config_lifecycle(self):
        """Test getting and updating the local Ollama configurations."""
        # 1. Fetch current config
        response = self.client.get("/api/config/local-ollama")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("model", data)
        self.assertIn("api_base", data)

        # 2. Update to new config (do not persist to .env during testing to preserve user's local config)
        payload = {
            "model": "test-model-name-xyz",
            "api_base": "http://localhost:9999",
            "persist": False
        }
        update_resp = self.client.post("/api/config/local-ollama", json=payload)
        self.assertEqual(update_resp.status_code, 200)
        
        # 3. Verify changes were applied in memory
        get_resp = self.client.get("/api/config/local-ollama")
        self.assertEqual(get_resp.status_code, 200)
        updated_data = get_resp.json()
        self.assertEqual(updated_data["model"], "test-model-name-xyz")
        self.assertEqual(updated_data["api_base"], "http://localhost:9999")

if __name__ == "__main__":
    unittest.main()

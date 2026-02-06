import sys
import json
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["joblib"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["sklearn.metrics"] = MagicMock()
sys.modules["sklearn.metrics.pairwise"] = MagicMock()

# Mock redis module completely since it's missing in env
mock_redis_module = MagicMock()
mock_redis_module.exceptions.ConnectionError = ConnectionError
mock_redis_module.exceptions.TimeoutError = TimeoutError
sys.modules["redis"] = mock_redis_module

# Mock Redis
class FakeRedis:
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            del self.data[key]

fake_redis = FakeRedis()
mock_config_redis = MagicMock()
mock_config_redis.redis_client = fake_redis
sys.modules["config.redis"] = mock_config_redis

# Mock utils
mock_utils = MagicMock()
mock_utils.preprocess_user_input = lambda x: x.lower()
mock_utils.init = lambda: None
sys.modules["utils"] = mock_utils

import unittest
import main
from main import chat, reset_context

# Patch detect_faq
def mock_detect_faq(q):
    if "bayar" in q and "pajak" in q:
        return "bayar_pajak", "Jawaban Bayar Pajak", 0.9
    return None, None, 0.0
main.detect_faq = mock_detect_faq

class TestNonPBBBug(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_bug_repro"
        reset_context(self.user_id)

    def tearDown(self):
        reset_context(self.user_id)

    def test_reproduce_bug(self):
        print("\n[TEST] Reproducing Non-PBB Bug")
        
        # 1. Trigger "bayar pajak" -> asks "mau bayar pajak apa?"
        response = chat(self.user_id, "aku mau bayar pajak")
        print(f"Bot 1: {response}")
        self.assertIn("mau bayar pajak apa", response)
        
        # 2. Answer "restoran"
        # EXPECTED: Should proceed to ask for NPWPD (bayarNonPBB flow)
        # BUG: Currently fails and falls through to default/FAQ
        response = chat(self.user_id, "restoran")
        print(f"Bot 2: {response}")
        
        # Assert failure (or success if fixed)
        self.assertIn("untuk pajak restoran", response)

if __name__ == "__main__":
    unittest.main()

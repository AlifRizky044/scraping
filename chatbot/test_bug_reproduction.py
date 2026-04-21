import unittest
from unittest.mock import patch

from main import chat, reset_context


def mock_detect_faq(q):
    if "bayar" in q and "pajak" in q:
        return "bayar_pajak", "Jawaban Bayar Pajak", 0.9
    return None, None, 0.0


class TestNonPBBBug(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_bug_repro"
        reset_context(self.user_id)
        self.detect_faq_patcher = patch("main.detect_faq", side_effect=mock_detect_faq)
        self.detect_faq_patcher.start()

    def tearDown(self):
        self.detect_faq_patcher.stop()
        reset_context(self.user_id)

    def test_reproduce_bug(self):
        response = chat(self.user_id, "aku mau bayar pajak")
        self.assertIn("mau bayar pajak apa", response)

        response = chat(self.user_id, "restoran")
        self.assertIn("Nomor Pokok Wajib Pajak Daerah", response)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from main import chat, reset_context


def mock_detect_faq(q):
    if "pajak" in q and "bayar" in q:
        return "bayar_pajak", "Jawaban Bayar Pajak", 0.9
    return None, None, 0.0


class TestNonPBBFlow(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_non_pbb"
        reset_context(self.user_id)
        self.detect_faq_patcher = patch("main.detect_faq", side_effect=mock_detect_faq)
        self.detect_faq_patcher.start()

    def tearDown(self):
        self.detect_faq_patcher.stop()
        reset_context(self.user_id)

    def test_valid_flow(self):
        response = chat(self.user_id, "aku mau bayar pajak")
        self.assertIn("mau bayar pajak apa", response)

        response = chat(self.user_id, "restoran")
        self.assertIn("masukkan Nomor Pokok Wajib Pajak Daerah", response)

        response = chat(self.user_id, "1234567890123456")
        self.assertIn("NPWPD Anda: 1234567890123456", response)
        self.assertIn("masukkan NIK/NIB", response)

        response = chat(self.user_id, "1234567890123456")
        self.assertIn("Masa Pajak", response)
        self.assertIn("Bulan-Tahun", response)

        response = chat(self.user_id, "13-2024")
        self.assertIn("Format Masa Pajak tidak valid", response)

        response = chat(self.user_id, "05-2024")
        self.assertIn("Masa Pajak: 05-2024", response)
        self.assertIn("Apakah data sudah benar", response)

        response = chat(self.user_id, "ya")
        self.assertIn("https://pajak.medan.go.id/bayar/nonpbb", response)


if __name__ == "__main__":
    unittest.main()

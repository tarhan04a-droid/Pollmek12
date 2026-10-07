"""Streamlit uygulama açılış testi (isteğe bağlı).

streamlit kurulu değilse veya app.py yoksa test atlanır.
Çalıştırma (repo kökünden):  python3 -m unittest discover -s tests -p "test_*.py"
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(ROOT, "app.py")

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # streamlit kurulu değil
    AppTest = None


@unittest.skipIf(AppTest is None, "streamlit kurulu değil")
@unittest.skipUnless(os.path.exists(APP_PATH), "app.py yok")
class AppOpensTest(unittest.TestCase):
    def test_app_opens_without_exception(self):
        at = AppTest.from_file(APP_PATH, default_timeout=30).run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])


if __name__ == "__main__":
    unittest.main()

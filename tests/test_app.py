"""Streamlit uygulama testleri (docs/CONTRACT.md "Güncelleme 2" > Uygulama).

streamlit kurulu değilse veya app.py yoksa testler atlanır.
İki adımlı kurulum: Oyuncu A seç -> "Oyuncu B'ye geç" -> Oyuncu B seç -> "Maçı başlat".
Widget'lar etiketleriyle bulunur (anahtar adlarına bağlı değil). Beklenen etiketler:
  "Kategori türü", "Kulüp seç" / "Lig seç" / "Ülke seç", "Formasyon",
  butonlar "Oyuncu B'ye geç", "Maçı başlat".
Çalıştırma (repo kökünden):  python3 -m unittest discover -s tests -p "test_*.py"
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(ROOT, "app.py")

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # streamlit kurulu değil
    AppTest = None

TYPE_LABELS = {"club": "Kulüp", "league": "Lig", "nation": "Ülke"}
TEXT_KINDS = ("markdown", "subheader", "caption", "header", "title", "text",
              "success", "info", "warning", "error", "metric")


def find(at, kind, label):
    matches = [w for w in at.get(kind) if getattr(w, "label", None) == label]
    if not matches:
        raise AssertionError(f"{kind} etiketi bulunamadı: {label!r}")
    return matches[0]


def all_text(at):
    parts = []
    for kind in TEXT_KINDS:
        for el in at.get(kind):
            value = getattr(el, "value", None)
            if isinstance(value, str):
                parts.append(value)
            elif value is not None:
                parts.append(str(value))
    return "\n".join(parts)


def pick(at, ctype, values):
    """Kategori türünü seçer, o türün çoklu seçimine değerleri yazar."""
    find(at, "selectbox", "Kategori türü").set_value(ctype).run()
    find(at, "multiselect", f"{TYPE_LABELS[ctype]} seç").set_value(values).run()
    return at


def selected_total(at):
    """Üç kategori türündeki toplam seçim sayısı (her türe geçip okur)."""
    total = 0
    for ctype in TYPE_LABELS:
        find(at, "selectbox", "Kategori türü").set_value(ctype).run()
        total += len(find(at, "multiselect", f"{TYPE_LABELS[ctype]} seç").value)
    return total


def set_formation(at, formation_id):
    find(at, "selectbox", "Formasyon").set_value(formation_id).run()


def start_app():
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


@unittest.skipIf(AppTest is None, "streamlit kurulu değil")
@unittest.skipUnless(os.path.exists(APP_PATH), "app.py yok")
class AppSetupFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "data", "formations.json"), encoding="utf-8") as fh:
            cls.formation_ids = [f["id"] for f in json.load(fh)]

    def test_app_opens_without_exception(self):
        at = start_app()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])

    def test_default_formation_is_first_in_data(self):
        at = start_app()
        self.assertEqual(find(at, "selectbox", "Formasyon").value, self.formation_ids[0])

    def test_two_step_setup_then_squads_show_each_formation(self):
        at = start_app()

        # 1. adım: Oyuncu A
        pick(at, "club", ["Chelsea"])
        set_formation(at, "4-4-2")
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        find(at, "button", "Oyuncu B'ye geç").click().run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])

        # 2. adım: Oyuncu B (A'nın seçimleri B'de kalmamalı; B kendi seçimini yapar)
        self.assertIn("Oyuncu B", all_text(at))
        pick(at, "league", ["Premier League"])
        set_formation(at, "3-5-2")
        find(at, "button", "Maçı başlat").click().run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])

        text = all_text(at)
        self.assertIn("4-4-2", text)
        self.assertIn("3-5-2", text)
        self.assertEqual(len(at.error), 0, [e.value for e in at.error])

    def test_start_is_not_available_before_side_b_is_set_up(self):
        at = start_app()
        pick(at, "club", ["Chelsea"])
        labels = [getattr(b, "label", None) for b in at.get("button")]
        self.assertIn("Oyuncu B'ye geç", labels)
        self.assertNotIn("Maçı başlat", labels)

    def test_side_b_without_categories_cannot_start(self):
        at = start_app()
        pick(at, "club", ["Chelsea"])
        find(at, "button", "Oyuncu B'ye geç").click().run()
        btn = find(at, "button", "Maçı başlat")
        if btn.disabled:
            return
        btn.click().run()
        self.assertGreater(len(at.error), 0, "0 kategori ile maç başlamamalı")
        self.assertNotIn("Kadrolar", all_text(at))

    def test_fifth_category_is_blocked_with_warning(self):
        at = start_app()
        pick(at, "club", ["Chelsea", "Boca Juniors"])
        pick(at, "league", ["Premier League"])
        pick(at, "nation", ["England"])
        self.assertEqual(selected_total(at), 4)

        # 5. kategori: engellenmeli ve uyarı gösterilmeli.
        pick(at, "club", ["Chelsea", "Boca Juniors", "Nacional"])
        self.assertEqual(selected_total(at), 4)
        self.assertGreater(len(at.warning), 0, "4 kategoriden sonra uyarı bekleniyordu")
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])


if __name__ == "__main__":
    unittest.main()

"""Streamlit uygulama testleri (docs/CONTRACT.md "Güncelleme 3" > Uygulama).

streamlit kurulu değilse veya app.py yoksa testler atlanır.
Akış: kurulum (Oyuncu A -> "Oyuncu B'ye geç" -> Oyuncu B -> "Maçı başlat") -> kadrolar
-> "Takas turlarını başlat" -> takas ("Takası yap") -> koruma ("Korumayı onayla") -> ... -> sonuç.
Koruma ayrı bir ekran değil; her takastan sonra aynı ekranda gelir. Son takastan sonra gelmez.
Widget'lar etiketleriyle bulunur (anahtar adlarına bağlı değil). Beklenen etiketler aşağıdaki
sabitlerde toplandı; app.py farklı etiket kullanırsa yalnızca bu sabitler güncellenir.
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

# Etiket sözleşmesi (app.py ile eşleşmeli)
BTN_NEXT_SIDE = "Oyuncu B'ye geç"
BTN_START_MATCH = "Maçı başlat"
BTN_START_STEALS = "Takas turlarını başlat"
BTN_STEAL = "Takası yap"
BTN_PROTECT = "Korumayı onayla"
SEL_TARGET = "Rakipten alınacak oyuncu"
SEL_GIVE = "Karşılığında verilecek oyuncu"
MULTI_PROTECT = "Korunacak oyuncular"
PROTECT_MAX = 3
TOTAL_STEALS = 6


def find(at, kind, label):
    matches = [w for w in at.get(kind) if getattr(w, "label", None) == label]
    if not matches:
        raise AssertionError(f"{kind} etiketi bulunamadı: {label!r}")
    return matches[0]


def has(at, kind, label):
    return any(getattr(w, "label", None) == label for w in at.get(kind))


def button_labels(at):
    return [getattr(b, "label", None) for b in at.get("button")]


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


def no_exceptions(at):
    return len(at.exception) == 0


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


def setup_two_sides(at):
    """Oyuncu A: Chelsea / 4-4-2; Oyuncu B: Premier League / 3-5-2 -> kadro ekranı."""
    pick(at, "club", ["Chelsea"])
    set_formation(at, "4-4-2")
    find(at, "button", BTN_NEXT_SIDE).click().run()
    pick(at, "league", ["Premier League"])
    set_formation(at, "3-5-2")
    find(at, "button", BTN_START_MATCH).click().run()
    return at


def squad_players(at, side):
    """Oyuncu nesneleri (id, name, pos, rating...) session_state'teki maç durumundan okunur."""
    state = at.session_state["state"]
    return [slot["player"] for slot in state["sides"][side]["slots"]]


def squad_ids(at, side):
    return [p["id"] for p in squad_players(at, side)]


def steal_and_protect(at, keep_first=PROTECT_MAX):
    """Sıradaki takası yapar; takas sonrası koruma çıkarsa ilk `keep_first` oyuncuyu korur.

    Multiselect.options ekranda görünen etiketleri döner; set_value ise oyuncu id'lerini ister.
    Bu yüzden id'ler session_state'ten alınır.
    Döner: (alınan oyuncu id'si veya None, koruma ekranı geldi mi)."""
    target = find(at, "selectbox", SEL_TARGET).value
    find(at, "button", BTN_STEAL).click().run()
    if not has(at, "multiselect", MULTI_PROTECT):
        return target, False
    turn = at.session_state["state"]["turn"]
    chosen = squad_ids(at, turn)[:keep_first]
    find(at, "multiselect", MULTI_PROTECT).set_value(chosen).run()
    find(at, "button", BTN_PROTECT).click().run()
    return target, True


def play_full_match(at):
    """Tüm takasları oynar; her takastan sonra koruma onaylanır. Oynanan takas sayısını döner."""
    steals = 0
    for _ in range(TOTAL_STEALS + 4):
        if not has(at, "button", BTN_STEAL):
            break
        steal_and_protect(at)
        steals += 1
        if not no_exceptions(at):
            break
    return steals


@unittest.skipIf(AppTest is None, "streamlit kurulu değil")
@unittest.skipUnless(os.path.exists(APP_PATH), "app.py yok")
class AppSetupFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "data", "formations.json"), encoding="utf-8") as fh:
            cls.formation_ids = [f["id"] for f in json.load(fh)]

    def test_app_opens_without_exception(self):
        at = start_app()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])

    def test_default_formation_is_first_in_data(self):
        at = start_app()
        self.assertEqual(find(at, "selectbox", "Formasyon").value, self.formation_ids[0])

    def test_two_step_setup_then_squads_show_each_formation(self):
        at = start_app()
        pick(at, "club", ["Chelsea"])
        set_formation(at, "4-4-2")
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        find(at, "button", BTN_NEXT_SIDE).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])

        self.assertIn("Oyuncu B", all_text(at))
        pick(at, "league", ["Premier League"])
        set_formation(at, "3-5-2")
        find(at, "button", BTN_START_MATCH).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])

        text = all_text(at)
        self.assertIn("4-4-2", text)
        self.assertIn("3-5-2", text)
        self.assertEqual(len(at.error), 0, [e.value for e in at.error])

    def test_start_is_not_available_before_side_b_is_set_up(self):
        at = start_app()
        pick(at, "club", ["Chelsea"])
        self.assertIn(BTN_NEXT_SIDE, button_labels(at))
        self.assertNotIn(BTN_START_MATCH, button_labels(at))

    def test_side_b_without_categories_cannot_start(self):
        at = start_app()
        pick(at, "club", ["Chelsea"])
        find(at, "button", BTN_NEXT_SIDE).click().run()
        btn = find(at, "button", BTN_START_MATCH)
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

        pick(at, "club", ["Chelsea", "Boca Juniors", "Nacional"])
        self.assertEqual(selected_total(at), 4)
        self.assertGreater(len(at.warning), 0, "4 kategoriden sonra uyarı bekleniyordu")
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])


@unittest.skipIf(AppTest is None, "streamlit kurulu değil")
@unittest.skipUnless(os.path.exists(APP_PATH), "app.py yok")
class AppStealFlowTest(unittest.TestCase):
    def test_squads_screen_starts_steals_directly_without_protect_screen(self):
        at = setup_two_sides(start_app())
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        labels = button_labels(at)
        self.assertIn(BTN_START_STEALS, labels)
        self.assertNotIn("Koruma aşamasına geç", labels)

    def test_steal_screen_has_no_protect_step_before_the_steal(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertIn("Oyuncu A", all_text(at))
        self.assertTrue(has(at, "button", BTN_STEAL))
        self.assertFalse(has(at, "multiselect", MULTI_PROTECT))

    def test_protect_step_appears_after_steal_and_hands_turn_to_b(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        target, protect_shown = steal_and_protect(at)
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertTrue(protect_shown, "takastan sonra koruma adımı gelmeliydi")
        self.assertIn("Oyuncu B", all_text(at))
        self.assertIn("Kalan takas hakkı", all_text(at))

    def test_newly_stolen_player_can_be_protected(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        target = find(at, "selectbox", SEL_TARGET).value
        find(at, "button", BTN_STEAL).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        turn = at.session_state["state"]["turn"]
        self.assertIn(target, squad_ids(at, turn))
        name = next(p["name"] for p in squad_players(at, turn) if p["id"] == target)
        options = find(at, "multiselect", MULTI_PROTECT).options  # ekran etiketleri
        self.assertTrue(any(name in o and "[yeni]" in o for o in options), options)
        find(at, "multiselect", MULTI_PROTECT).set_value([target]).run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        find(at, "button", BTN_PROTECT).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertIn(target, at.session_state["state"]["sides"][turn]["protected_ids"])

    def test_protect_accepts_empty_selection(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        find(at, "button", BTN_STEAL).click().run()
        find(at, "multiselect", MULTI_PROTECT).set_value([]).run()
        find(at, "button", BTN_PROTECT).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertIn("Oyuncu B", all_text(at))

    def test_full_match_setup_to_result(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        steals = play_full_match(at)

        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(steals, TOTAL_STEALS)
        self.assertFalse(has(at, "button", BTN_STEAL), "takas bitince takas ekranı kalmamalı")
        self.assertFalse(has(at, "multiselect", MULTI_PROTECT),
                         "son takastan sonra koruma adımı gelmemeli")
        text = all_text(at)
        self.assertTrue(any(word in text for word in ("kazandı", "Berabere")), text)
        self.assertIn("Yeni maç", button_labels(at))
        self.assertEqual(len(at.error), 0, [e.value for e in at.error])


if __name__ == "__main__":
    unittest.main()

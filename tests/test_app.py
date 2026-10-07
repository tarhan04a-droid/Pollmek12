"""Streamlit uygulama testleri (docs/CONTRACT.md "Güncelleme 4" > Uygulama).

streamlit kurulu değilse veya app.py yoksa testler atlanır.
Akış: kurulum (Oyuncu A -> "Oyuncu B'ye geç" -> Oyuncu B -> "Maçı başlat") -> kadrolar (ilk 11 +
"Yedekler") -> "Takas turlarını başlat" -> takas ("Takası yap") -> koruma ("Korumayı onayla")
-> ... -> son takas -> arrange ("Düzeni onayla" A, sonra B) -> sonuç.
Kadro düzeni (ilk 11 <-> yedek yer değiştirme) sırası gelen tarafın ekranında "Kadro düzeni"
bölümünde yapılır.

Widget'lar etiketleriyle bulunur. Beklenen etiketler aşağıdaki sabitlerde toplandı; app.py farklı
etiket kullanırsa yalnızca bu sabitler güncellenir. Oyuncu seçimleri (selectbox/multiselect) için
`.options` etiketlerdir, `set_value` ise oyuncu id'si ister; id'ler session_state['state'] üzerinden
alınır.
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
HDR_BENCH = "Yedekler"
HDR_LAYOUT = "Kadro düzeni"
SEL_SLOT = "İlk 11'den oyuncu"
SEL_BENCH = "Yedekten oyuncu"
BTN_SWAP = "Yer değiştir"
BTN_CONFIRM_ARRANGE = "Düzeni onayla"
BTN_NEW_MATCH = "Yeni maç"
PROTECT_MAX = 3
TOTAL_STEALS = 6
BENCH_SIZE = 8
SQUAD_SIZE = 19
OTHER_SIDE = {"A": "B", "B": "A"}


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
    """İlk 11 oyuncu nesneleri (id, name, pos, rating...) session_state'teki maç durumundan okunur."""
    state = at.session_state["state"]
    return [slot["player"] for slot in state["sides"][side]["slots"]]


def squad_ids(at, side):
    return [p["id"] for p in squad_players(at, side)]


def bench_players(at, side):
    return at.session_state["state"]["sides"][side]["bench"]


def bench_ids(at, side):
    return [p["id"] for p in bench_players(at, side)]


def steal_and_protect(at, keep_first=PROTECT_MAX):
    """Sıradaki takası yapar; takas sonrası koruma çıkarsa ilk `keep_first` oyuncuyu korur.

    Döner: (alınan oyuncu id'si, koruma ekranı geldi mi)."""
    state = at.session_state["state"]
    turn = state["turn"]
    other = OTHER_SIDE[turn]
    # Seçimler id ile yapılır: hedef rakipten korumasız ilk oyuncu, karşılık kendi korumasız ilk oyuncusu.
    target = next(pid for pid in squad_ids(at, other) + bench_ids(at, other)
                  if pid not in state["sides"][other]["protected_ids"])
    give = next(pid for pid in squad_ids(at, turn) + bench_ids(at, turn)
                if pid not in state["sides"][turn]["protected_ids"])
    find(at, "selectbox", SEL_TARGET).set_value(target).run()
    find(at, "selectbox", SEL_GIVE).set_value(give).run()
    find(at, "button", BTN_STEAL).click().run()
    if not has(at, "multiselect", MULTI_PROTECT):
        return target, False
    turn = at.session_state["state"]["turn"]
    chosen = (squad_ids(at, turn) + bench_ids(at, turn))[:keep_first]
    find(at, "multiselect", MULTI_PROTECT).set_value(chosen).run()
    find(at, "button", BTN_PROTECT).click().run()
    return target, True


def swap_by_index(at, slot_idx, bench_idx):
    """Kadro düzeni bölümünde ilk 11 (slot_idx) ile yedek (bench_idx) yer değiştirir.
    Bu selectbox'ların değerleri oyuncu id'si değil, listedeki indekstir."""
    find(at, "selectbox", SEL_SLOT).set_value(slot_idx).run()
    find(at, "selectbox", SEL_BENCH).set_value(bench_idx).run()
    find(at, "button", BTN_SWAP).click().run()


def finish_arrangement(at):
    """Her iki taraf da "Düzeni onayla" der (A, sonra B)."""
    for _ in range(2):
        if not has(at, "button", BTN_CONFIRM_ARRANGE):
            break
        find(at, "button", BTN_CONFIRM_ARRANGE).click().run()
        if not no_exceptions(at):
            break


def play_full_match(at):
    """Tüm takasları oynar, düzeni onaylatır. Oynanan takas sayısını döner."""
    if has(at, "button", BTN_START_STEALS):
        find(at, "button", BTN_START_STEALS).click().run()
    steals = 0
    for _ in range(TOTAL_STEALS + 4):
        if not has(at, "button", BTN_STEAL):
            break
        steal_and_protect(at)
        steals += 1
        if not no_exceptions(at):
            break
    finish_arrangement(at)
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
class AppSquadTest(unittest.TestCase):
    def test_squad_screen_shows_eight_bench_players_per_side(self):
        at = setup_two_sides(start_app())
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertIn(HDR_BENCH, all_text(at))
        for side in ("A", "B"):
            self.assertEqual(len(bench_players(at, side)), BENCH_SIZE)
            self.assertEqual(len(squad_ids(at, side)) + len(bench_ids(at, side)), SQUAD_SIZE)
            for player in bench_players(at, side):
                self.assertIn(player["name"], all_text(at))

    def test_steal_selectors_list_all_nineteen_players(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(len(find(at, "selectbox", SEL_TARGET).options), SQUAD_SIZE)
        self.assertEqual(len(find(at, "selectbox", SEL_GIVE).options), SQUAD_SIZE)
        # Uygulama yedekleri küçük harfle "[yedek]" olarak etiketler; büyük/küçük harf duyarsız ara.
        target_opts = find(at, "selectbox", SEL_TARGET).options
        self.assertEqual(sum("yedek" in o.lower() for o in target_opts), BENCH_SIZE)

    def test_protect_selector_lists_all_nineteen_players(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        find(at, "button", BTN_STEAL).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(len(find(at, "multiselect", MULTI_PROTECT).options), SQUAD_SIZE)

    def test_bench_player_can_be_protected(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        find(at, "button", BTN_STEAL).click().run()
        turn = at.session_state["state"]["turn"]
        bench_pid = bench_ids(at, turn)[0]
        find(at, "multiselect", MULTI_PROTECT).set_value([bench_pid]).run()
        find(at, "button", BTN_PROTECT).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(at.session_state["state"]["sides"][turn]["protected_ids"], [bench_pid])


@unittest.skipIf(AppTest is None, "streamlit kurulu değil")
@unittest.skipUnless(os.path.exists(APP_PATH), "app.py yok")
class AppArrangeSwapTest(unittest.TestCase):
    def test_layout_section_swaps_slot_with_bench_player(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        turn = at.session_state["state"]["turn"]
        slot_pid = squad_ids(at, turn)[0]
        bench_pid = bench_ids(at, turn)[0]

        self.assertIn(HDR_LAYOUT, all_text(at))
        swap_by_index(at, 0, 0)

        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(squad_ids(at, turn)[0], bench_pid)
        self.assertEqual(bench_ids(at, turn)[0], slot_pid)

    def test_layout_warns_when_positions_do_not_match(self):
        at = setup_two_sides(start_app())
        find(at, "button", BTN_START_STEALS).click().run()
        turn = at.session_state["state"]["turn"]
        slots = squad_players(at, turn)
        bench = bench_players(at, turn)
        pair = next(((si, bi) for si, s in enumerate(slots) for bi, b in enumerate(bench)
                     if s["pos"] != b["pos"] and s["pos"] not in b.get("alt", [])), None)
        if pair is None:
            self.skipTest("uyumsuz pozisyonlu yedek-ilk11 çifti yok")
        slot_idx, bench_idx = pair
        find(at, "selectbox", SEL_SLOT).set_value(slot_idx).run()
        find(at, "selectbox", SEL_BENCH).set_value(bench_idx).run()
        # Sayfada her zaman bulunan uyarılardan ayırmak için uyumsuzluk metnine bak.
        self.assertTrue(any("Uyumsuz" in w.value for w in at.warning),
                        [w.value for w in at.warning])



@unittest.skipIf(AppTest is None, "streamlit kurulu değil")
@unittest.skipUnless(os.path.exists(APP_PATH), "app.py yok")
class AppArrangeAndResultTest(unittest.TestCase):
    def play_until_arrange(self, at):
        find(at, "button", BTN_START_STEALS).click().run()
        steals = 0
        while has(at, "button", BTN_STEAL) and steals < TOTAL_STEALS:
            steal_and_protect(at)
            steals += 1
            self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        return steals

    def test_last_steal_shows_arrange_screen_not_protect(self):
        at = setup_two_sides(start_app())
        steals = self.play_until_arrange(at)
        self.assertEqual(steals, TOTAL_STEALS)
        self.assertEqual(at.session_state["state"]["phase"], "arrange")
        self.assertFalse(has(at, "multiselect", MULTI_PROTECT))
        self.assertIn(BTN_CONFIRM_ARRANGE, button_labels(at))
        self.assertIn("Oyuncu A", all_text(at))

    def test_arrange_confirms_a_then_b_then_shows_result(self):
        at = setup_two_sides(start_app())
        self.play_until_arrange(at)

        find(at, "button", BTN_CONFIRM_ARRANGE).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(at.session_state["state"]["phase"], "arrange")
        self.assertEqual(at.session_state["state"]["arranged"], {"A": True, "B": False})
        self.assertIn("Oyuncu B", all_text(at))

        find(at, "button", BTN_CONFIRM_ARRANGE).click().run()
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(at.session_state["state"]["phase"], "done")
        self.assertFalse(has(at, "button", BTN_CONFIRM_ARRANGE))

    def test_arrange_allows_layout_swaps_for_both_sides(self):
        at = setup_two_sides(start_app())
        self.play_until_arrange(at)
        side = "A"
        bench_pid = bench_ids(at, side)[1]
        swap_by_index(at, 1, 1)
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(squad_ids(at, side)[1], bench_pid)

        find(at, "button", BTN_CONFIRM_ARRANGE).click().run()
        self.assertEqual(at.session_state["state"]["arranged"], {"A": True, "B": False})
        side = "B"
        bench_pid = bench_ids(at, side)[2]
        swap_by_index(at, 2, 2)
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(squad_ids(at, side)[2], bench_pid)

    def test_result_screen_shows_winner_and_bench_players(self):
        at = setup_two_sides(start_app())
        steals = play_full_match(at)
        self.assertTrue(no_exceptions(at), [e.value for e in at.exception])
        self.assertEqual(steals, TOTAL_STEALS)
        self.assertEqual(at.session_state["state"]["phase"], "done")
        text = all_text(at)
        self.assertTrue(any(word in text for word in ("kazandı", "Berabere")), text)
        self.assertIn(HDR_BENCH, text)
        for side in ("A", "B"):
            for player in bench_players(at, side):
                self.assertIn(player["name"], text)
        self.assertIn(BTN_NEW_MATCH, button_labels(at))
        self.assertEqual(len(at.error), 0, [e.value for e in at.error])


if __name__ == "__main__":
    unittest.main()

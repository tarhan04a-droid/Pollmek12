"""Streamlit sürümü motor testleri (docs/CONTRACT.md "Güncelleme 6" > Motor).

Yalnızca standart unittest. engine.py repo kökünde olmalı; bu dosya kökü sys.path'e ekler.
Güncelleme 6: her taraf 11 ilk 11 + 8 yedek + 4 rezerv = 23 oyuncu alır. Takas ve koruma üç
gruptan herhangi birini kapsar (23 oyuncu). Yerleştirme: swap_bench (ilk 11 <-> yedek) ve
swap_reserve (yedek <-> rezerv). Takım puanı ilk 11 (slot_score) + 8 yedek (düz rating)
ortalamasıdır (19 oyuncu); rezervler puana girmez. Kalite penceresi (varsayılan 10) kaleci
slotunda 90/80/71/68 örneğiyle test edilir.
Çalıştırma (repo kökünden):  python3 -m unittest discover -s tests -p "test_*.py"
"""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import (  # noqa: E402
    confirm_arrange,
    create_match,
    protect,
    result,
    slot_score,
    steal,
    swap_bench,
    swap_reserve,
    team_rating,
)

FIRST_ELEVEN = 11
BENCH_SIZE = 8
RESERVE_SIZE = 4
SQUAD_SIZE = FIRST_ELEVEN + BENCH_SIZE + RESERVE_SIZE  # 23
PROTECT_COUNT = 3
STEALS_PER_SIDE = 3
QUALITY_WINDOW = 10
SIDES = ("A", "B")
OTHER = {"A": "B", "B": "A"}

FORMATION_433 = {
    "id": "4-3-3",
    "slots": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"],
}
FORMATION_442 = {
    "id": "4-4-2",
    "slots": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"],
}
FORMATION_352 = {
    "id": "3-5-2",
    "slots": ["GK", "CB", "CB", "CB", "LM", "CDM", "CAM", "CM", "RM", "ST", "ST"],
}
FORMATION_4231 = {
    "id": "4-2-3-1",
    "slots": ["GK", "LB", "CB", "CB", "RB", "CDM", "CDM", "LW", "CAM", "RW", "ST"],
}
LABELS = ["GK", "LB", "CB", "RB", "CM", "CDM", "CAM", "LM", "RM", "LW", "RW", "ST"]
OUTFIELD_LABELS = [label for label in LABELS if label != "GK"]
PLAYERS_PATH = os.path.join(ROOT, "data", "players.json")


# ---------------------------------------------------------------- veri yardımcıları

def make_player(pid, pos, club="Alpha", league="L1", nation="Nationa", rating=75, alt=None):
    return {
        "id": str(pid),
        "name": f"Oyuncu {pid}",
        "pos": pos,
        "alt": list(alt or []),
        "rating": rating,
        "club": club,
        "league": league,
        "nation": nation,
        "pac": 70, "sho": 70, "pas": 70, "dri": 70, "def": 70, "phy": 70,
    }


def make_pool(prefix, club, count=120, labels=LABELS, base=70):
    """Aynı kulüpte, pozisyonları döngüsel dağılmış, puanları 70-89 arası oyuncular."""
    players = []
    for i in range(count):
        pos = labels[i % len(labels)]
        players.append(make_player(f"{prefix}{i:03d}", pos, club=club,
                                   rating=base + (i * 7) % 20))
    return players


def gk_pool(prefix, club):
    """Dört kaleci (90, 80, 71, 68) + kalesiz bol oyuncu."""
    keepers = [make_player(f"{prefix}gk{r}", "GK", club=club, rating=r) for r in (90, 80, 71, 68)]
    return keepers + make_pool(prefix, club, count=120, labels=OUTFIELD_LABELS)


def setup(club, formation):
    return {"categories": [{"type": "club", "value": club}], "formation": formation}


def two_side_setups(a_club="Alpha", b_club="Beta", a_formation=FORMATION_433,
                    b_formation=FORMATION_442):
    return {"A": setup(a_club, a_formation), "B": setup(b_club, b_formation)}


def base_players():
    return make_pool("a", "Alpha") + make_pool("b", "Beta")


def new_match(seed=1, **kwargs):
    return create_match(base_players(), two_side_setups(), seed=seed, **kwargs)


def side_players(side_state):
    return ([s["player"] for s in side_state["slots"]]
            + list(side_state["bench"]) + list(side_state["reserves"]))


def side_ids(side_state):
    return [p["id"] for p in side_players(side_state)]


def slot_ids(side_state):
    return [s["player"]["id"] for s in side_state["slots"]]


def bench_ids(side_state):
    return [p["id"] for p in side_state["bench"]]


def reserve_ids(side_state):
    return [p["id"] for p in side_state["reserves"]]


def unprotected_ids(side_state):
    protected = set(side_state["protected_ids"])
    return [pid for pid in side_ids(side_state) if pid not in protected]


def expected_team(state, side):
    """Güncelleme 6 kuralının doğrudan karşılığı: ilk 11 slot_score + 8 yedek rating, 19'a bölünür."""
    s = state["sides"][side]
    total = sum(slot_score(x["pos"], x["player"]) for x in s["slots"])
    total += sum(p["rating"] for p in s["bench"])
    return round(total / (len(s["slots"]) + len(s["bench"])))


def play_round(state):
    """Sıradaki takası yapar (ilk korumasız hedef ve verilen); takastan sonra koruma adımı
    gelirse ilk PROTECT_COUNT kendi oyuncusunu korur."""
    turn = state["turn"]
    foe = OTHER[turn]
    target = unprotected_ids(state["sides"][foe])[0]
    give = unprotected_ids(state["sides"][turn])[0]
    state = steal(state, turn, target, give)
    if state["phase"] == "steal":
        state = protect(state, turn, side_ids(state["sides"][turn])[:PROTECT_COUNT])
    return state


def play_until_arrange(state):
    """Takas turlarını sonuna kadar oynar; faz "arrange" olunca döner."""
    while state["phase"] == "steal":
        state = play_round(state)
    return state


def play_full_match(state):
    """Tüm takasları oynar, sonra iki tarafın düzenini onaylatır. (son state, takas sayısı)."""
    steals = 0
    while state["phase"] == "steal":
        state = play_round(state)
        steals += 1
    state = confirm_arrange(state, "A")
    state = confirm_arrange(state, "B")
    return state, steals


def manual_player(pid, pos, rating, alt=None):
    return make_player(pid, pos, rating=rating, alt=alt)


def manual_side(slot_entries, bench, reserves=()):
    """slot_entries: [(slot_pos, player)] listesi."""
    return {
        "slots": [{"pos": pos, "player": player} for pos, player in slot_entries],
        "bench": list(bench),
        "reserves": list(reserves),
        "protected_ids": [],
    }


def manual_state(side_a, side_b, phase="done"):
    return {"phase": phase, "sides": {"A": side_a, "B": side_b}}


# ---------------------------------------------------------------- kurulum

class CreateMatchTests(unittest.TestCase):
    def test_each_side_gets_eleven_eight_bench_and_four_reserves(self):
        state = new_match()
        for side in SIDES:
            s = state["sides"][side]
            self.assertEqual(len(s["slots"]), FIRST_ELEVEN)
            self.assertEqual(len(s["bench"]), BENCH_SIZE)
            self.assertEqual(len(s["reserves"]), RESERVE_SIZE)
            self.assertEqual(len(side_ids(s)), SQUAD_SIZE)
            self.assertEqual(s["protected_ids"], [])

    def test_no_player_shared_between_sides_or_groups(self):
        state = new_match()
        ids = side_ids(state["sides"]["A"]) + side_ids(state["sides"]["B"])
        self.assertEqual(len(ids), 2 * SQUAD_SIZE)
        self.assertEqual(len(set(ids)), len(ids))

    def test_slot_positions_follow_formation_and_fit_player(self):
        state = new_match()
        for side, formation in (("A", FORMATION_433), ("B", FORMATION_442)):
            slots = state["sides"][side]["slots"]
            self.assertEqual([s["pos"] for s in slots], formation["slots"])
            for s in slots:
                player = s["player"]
                self.assertTrue(player["pos"] == s["pos"] or s["pos"] in player["alt"],
                                f"{side}: {player['pos']} oyuncusu {s['pos']} slotuna uymuyor")

    def test_initial_state_fields(self):
        state = new_match()
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["step"], "steal")
        self.assertEqual(state["turn"], "A")
        self.assertEqual(state["steals_left"], {"A": STEALS_PER_SIDE, "B": STEALS_PER_SIDE})
        self.assertEqual(state["protect_count"], PROTECT_COUNT)
        self.assertEqual(state["arranged"], {"A": False, "B": False})
        self.assertEqual(state["setups"]["A"]["formation_id"], "4-3-3")
        self.assertEqual(state["setups"]["B"]["formation_id"], "4-4-2")

    def test_players_come_only_from_own_categories(self):
        state = new_match()
        for p in side_players(state["sides"]["A"]):
            self.assertEqual(p["club"], "Alpha")
        for p in side_players(state["sides"]["B"]):
            self.assertEqual(p["club"], "Beta")

    def test_side_a_pool_too_small_raises(self):
        players = make_pool("a", "Alpha", count=22) + make_pool("b", "Beta")
        with self.assertRaises(ValueError) as cm:
            create_match(players, two_side_setups(), seed=1)
        self.assertRegex(str(cm.exception), r"A tarafı")

    def test_side_b_pool_too_small_raises(self):
        players = make_pool("a", "Alpha") + make_pool("b", "Beta", count=22)
        with self.assertRaises(ValueError) as cm:
            create_match(players, two_side_setups(), seed=1)
        self.assertRegex(str(cm.exception), r"B tarafı")

    def test_shared_pool_too_small_for_both_sides_raises(self):
        players = make_pool("s", "Shared", count=45)
        setups = {"A": setup("Shared", FORMATION_433), "B": setup("Shared", FORMATION_442)}
        with self.assertRaises(ValueError):
            create_match(players, setups, seed=1)

    def test_zero_categories_raises_for_that_side(self):
        setups = two_side_setups()
        setups["B"]["categories"] = []
        with self.assertRaises(ValueError) as cm:
            create_match(base_players(), setups, seed=1)
        self.assertRegex(str(cm.exception), r"B")

    def test_five_categories_raises(self):
        setups = two_side_setups()
        setups["B"]["categories"] = [{"type": "club", "value": "Beta"}] + [
            {"type": "league", "value": f"L{i}"} for i in range(4)
        ]
        with self.assertRaises(ValueError):
            create_match(base_players(), setups, seed=1)

    def test_four_categories_allowed(self):
        setups = two_side_setups()
        setups["A"]["categories"] = [
            {"type": "club", "value": "Alpha"},
            {"type": "league", "value": "L1"},
            {"type": "nation", "value": "Nationa"},
            {"type": "club", "value": "Gamma"},
        ]
        state = create_match(base_players(), setups, seed=1)
        self.assertEqual(len(side_ids(state["sides"]["A"])), SQUAD_SIZE)

    def test_same_seed_same_state(self):
        self.assertEqual(new_match(seed=7), new_match(seed=7))

    def test_different_seed_changes_deal(self):
        base = new_match(seed=1)
        self.assertTrue(any(new_match(seed=s) != base for s in range(2, 8)))

    def test_inputs_are_not_mutated(self):
        players = base_players()
        setups = two_side_setups()
        players_before = copy.deepcopy(players)
        setups_before = copy.deepcopy(setups)
        create_match(players, setups, seed=3)
        self.assertEqual(players, players_before)
        self.assertEqual(setups, setups_before)

    def test_bench_and_reserve_sizes_are_configurable(self):
        state = create_match(base_players(), two_side_setups(), bench_size=5, reserve_size=2, seed=1)
        self.assertEqual(len(state["sides"]["A"]["bench"]), 5)
        self.assertEqual(len(state["sides"]["A"]["reserves"]), 2)


class RealDataTests(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(PLAYERS_PATH), "data/players.json yok")
    def test_real_clubs_deal_full_squads_for_many_seeds(self):
        with open(PLAYERS_PATH, encoding="utf-8") as fh:
            players = json.load(fh)
        setups = {
            "A": setup("Real Madrid", FORMATION_433),
            "B": setup("Chelsea", FORMATION_442),
        }
        for seed in range(1, 21):
            state = create_match(players, setups, seed=seed)
            for side in SIDES:
                self.assertEqual(len(side_ids(state["sides"][side])), SQUAD_SIZE)
            ids = side_ids(state["sides"]["A"]) + side_ids(state["sides"]["B"])
            self.assertEqual(len(set(ids)), len(ids), f"seed {seed}: aynı oyuncu iki yerde")


# ---------------------------------------------------------------- kalite penceresi

class QualityWindowTests(unittest.TestCase):
    def test_goalkeeper_slot_gets_only_90_or_80_with_own_pools(self):
        players = gk_pool("a", "Alpha") + gk_pool("b", "Beta")
        for seed in range(50):
            state = create_match(players, two_side_setups(), seed=seed)
            for side in SIDES:
                gk = [s["player"]["rating"] for s in state["sides"][side]["slots"]
                      if s["pos"] == "GK"]
                self.assertEqual(len(gk), 1)
                self.assertIn(gk[0], (90, 80), f"seed {seed}, taraf {side}")

    def test_shared_pool_gives_one_side_90_and_other_80(self):
        players = gk_pool("s", "Shared")
        setups = {"A": setup("Shared", FORMATION_433), "B": setup("Shared", FORMATION_442)}
        for seed in range(20):
            state = create_match(players, setups, seed=seed)
            gks = sorted(
                s["player"]["rating"]
                for side in SIDES
                for s in state["sides"][side]["slots"] if s["pos"] == "GK"
            )
            self.assertEqual(gks, [80, 90], f"seed {seed}")

    def test_weak_goalkeepers_appear_without_window(self):
        players = gk_pool("a", "Alpha") + gk_pool("b", "Beta")
        seen = set()
        for seed in range(50):
            state = create_match(players, two_side_setups(), seed=seed, quality_window=None)
            for side in SIDES:
                for s in state["sides"][side]["slots"]:
                    if s["pos"] == "GK":
                        seen.add(s["player"]["rating"])
        self.assertTrue(seen & {71, 68}, f"pencere kapalıyken 71/68 bekleniyordu: {seen}")

    def test_zero_window_falls_back_to_remaining_best_for_second_side(self):
        players = gk_pool("s", "Shared")
        setups = {"A": setup("Shared", FORMATION_433), "B": setup("Shared", FORMATION_442)}
        for seed in range(20):
            state = create_match(players, setups, seed=seed, quality_window=0)
            a_gk = [s["player"]["rating"] for s in state["sides"]["A"]["slots"] if s["pos"] == "GK"]
            b_gk = [s["player"]["rating"] for s in state["sides"]["B"]["slots"] if s["pos"] == "GK"]
            self.assertEqual(a_gk, [90])
            self.assertEqual(b_gk, [80])

    def test_default_quality_window_is_ten(self):
        self.assertEqual(
            create_match(base_players(), two_side_setups(), seed=5),
            create_match(base_players(), two_side_setups(), seed=5,
                         quality_window=QUALITY_WINDOW),
        )


# ---------------------------------------------------------------- takım puanı

class TeamRatingTests(unittest.TestCase):
    def test_nineteen_player_average_with_exact_numbers(self):
        slots = [("ST", manual_player(f"s{i}", "ST", 80)) for i in range(FIRST_ELEVEN)]
        bench = [manual_player(f"b{i}", "GK", 60) for i in range(BENCH_SIZE)]
        state = manual_state(manual_side(slots, bench), manual_side(slots, bench))
        # (11*80 + 8*60) / 19 = 71.58 -> 72. Yedekte pozisyon cezası olsaydı 67 çıkardı.
        self.assertEqual(team_rating(state, "A"), 72)

    def test_reserves_do_not_count(self):
        slots = [("ST", manual_player(f"s{i}", "ST", 80)) for i in range(FIRST_ELEVEN)]
        bench = [manual_player(f"b{i}", "GK", 60) for i in range(BENCH_SIZE)]
        reserves = [manual_player(f"r{i}", "ST", 99) for i in range(RESERVE_SIZE)]
        state = manual_state(manual_side(slots, bench, reserves), manual_side(slots, bench))
        self.assertEqual(team_rating(state, "A"), 72)

    def test_slot_mismatch_penalty_applies_to_first_eleven_only(self):
        slots = [("ST", manual_player(f"s{i}", "ST", 80)) for i in range(10)]
        slots.append(("ST", manual_player("gk", "GK", 80)))  # 80 - 10 = 70
        bench = [manual_player(f"b{i}", "GK", 60) for i in range(BENCH_SIZE)]
        state = manual_state(manual_side(slots, bench), manual_side(slots, bench))
        # (10*80 + 70 + 8*60) / 19 = 1350 / 19 = 71.05 -> 71
        self.assertEqual(team_rating(state, "A"), 71)

    def test_rounding_is_to_integer(self):
        slots = [("ST", manual_player(f"s{i}", "ST", 81)) for i in range(FIRST_ELEVEN)]
        bench = [manual_player(f"b{i}", "ST", 80) for i in range(BENCH_SIZE)]
        state = manual_state(manual_side(slots, bench), manual_side(slots, bench))
        value = team_rating(state, "A")
        self.assertIsInstance(value, int)
        self.assertEqual(value, round((11 * 81 + 8 * 80) / 19))

    def test_reserve_swap_keeps_rating_and_bench_swap_changes_it(self):
        st = new_match()
        before_a = team_rating(st, "A")
        before_b = team_rating(st, "B")
        # Rezerv <-> rezerv: iki tarafın ilk 11 ve yedekleri değişmez, puan sabit.
        r = steal(st, "A", st["sides"]["B"]["reserves"][0]["id"],
                  st["sides"]["A"]["reserves"][0]["id"])
        self.assertEqual(team_rating(r, "A"), before_a)
        self.assertEqual(team_rating(r, "B"), before_b)
        # Yedek <-> yedek: puan yedeklerin ratinglerine göre yeniden hesaplanır.
        b = steal(st, "A", st["sides"]["B"]["bench"][0]["id"], st["sides"]["A"]["bench"][0]["id"])
        self.assertEqual(team_rating(b, "A"), expected_team(b, "A"))
        self.assertEqual(team_rating(b, "B"), expected_team(b, "B"))

    def test_bench_swap_changes_rating_when_ratings_differ(self):
        slots = [("ST", manual_player(f"s{i}", "ST", 80)) for i in range(FIRST_ELEVEN)]
        bench_a = [manual_player(f"a{i}", "ST", 60) for i in range(BENCH_SIZE)]
        bench_b = [manual_player(f"c{i}", "ST", 90) for i in range(BENCH_SIZE)]
        before = manual_state(manual_side(slots, bench_a), manual_side(slots, bench_b))
        bench_a2 = list(bench_a)
        bench_a2[0] = bench_b[0]
        after = manual_state(manual_side(slots, bench_a2), manual_side(slots, bench_b))
        self.assertNotEqual(team_rating(before, "A"), team_rating(after, "A"))
        self.assertEqual(team_rating(after, "A"), round((11 * 80 + 7 * 60 + 90) / 19))


# ---------------------------------------------------------------- slot_score

class SlotScoreTests(unittest.TestCase):
    def test_exact_position_gives_rating(self):
        self.assertEqual(slot_score("ST", make_player("1", "ST", rating=85)), 85)

    def test_alternate_position_gives_rating(self):
        self.assertEqual(slot_score("LW", make_player("1", "ST", rating=85, alt=["LW"])), 85)

    def test_mismatch_gives_rating_minus_ten(self):
        self.assertEqual(slot_score("GK", make_player("1", "ST", rating=85)), 75)

    def test_penalty_never_goes_below_zero(self):
        self.assertEqual(slot_score("GK", make_player("1", "ST", rating=5)), 0)
        self.assertEqual(slot_score("GK", make_player("1", "ST", rating=10)), 0)


# ---------------------------------------------------------------- takas

class StealTests(unittest.TestCase):
    def test_steal_requires_turn(self):
        st = new_match()
        with self.assertRaises(ValueError):
            steal(st, "B", st["sides"]["A"]["slots"][0]["player"]["id"],
                  st["sides"]["B"]["slots"][0]["player"]["id"])

    def test_slot_for_bench_across_sides(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        target = slot_ids(b)[0]
        give = bench_ids(a)[0]
        new = steal(st, "A", target, give)
        na, nb = new["sides"]["A"], new["sides"]["B"]
        self.assertEqual(na["bench"][0]["id"], target)
        self.assertEqual(nb["slots"][0]["player"]["id"], give)
        # Slot pozisyon etiketleri yerinde kalır.
        self.assertEqual(nb["slots"][0]["pos"], b["slots"][0]["pos"])
        self.assertEqual(na["slots"][0]["pos"], a["slots"][0]["pos"])

    def test_reserve_for_slot(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        target = reserve_ids(b)[1]
        give = slot_ids(a)[2]
        new = steal(st, "A", target, give)
        self.assertEqual(new["sides"]["A"]["slots"][2]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["reserves"][1]["id"], give)

    def test_bench_for_reserve(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        target = bench_ids(b)[3]
        give = reserve_ids(a)[0]
        new = steal(st, "A", target, give)
        self.assertEqual(new["sides"]["A"]["reserves"][0]["id"], target)
        self.assertEqual(new["sides"]["B"]["bench"][3]["id"], give)

    def test_stolen_player_is_not_protected_and_sets_protect_step(self):
        st = new_match()
        target = slot_ids(st["sides"]["B"])[0]
        new = steal(st, "A", target, bench_ids(st["sides"]["A"])[0])
        self.assertEqual(new["sides"]["A"]["protected_ids"], [])
        self.assertNotIn(target, new["sides"]["A"]["protected_ids"])
        self.assertEqual(new["phase"], "steal")
        self.assertEqual(new["step"], "protect")
        self.assertEqual(new["turn"], "A")
        self.assertEqual(new["steals_left"]["A"], STEALS_PER_SIDE - 1)

    def test_steal_target_not_in_rival_roster_raises(self):
        st = new_match()
        own = slot_ids(st["sides"]["A"])[0]
        with self.assertRaises(ValueError):
            steal(st, "A", own, bench_ids(st["sides"]["A"])[0])

    def test_give_not_in_own_roster_raises(self):
        st = new_match()
        foreign = slot_ids(st["sides"]["B"])[0]
        with self.assertRaises(ValueError):
            steal(st, "A", slot_ids(st["sides"]["B"])[1], foreign)

    def test_protected_target_cannot_be_stolen(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        st = steal(st, "A", slot_ids(b)[0], bench_ids(a)[0])
        st = protect(st, "A", [slot_ids(a)[0]])
        with self.assertRaises(ValueError):
            steal(st, "B", slot_ids(a)[0], slot_ids(b)[1])

    def test_protected_give_cannot_be_given(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        st = steal(st, "A", slot_ids(b)[0], bench_ids(a)[0])
        st = protect(st, "A", [reserve_ids(a)[0]])
        st = steal(st, "B", slot_ids(a)[0], slot_ids(b)[1])
        st = protect(st, "B", [])
        with self.assertRaises(ValueError):
            steal(st, "A", slot_ids(st["sides"]["B"])[1], reserve_ids(a)[0])

    def test_steal_during_protect_step_raises(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        st = steal(st, "A", slot_ids(b)[0], bench_ids(a)[0])
        self.assertEqual(st["step"], "protect")
        with self.assertRaises(ValueError):
            steal(st, "A", slot_ids(b)[1], slot_ids(a)[1])

    def test_steal_does_not_mutate_input(self):
        st = new_match()
        before = copy.deepcopy(st)
        steal(st, "A", slot_ids(st["sides"]["B"])[0], bench_ids(st["sides"]["A"])[0])
        self.assertEqual(st, before)

    def test_stealing_from_exhausted_side_raises(self):
        st = new_match()
        st["steals_left"]["A"] = 0
        with self.assertRaises(ValueError):
            steal(st, "A", slot_ids(st["sides"]["B"])[0], slot_ids(st["sides"]["A"])[0])


# ---------------------------------------------------------------- koruma

class ProtectTests(unittest.TestCase):
    def after_first_steal(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        return steal(st, "A", slot_ids(b)[0], bench_ids(a)[0])

    def test_protect_accepts_three_from_any_group(self):
        st = self.after_first_steal()
        a = st["sides"]["A"]
        ids = [slot_ids(a)[0], bench_ids(a)[0], reserve_ids(a)[0]]
        new = protect(st, "A", ids)
        self.assertEqual(new["sides"]["A"]["protected_ids"], ids)
        self.assertEqual(new["turn"], "B")
        self.assertEqual(new["step"], "steal")

    def test_protect_rejects_more_than_protect_count(self):
        st = self.after_first_steal()
        ids = side_ids(st["sides"]["A"])[:PROTECT_COUNT + 1]
        with self.assertRaises(ValueError):
            protect(st, "A", ids)

    def test_protect_rejects_duplicates(self):
        st = self.after_first_steal()
        pid = slot_ids(st["sides"]["A"])[0]
        with self.assertRaises(ValueError):
            protect(st, "A", [pid, pid])

    def test_protect_rejects_foreign_player(self):
        st = self.after_first_steal()
        with self.assertRaises(ValueError):
            protect(st, "A", [slot_ids(st["sides"]["B"])[0]])

    def test_protect_outside_protect_step_raises(self):
        with self.assertRaises(ValueError):
            protect(new_match(), "A", [])

    def test_protect_by_wrong_side_raises(self):
        st = self.after_first_steal()
        with self.assertRaises(ValueError):
            protect(st, "B", [])

    def test_new_protect_list_replaces_previous(self):
        st = self.after_first_steal()
        a = st["sides"]["A"]
        first_three = slot_ids(a)[:3]
        st = protect(st, "A", first_three)
        st = steal(st, "B", unprotected_ids(st["sides"]["A"])[0], slot_ids(st["sides"]["B"])[0])
        st = protect(st, "B", [])
        st = steal(st, "A", unprotected_ids(st["sides"]["B"])[0],
                   unprotected_ids(st["sides"]["A"])[0])
        new_list = [bench_ids(st["sides"]["A"])[0]]
        st = protect(st, "A", new_list)
        self.assertEqual(st["sides"]["A"]["protected_ids"], new_list)
        self.assertNotEqual(st["sides"]["A"]["protected_ids"], first_three)

    def test_empty_protect_list_is_allowed(self):
        st = self.after_first_steal()
        new = protect(st, "A", [])
        self.assertEqual(new["sides"]["A"]["protected_ids"], [])

    def test_protected_player_can_be_moved_by_swaps(self):
        st = self.after_first_steal()
        a, b = st["sides"]["A"], st["sides"]["B"]
        st = protect(st, "A", [slot_ids(a)[0]])
        st = steal(st, "B", bench_ids(st["sides"]["A"])[1], slot_ids(b)[1])
        st = protect(st, "B", [])
        moved = swap_bench(st, "A", 0, 0)
        self.assertEqual(moved["sides"]["A"]["protected_ids"], [slot_ids(a)[0]])
        self.assertEqual(bench_ids(moved["sides"]["A"])[0], slot_ids(a)[0])


# ---------------------------------------------------------------- yerleştirme

class SwapTests(unittest.TestCase):
    def test_swap_bench_exchanges_slot_and_bench(self):
        st = new_match()
        a = st["sides"]["A"]
        slot_pid, bench_pid = slot_ids(a)[2], bench_ids(a)[5]
        new = swap_bench(st, "A", 2, 5)
        na = new["sides"]["A"]
        self.assertEqual(na["slots"][2]["player"]["id"], bench_pid)
        self.assertEqual(na["bench"][5]["id"], slot_pid)
        self.assertEqual(na["slots"][2]["pos"], a["slots"][2]["pos"])
        self.assertEqual(reserve_ids(na), reserve_ids(a))

    def test_swap_bench_index_out_of_range_raises(self):
        st = new_match()
        for slot_index, bench_index in ((11, 0), (0, BENCH_SIZE), (-1, 0), (0, -1)):
            with self.subTest(slot_index=slot_index, bench_index=bench_index):
                with self.assertRaises(ValueError):
                    swap_bench(st, "A", slot_index, bench_index)

    def test_swap_bench_wrong_turn_in_steal_raises(self):
        with self.assertRaises(ValueError):
            swap_bench(new_match(), "B", 0, 0)

    def test_swap_reserve_exchanges_bench_and_reserve(self):
        st = new_match()
        a = st["sides"]["A"]
        bench_pid, reserve_pid = bench_ids(a)[3], reserve_ids(a)[1]
        new = swap_reserve(st, "A", 3, 1)
        na = new["sides"]["A"]
        self.assertEqual(na["bench"][3]["id"], reserve_pid)
        self.assertEqual(na["reserves"][1]["id"], bench_pid)
        self.assertEqual(slot_ids(na), slot_ids(a))

    def test_swap_reserve_index_out_of_range_raises(self):
        st = new_match()
        for bench_index, reserve_index in ((BENCH_SIZE, 0), (0, RESERVE_SIZE), (-1, 0), (0, -1)):
            with self.subTest(bench_index=bench_index, reserve_index=reserve_index):
                with self.assertRaises(ValueError):
                    swap_reserve(st, "A", bench_index, reserve_index)

    def test_swap_reserve_wrong_turn_in_steal_raises(self):
        with self.assertRaises(ValueError):
            swap_reserve(new_match(), "B", 0, 0)

    def test_swap_bench_does_not_touch_reserves(self):
        st = new_match()
        new = swap_bench(st, "A", 0, 0)
        self.assertEqual(reserve_ids(new["sides"]["A"]), reserve_ids(st["sides"]["A"]))

    def test_protected_reserve_can_be_swapped_and_keeps_protection(self):
        st = new_match()
        a, b = st["sides"]["A"], st["sides"]["B"]
        st = steal(st, "A", slot_ids(b)[0], bench_ids(a)[0])
        st = protect(st, "A", [reserve_ids(a)[0]])
        st = steal(st, "B", unprotected_ids(st["sides"]["A"])[0], slot_ids(b)[1])
        st = protect(st, "B", [])
        new = swap_reserve(st, "A", 0, 0)
        self.assertEqual(new["sides"]["A"]["bench"][0]["id"], reserve_ids(a)[0])
        self.assertEqual(new["sides"]["A"]["protected_ids"], [reserve_ids(a)[0]])

    def test_arrange_allows_swaps_until_side_confirms(self):
        st = play_until_arrange(new_match(steals_per_side=1))
        self.assertEqual(st["phase"], "arrange")
        st = swap_reserve(st, "A", 0, 0)
        st = swap_reserve(st, "B", 1, 1)
        st = confirm_arrange(st, "A")
        with self.assertRaises(ValueError):
            swap_reserve(st, "A", 0, 0)
        with self.assertRaises(ValueError):
            swap_bench(st, "A", 0, 0)
        b_slot, b_bench = st["sides"]["B"]["slots"][0]["player"]["id"], st["sides"]["B"]["bench"][0]["id"]
        st = swap_bench(st, "B", 0, 0)
        self.assertEqual(st["sides"]["B"]["slots"][0]["player"]["id"], b_bench)
        self.assertEqual(st["sides"]["B"]["bench"][0]["id"], b_slot)


# ---------------------------------------------------------------- akış, düzen, sonuç

class MatchFlowTests(unittest.TestCase):
    def test_full_steal_sequence_ends_in_arrange(self):
        st = play_until_arrange(new_match())
        self.assertEqual(st["phase"], "arrange")
        self.assertEqual(st["steals_left"], {"A": 0, "B": 0})

    def test_last_steal_goes_to_arrange_without_protect_step(self):
        st = new_match()
        for _ in range(2 * STEALS_PER_SIDE - 1):
            st = play_round(st)
        self.assertEqual(st["phase"], "steal")
        self.assertEqual(st["step"], "steal")
        turn = st["turn"]
        last = steal(st, turn, unprotected_ids(st["sides"][OTHER[turn]])[0],
                     unprotected_ids(st["sides"][turn])[0])
        self.assertEqual(last["phase"], "arrange")
        self.assertEqual(last["arranged"], {"A": False, "B": False})

    def test_confirm_a_then_b_finishes(self):
        st = play_until_arrange(new_match(steals_per_side=1))
        st = confirm_arrange(st, "A")
        self.assertEqual(st["phase"], "arrange")
        st = confirm_arrange(st, "B")
        self.assertEqual(st["phase"], "done")

    def test_confirm_outside_arrange_raises(self):
        with self.assertRaises(ValueError):
            confirm_arrange(new_match(), "A")

    def test_confirm_twice_raises(self):
        st = play_until_arrange(new_match(steals_per_side=1))
        st = confirm_arrange(st, "A")
        with self.assertRaises(ValueError):
            confirm_arrange(st, "A")

    def test_zero_steals_starts_in_arrange(self):
        st = new_match(steals_per_side=0)
        self.assertEqual(st["phase"], "arrange")
        st, steals = play_full_match(st)
        self.assertEqual(steals, 0)
        self.assertEqual(st["phase"], "done")

    def test_result_requires_done(self):
        with self.assertRaises(ValueError):
            result(new_match())

    def test_result_values_match_team_rating_and_winner(self):
        st, _ = play_full_match(new_match())
        res = result(st)
        self.assertEqual(res["A"], team_rating(st, "A"))
        self.assertEqual(res["B"], team_rating(st, "B"))
        if res["A"] > res["B"]:
            self.assertEqual(res["winner"], "A")
        elif res["B"] > res["A"]:
            self.assertEqual(res["winner"], "B")
        else:
            self.assertEqual(res["winner"], "draw")

    def test_result_draw_on_equal_ratings(self):
        slots = [("ST", manual_player(f"s{i}", "ST", 80)) for i in range(FIRST_ELEVEN)]
        bench = [manual_player(f"b{i}", "ST", 70) for i in range(BENCH_SIZE)]
        side = manual_side(slots, bench)
        res = result(manual_state(side, copy.deepcopy(side)))
        self.assertEqual(res["winner"], "draw")
        self.assertEqual(res["A"], res["B"])

    def test_result_winner_on_higher_rating(self):
        strong = manual_side([("ST", manual_player(f"s{i}", "ST", 85)) for i in range(FIRST_ELEVEN)],
                             [manual_player(f"b{i}", "ST", 85) for i in range(BENCH_SIZE)])
        weak = manual_side([("ST", manual_player(f"w{i}", "ST", 60)) for i in range(FIRST_ELEVEN)],
                           [manual_player(f"v{i}", "ST", 60) for i in range(BENCH_SIZE)])
        res = result(manual_state(weak, strong))
        self.assertEqual(res["winner"], "B")

    def test_full_match_is_deterministic(self):
        first, steals1 = play_full_match(new_match(seed=11))
        second, steals2 = play_full_match(new_match(seed=11))
        self.assertEqual(steals1, STEALS_PER_SIDE * 2)
        self.assertEqual(steals2, steals1)
        self.assertEqual(first, second)
        self.assertEqual(result(first), result(second))

    def test_full_match_keeps_23_players_per_side_and_no_duplicates(self):
        st, _ = play_full_match(new_match(seed=4))
        for side in SIDES:
            self.assertEqual(len(side_ids(st["sides"][side])), SQUAD_SIZE)
        ids = side_ids(st["sides"]["A"]) + side_ids(st["sides"]["B"])
        self.assertEqual(len(set(ids)), len(ids))


if __name__ == "__main__":
    unittest.main()

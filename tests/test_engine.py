"""Streamlit sürümü motor testleri (docs/CONTRACT.md "Güncelleme 4" > Motor).

Yalnızca standart unittest. engine.py repo kökünde olmalı; bu dosya kökü sys.path'e ekler.
Güncelleme 4: her taraf 11 ilk + 8 yedek (19) alır; takas yedekleri de kapsar; koruma 19 oyuncudan;
son takastan sonra phase "arrange" (swap_bench + confirm_arrange), iki onaydan sonra "done".
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
    team_rating,
)

BENCH_SIZE = 8
SQUAD_SIZE = 11 + BENCH_SIZE

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
ALL_FORMATIONS = (FORMATION_433, FORMATION_442, FORMATION_352)
POSITIONS = sorted({pos for f in ALL_FORMATIONS for pos in f["slots"]})


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


def make_pool():
    """Alpha ve Beta: her pozisyondan 3'er oyuncu (L1; ülkeleri farklı) -> 36'şar oyuncu.
    Gamma: sadece 3 ST (yetersiz havuz)."""
    players = []
    pid = 1
    for club, nation in (("Alpha", "Nationa"), ("Beta", "Nationb")):
        for _ in range(3):
            for pos in POSITIONS:
                players.append(make_player(pid, pos, club=club, league="L1", nation=nation,
                                           rating=60 + (pid * 7) % 35))
                pid += 1
    for _ in range(3):
        players.append(make_player(pid, "ST", club="Gamma", league="L2", nation="Nationa",
                                   rating=75))
        pid += 1
    return players


PLAYERS = make_pool()
PLAYERS_BY_ID = {p["id"]: p for p in PLAYERS}
CLUB_ALPHA = [{"type": "club", "value": "Alpha"}]
CLUB_BETA = [{"type": "club", "value": "Beta"}]
LEAGUE_L1 = [{"type": "league", "value": "L1"}]


def setup(categories=CLUB_ALPHA, formation=FORMATION_433):
    return {"categories": copy.deepcopy(categories), "formation": copy.deepcopy(formation)}


def default_setups():
    return {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_433)}


def new_match(setups=None, players=None, **overrides):
    kwargs = dict(players=players if players is not None else PLAYERS,
                  setups=setups if setups is not None else default_setups(), seed=1)
    kwargs.update(overrides)
    return create_match(**kwargs)


def squad_ids(state, side):
    """İlk 11 id'leri (slot sırasıyla)."""
    return [slot["player"]["id"] for slot in state["sides"][side]["slots"]]


def bench_ids(state, side):
    return [p["id"] for p in state["sides"][side]["bench"]]


def all_ids(state, side):
    """19 oyuncunun id'leri: önce ilk 11, sonra yedekler."""
    return squad_ids(state, side) + bench_ids(state, side)


def unprotected_ids(state, side):
    protected = state["sides"][side]["protected_ids"]
    return [pid for pid in all_ids(state, side) if pid not in protected]


def other(side):
    return "B" if side == "A" else "A"


def locate(state, side, pid):
    """('slot', i) veya ('bench', j); yoksa AssertionError."""
    for i, slot in enumerate(state["sides"][side]["slots"]):
        if slot["player"]["id"] == pid:
            return ("slot", i)
    for j, player in enumerate(state["sides"][side]["bench"]):
        if player["id"] == pid:
            return ("bench", j)
    raise AssertionError(f"{pid} {side} kadrosunda yok")


def first_steal(state, side=None):
    """Sıradaki tarafın takasını yapar (koruma adımına GEÇMEZ): rakipten ilk korumasız,
    kendinden ilk korumasız (ilk 11 ve yedekler dahil)."""
    side = side or state["turn"]
    target = unprotected_ids(state, other(side))[0]
    give = unprotected_ids(state, side)[0]
    return steal(state, side, target, give)


def steal_and_protect(state, keep=None):
    """Bir tam tur: takas + koruma (keep verilmezse kadronun ilk 3'ü). Son takasta koruma yok."""
    side = state["turn"]
    state = first_steal(state, side)
    if state["phase"] != "steal":
        return state
    ids = squad_ids(state, side)[:3] if keep is None else keep
    return protect(state, side, ids)


def play_out(state):
    """Takas aşamasını deterministik seçimlerle bitirir (phase "arrange" olur)."""
    while state["phase"] == "steal":
        state = steal_and_protect(state)
    return state


def finish_arrange(state):
    """Her iki taraf da düzeni onaylar (A, sonra B) -> phase "done"."""
    for side in ("A", "B"):
        state = confirm_arrange(state, side)
    return state


def team_rating_from_slots(state, side):
    slots = state["sides"][side]["slots"]
    return round(sum(slot_score(s["pos"], s["player"]) for s in slots) / len(slots))


class CreateMatchTests(unittest.TestCase):
    def test_pool_too_small_raises_and_names_side(self):
        setups = default_setups()
        setups["B"] = setup([{"type": "club", "value": "Gamma"}], FORMATION_433)
        with self.assertRaises(ValueError) as cm:
            new_match(setups=setups)
        self.assertRegex(str(cm.exception), r"\bB\b")

    def test_pool_of_eighteen_is_too_small_for_eleven_plus_eight(self):
        # 11 ilk oyuncu tek başına yeterli, ama 19 için 18 yetmez -> hata, taraf A.
        players = [make_player(f"s{i}", pos, club="Solo")
                   for i, pos in enumerate(FORMATION_433["slots"], 1)]
        players += [make_player(f"s{100 + i}", "CM", club="Solo") for i in range(7)]
        setups = {"A": setup([{"type": "club", "value": "Solo"}], FORMATION_433),
                  "B": setup(CLUB_BETA, FORMATION_433)}
        with self.assertRaises(ValueError) as cm:
            new_match(setups=setups, players=players + PLAYERS)
        self.assertRegex(str(cm.exception), r"\bA\b")

    def test_pool_of_exactly_nineteen_is_enough(self):
        players = [make_player(f"s{i}", pos, club="Solo")
                   for i, pos in enumerate(FORMATION_433["slots"], 1)]
        players += [make_player(f"s{100 + i}", "CM", club="Solo") for i in range(8)]
        setups = {"A": setup([{"type": "club", "value": "Solo"}], FORMATION_433),
                  "B": setup(CLUB_BETA, FORMATION_433)}
        state = new_match(setups=setups, players=players + PLAYERS)
        self.assertEqual(len(all_ids(state, "A")), SQUAD_SIZE)
        self.assertEqual(len(set(all_ids(state, "A"))), SQUAD_SIZE)

    def test_no_matching_category_raises(self):
        setups = default_setups()
        setups["A"] = setup([{"type": "nation", "value": "Yokhayir"}], FORMATION_433)
        with self.assertRaises(ValueError):
            new_match(setups=setups)

    def test_zero_categories_raises_with_side_A(self):
        setups = default_setups()
        setups["A"] = setup([], FORMATION_433)
        with self.assertRaises(ValueError) as cm:
            new_match(setups=setups)
        self.assertRegex(str(cm.exception), r"\bA\b")

    def test_zero_categories_raises_with_side_B(self):
        setups = default_setups()
        setups["B"] = setup([], FORMATION_433)
        with self.assertRaises(ValueError) as cm:
            new_match(setups=setups)
        self.assertRegex(str(cm.exception), r"\bB\b")

    def test_five_categories_raises_with_side(self):
        five = [
            {"type": "club", "value": "Alpha"},
            {"type": "club", "value": "Beta"},
            {"type": "league", "value": "L1"},
            {"type": "nation", "value": "Nationa"},
            {"type": "nation", "value": "Nationb"},
        ]
        for side in ("A", "B"):
            setups = default_setups()
            setups[side] = setup(five, FORMATION_433)
            with self.subTest(side=side), self.assertRaises(ValueError) as cm:
                new_match(setups=setups)
            self.assertRegex(str(cm.exception), rf"\b{side}\b")

    def test_four_categories_allowed(self):
        four = [
            {"type": "club", "value": "Alpha"},
            {"type": "club", "value": "Gamma"},
            {"type": "league", "value": "L2"},
            {"type": "nation", "value": "Nationa"},
        ]
        setups = default_setups()
        setups["A"] = setup(four, FORMATION_433)
        state = new_match(setups=setups)
        self.assertEqual(len(squad_ids(state, "A")), 11)

    def test_each_side_has_eleven_slots_and_eight_bench_players(self):
        state = new_match()
        for side in ("A", "B"):
            self.assertEqual(len(state["sides"][side]["slots"]), 11)
            self.assertEqual(len(state["sides"][side]["bench"]), BENCH_SIZE)
            self.assertEqual(len(set(all_ids(state, side))), SQUAD_SIZE)

    def test_bench_size_parameter_is_respected(self):
        state = new_match(bench_size=2)
        self.assertEqual(len(state["sides"]["A"]["bench"]), 2)
        self.assertEqual(len(state["sides"]["B"]["bench"]), 2)

    def test_no_player_repeats_within_or_across_sides(self):
        state = new_match()
        a, b = all_ids(state, "A"), all_ids(state, "B")
        self.assertEqual(len(set(a)), SQUAD_SIZE)
        self.assertEqual(len(set(b)), SQUAD_SIZE)
        self.assertEqual(set(a) & set(b), set())

    def test_each_side_slots_follow_its_own_formation_order(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        state = new_match(setups=setups)
        for side, formation in (("A", FORMATION_433), ("B", FORMATION_442)):
            slots = state["sides"][side]["slots"]
            self.assertEqual([s["pos"] for s in slots], formation["slots"])

    def test_different_formations_both_recorded_in_state(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_352)}
        state = new_match(setups=setups)
        self.assertEqual(state["setups"]["A"]["formation_id"], "4-3-3")
        self.assertEqual(state["setups"]["B"]["formation_id"], "3-5-2")
        self.assertEqual(state["setups"]["A"]["categories"], CLUB_ALPHA)
        self.assertEqual(state["setups"]["B"]["categories"], CLUB_BETA)

    def test_each_side_player_comes_only_from_its_own_categories(self):
        setups = {
            "A": setup([{"type": "club", "value": "Alpha"}], FORMATION_433),
            "B": setup([{"type": "club", "value": "Beta"}, {"type": "nation", "value": "Nationb"}],
                       FORMATION_442),
        }
        state = new_match(setups=setups)
        for pid in all_ids(state, "A"):
            self.assertEqual(PLAYERS_BY_ID[pid]["club"], "Alpha")
        for pid in all_ids(state, "B"):
            p = PLAYERS_BY_ID[pid]
            self.assertTrue(p["club"] == "Beta" or p["nation"] == "Nationb")

    def test_overlapping_pools_player_only_on_one_side(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(LEAGUE_L1, FORMATION_442)}
        state = new_match(setups=setups)
        self.assertEqual(set(all_ids(state, "A")) & set(all_ids(state, "B")), set())

    def test_identical_pools_no_player_on_both_sides(self):
        setups = {"A": setup(LEAGUE_L1, FORMATION_433), "B": setup(LEAGUE_L1, FORMATION_433)}
        state = new_match(setups=setups)
        self.assertEqual(len(set(all_ids(state, "A"))), SQUAD_SIZE)
        self.assertEqual(len(set(all_ids(state, "B"))), SQUAD_SIZE)
        self.assertEqual(set(all_ids(state, "A")) & set(all_ids(state, "B")), set())

    def test_dealt_slot_player_fits_slot_by_pos_or_alt(self):
        pool = [make_player(i, "LW", alt=["ST"]) for i in range(1, 41)]
        formation = {"id": "x", "slots": ["ST"] * 11}
        setups = {"A": setup(CLUB_ALPHA, formation), "B": setup(CLUB_ALPHA, formation)}
        state = create_match(players=pool, setups=setups, seed=5)
        for side in ("A", "B"):
            for slot in state["sides"][side]["slots"]:
                self.assertTrue(slot["player"]["pos"] == slot["pos"]
                                or slot["pos"] in slot["player"]["alt"])

    def test_initial_state_starts_unprotected_in_steal_step(self):
        state = new_match()
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["step"], "steal")
        self.assertEqual(state["turn"], "A")
        self.assertEqual(state["steals_left"], {"A": 3, "B": 3})
        self.assertEqual(state["protect_count"], 3)
        self.assertEqual(state["arranged"], {"A": False, "B": False})
        self.assertEqual(state["sides"]["A"]["protected_ids"], [])
        self.assertEqual(state["sides"]["B"]["protected_ids"], [])

    def test_same_seed_same_state_including_bench(self):
        self.assertEqual(new_match(seed=7), new_match(seed=7))

    def test_same_seed_same_state_with_different_formations(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        self.assertEqual(new_match(setups=setups, seed=9), new_match(setups=setups, seed=9))

    def test_different_seed_different_deal(self):
        s1, s2 = new_match(seed=1), new_match(seed=2)
        self.assertNotEqual(all_ids(s1, "A"), all_ids(s2, "A"))

    def test_inputs_are_not_mutated(self):
        players = copy.deepcopy(PLAYERS)
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        setups_before = copy.deepcopy(setups)
        create_match(players=players, setups=setups, seed=3)
        self.assertEqual(players, PLAYERS)
        self.assertEqual(setups, setups_before)


class StealTests(unittest.TestCase):
    def test_steal_in_arrange_phase_raises(self):
        arranging = play_out(new_match())
        with self.assertRaises(ValueError):
            steal(arranging, "A", unprotected_ids(arranging, "B")[0], unprotected_ids(arranging, "A")[0])

    def test_steal_in_done_phase_raises(self):
        done = finish_arrange(play_out(new_match()))
        with self.assertRaises(ValueError):
            steal(done, "A", unprotected_ids(done, "B")[0], unprotected_ids(done, "A")[0])

    def test_second_steal_before_protect_step_raises(self):
        state = first_steal(new_match(), "A")
        self.assertEqual(state["step"], "protect")
        self.assertEqual(state["turn"], "A")
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])

    def test_wrong_turn_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])

    def test_protected_slot_target_raises(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        protected_a = state["sides"]["A"]["protected_ids"][0]
        with self.assertRaises(ValueError):
            steal(state, "B", protected_a, unprotected_ids(state, "B")[0])

    def test_protected_bench_target_raises(self):
        state = first_steal(new_match(), "A")
        bench_a = bench_ids(state, "A")[0]
        state = protect(state, "A", [bench_a])
        with self.assertRaises(ValueError):
            steal(state, "B", bench_a, unprotected_ids(state, "B")[0])

    def test_protected_give_raises(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        protected_a = state["sides"]["A"]["protected_ids"][0]
        state = steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])
        state = protect(state, "B", squad_ids(state, "B")[:3])
        self.assertIn(protected_a, all_ids(state, "A"))
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], protected_a)

    def test_target_on_own_side_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "A")[0], unprotected_ids(state, "A")[1])

    def test_give_from_opponent_side_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "B")[0])

    def test_unknown_ids_raise(self):
        state = new_match()
        with self.assertRaises(ValueError):
            steal(state, "A", "does-not-exist", unprotected_ids(state, "A")[0])
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], "does-not-exist")

    def test_slot_to_slot_swap_moves_players_and_keeps_slot_pos(self):
        state = new_match()
        target = squad_ids(state, "B")[0]
        give = squad_ids(state, "A")[0]
        new = steal(state, "A", target, give)
        self.assertEqual(new["sides"]["A"]["slots"][0]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["slots"][0]["player"]["id"], give)
        self.assertEqual(new["sides"]["A"]["slots"][0]["pos"], FORMATION_433["slots"][0])
        self.assertEqual(len(set(squad_ids(new, "A"))), 11)
        self.assertEqual(len(set(squad_ids(new, "B"))), 11)

    def test_steal_rival_bench_player_for_own_slot_player(self):
        state = new_match()
        target = bench_ids(state, "B")[2]
        give = squad_ids(state, "A")[4]
        new = steal(state, "A", target, give)
        self.assertEqual(locate(new, "A", target), ("slot", 4))
        self.assertEqual(locate(new, "B", give), ("bench", 2))
        self.assertEqual(new["sides"]["A"]["slots"][4]["pos"], FORMATION_433["slots"][4])

    def test_steal_own_bench_player_for_rival_slot_player(self):
        state = new_match()
        target = squad_ids(state, "B")[7]
        give = bench_ids(state, "A")[5]
        new = steal(state, "A", target, give)
        self.assertEqual(locate(new, "A", target), ("bench", 5))
        self.assertEqual(locate(new, "B", give), ("slot", 7))

    def test_bench_for_bench_swap(self):
        state = new_match()
        target = bench_ids(state, "B")[1]
        give = bench_ids(state, "A")[6]
        new = steal(state, "A", target, give)
        self.assertEqual(locate(new, "A", target), ("bench", 6))
        self.assertEqual(locate(new, "B", give), ("bench", 1))
        self.assertEqual(len(all_ids(new, "A")), SQUAD_SIZE)
        self.assertEqual(len(all_ids(new, "B")), SQUAD_SIZE)

    def test_swap_with_different_formations_keeps_each_side_layout(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        state = new_match(setups=setups)
        target = squad_ids(state, "B")[9]
        give = squad_ids(state, "A")[9]
        new = steal(state, "A", target, give)
        self.assertEqual([s["pos"] for s in new["sides"]["A"]["slots"]], FORMATION_433["slots"])
        self.assertEqual([s["pos"] for s in new["sides"]["B"]["slots"]], FORMATION_442["slots"])
        self.assertEqual(new["sides"]["A"]["slots"][9]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["slots"][9]["player"]["id"], give)

    def test_steal_moves_to_protect_step_same_turn(self):
        new = first_steal(new_match(), "A")
        self.assertEqual(new["phase"], "steal")
        self.assertEqual(new["step"], "protect")
        self.assertEqual(new["turn"], "A")
        self.assertEqual(new["steals_left"], {"A": 2, "B": 3})

    def test_steal_does_not_auto_protect_anyone(self):
        state = new_match()
        new = steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])
        self.assertEqual(new["sides"]["A"]["protected_ids"], [])
        self.assertEqual(new["sides"]["B"]["protected_ids"], [])

    def test_stolen_player_can_be_protected_in_protect_step(self):
        state = new_match()
        target = unprotected_ids(state, "B")[0]
        state = steal(state, "A", target, unprotected_ids(state, "A")[0])
        state = protect(state, "A", [target])
        self.assertEqual(state["sides"]["A"]["protected_ids"], [target])

    def test_unprotected_stolen_player_can_be_stolen_back(self):
        state = new_match()
        target = unprotected_ids(state, "B")[0]
        state = steal(state, "A", target, unprotected_ids(state, "A")[0])
        self.assertIn(target, all_ids(state, "A"))
        # Yeni alınan oyuncu korunmadı -> rakip (B) geri alabilir.
        state = protect(state, "A", squad_ids(state, "A")[1:4])
        self.assertNotIn(target, state["sides"]["A"]["protected_ids"])
        new = steal(state, "B", target, unprotected_ids(state, "B")[0])
        self.assertIn(target, all_ids(new, "B"))

    def test_steal_does_not_mutate_input(self):
        state = new_match()
        before = copy.deepcopy(state)
        steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])
        self.assertEqual(state, before)


class ProtectTests(unittest.TestCase):
    def test_protect_in_steal_step_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            protect(state, "A", squad_ids(state, "A")[:3])

    def test_protect_wrong_turn_raises(self):
        state = first_steal(new_match(), "A")
        with self.assertRaises(ValueError):
            protect(state, "B", squad_ids(state, "B")[:3])

    def test_more_than_three_raises(self):
        state = first_steal(new_match(), "A")
        with self.assertRaises(ValueError):
            protect(state, "A", all_ids(state, "A")[:4])

    def test_duplicate_ids_raise(self):
        state = first_steal(new_match(), "A")
        pid = squad_ids(state, "A")[0]
        with self.assertRaises(ValueError):
            protect(state, "A", [pid, pid])

    def test_id_from_other_side_raises(self):
        state = first_steal(new_match(), "A")
        with self.assertRaises(ValueError):
            protect(state, "A", [squad_ids(state, "B")[0]])

    def test_bench_player_can_be_protected(self):
        state = first_steal(new_match(), "A")
        bench_a = bench_ids(state, "A")[3]
        state = protect(state, "A", [bench_a, squad_ids(state, "A")[0]])
        self.assertEqual(state["sides"]["A"]["protected_ids"], [bench_a, squad_ids(state, "A")[0]])

    def test_all_nineteen_are_eligible_but_at_most_three_protected(self):
        state = first_steal(new_match(), "A")
        for pid in all_ids(state, "A"):
            with self.subTest(pid=pid):
                protected = protect(state, "A", [pid])
                self.assertEqual(protected["sides"]["A"]["protected_ids"], [pid])

    def test_empty_list_is_allowed(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", [])
        self.assertEqual(state["sides"]["A"]["protected_ids"], [])

    def test_fewer_than_three_is_allowed(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:2])
        self.assertEqual(len(state["sides"]["A"]["protected_ids"]), 2)

    def test_protect_replaces_previous_protection(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        state = steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])
        state = protect(state, "B", squad_ids(state, "B")[:3])
        state = steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])
        new_ids = bench_ids(state, "A")[:2]
        state = protect(state, "A", new_ids)
        self.assertEqual(state["sides"]["A"]["protected_ids"], new_ids)

    def test_protect_advances_turn_and_step(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        self.assertEqual(state["turn"], "B")
        self.assertEqual(state["step"], "steal")

    def test_protect_does_not_mutate_input(self):
        state = first_steal(new_match(), "A")
        before = copy.deepcopy(state)
        protect(state, "A", squad_ids(state, "A")[:3])
        self.assertEqual(state, before)

    def test_protect_in_arrange_phase_raises(self):
        arranging = play_out(new_match())
        with self.assertRaises(ValueError):
            protect(arranging, "A", squad_ids(arranging, "A")[:3])


class TurnFlowTests(unittest.TestCase):
    def test_last_steal_moves_to_arrange_without_protect_step(self):
        state = play_out(new_match())
        self.assertEqual(state["phase"], "arrange")
        self.assertEqual(state["steals_left"], {"A": 0, "B": 0})
        self.assertEqual(state["arranged"], {"A": False, "B": False})

    def test_six_steals_end_in_arrange_and_further_steal_raises(self):
        state = new_match()
        steals = 0
        while state["phase"] == "steal":
            state = first_steal(state)
            steals += 1
            if state["phase"] == "steal":
                state = protect(state, state["turn"], [])
                # protect sonrası sıra değişti; takas yapan taraf bir önceki turdu
        self.assertEqual(steals, 6)
        self.assertEqual(state["phase"], "arrange")
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])

    def test_turns_alternate_between_sides(self):
        state = new_match()
        turns = []
        while state["phase"] == "steal":
            turns.append(state["turn"])
            state = steal_and_protect(state)
        self.assertEqual(turns, ["A", "B", "A", "B", "A", "B"])


class SwapBenchTests(unittest.TestCase):
    def test_swap_exchanges_slot_and_bench_players(self):
        state = first_steal(new_match(), "A")
        slot_pid = squad_ids(state, "A")[5]
        bench_pid = bench_ids(state, "A")[2]
        new = swap_bench(state, "A", 5, 2)
        self.assertEqual(new["sides"]["A"]["slots"][5]["player"]["id"], bench_pid)
        self.assertEqual(new["sides"]["A"]["bench"][2]["id"], slot_pid)

    def test_swap_keeps_slot_positions_and_side_membership(self):
        state = first_steal(new_match(), "A")
        new = swap_bench(state, "A", 0, 0)
        self.assertEqual([s["pos"] for s in new["sides"]["A"]["slots"]], FORMATION_433["slots"])
        self.assertEqual(set(all_ids(new, "A")), set(all_ids(state, "A")))
        self.assertEqual(set(all_ids(new, "B")), set(all_ids(state, "B")))

    def test_protected_player_can_be_swapped_out_to_bench(self):
        state = first_steal(new_match(), "A")
        protected_pid = squad_ids(state, "A")[0]
        state = protect(state, "A", [protected_pid])
        # Sıra B'de; A'nın yerleşimi yalnızca kendi sırasında yapılır.
        state = steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])
        state = protect(state, "B", [])
        state = first_steal(state, "A")
        new = swap_bench(state, "A", 0, 0)
        self.assertIn(protected_pid, bench_ids(new, "A"))

    def test_swap_allowed_during_steal_step_of_own_turn(self):
        state = new_match()
        self.assertEqual(state["step"], "steal")
        new = swap_bench(state, "A", 3, 4)
        self.assertEqual(new["sides"]["A"]["slots"][3]["player"]["id"], bench_ids(state, "A")[4])

    def test_swap_allowed_during_protect_step_of_own_turn(self):
        state = first_steal(new_match(), "A")
        self.assertEqual(state["step"], "protect")
        new = swap_bench(state, "A", 1, 1)
        self.assertEqual(new["sides"]["A"]["slots"][1]["player"]["id"], bench_ids(state, "A")[1])

    def test_swap_on_other_side_during_steal_phase_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            swap_bench(state, "B", 0, 0)

    def test_swap_for_other_side_during_protect_step_raises(self):
        state = first_steal(new_match(), "A")
        with self.assertRaises(ValueError):
            swap_bench(state, "B", 0, 0)

    def test_slot_index_out_of_range_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            swap_bench(state, "A", 11, 0)

    def test_bench_index_out_of_range_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            swap_bench(state, "A", 0, BENCH_SIZE)

    def test_swap_does_not_mutate_input(self):
        state = new_match()
        before = copy.deepcopy(state)
        swap_bench(state, "A", 2, 2)
        self.assertEqual(state, before)

    def test_swap_does_not_change_phase_or_turn(self):
        state = new_match()
        new = swap_bench(state, "A", 0, 0)
        self.assertEqual(new["phase"], "steal")
        self.assertEqual(new["turn"], "A")
        self.assertEqual(new["steals_left"], state["steals_left"])


class ArrangeTests(unittest.TestCase):
    def test_last_steal_starts_arrange_and_both_sides_confirm_to_done(self):
        arranging = play_out(new_match())
        self.assertEqual(arranging["phase"], "arrange")
        once = confirm_arrange(arranging, "A")
        self.assertEqual(once["arranged"], {"A": True, "B": False})
        self.assertEqual(once["phase"], "arrange")
        twice = confirm_arrange(once, "B")
        self.assertEqual(twice["arranged"], {"A": True, "B": True})
        self.assertEqual(twice["phase"], "done")

    def test_order_of_confirmation_does_not_matter(self):
        arranging = play_out(new_match())
        state = confirm_arrange(arranging, "B")
        self.assertEqual(state["phase"], "arrange")
        state = confirm_arrange(state, "A")
        self.assertEqual(state["phase"], "done")

    def test_arrangement_swaps_are_allowed_until_side_confirms(self):
        arranging = play_out(new_match())
        a_swapped = swap_bench(arranging, "A", 4, 3)
        a_ready = confirm_arrange(a_swapped, "A")
        b_swapped = swap_bench(a_ready, "B", 9, 7)
        self.assertEqual(b_swapped["sides"]["B"]["slots"][9]["player"]["id"],
                         bench_ids(a_ready, "B")[7])
        done = confirm_arrange(b_swapped, "B")
        self.assertEqual(done["phase"], "done")
        self.assertEqual(done["sides"]["A"]["slots"][4]["player"]["id"],
                         bench_ids(arranging, "A")[3])

    def test_swap_after_own_confirm_raises(self):
        arranging = confirm_arrange(play_out(new_match()), "A")
        with self.assertRaises(ValueError):
            swap_bench(arranging, "A", 0, 0)
        # Karşı taraf hâlâ düzenleyebilir.
        self.assertEqual(swap_bench(arranging, "B", 0, 0)["phase"], "arrange")

    def test_confirm_twice_raises(self):
        arranging = confirm_arrange(play_out(new_match()), "A")
        with self.assertRaises(ValueError):
            confirm_arrange(arranging, "A")

    def test_confirm_during_steal_phase_raises(self):
        with self.assertRaises(ValueError):
            confirm_arrange(new_match(), "A")

    def test_confirm_in_done_phase_raises(self):
        done = finish_arrange(play_out(new_match()))
        with self.assertRaises(ValueError):
            confirm_arrange(done, "A")

    def test_confirm_invalid_side_raises(self):
        with self.assertRaises(ValueError):
            confirm_arrange(play_out(new_match()), "C")

    def test_protect_and_steal_are_closed_in_arrange(self):
        arranging = play_out(new_match())
        with self.assertRaises(ValueError):
            steal(arranging, "A", unprotected_ids(arranging, "B")[0], unprotected_ids(arranging, "A")[0])
        with self.assertRaises(ValueError):
            protect(arranging, "A", [])

    def test_does_not_mutate_input(self):
        arranging = play_out(new_match())
        before = copy.deepcopy(arranging)
        confirm_arrange(arranging, "A")
        swap_bench(arranging, "B", 0, 0)
        self.assertEqual(arranging, before)


class SlotScoreTests(unittest.TestCase):
    def test_exact_pos_gives_rating(self):
        self.assertEqual(slot_score("ST", make_player(1, "ST", rating=80)), 80)

    def test_alt_pos_gives_rating(self):
        self.assertEqual(slot_score("ST", make_player(1, "LW", alt=["ST"], rating=80)), 80)

    def test_other_pos_gives_rating_minus_ten(self):
        self.assertEqual(slot_score("GK", make_player(1, "ST", rating=80)), 70)

    def test_penalty_never_below_zero(self):
        self.assertEqual(slot_score("GK", make_player(1, "ST", rating=5)), 0)


class TeamRatingAndResultTests(unittest.TestCase):
    def test_team_rating_is_rounded_mean_of_own_slot_scores(self):
        state = play_out(new_match())
        for side in ("A", "B"):
            self.assertEqual(team_rating(state, side), team_rating_from_slots(state, side))

    def test_team_rating_ignores_bench_players(self):
        state = play_out(new_match())
        changed = copy.deepcopy(state)
        for side in ("A", "B"):
            for player in changed["sides"][side]["bench"]:
                player["rating"] = 99
        for side in ("A", "B"):
            self.assertEqual(team_rating(changed, side), team_rating(state, side))

    def test_team_rating_reflects_slot_player_after_bench_swap(self):
        state = play_out(new_match())
        # Yedek, ilk 11'in 0. slotuna (GK) geçince puana o oyuncunun slot puanı yansır.
        state["sides"]["A"]["bench"][0]["rating"] = 99
        state["sides"]["A"]["bench"][0]["pos"] = "GK"
        swapped = swap_bench(state, "A", 0, 0)
        self.assertEqual(slot_score("GK", swapped["sides"]["A"]["slots"][0]["player"]), 99)
        self.assertEqual(team_rating(swapped, "A"), team_rating_from_slots(swapped, "A"))

    def test_result_requires_done_phase(self):
        with self.assertRaises(ValueError):
            result(play_out(new_match()))
        with self.assertRaises(ValueError):
            result(new_match())

    def test_result_matches_final_ratings_and_winner(self):
        state = finish_arrange(play_out(new_match()))
        res = result(state)
        a = team_rating(state, "A")
        b = team_rating(state, "B")
        self.assertEqual(res["A"], a)
        self.assertEqual(res["B"], b)
        expected = "A" if a > b else "B" if b > a else "draw"
        self.assertEqual(res["winner"], expected)


class DeterminismTests(unittest.TestCase):
    def play(self, seed):
        state = new_match(seed=seed)
        state = first_steal(state, "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        state = swap_bench(state, "B", 2, 1)
        state = steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])
        state = protect(state, "B", [])
        state = play_out(state)
        state = swap_bench(state, "A", 1, 4)
        return finish_arrange(state)

    def test_same_seed_and_moves_give_same_state_and_result(self):
        first, second = self.play(seed=11), self.play(seed=11)
        self.assertEqual(first, second)
        self.assertEqual(result(first), result(second))

    def test_same_seed_and_moves_with_different_formations(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_352)}

        def run():
            state = new_match(setups=setups, seed=4)
            state = play_out(state)
            return finish_arrange(swap_bench(state, "A", 0, 0))

        self.assertEqual(run(), run())


class RealDataEndToEndTests(unittest.TestCase):
    """Gerçek data/*.json ile tam maç: farklı kategori + formasyon, 19 oyuncu, 6 takas, arrange."""

    @classmethod
    def setUpClass(cls):
        def load(name):
            with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
                return json.load(fh)

        cls.players = load("players.json")
        cls.formations = load("formations.json")

    def formation(self, fid):
        return next(f for f in self.formations if f["id"] == fid)

    def build(self, seed=1):
        setups = {
            "A": setup([{"type": "nation", "value": "England"}], self.formation("4-3-3")),
            "B": setup([{"type": "league", "value": "Premier League"}], self.formation("4-4-2")),
        }
        return create_match(players=self.players, setups=setups,
                            protect_count=3, steals_per_side=3, bench_size=8, seed=seed)

    def test_real_data_deal_respects_categories_and_disjointness(self):
        state = self.build()
        by_id = {p["id"]: p for p in self.players}
        for pid in all_ids(state, "A"):
            self.assertEqual(by_id[pid]["nation"], "England")
        for pid in all_ids(state, "B"):
            self.assertEqual(by_id[pid]["league"], "Premier League")
        self.assertEqual(len(bench_ids(state, "A")), BENCH_SIZE)
        self.assertEqual(len(bench_ids(state, "B")), BENCH_SIZE)
        self.assertEqual(set(all_ids(state, "A")) & set(all_ids(state, "B")), set())
        self.assertEqual([s["pos"] for s in state["sides"]["B"]["slots"]],
                         self.formation("4-4-2")["slots"])
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["step"], "steal")

    def test_full_match_with_six_steals_arrange_and_result(self):
        state = self.build()
        steals = 0
        while state["phase"] == "steal":
            side = state["turn"]
            before = {s: set(all_ids(state, s)) for s in ("A", "B")}
            state = first_steal(state, side)
            steals += 1
            after = {s: set(all_ids(state, s)) for s in ("A", "B")}
            # Her takasta iki taraf da 19 oyuncuyu korur ve iki oyuncu el değiştirir.
            self.assertEqual(len(after["A"]), SQUAD_SIZE)
            self.assertEqual(len(after["B"]), SQUAD_SIZE)
            self.assertEqual(len(before["A"] ^ after["A"]), 2)
            self.assertEqual(len(before["B"] ^ after["B"]), 2)
            if state["phase"] == "steal":
                self.assertEqual(state["step"], "protect")
                state = protect(state, side, squad_ids(state, side)[:3])

        self.assertEqual(steals, 6)
        self.assertEqual(state["phase"], "arrange")
        for side in ("A", "B"):
            self.assertEqual(len(set(all_ids(state, side))), SQUAD_SIZE)
            self.assertLessEqual(len(state["sides"][side]["protected_ids"]), 3)
            self.assertTrue(set(state["sides"][side]["protected_ids"]) <= set(all_ids(state, side)))
        self.assertEqual(set(all_ids(state, "A")) & set(all_ids(state, "B")), set())

        state = finish_arrange(state)
        self.assertEqual(state["phase"], "done")
        res = result(state)
        self.assertIn(res["winner"], ("A", "B", "draw"))
        self.assertEqual(res["A"], team_rating(state, "A"))
        self.assertEqual(res["B"], team_rating(state, "B"))


if __name__ == "__main__":
    unittest.main()

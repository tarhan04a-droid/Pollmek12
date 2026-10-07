"""Streamlit sürümü motor testleri (docs/CONTRACT.md "Güncelleme 2" > Motor).

Yalnızca standart unittest. engine.py repo kökünde olmalı; bu dosya kökü sys.path'e ekler.
Yeni imza: create_match(players, setups, protect_count=3, steals_per_side=3, seed=1).
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

from engine import create_match, protect, result, slot_score, steal, team_rating  # noqa: E402

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
    """Alpha ve Beta: her pozisyondan 3'er oyuncu (L1; ülkeleri farklı).
    Gamma: sadece 3 ST (yetersiz havuz)."""
    players = []
    pid = 1
    for club, nation in (("Alpha", "Nationa"), ("Beta", "Nationb")):
        for _ in range(3):
            for pos in POSITIONS:
                players.append(make_player(pid, pos, club=club, league="L1", nation=nation,
                                           rating=70 + (pid % 20)))
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


def new_match(setups=None, **overrides):
    kwargs = dict(players=PLAYERS, setups=setups if setups is not None else default_setups(), seed=1)
    kwargs.update(overrides)
    return create_match(**kwargs)


def squad_ids(state, side):
    return [slot["player"]["id"] for slot in state["sides"][side]["slots"]]


def unprotected_ids(state, side):
    protected = state["sides"][side]["protected_ids"]
    return [pid for pid in squad_ids(state, side) if pid not in protected]


def other(side):
    return "B" if side == "A" else "A"


def ready_for_steal(**overrides):
    """Her iki taraf ilk protect_count oyuncusunu korur -> phase 'steal', turn 'A'."""
    state = new_match(**overrides)
    k = state["protect_count"]
    state = protect(state, "A", squad_ids(state, "A")[:k])
    state = protect(state, "B", squad_ids(state, "B")[:k])
    return state


def play_out(state):
    """Kalan tüm takas turlarını deterministik seçimlerle oynar."""
    while state["phase"] == "steal":
        side = state["turn"]
        target = unprotected_ids(state, other(side))[0]
        give = unprotected_ids(state, side)[0]
        state = steal(state, side, target, give)
    return state


def find_slot_index(state, side, pid):
    for i, slot in enumerate(state["sides"][side]["slots"]):
        if slot["player"]["id"] == pid:
            return i
    raise AssertionError(f"{pid} {side} kadrosunda yok")


class CreateMatchTests(unittest.TestCase):
    def test_pool_too_small_raises_and_names_side(self):
        setups = default_setups()
        setups["B"] = setup([{"type": "club", "value": "Gamma"}], FORMATION_433)
        with self.assertRaises(ValueError) as cm:
            new_match(setups=setups)
        self.assertRegex(str(cm.exception), r"\bB\b")

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
        # Beta/L1 kullanılmaz: B'nin havuzunu tüketmemek için (havuzlar kesişirse oyuncu tek tarafta).
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

    def test_each_side_gets_eleven_slots_in_its_own_formation_order(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        state = new_match(setups=setups)
        for side, formation in (("A", FORMATION_433), ("B", FORMATION_442)):
            slots = state["sides"][side]["slots"]
            self.assertEqual(len(slots), 11)
            self.assertEqual([s["pos"] for s in slots], formation["slots"])
            self.assertEqual(state["sides"][side]["protected_ids"], [])

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
        for pid in squad_ids(state, "A"):
            self.assertEqual(PLAYERS_BY_ID[pid]["club"], "Alpha")
        for pid in squad_ids(state, "B"):
            p = PLAYERS_BY_ID[pid]
            self.assertTrue(p["club"] == "Beta" or p["nation"] == "Nationb")

    def test_overlapping_pools_player_only_on_one_side(self):
        setups = {
            "A": setup(CLUB_ALPHA, FORMATION_433),
            "B": setup(LEAGUE_L1, FORMATION_442),
        }
        state = new_match(setups=setups)
        a, b = squad_ids(state, "A"), squad_ids(state, "B")
        self.assertEqual(len(set(a)), 11)
        self.assertEqual(len(set(b)), 11)
        self.assertEqual(set(a) & set(b), set())

    def test_identical_pools_no_player_on_both_sides(self):
        setups = {"A": setup(LEAGUE_L1, FORMATION_433), "B": setup(LEAGUE_L1, FORMATION_433)}
        state = new_match(setups=setups)
        a, b = squad_ids(state, "A"), squad_ids(state, "B")
        self.assertEqual(len(set(a)), 11)
        self.assertEqual(len(set(b)), 11)
        self.assertEqual(set(a) & set(b), set())

    def test_dealt_player_fits_slot_by_pos_or_alt(self):
        pool = [make_player(i, "LW", alt=["ST"]) for i in range(1, 23)]
        formation = {"id": "x", "slots": ["ST"] * 11}
        setups = {"A": setup(CLUB_ALPHA, formation), "B": setup(CLUB_ALPHA, formation)}
        state = create_match(players=pool, setups=setups, seed=5)
        for side in ("A", "B"):
            for slot in state["sides"][side]["slots"]:
                self.assertTrue(slot["player"]["pos"] == slot["pos"]
                                or slot["pos"] in slot["player"]["alt"])

    def test_initial_state_fields(self):
        state = new_match()
        self.assertEqual(state["phase"], "protect")
        self.assertEqual(state["steals_left"], {"A": 3, "B": 3})
        self.assertEqual(state["protect_count"], 3)
        self.assertIn(state["turn"], ("A", "B"))

    def test_same_seed_same_state(self):
        self.assertEqual(new_match(seed=7), new_match(seed=7))

    def test_same_seed_same_state_with_different_formations(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        self.assertEqual(new_match(setups=setups, seed=9), new_match(setups=setups, seed=9))

    def test_different_seed_different_deal(self):
        self.assertNotEqual(squad_ids(new_match(seed=1), "A"), squad_ids(new_match(seed=2), "A"))

    def test_inputs_are_not_mutated(self):
        players = copy.deepcopy(PLAYERS)
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        setups_before = copy.deepcopy(setups)
        create_match(players=players, setups=setups, seed=3)
        self.assertEqual(players, PLAYERS)
        self.assertEqual(setups, setups_before)


class ProtectTests(unittest.TestCase):
    def test_wrong_count_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            protect(state, "A", squad_ids(state, "A")[:2])

    def test_id_from_other_side_raises(self):
        state = new_match()
        with self.assertRaises(ValueError):
            protect(state, "A", squad_ids(state, "B")[:3])

    def test_phase_moves_to_steal_only_after_both_sides(self):
        state = new_match()
        state = protect(state, "A", squad_ids(state, "A")[:3])
        self.assertEqual(state["phase"], "protect")
        state = protect(state, "B", squad_ids(state, "B")[:3])
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["turn"], "A")
        self.assertEqual(sorted(state["sides"]["A"]["protected_ids"]),
                         sorted(squad_ids(state, "A")[:3]))

    def test_protect_does_not_mutate_input(self):
        state = new_match()
        before = copy.deepcopy(state)
        protect(state, "A", squad_ids(state, "A")[:3])
        self.assertEqual(state, before)


class StealRuleTests(unittest.TestCase):
    def test_steal_before_both_protect_raises(self):
        state = new_match()
        state = protect(state, "A", squad_ids(state, "A")[:3])
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])

    def test_wrong_turn_raises(self):
        state = ready_for_steal()
        with self.assertRaises(ValueError):
            steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])

    def test_protected_target_raises(self):
        state = ready_for_steal()
        protected_b = state["sides"]["B"]["protected_ids"][0]
        with self.assertRaises(ValueError):
            steal(state, "A", protected_b, unprotected_ids(state, "A")[0])

    def test_protected_give_raises(self):
        state = ready_for_steal()
        protected_a = state["sides"]["A"]["protected_ids"][0]
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], protected_a)

    def test_target_on_own_side_raises(self):
        state = ready_for_steal()
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "A")[0], unprotected_ids(state, "A")[1])

    def test_give_from_opponent_side_raises(self):
        state = ready_for_steal()
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "B")[0])

    def test_swap_moves_players_into_each_others_slots(self):
        state = ready_for_steal()
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        idx_a = find_slot_index(state, "A", give)
        idx_b = find_slot_index(state, "B", target)
        pos_a = state["sides"]["A"]["slots"][idx_a]["pos"]
        pos_b = state["sides"]["B"]["slots"][idx_b]["pos"]

        new = steal(state, "A", target, give)

        self.assertEqual(new["sides"]["A"]["slots"][idx_a]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["slots"][idx_b]["player"]["id"], give)
        # Slot pozisyon etiketleri değişmez.
        self.assertEqual(new["sides"]["A"]["slots"][idx_a]["pos"], pos_a)
        self.assertEqual(new["sides"]["B"]["slots"][idx_b]["pos"], pos_b)
        self.assertEqual(len(set(squad_ids(new, "A"))), 11)
        self.assertEqual(len(set(squad_ids(new, "B"))), 11)

    def test_swap_with_different_formations_keeps_each_side_layout(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        state = ready_for_steal(setups=setups)
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        idx_a = find_slot_index(state, "A", give)
        idx_b = find_slot_index(state, "B", target)

        new = steal(state, "A", target, give)

        self.assertEqual([s["pos"] for s in new["sides"]["A"]["slots"]], FORMATION_433["slots"])
        self.assertEqual([s["pos"] for s in new["sides"]["B"]["slots"]], FORMATION_442["slots"])
        self.assertEqual(new["sides"]["A"]["slots"][idx_a]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["slots"][idx_b]["player"]["id"], give)

    def test_stolen_player_becomes_protected_for_thief(self):
        state = ready_for_steal()
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        new = steal(state, "A", target, give)
        self.assertIn(target, new["sides"]["A"]["protected_ids"])
        self.assertEqual(len(new["sides"]["A"]["protected_ids"]), 4)
        self.assertNotIn(give, new["sides"]["A"]["protected_ids"])

    def test_stolen_player_cannot_be_stolen_back(self):
        state = ready_for_steal()
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        state = steal(state, "A", target, give)
        # Sıra B'de; A'nın kadrosundaki (artık A'da) target korumalı.
        with self.assertRaises(ValueError):
            steal(state, "B", target, unprotected_ids(state, "B")[0])

    def test_turn_and_steals_left_update(self):
        state = ready_for_steal()
        new = steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])
        self.assertEqual(new["turn"], "B")
        self.assertEqual(new["steals_left"], {"A": 2, "B": 3})
        self.assertEqual(new["phase"], "steal")

    def test_steal_does_not_mutate_input(self):
        state = ready_for_steal()
        before = copy.deepcopy(state)
        steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])
        self.assertEqual(state, before)

    def test_six_steals_end_in_done_and_further_steal_raises(self):
        state = ready_for_steal()
        for i in range(5):
            side = state["turn"]
            state = steal(state, side, unprotected_ids(state, other(side))[0],
                          unprotected_ids(state, side)[0])
            self.assertEqual(state["phase"], "steal", f"tur {i + 1} sonrası erken bitti")
        side = state["turn"]
        state = steal(state, side, unprotected_ids(state, other(side))[0],
                      unprotected_ids(state, side)[0])
        self.assertEqual(state["phase"], "done")
        self.assertEqual(state["steals_left"], {"A": 0, "B": 0})
        with self.assertRaises(ValueError):
            steal(state, "A", unprotected_ids(state, "B")[0], unprotected_ids(state, "A")[0])


class SlotScoreTests(unittest.TestCase):
    def test_exact_pos_gives_rating(self):
        self.assertEqual(slot_score("ST", make_player(1, "ST", rating=80)), 80)

    def test_alt_pos_gives_rating(self):
        self.assertEqual(slot_score("ST", make_player(1, "LW", rating=80, alt=["ST"])), 80)

    def test_other_pos_gives_rating_minus_ten(self):
        self.assertEqual(slot_score("ST", make_player(1, "CB", rating=80)), 70)

    def test_penalty_never_below_zero(self):
        self.assertEqual(slot_score("ST", make_player(1, "CB", rating=5)), 0)
        self.assertEqual(slot_score("ST", make_player(1, "CB", rating=10)), 0)


class TeamRatingAndResultTests(unittest.TestCase):
    def test_team_rating_is_rounded_mean_of_own_slot_scores(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        state = ready_for_steal(setups=setups)
        for side in ("A", "B"):
            scores = [slot_score(s["pos"], s["player"]) for s in state["sides"][side]["slots"]]
            self.assertEqual(team_rating(state, side), round(sum(scores) / 11))

    def test_result_requires_done_phase(self):
        with self.assertRaises(ValueError):
            result(ready_for_steal())

    def test_result_matches_final_ratings_and_winner(self):
        done = play_out(ready_for_steal())
        res = result(done)
        self.assertEqual(res["A"], team_rating(done, "A"))
        self.assertEqual(res["B"], team_rating(done, "B"))
        if res["A"] > res["B"]:
            expected = "A"
        elif res["B"] > res["A"]:
            expected = "B"
        else:
            expected = "draw"
        self.assertEqual(res["winner"], expected)


class DeterminismTests(unittest.TestCase):
    def test_same_seed_and_moves_give_same_result(self):
        first = play_out(ready_for_steal(seed=11))
        second = play_out(ready_for_steal(seed=11))
        self.assertEqual(first, second)
        self.assertEqual(result(first), result(second))

    def test_same_seed_and_moves_with_different_formations(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_352), "B": setup(CLUB_BETA, FORMATION_433)}
        first = play_out(ready_for_steal(setups=setups, seed=4))
        second = play_out(ready_for_steal(setups=setups, seed=4))
        self.assertEqual(first, second)
        self.assertEqual(result(first), result(second))


class RealDataEndToEndTests(unittest.TestCase):
    """Gerçek data/*.json ile tam maç: farklı kategori + farklı formasyon, 3 koruma + 6 takas."""

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
                            protect_count=3, steals_per_side=3, seed=seed)

    def test_real_data_deal_respects_categories_and_disjointness(self):
        state = self.build()
        by_id = {p["id"]: p for p in self.players}
        for pid in squad_ids(state, "A"):
            self.assertEqual(by_id[pid]["nation"], "England")
        for pid in squad_ids(state, "B"):
            self.assertEqual(by_id[pid]["league"], "Premier League")
        self.assertEqual(set(squad_ids(state, "A")) & set(squad_ids(state, "B")), set())
        self.assertEqual([s["pos"] for s in state["sides"]["B"]["slots"]],
                         self.formation("4-4-2")["slots"])

    def test_full_match_with_six_steals(self):
        state = self.build()
        k = state["protect_count"]
        state = protect(state, "A", squad_ids(state, "A")[:k])
        state = protect(state, "B", squad_ids(state, "B")[:k])

        steals = 0
        while state["phase"] == "steal":
            side = state["turn"]
            before = {s: set(squad_ids(state, s)) for s in ("A", "B")}
            state = steal(state, side, unprotected_ids(state, other(side))[0],
                          unprotected_ids(state, side)[0])
            steals += 1
            after = {s: set(squad_ids(state, s)) for s in ("A", "B")}
            # Her takasta iki taraf da kadro büyüklüğünü korur ve oyuncu el değiştirir.
            self.assertEqual(len(after["A"]), 11)
            self.assertEqual(len(after["B"]), 11)
            self.assertEqual(len(before["A"] ^ after["A"]), 2)
            self.assertEqual(len(before["B"] ^ after["B"]), 2)

        self.assertEqual(steals, 6)
        self.assertEqual(state["phase"], "done")
        for side in ("A", "B"):
            self.assertEqual(len(set(squad_ids(state, side))), 11)
            self.assertEqual(len(state["sides"][side]["protected_ids"]), 6)
        self.assertEqual(set(squad_ids(state, "A")) & set(squad_ids(state, "B")), set())

        res = result(state)
        self.assertIn(res["winner"], ("A", "B", "draw"))
        self.assertEqual(res["A"], team_rating(state, "A"))
        self.assertEqual(res["B"], team_rating(state, "B"))


if __name__ == "__main__":
    unittest.main()

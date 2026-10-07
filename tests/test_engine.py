"""Streamlit sürümü motor testleri (docs/CONTRACT.md "Streamlit sürümü > Motor").

Yalnızca standart unittest. engine.py repo kökünde olmalı; bu dosya kökü sys.path'e ekler.
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

FORMATION = {
    "id": "4-3-3",
    "slots": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"],
}


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
    """Alpha: 22 oyuncu (her slot pozisyonundan 2 tane). Beta: 22 oyuncu (L1).
    Gamma: sadece 3 ST (yetersiz havuz)."""
    players = []
    pid = 1
    for club, nation in (("Alpha", "Nationa"), ("Beta", "Nationb")):
        for _ in range(2):
            for pos in FORMATION["slots"]:
                players.append(make_player(pid, pos, club=club, league="L1", nation=nation,
                                           rating=70 + (pid % 20)))
                pid += 1
    for _ in range(3):
        players.append(make_player(pid, "ST", club="Gamma", league="L2", nation="Nationa",
                                   rating=75))
        pid += 1
    return players


PLAYERS = make_pool()
CLUB_ALPHA = [{"type": "club", "value": "Alpha"}]


def new_match(**overrides):
    kwargs = dict(players=PLAYERS, categories=CLUB_ALPHA, formation=FORMATION, seed=1)
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
    def test_pool_too_small_raises(self):
        with self.assertRaises(ValueError):
            new_match(categories=[{"type": "club", "value": "Gamma"}])

    def test_no_matching_category_raises(self):
        with self.assertRaises(ValueError):
            new_match(categories=[{"type": "nation", "value": "Yokhayir"}])

    def test_both_sides_get_every_slot_in_formation_order(self):
        state = new_match()
        for side in ("A", "B"):
            slots = state["sides"][side]["slots"]
            self.assertEqual(len(slots), 11)
            self.assertEqual([s["pos"] for s in slots], FORMATION["slots"])
            self.assertEqual(state["sides"][side]["protected_ids"], [])

    def test_no_player_on_both_sides_and_no_duplicates_within_side(self):
        state = new_match(categories=[{"type": "league", "value": "L1"}])
        a, b = squad_ids(state, "A"), squad_ids(state, "B")
        self.assertEqual(len(set(a)), 11)
        self.assertEqual(len(set(b)), 11)
        self.assertEqual(set(a) & set(b), set())

    def test_dealt_player_fits_slot_by_pos_or_alt(self):
        pool = [make_player(i, "LW", alt=["ST"]) for i in range(1, 23)]
        state = create_match(players=pool, categories=CLUB_ALPHA,
                             formation={"id": "x", "slots": ["ST"] * 11}, seed=5)
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
        self.assertIsInstance(state["log"], list)

    def test_same_seed_same_state(self):
        self.assertEqual(new_match(seed=7), new_match(seed=7))

    def test_different_seed_different_deal(self):
        self.assertNotEqual(squad_ids(new_match(seed=1), "A"), squad_ids(new_match(seed=2), "A"))

    def test_inputs_are_not_mutated(self):
        players = copy.deepcopy(PLAYERS)
        categories = [{"type": "club", "value": "Alpha"}]
        formation = copy.deepcopy(FORMATION)
        create_match(players=players, categories=categories, formation=formation, seed=3)
        self.assertEqual(players, PLAYERS)
        self.assertEqual(categories, [{"type": "club", "value": "Alpha"}])
        self.assertEqual(formation, FORMATION)


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
    def test_team_rating_is_rounded_mean_of_slot_scores(self):
        state = ready_for_steal()
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


class RealDataEndToEndTests(unittest.TestCase):
    """Gerçek data/*.json ile tam maç: 3 koruma + 6 takas."""

    @classmethod
    def setUpClass(cls):
        def load(name):
            with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
                return json.load(fh)

        cls.players = load("players.json")
        formations = load("formations.json")
        cls.formation = next(f for f in formations if f["id"] == "4-3-3")

    def test_full_match_with_six_steals(self):
        state = create_match(
            players=self.players,
            categories=[{"type": "league", "value": "Premier League"}],
            formation=self.formation,
            protect_count=3,
            steals_per_side=3,
            seed=1,
        )
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

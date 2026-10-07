"""Streamlit sürümü motor testleri (docs/CONTRACT.md "Güncelleme 3" > Motor).

Yalnızca standart unittest. engine.py repo kökünde olmalı; bu dosya kökü sys.path'e ekler.
Güncelleme 3: ayrı koruma aşaması yok. phase "steal"/"done"; step "steal" -> (takas) -> "protect" -> (koruma) -> "steal".
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


def first_steal(state, side=None):
    """Sıradaki tarafın takasını yapar (koruma adımına GEÇMEZ): rakipten ilk korumasız, kendinden ilk korumasız."""
    side = side or state["turn"]
    target = unprotected_ids(state, other(side))[0]
    give = unprotected_ids(state, side)[0]
    return steal(state, side, target, give)


def steal_and_protect(state, keep=None):
    """Bir tam tur: takas + koruma (keep verilmezse kadronun ilk 3'ü). Maç biterse koruma yok."""
    side = state["turn"]
    state = first_steal(state, side)
    if state["phase"] == "done":
        return state
    ids = squad_ids(state, side)[:3] if keep is None else keep
    return protect(state, side, ids)


def play_out(state):
    """Kalan tüm turları deterministik seçimlerle oynar."""
    while state["phase"] == "steal":
        state = steal_and_protect(state)
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

    def test_initial_state_starts_unprotected_in_steal_step(self):
        state = new_match()
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["step"], "steal")
        self.assertEqual(state["turn"], "A")
        self.assertEqual(state["steals_left"], {"A": 3, "B": 3})
        self.assertEqual(state["protect_count"], 3)
        self.assertEqual(state["sides"]["A"]["protected_ids"], [])
        self.assertEqual(state["sides"]["B"]["protected_ids"], [])

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


class StealTests(unittest.TestCase):
    def test_steal_in_done_phase_raises(self):
        done = play_out(new_match())
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

    def test_protected_target_raises(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        protected_a = state["sides"]["A"]["protected_ids"][0]
        with self.assertRaises(ValueError):
            steal(state, "B", protected_a, unprotected_ids(state, "B")[0])

    def test_protected_give_raises(self):
        state = first_steal(new_match(), "A")
        state = protect(state, "A", squad_ids(state, "A")[:3])
        protected_a = state["sides"]["A"]["protected_ids"][0]
        state = steal(state, "B", unprotected_ids(state, "A")[0], unprotected_ids(state, "B")[0])
        state = protect(state, "B", squad_ids(state, "B")[:3])
        self.assertIn(protected_a, squad_ids(state, "A"))
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

    def test_swap_moves_players_into_each_others_slots(self):
        state = new_match()
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        idx_a = find_slot_index(state, "A", give)
        idx_b = find_slot_index(state, "B", target)
        pos_a = state["sides"]["A"]["slots"][idx_a]["pos"]
        pos_b = state["sides"]["B"]["slots"][idx_b]["pos"]

        new = steal(state, "A", target, give)

        self.assertEqual(new["sides"]["A"]["slots"][idx_a]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["slots"][idx_b]["player"]["id"], give)
        self.assertEqual(new["sides"]["A"]["slots"][idx_a]["pos"], pos_a)
        self.assertEqual(new["sides"]["B"]["slots"][idx_b]["pos"], pos_b)
        self.assertEqual(len(set(squad_ids(new, "A"))), 11)
        self.assertEqual(len(set(squad_ids(new, "B"))), 11)

    def test_swap_with_different_formations_keeps_each_side_layout(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_433), "B": setup(CLUB_BETA, FORMATION_442)}
        state = new_match(setups=setups)
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        idx_a = find_slot_index(state, "A", give)
        idx_b = find_slot_index(state, "B", target)

        new = steal(state, "A", target, give)

        self.assertEqual([s["pos"] for s in new["sides"]["A"]["slots"]], FORMATION_433["slots"])
        self.assertEqual([s["pos"] for s in new["sides"]["B"]["slots"]], FORMATION_442["slots"])
        self.assertEqual(new["sides"]["A"]["slots"][idx_a]["player"]["id"], target)
        self.assertEqual(new["sides"]["B"]["slots"][idx_b]["player"]["id"], give)

    def test_steal_moves_to_protect_step_same_turn(self):
        state = new_match()
        new = first_steal(state, "A")
        self.assertEqual(new["phase"], "steal")
        self.assertEqual(new["step"], "protect")
        self.assertEqual(new["turn"], "A")
        self.assertEqual(new["steals_left"], {"A": 2, "B": 3})

    def test_steal_does_not_auto_protect_anyone(self):
        state = new_match()
        target = unprotected_ids(state, "B")[0]
        give = unprotected_ids(state, "A")[0]
        new = steal(state, "A", target, give)
        self.assertEqual(new["sides"]["A"]["protected_ids"], [])
        self.assertEqual(new["sides"]["B"]["protected_ids"], [])
        self.assertNotIn(target, new["sides"]["A"]["protected_ids"])

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
        self.assertIn(target, squad_ids(state, "A"))
        # Yeni alınan oyuncu korunmadı -> rakip (B) geri alabilir.
        state = protect(state, "A", squad_ids(state, "A")[1:4])
        self.assertNotIn(target, state["sides"]["A"]["protected_ids"])
        new = steal(state, "B", target, unprotected_ids(state, "B")[0])
        self.assertIn(target, squad_ids(new, "B"))

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
            protect(state, "A", squad_ids(state, "A")[:4])

    def test_duplicate_ids_raise(self):
        state = first_steal(new_match(), "A")
        ids = squad_ids(state, "A")
        with self.assertRaises(ValueError):
            protect(state, "A", [ids[0], ids[0]])

    def test_id_from_other_side_raises(self):
        state = first_steal(new_match(), "A")
        with self.assertRaises(ValueError):
            protect(state, "A", [squad_ids(state, "B")[0]])

    def test_empty_list_is_allowed(self):
        state = protect(first_steal(new_match(), "A"), "A", [])
        self.assertEqual(state["sides"]["A"]["protected_ids"], [])
        self.assertEqual(state["turn"], "B")
        self.assertEqual(state["step"], "steal")

    def test_fewer_than_three_is_allowed(self):
        state = first_steal(new_match(), "A")
        ids = squad_ids(state, "A")
        state = protect(state, "A", [ids[0]])
        self.assertEqual(state["sides"]["A"]["protected_ids"], [ids[0]])

    def test_protect_replaces_previous_protection(self):
        state = first_steal(new_match(), "A")
        old = squad_ids(state, "A")[:3]
        state = protect(state, "A", old)
        state = first_steal(state, "B")
        state = protect(state, "B", [])
        # A'nın 2. turu: kendi korumasız bir oyuncusunu verip eskisi yerine yeni koruma seçer.
        state = first_steal(state, "A")
        new_id = unprotected_ids(state, "A")[0]
        state = protect(state, "A", [new_id])
        self.assertEqual(state["sides"]["A"]["protected_ids"], [new_id])
        for pid in old:
            self.assertIn(pid, unprotected_ids(state, "A"))

    def test_protect_advances_turn_and_step(self):
        state = first_steal(new_match(), "A")
        new = protect(state, "A", squad_ids(state, "A")[:3])
        self.assertEqual(new["phase"], "steal")
        self.assertEqual(new["step"], "steal")
        self.assertEqual(new["turn"], "B")

    def test_protect_does_not_mutate_input(self):
        state = first_steal(new_match(), "A")
        before = copy.deepcopy(state)
        protect(state, "A", squad_ids(state, "A")[:3])
        self.assertEqual(state, before)

    def test_protect_after_done_raises(self):
        done = play_out(new_match())
        with self.assertRaises(ValueError):
            protect(done, "A", squad_ids(done, "A")[:3])


class TurnFlowTests(unittest.TestCase):
    def test_last_steal_ends_match_without_protect_step(self):
        state = new_match()
        for _ in range(5):
            state = steal_and_protect(state)
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["steals_left"], {"A": 0, "B": 1})
        # 6. takas: B'nin son hakkı; koruma adımı yok, maç biter.
        self.assertEqual(state["turn"], "B")
        state = first_steal(state, "B")
        self.assertEqual(state["phase"], "done")
        self.assertEqual(state["steals_left"], {"A": 0, "B": 0})
        with self.assertRaises(ValueError):
            protect(state, "B", squad_ids(state, "B")[:3])

    def test_six_steals_end_in_done_and_further_steal_raises(self):
        state = new_match()
        for i in range(5):
            state = steal_and_protect(state)
            self.assertEqual(state["phase"], "steal", f"tur {i + 1} sonrası erken bitti")
        state = first_steal(state)
        self.assertEqual(state["phase"], "done")
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
        state = new_match(setups=setups)
        for side in ("A", "B"):
            scores = [slot_score(s["pos"], s["player"]) for s in state["sides"][side]["slots"]]
            self.assertEqual(team_rating(state, side), round(sum(scores) / 11))

    def test_result_requires_done_phase(self):
        with self.assertRaises(ValueError):
            result(new_match())

    def test_result_matches_final_ratings_and_winner(self):
        done = play_out(new_match())
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
        first = play_out(new_match(seed=11))
        second = play_out(new_match(seed=11))
        self.assertEqual(first, second)
        self.assertEqual(result(first), result(second))

    def test_same_seed_and_moves_with_different_formations(self):
        setups = {"A": setup(CLUB_ALPHA, FORMATION_352), "B": setup(CLUB_BETA, FORMATION_433)}
        first = play_out(new_match(setups=setups, seed=4))
        second = play_out(new_match(setups=setups, seed=4))
        self.assertEqual(first, second)
        self.assertEqual(result(first), result(second))


class RealDataEndToEndTests(unittest.TestCase):
    """Gerçek data/*.json ile tam maç: farklı kategori + farklı formasyon, 6 takas, koruma takasın içinde."""

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
        self.assertEqual(state["phase"], "steal")
        self.assertEqual(state["step"], "steal")

    def test_full_match_with_six_steals_and_protects(self):
        state = self.build()
        steals = 0
        while state["phase"] == "steal":
            side = state["turn"]
            before = {s: set(squad_ids(state, s)) for s in ("A", "B")}
            state = first_steal(state, side)
            steals += 1
            after = {s: set(squad_ids(state, s)) for s in ("A", "B")}
            # Her takasta iki taraf da kadro büyüklüğünü korur ve oyuncu el değiştirir.
            self.assertEqual(len(after["A"]), 11)
            self.assertEqual(len(after["B"]), 11)
            self.assertEqual(len(before["A"] ^ after["A"]), 2)
            self.assertEqual(len(before["B"] ^ after["B"]), 2)
            if state["phase"] == "steal":
                self.assertEqual(state["step"], "protect")
                state = protect(state, side, squad_ids(state, side)[:3])

        self.assertEqual(steals, 6)
        self.assertEqual(state["phase"], "done")
        for side in ("A", "B"):
            self.assertEqual(len(set(squad_ids(state, side))), 11)
            self.assertLessEqual(len(state["sides"][side]["protected_ids"]), 3)
            self.assertTrue(set(state["sides"][side]["protected_ids"]) <= set(squad_ids(state, side)))
        self.assertEqual(set(squad_ids(state, "A")) & set(squad_ids(state, "B")), set())

        res = result(state)
        self.assertIn(res["winner"], ("A", "B", "draw"))
        self.assertEqual(res["A"], team_rating(state, "A"))
        self.assertEqual(res["B"], team_rating(state, "B"))


if __name__ == "__main__":
    unittest.main()

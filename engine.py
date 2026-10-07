"""Rastgele Seçimli Maç motoru (Python). Saf fonksiyonlar, yalnızca standart kütüphane.

Sözleşme: docs/CONTRACT.md > "Streamlit sürümü" > Motor. src/engine.js ile aynı kurallar.
State düz dict; hiçbir fonksiyon girdiyi değiştirmez (copy.deepcopy). Hata = ValueError.
"""

import copy
import random

SIDES = ("A", "B")
CATEGORY_TYPES = ("club", "league", "nation")
ALT_PENALTY = 10


def _fail(message):
    raise ValueError(message)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_side(side):
    if side not in SIDES:
        _fail(f"Geçersiz taraf: {side!r} (A veya B olmalı)")


def _check_state(state):
    if not isinstance(state, dict) or "sides" not in state or "phase" not in state:
        _fail("Geçersiz state: create_match ile oluşturulmuş bir state gerekli")


def _other(side):
    return "B" if side == "A" else "A"


def _matches_category(player, category):
    # category["type"] ("club"|"league"|"nation") oyuncunun aynı alanı ile eşleşir.
    return player.get(category["type"]) == category["value"]


def _deal_sides(pool, slot_positions, rng):
    """Önce tam pozisyon, yoksa alt pozisyon. İki taraf aynı havuzdan tekrarsız çekilir."""
    used = set()
    dealt = {}
    for side in SIDES:
        slots = []
        for pos in slot_positions:
            free = [p for p in pool if p["id"] not in used]
            candidates = [p for p in free if p["pos"] == pos]
            if not candidates:
                candidates = [p for p in free if pos in (p.get("alt") or [])]
            if not candidates:
                _fail(f'Havuz yetersiz: {side} tarafının "{pos}" slotu için uygun oyuncu kalmadı')
            player = rng.choice(candidates)
            used.add(player["id"])
            slots.append({"pos": pos, "player": player})
        dealt[side] = slots
    return dealt


def create_match(players, categories, formation, protect_count=3, steals_per_side=3, seed=1):
    if not isinstance(players, list) or len(players) == 0:
        _fail("Oyuncu listesi boş")
    if not isinstance(categories, list) or len(categories) == 0:
        _fail("En az bir kategori seçilmeli")
    for category in categories:
        if (
            not isinstance(category, dict)
            or category.get("type") not in CATEGORY_TYPES
            or not isinstance(category.get("value"), str)
        ):
            _fail(f"Geçersiz kategori: {category!r} (type club|league|nation, value metin olmalı)")
    if not isinstance(formation, dict) or not isinstance(formation.get("slots"), list) or not formation["slots"]:
        _fail("Geçersiz formasyon: slots dolu bir dizi olmalı")
    if any(not isinstance(slot, str) or slot == "" for slot in formation["slots"]):
        _fail("Geçersiz formasyon: her slot bir pozisyon metni olmalı")
    slot_count = len(formation["slots"])
    if not _is_int(protect_count) or protect_count < 0 or protect_count > slot_count:
        _fail(f"Geçersiz protect_count: {protect_count} (0..{slot_count} tam sayı olmalı)")
    if not _is_int(steals_per_side) or steals_per_side < 0:
        _fail(f"Geçersiz steals_per_side: {steals_per_side} (0 veya büyük tam sayı olmalı)")

    seen = set()
    pool = []
    for player in players:
        if player["id"] in seen:
            continue
        if any(_matches_category(player, c) for c in categories):
            seen.add(player["id"])
            pool.append(player)
    if not pool:
        _fail("Seçilen kategorilerde oyuncu yok")

    rng = random.Random(seed)
    dealt = _deal_sides(pool, formation["slots"], rng)

    state = {
        "phase": "protect",
        "sides": {
            "A": {"slots": dealt["A"], "protected_ids": []},
            "B": {"slots": dealt["B"], "protected_ids": []},
        },
        "turn": "A",
        "steals_left": {"A": steals_per_side, "B": steals_per_side},
        "protect_count": protect_count,
        # Sözleşmede log yok; her iki tarafın koruma yapıp yapmadığını burada tutarız.
        "protected": {"A": False, "B": False},
    }
    return copy.deepcopy(state)


def protect(state, side, player_ids):
    _check_state(state)
    _check_side(side)
    if state["phase"] != "protect":
        _fail(f"Koruma aşamasında değil (faz: {state['phase']})")
    if state["protected"][side]:
        _fail(f"{side} tarafı zaten koruma yaptı")
    if not isinstance(player_ids, (list, tuple)):
        _fail("player_ids bir dizi olmalı")
    player_ids = list(player_ids)
    if len(player_ids) != state["protect_count"]:
        _fail(f"Tam {state['protect_count']} oyuncu korunmalı (verilen: {len(player_ids)})")
    if len(set(player_ids)) != len(player_ids):
        _fail("Aynı oyuncu birden fazla kez korunamaz")
    roster = {slot["player"]["id"] for slot in state["sides"][side]["slots"]}
    for pid in player_ids:
        if pid not in roster:
            _fail(f"{pid} {side} tarafının kadrosunda değil")

    new = copy.deepcopy(state)
    new["sides"][side]["protected_ids"] = player_ids
    new["protected"][side] = True
    if all(new["protected"][s] for s in SIDES):
        new["turn"] = "A"
        steals_total = new["steals_left"]["A"] + new["steals_left"]["B"]
        new["phase"] = "done" if steals_total == 0 else "steal"
    return new


def steal(state, side, target_id, give_id):
    _check_state(state)
    _check_side(side)
    if state["phase"] != "steal":
        _fail(f"Takas aşamasında değil (faz: {state['phase']})")
    if state["turn"] != side:
        _fail(f"Sıra {state['turn']} tarafında, {side} takas yapamaz")
    if state["steals_left"][side] <= 0:
        _fail(f"{side} tarafının takas hakkı kalmadı")

    foe = _other(side)
    me = state["sides"][side]
    rival = state["sides"][foe]

    target_index = next(
        (i for i, slot in enumerate(rival["slots"]) if slot["player"]["id"] == target_id), None
    )
    if target_index is None:
        _fail(f"{target_id} rakip kadrosunda değil")
    if target_id in rival["protected_ids"]:
        _fail(f"{target_id} korumalı, alınamaz")

    give_index = next(
        (i for i, slot in enumerate(me["slots"]) if slot["player"]["id"] == give_id), None
    )
    if give_index is None:
        _fail(f"{give_id} kendi kadrosunda değil")
    if give_id in me["protected_ids"]:
        _fail(f"{give_id} korumalı, verilemez")

    new = copy.deepcopy(state)
    target_player = new["sides"][foe]["slots"][target_index]["player"]
    give_player = new["sides"][side]["slots"][give_index]["player"]
    # Oyuncular birbirinin slotuna geçer; slot pozisyon etiketi yerinde kalır.
    new["sides"][side]["slots"][give_index]["player"] = target_player
    new["sides"][foe]["slots"][target_index]["player"] = give_player
    new["sides"][side]["protected_ids"] = list(me["protected_ids"]) + [target_id]

    new["steals_left"][side] -= 1
    new["turn"] = foe
    if new["steals_left"]["A"] == 0 and new["steals_left"]["B"] == 0:
        new["phase"] = "done"
    return new


def slot_score(slot_pos, player):
    if player["pos"] == slot_pos or slot_pos in (player.get("alt") or []):
        return player["rating"]
    return max(0, player["rating"] - ALT_PENALTY)


def team_rating(state, side):
    _check_state(state)
    _check_side(side)
    slots = state["sides"][side]["slots"]
    total = sum(slot_score(slot["pos"], slot["player"]) for slot in slots)
    return round(total / len(slots))


def result(state):
    _check_state(state)
    if state["phase"] != "done":
        _fail(f"Sonuç için maç bitmiş olmalı (faz: {state['phase']})")
    a = team_rating(state, "A")
    b = team_rating(state, "B")
    winner = "A" if a > b else "B" if b > a else "draw"
    return {"A": a, "B": b, "winner": winner}

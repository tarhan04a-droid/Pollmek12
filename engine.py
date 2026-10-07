"""Rastgele Seçimli Maç motoru (Python). Saf fonksiyonlar, yalnızca standart kütüphane.

Sözleşme: docs/CONTRACT.md > "Güncelleme 2" > Motor. Her oyuncu kendi kategorilerini ve
formasyonunu seçer; iki taraf farklı havuzlardan dağıtılır.
State düz dict; hiçbir fonksiyon girdiyi değiştirmez (copy.deepcopy). Hata = ValueError.
"""

import copy
import random

SIDES = ("A", "B")
CATEGORY_TYPES = ("club", "league", "nation")
MIN_CATEGORIES = 1
MAX_CATEGORIES = 4
FORMATION_SLOTS = 11
ALT_PENALTY = 10
MAX_DEAL_ATTEMPTS = 50


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


def _check_setup(side, setup):
    if not isinstance(setup, dict):
        _fail(f"{side} tarafı için setup eksik (categories ve formation gerekli)")

    categories = setup.get("categories")
    if not isinstance(categories, list):
        _fail(f"{side} tarafı: categories bir dizi olmalı")
    if not (MIN_CATEGORIES <= len(categories) <= MAX_CATEGORIES):
        _fail(
            f"{side} tarafı: {MIN_CATEGORIES}-{MAX_CATEGORIES} kategori seçilmeli "
            f"(verilen: {len(categories)})"
        )
    for category in categories:
        if (
            not isinstance(category, dict)
            or category.get("type") not in CATEGORY_TYPES
            or not isinstance(category.get("value"), str)
        ):
            _fail(
                f"{side} tarafı: geçersiz kategori {category!r} "
                "(type club|league|nation, value metin olmalı)"
            )

    formation = setup.get("formation")
    if not isinstance(formation, dict) or not isinstance(formation.get("id"), str):
        _fail(f"{side} tarafı: formation {{id, slots}} sözlüğü olmalı")
    slots = formation.get("slots")
    if not isinstance(slots, list) or len(slots) != FORMATION_SLOTS:
        _fail(f"{side} tarafı: formasyonda tam {FORMATION_SLOTS} slot olmalı")
    if any(not isinstance(slot, str) or slot == "" for slot in slots):
        _fail(f"{side} tarafı: her slot bir pozisyon metni olmalı")


def _build_pool(players, categories):
    seen = set()
    pool = []
    for player in players:
        if player["id"] in seen:
            continue
        if any(_matches_category(player, c) for c in categories):
            seen.add(player["id"])
            pool.append(player)
    return pool


def _slot_order(slot_lists):
    """Dağıtım sırası: A slot1, B slot1, A slot2, B slot2, ..."""
    order = []
    longest = max(len(slot_lists[side]) for side in SIDES)
    for i in range(longest):
        for side in SIDES:
            if i < len(slot_lists[side]):
                order.append((side, i))
    return order


def _try_deal(pools, slot_lists, order, rng):
    """Bir deneme. Başarısızsa (False, taraf, pozisyon) döner."""
    shuffled = {side: rng.sample(pools[side], len(pools[side])) for side in SIDES}
    used = set()
    dealt = {side: [] for side in SIDES}
    for side, index in order:
        pos = slot_lists[side][index]
        free = [p for p in shuffled[side] if p["id"] not in used]
        pick = next((p for p in free if p["pos"] == pos), None)
        if pick is None:
            pick = next((p for p in free if pos in (p.get("alt") or [])), None)
        if pick is None:
            return False, side, pos, None
        used.add(pick["id"])
        dealt[side].append({"pos": pos, "player": copy.deepcopy(pick)})
    return True, None, None, dealt


def _deal_sides(pools, slot_lists, seed):
    """İki tarafı çakışmasız dağıtır. Tıkanırsa seed'den türetilen yeni karıştırmayla
    en fazla MAX_DEAL_ATTEMPTS kez dener; hâlâ olmazsa ValueError."""
    order = _slot_order(slot_lists)
    failure = None
    for attempt in range(MAX_DEAL_ATTEMPTS):
        rng = random.Random(seed) if attempt == 0 else random.Random(f"{seed}:{attempt}")
        ok, side, pos, dealt = _try_deal(pools, slot_lists, order, rng)
        if ok:
            return dealt
        failure = (side, pos)
    side, pos = failure
    _fail(f'Havuz yetersiz: {side} tarafının "{pos}" slotu için uygun oyuncu kalmadı')


def create_match(players, setups, protect_count=3, steals_per_side=3, seed=1):
    if not isinstance(players, list) or len(players) == 0:
        _fail("Oyuncu listesi boş")
    if not isinstance(setups, dict) or set(setups.keys()) != set(SIDES):
        _fail('setups {"A": {...}, "B": {...}} biçiminde olmalı')
    for side in SIDES:
        _check_setup(side, setups[side])

    slot_lists = {side: setups[side]["formation"]["slots"] for side in SIDES}
    slot_count = min(len(slot_lists[side]) for side in SIDES)
    if not _is_int(protect_count) or protect_count < 0 or protect_count > slot_count:
        _fail(f"Geçersiz protect_count: {protect_count} (0..{slot_count} tam sayı olmalı)")
    if not _is_int(steals_per_side) or steals_per_side < 0:
        _fail(f"Geçersiz steals_per_side: {steals_per_side} (0 veya büyük tam sayı olmalı)")

    pools = {}
    for side in SIDES:
        pools[side] = _build_pool(players, setups[side]["categories"])
        if not pools[side]:
            _fail(f"{side} tarafı: seçilen kategorilerde oyuncu yok")

    dealt = _deal_sides(pools, slot_lists, seed)

    state = {
        "phase": "protect",
        "sides": {
            side: {"slots": dealt[side], "protected_ids": []} for side in SIDES
        },
        "turn": "A",
        "steals_left": {"A": steals_per_side, "B": steals_per_side},
        "protect_count": protect_count,
        # Sözleşmede log yok; her iki tarafın koruma yapıp yapmadığını burada tutarız.
        "protected": {"A": False, "B": False},
        "setups": {
            side: {
                "categories": [dict(c) for c in setups[side]["categories"]],
                "formation_id": setups[side]["formation"]["id"],
            }
            for side in SIDES
        },
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

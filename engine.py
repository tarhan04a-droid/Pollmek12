"""Rastgele Seçimli Maç motoru (Python). Saf fonksiyonlar, yalnızca standart kütüphane.

Sözleşme: docs/CONTRACT.md > "Güncelleme 4" > Motor (8 yedek oyuncu).
Her oyuncu kendi kategorilerini ve formasyonunu seçer; iki taraf farklı havuzlardan dağıtılır.
Her taraf ilk 11 + bench_size yedek alır. Takas ilk 11 ve yedekleri kapsar.
Fazlar: "steal" (sıra A, B, A, B...; her takastan sonra koruma adımı, step: "steal" -> "protect"),
"arrange" (son takastan sonra iki taraf düzenini yapıp onaylar), "done" (sonuç).
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


def _deal_order(slot_lists, bench_size):
    """Dağıtım sırası: önce ilk 11 (A slot1, B slot1, A slot2, ...), sonra yedekler
    (A, B, A, B, ...). Yedek girdisi index None ile işaretlenir."""
    order = []
    longest = max(len(slot_lists[side]) for side in SIDES)
    for i in range(longest):
        for side in SIDES:
            if i < len(slot_lists[side]):
                order.append((side, i))
    for _ in range(bench_size):
        for side in SIDES:
            order.append((side, None))
    return order


def _try_deal(pools, slot_lists, order, rng):
    """Bir deneme. Başarısızsa (False, taraf, etiket, None) döner; yedekte etiket None."""
    shuffled = {side: rng.sample(pools[side], len(pools[side])) for side in SIDES}
    used = set()
    dealt = {side: {"slots": [], "bench": []} for side in SIDES}
    for side, index in order:
        free = [p for p in shuffled[side] if p["id"] not in used]
        if index is None:
            if not free:
                return False, side, None, None
            pick = free[0]
            used.add(pick["id"])
            dealt[side]["bench"].append(copy.deepcopy(pick))
            continue
        pos = slot_lists[side][index]
        pick = next((p for p in free if p["pos"] == pos), None)
        if pick is None:
            pick = next((p for p in free if pos in (p.get("alt") or [])), None)
        if pick is None:
            return False, side, pos, None
        used.add(pick["id"])
        dealt[side]["slots"].append({"pos": pos, "player": copy.deepcopy(pick)})
    return True, None, None, dealt


def _deal_sides(pools, slot_lists, bench_size, seed):
    """İki tarafı çakışmasız dağıtır. Tıkanırsa seed'den türetilen yeni karıştırmayla
    en fazla MAX_DEAL_ATTEMPTS kez dener; hâlâ olmazsa ValueError."""
    order = _deal_order(slot_lists, bench_size)
    failure = None
    for attempt in range(MAX_DEAL_ATTEMPTS):
        rng = random.Random(seed) if attempt == 0 else random.Random(f"{seed}:{attempt}")
        ok, side, label, dealt = _try_deal(pools, slot_lists, order, rng)
        if ok:
            return dealt
        failure = (side, label)
    side, label = failure
    if label is None:
        _fail(f"Havuz yetersiz: {side} tarafı için yedek oyuncu kalmadı")
    _fail(f'Havuz yetersiz: {side} tarafının "{label}" slotu için uygun oyuncu kalmadı')


def _roster_ids(side_state):
    return [slot["player"]["id"] for slot in side_state["slots"]] + [
        p["id"] for p in side_state["bench"]
    ]


def _locate(side_state, player_id):
    """Oyuncunun yerini ("slots", indeks) veya ("bench", indeks) olarak döner; yoksa None."""
    for i, slot in enumerate(side_state["slots"]):
        if slot["player"]["id"] == player_id:
            return ("slots", i)
    for i, player in enumerate(side_state["bench"]):
        if player["id"] == player_id:
            return ("bench", i)
    return None


def _get_at(side_state, loc):
    kind, index = loc
    if kind == "bench":
        return side_state["bench"][index]
    return side_state["slots"][index]["player"]


def _put_at(side_state, loc, player):
    kind, index = loc
    if kind == "bench":
        side_state["bench"][index] = player
    else:
        side_state["slots"][index]["player"] = player


def create_match(players, setups, protect_count=3, steals_per_side=3, bench_size=8, seed=1):
    if not isinstance(players, list) or len(players) == 0:
        _fail("Oyuncu listesi boş")
    if not isinstance(setups, dict) or set(setups.keys()) != set(SIDES):
        _fail('setups {"A": {...}, "B": {...}} biçiminde olmalı')
    for side in SIDES:
        _check_setup(side, setups[side])

    slot_lists = {side: setups[side]["formation"]["slots"] for side in SIDES}
    slot_count = min(len(slot_lists[side]) for side in SIDES)
    if not _is_int(bench_size) or bench_size < 0:
        _fail(f"Geçersiz bench_size: {bench_size} (0 veya büyük tam sayı olmalı)")
    roster_size = slot_count + bench_size
    if not _is_int(protect_count) or protect_count < 0 or protect_count > roster_size:
        _fail(f"Geçersiz protect_count: {protect_count} (0..{roster_size} tam sayı olmalı)")
    if not _is_int(steals_per_side) or steals_per_side < 0:
        _fail(f"Geçersiz steals_per_side: {steals_per_side} (0 veya büyük tam sayı olmalı)")

    pools = {}
    for side in SIDES:
        pools[side] = _build_pool(players, setups[side]["categories"])
        if not pools[side]:
            _fail(f"{side} tarafı: seçilen kategorilerde oyuncu yok")
        if len(pools[side]) < roster_size:
            _fail(
                f"{side} tarafı: havuz yetersiz (ilk 11 + yedek için {roster_size} oyuncu "
                f"gerekli, bulunan {len(pools[side])})"
            )

    dealt = _deal_sides(pools, slot_lists, bench_size, seed)

    state = {
        # Takas yoksa (steals_per_side == 0) da düzen onayı yapılır; sonra sonuç.
        "phase": "steal" if steals_per_side > 0 else "arrange",
        "step": "steal",
        "sides": {
            side: {
                "slots": dealt[side]["slots"],
                "bench": dealt[side]["bench"],
                "protected_ids": [],
            }
            for side in SIDES
        },
        "turn": "A",
        "steals_left": {"A": steals_per_side, "B": steals_per_side},
        "protect_count": protect_count,
        "arranged": {"A": False, "B": False},
        "setups": {
            side: {
                "categories": [dict(c) for c in setups[side]["categories"]],
                "formation_id": setups[side]["formation"]["id"],
            }
            for side in SIDES
        },
    }
    return copy.deepcopy(state)


def steal(state, side, target_id, give_id):
    _check_state(state)
    _check_side(side)
    if state["phase"] != "steal":
        _fail(f"Takas aşamasında değil (faz: {state['phase']})")
    if state["step"] != "steal":
        _fail("Şu an koruma adımı var; önce korumayı onayla")
    if state["turn"] != side:
        _fail(f"Sıra {state['turn']} tarafında, {side} takas yapamaz")
    if state["steals_left"][side] <= 0:
        _fail(f"{side} tarafının takas hakkı kalmadı")

    foe = _other(side)
    me = state["sides"][side]
    rival = state["sides"][foe]

    target_loc = _locate(rival, target_id)
    if target_loc is None:
        _fail(f"{target_id} rakip kadrosunda değil")
    if target_id in rival["protected_ids"]:
        _fail(f"{target_id} korumalı, alınamaz")

    give_loc = _locate(me, give_id)
    if give_loc is None:
        _fail(f"{give_id} kendi kadrosunda değil")
    if give_id in me["protected_ids"]:
        _fail(f"{give_id} korumalı, verilemez")

    new = copy.deepcopy(state)
    new_me = new["sides"][side]
    new_rival = new["sides"][foe]
    target_player = _get_at(new_rival, target_loc)
    give_player = _get_at(new_me, give_loc)
    # Yer değişimi: hedef verenin bulunduğu yere, verilen hedefin bulunduğu yere geçer.
    # Slot pozisyon etiketi yerinde kalır; yedekler sırasını korur.
    _put_at(new_me, give_loc, target_player)
    _put_at(new_rival, target_loc, give_player)
    # Otomatik koruma yok: alınan oyuncu korumalı değildir.

    new["steals_left"][side] -= 1
    if new["steals_left"]["A"] == 0 and new["steals_left"]["B"] == 0:
        # Son takas: koruma adımı atlanır, düzen onayına geçilir.
        new["phase"] = "arrange"
    else:
        # Sıra aynı tarafta kalır; takastan sonra koruma adımı gelir.
        new["step"] = "protect"
    return new


def protect(state, side, player_ids):
    _check_state(state)
    _check_side(side)
    if state["phase"] != "steal":
        _fail(f"Koruma aşamasında değil (faz: {state['phase']})")
    if state["step"] != "protect":
        _fail("Şu an takas adımı var; koruma yalnızca takastan sonra yapılır")
    if state["turn"] != side:
        _fail(f"Sıra {state['turn']} tarafında, {side} koruma yapamaz")
    if not isinstance(player_ids, (list, tuple)):
        _fail("player_ids bir dizi olmalı")
    player_ids = list(player_ids)
    if len(player_ids) > state["protect_count"]:
        _fail(f"En fazla {state['protect_count']} oyuncu korunabilir (verilen: {len(player_ids)})")
    if len(set(player_ids)) != len(player_ids):
        _fail("Aynı oyuncu birden fazla kez korunamaz")
    roster = set(_roster_ids(state["sides"][side]))
    for pid in player_ids:
        if pid not in roster:
            _fail(f"{pid} {side} tarafının kadrosunda değil")

    new = copy.deepcopy(state)
    # Bu liste önceki korumanın yerine geçer.
    new["sides"][side]["protected_ids"] = player_ids
    new["turn"] = _other(side)
    new["step"] = "steal"
    return new


def swap_bench(state, side, slot_index, bench_index):
    """İlk 11'deki slot_index oyuncusu ile bench_index yedeğini yer değiştirir.
    Mülkiyet değişmez, korumalılar da yer değiştirebilir."""
    _check_state(state)
    _check_side(side)
    phase = state["phase"]
    if phase == "steal":
        if state["turn"] != side:
            _fail(f"Sıra {state['turn']} tarafında, {side} kadro düzenleyemez")
    elif phase == "arrange":
        if state["arranged"][side]:
            _fail(f"{side} tarafı düzenini zaten onayladı")
    else:
        _fail(f"Kadro düzenlenemez (faz: {phase})")

    me = state["sides"][side]
    if not _is_int(slot_index) or not (0 <= slot_index < len(me["slots"])):
        _fail(f"Geçersiz slot_index: {slot_index} (0..{len(me['slots']) - 1})")
    if not _is_int(bench_index) or not (0 <= bench_index < len(me["bench"])):
        _fail(f"Geçersiz bench_index: {bench_index} (0..{len(me['bench']) - 1})")

    new = copy.deepcopy(state)
    ns = new["sides"][side]
    slot_player = ns["slots"][slot_index]["player"]
    bench_player = ns["bench"][bench_index]
    ns["slots"][slot_index]["player"] = bench_player
    ns["bench"][bench_index] = slot_player
    return new


def confirm_arrange(state, side):
    _check_state(state)
    _check_side(side)
    if state["phase"] != "arrange":
        _fail(f"Düzen onayı yalnızca düzen aşamasında yapılır (faz: {state['phase']})")
    if state["arranged"][side]:
        _fail(f"{side} tarafı düzenini zaten onayladı")

    new = copy.deepcopy(state)
    new["arranged"][side] = True
    if new["arranged"]["A"] and new["arranged"]["B"]:
        new["phase"] = "done"
    return new


def slot_score(slot_pos, player):
    if player["pos"] == slot_pos or slot_pos in (player.get("alt") or []):
        return player["rating"]
    return max(0, player["rating"] - ALT_PENALTY)


def team_rating(state, side):
    """Yalnızca ilk 11 puana katılır; yedekler hesaba girmez."""
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

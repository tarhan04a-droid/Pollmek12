"""Rastgele Seçimli Maç - Streamlit arayüzü (hot-seat).

Çalıştırma: streamlit run app.py
Oyun kuralları engine.py içinde; bu dosya yalnızca arayüzü yönetir.
Sözleşme: docs/CONTRACT.md > "Güncelleme 6 > Uygulama".
"""

import json
import random
from pathlib import Path

import streamlit as st

from engine import (
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

DATA_DIR = Path(__file__).resolve().parent / "data"
TYPE_LABELS = {"club": "Kulüp", "league": "Lig", "nation": "Ülke"}
PROTECT_COUNT = 3
STEALS_PER_SIDE = 3
BENCH_SIZE = 8
RESERVE_SIZE = 4
MAX_CATEGORIES = 4  # her oyuncu için toplam üst sınır
SIDE_ORDER = ("A", "B")
OTHER = {"A": "B", "B": "A"}
TAG_BENCH = "yedek"
TAG_RESERVE = "rezerv"
# Sıfırlamada silinecek widget anahtarı önekleri (yeni maçta eski seçimler kalmasın).
WIDGET_PREFIXES = ("A_", "B_", "target_", "give_", "protect_", "sw_")

st.set_page_config(page_title="Rastgele Seçimli Maç", layout="centered")


@st.cache_data
def load_data():
    def read(name):
        with open(DATA_DIR / name, encoding="utf-8") as f:
            return json.load(f)

    return read("players.json"), read("categories.json"), read("formations.json")


PLAYERS, CATEGORIES, FORMATIONS = load_data()
PLAYERS_BY_ID = {p["id"]: p for p in PLAYERS}
FORMATIONS_BY_ID = {f["id"]: f for f in FORMATIONS}


def label(p, protected=False, tag=None):
    """Oyuncu etiketi. tag: None (ilk 11), TAG_BENCH veya TAG_RESERVE."""
    text = f"{p['name']} · {p['pos']} · {p['rating']}"
    if tag:
        text += f" [{tag}]"
    if protected:
        text += " [korumalı]"
    return text


def roster(side):
    """Tarafın tüm oyuncuları: ilk 11 (tag None), yedekler (TAG_BENCH), rezervler (TAG_RESERVE)."""
    return (
        [(s["player"], None) for s in side["slots"]]
        + [(p, TAG_BENCH) for p in side["bench"]]
        + [(p, TAG_RESERVE) for p in side["reserves"]]
    )


def pool_size(chosen):
    """Seçilen kategorilerden herhangi birine uyan oyuncu sayısı (yalnızca gösterim için)."""
    fields = {"club", "league", "nation"}
    wanted = [(c["type"], c["value"]) for c in chosen if c["type"] in fields]
    return sum(1 for p in PLAYERS if any(p.get(t) == v for t, v in wanted))


def reset_match():
    for key in ("stage", "state", "seed", "setup", "new_id"):
        st.session_state.pop(key, None)
    # Widget durumları da sıfırlansın (kurulum, takas, koruma, yer değiştirme).
    for key in list(st.session_state.keys()):
        if key.startswith(WIDGET_PREFIXES):
            st.session_state.pop(key, None)


def render_squad(side_name, state, formation_id):
    side = state["sides"][side_name]
    st.subheader(f"Oyuncu {side_name} · {formation_id}")
    for slot in side["slots"]:
        p = slot["player"]
        st.write(f"**{slot['pos']}** — {p['name']} ({p['rating']}) · {p['club']}")
    st.markdown("**Yedekler**")
    for p in side["bench"]:
        st.write(label(p))
    st.markdown("**Rezervler**")
    for p in side["reserves"]:
        st.write(label(p))
    st.caption(
        f"Takım puanı: {team_rating(state, side_name)} "
        "(ilk 11 + yedekler ortalaması; rezervler puana dahil değil)"
    )


# ---------------------------------------------------------------- kurulum
def setup_state():
    if "setup" not in st.session_state:
        st.session_state.setup = {
            "step": "A",
            "sides": {
                s: {"chosen": [], "formation_id": FORMATIONS[0]["id"]} for s in SIDE_ORDER
            },
        }
    return st.session_state.setup


def start_match(setup):
    seed = random.randrange(1, 2**31)
    setups = {
        s: {
            "categories": setup["sides"][s]["chosen"],
            "formation": FORMATIONS_BY_ID[setup["sides"][s]["formation_id"]],
        }
        for s in SIDE_ORDER
    }
    try:
        st.session_state.state = create_match(
            PLAYERS,
            setups,
            protect_count=PROTECT_COUNT,
            steals_per_side=STEALS_PER_SIDE,
            bench_size=BENCH_SIZE,
            reserve_size=RESERVE_SIZE,
            seed=seed,
        )
    except ValueError as e:
        st.error(f"Maç oluşturulamadı: {e}. Kategorileri değiştirip tekrar deneyin.")
        return
    st.session_state.seed = seed
    st.session_state.stage = "squads"
    st.rerun()


def screen_setup_side(setup, side):
    """Tek oyuncunun kurulum ekranı; A ve B aynı bileşeni kullanır."""
    data = setup["sides"][side]
    st.title("Rastgele Seçimli Maç")
    st.subheader(f"Oyuncu {side}: kategorilerini ve formasyonunu seç")
    st.caption(
        f"En az 1, en fazla {MAX_CATEGORIES} kategori (ülke, kulüp, lig karışık olabilir). "
        "Diğer oyuncu ekrana bakmasın."
    )

    st.markdown("**1. Kategori seç**")
    ctype = st.selectbox(
        "Kategori türü",
        options=list(TYPE_LABELS),
        format_func=TYPE_LABELS.get,
        key=f"{side}_cat_type",
    )
    options = CATEGORIES.get(ctype, [])
    counts = {o["value"]: o["count"] for o in options}
    chosen = data["chosen"]
    current = [c["value"] for c in chosen if c["type"] == ctype]
    room = MAX_CATEGORIES - (len(chosen) - len(current))  # bu tür için kalan hak
    picked = st.multiselect(
        f"{TYPE_LABELS[ctype]} seç",
        options=[o["value"] for o in options],
        default=current,
        format_func=lambda v: f"{v} ({counts.get(v, 0)})",
        placeholder="Yazarak arayın",
        max_selections=max(room, 1),
        disabled=room <= 0,
        key=f"{side}_cat_pick_{ctype}",
    )
    # Bu türün seçimlerini oyuncunun genel listesine yaz (tür değişince kaybolmasın).
    chosen = [c for c in chosen if c["type"] != ctype] + [
        {"type": ctype, "value": v} for v in picked
    ]
    data["chosen"] = chosen

    if len(chosen) >= MAX_CATEGORIES:
        st.warning(
            f"Toplam {MAX_CATEGORIES} kategori sınırına ulaştınız. "
            "Yeni eklemek için önce bir kategoriyi kaldırın."
        )
    if chosen:
        st.write("Seçilenler: " + ", ".join(f"{c['value']} ({TYPE_LABELS[c['type']]})" for c in chosen))
        st.info(f"Havuz: {pool_size(chosen)} oyuncu")
    else:
        st.write("Henüz kategori seçilmedi.")

    st.markdown("**2. Formasyon**")
    formation_ids = [f["id"] for f in FORMATIONS]
    data["formation_id"] = st.selectbox(
        "Formasyon", options=formation_ids, index=0, key=f"{side}_formation"
    )

    if side == "A":
        if st.button("Oyuncu B'ye geç", type="primary", disabled=not chosen):
            setup["step"] = "B"
            st.rerun()
    else:
        if st.button("Maçı başlat", type="primary", disabled=not chosen):
            start_match(setup)


def screen_setup():
    setup = setup_state()
    screen_setup_side(setup, setup["step"])


# ---------------------------------------------------------------- kadrolar
def screen_squads():
    state = st.session_state.state
    setups = state["setups"]
    st.title("Kadrolar")
    col_a, col_b = st.columns(2)
    with col_a:
        render_squad("A", state, setups["A"]["formation_id"])
    with col_b:
        render_squad("B", state, setups["B"]["formation_id"])

    if st.button("Takas turlarını başlat", type="primary"):
        st.session_state.stage = "play"
        st.rerun()
    if st.button("Yeni maç"):
        reset_match()
        st.rerun()


# ---------------------------------------------------------------- kadro düzeni (yer değiştirme)
def render_arrange_controls(state, side):
    """Tarafın iki yer değiştirme aracı: ilk 11 <-> yedek (swap_bench) ve yedek <-> rezerv (swap_reserve)."""
    me = state["sides"][side]
    bench = me["bench"]
    reserves = me["reserves"]
    if not bench and not reserves:
        return
    prot = set(me["protected_ids"])
    st.markdown("**Kadro düzeni**")
    st.caption(
        "İlk 11 ile yedek, yedek ile rezerv yer değiştirilebilir. "
        "İlk 11 ile rezerv doğrudan yer değiştiremez. Pozisyon uyumsuzsa puandan 10 düşülür."
    )

    if bench:
        slot_idx = st.selectbox(
            "İlk 11'den oyuncu",
            options=list(range(len(me["slots"]))),
            format_func=lambda i: (
                f"{me['slots'][i]['pos']} — "
                f"{label(me['slots'][i]['player'], me['slots'][i]['player']['id'] in prot)}"
            ),
            key=f"sw_slot_{side}",
        )
        bench_idx = st.selectbox(
            "Yedekten oyuncu",
            options=list(range(len(bench))),
            format_func=lambda i: label(bench[i], bench[i]["id"] in prot, TAG_BENCH),
            key=f"sw_bench_{side}",
        )
        slot_pos = me["slots"][slot_idx]["pos"]
        cand = bench[bench_idx]
        if slot_score(slot_pos, cand) < cand["rating"]:
            st.warning(f"Uyumsuz: {cand['name']} {slot_pos} slotunda puandan 10 düşük sayılır.")
        if st.button("Yer değiştir", key=f"sw_btn_{side}"):
            try:
                st.session_state.state = swap_bench(state, side, slot_idx, bench_idx)
            except ValueError as e:
                st.error(str(e))
                return
            st.rerun()

    if bench and reserves:
        rbench_idx = st.selectbox(
            "Yedekten oyuncu",
            options=list(range(len(bench))),
            format_func=lambda i: label(bench[i], bench[i]["id"] in prot, TAG_BENCH),
            key=f"sw_rbench_{side}",
        )
        reserve_idx = st.selectbox(
            "Rezervden oyuncu",
            options=list(range(len(reserves))),
            format_func=lambda i: label(reserves[i], reserves[i]["id"] in prot, TAG_RESERVE),
            key=f"sw_res_{side}",
        )
        if st.button("Rezervle yer değiştir", key=f"sw_rbtn_{side}"):
            try:
                st.session_state.state = swap_reserve(state, side, rbench_idx, reserve_idx)
            except ValueError as e:
                st.error(str(e))
                return
            st.rerun()


# ---------------------------------------------------------------- takas (takas + koruma)
def screen_steal(state):
    """Sıra sahibinin ekranı: önce takas, takas yapılınca aynı ekranda koruma adımı."""
    turn = state["turn"]
    other = OTHER[turn]
    left = state["steals_left"][turn]
    st.title("Takas")
    st.subheader(f"Sıra: Oyuncu {turn}")
    st.write(f"Kalan takas hakkı: **{left}** (bu taraf) · **{state['steals_left'][other]}** (rakip)")
    st.warning("Ekranı sadece sırası olan oyuncu görsün.")
    render_arrange_controls(state, turn)
    st.divider()
    if state["step"] == "protect":
        screen_protect_step(state, turn)
    else:
        screen_steal_step(state, turn, other, left)


def screen_steal_step(state, turn, other, left):
    st.markdown("**Adım 1/2: Takas**")
    me = state["sides"][turn]
    rival = state["sides"][other]
    rival_prot = set(rival["protected_ids"])
    my_prot = set(me["protected_ids"])

    rival_roster = roster(rival)
    my_roster = roster(me)
    target_names = {p["id"]: label(p, p["id"] in rival_prot, tag) for p, tag in rival_roster}
    give_names = {p["id"]: label(p, p["id"] in my_prot, tag) for p, tag in my_roster}
    target_opts = [p["id"] for p, _ in rival_roster if p["id"] not in rival_prot]
    give_opts = [p["id"] for p, _ in my_roster if p["id"] not in my_prot]

    with st.expander("Rakip kadrosu (yedekler, rezervler ve korumalılar işaretli)"):
        for p, tag in rival_roster:
            st.write(label(p, p["id"] in rival_prot, tag))

    if not target_opts or not give_opts:
        st.error("Takas için uygun oyuncu kalmadı. Maç ilerlemiyor.")
        return

    target = st.selectbox(
        "Rakipten alınacak oyuncu",
        options=target_opts,
        format_func=target_names.get,
        key=f"target_{turn}_{left}",
    )
    give = st.selectbox(
        "Karşılığında verilecek oyuncu",
        options=give_opts,
        format_func=give_names.get,
        key=f"give_{turn}_{left}",
    )
    if st.button("Takası yap", type="primary"):
        try:
            st.session_state.state = steal(state, turn, target, give)
        except ValueError as e:
            st.error(str(e))
            return
        st.session_state.new_id = target  # koruma adımında "yeni" etiketi için
        st.rerun()


def screen_protect_step(state, turn):
    st.markdown("**Adım 2/2: Koruma**")
    st.caption(
        f"Kadronuzdan (ilk 11, yedekler ve rezervler) en fazla {PROTECT_COUNT} oyuncu koruyun; "
        "boş onay da serbest. Seçim öncekinin yerine geçer."
    )
    squad = roster(state["sides"][turn])
    current = set(state["sides"][turn]["protected_ids"])
    new_id = st.session_state.get("new_id")
    options = [p["id"] for p, _ in squad]
    names = {
        p["id"]: label(p, p["id"] in current, tag) + (" [yeni]" if p["id"] == new_id else "")
        for p, tag in squad
    }
    ids = st.multiselect(
        "Korunacak oyuncular",
        options=options,
        default=[pid for pid in state["sides"][turn]["protected_ids"] if pid in options],
        format_func=names.get,
        max_selections=PROTECT_COUNT,
        key=f"protect_{turn}_{state['steals_left'][turn]}",
    )
    if st.button("Korumayı onayla", type="primary"):
        try:
            st.session_state.state = protect(state, turn, ids)
        except ValueError as e:
            st.error(str(e))
            return
        st.session_state.pop("new_id", None)
        st.rerun()


# ---------------------------------------------------------------- kadro düzeni aşaması
def screen_arrange(state):
    """phase == "arrange": A, sonra B kendi düzenini yapıp onaylar."""
    side = next(s for s in SIDE_ORDER if not state["arranged"][s])
    st.title("Kadro düzeni")
    st.subheader(f"Sıra: Oyuncu {side}")
    if state["arranged"][OTHER[side]]:
        st.info(f"Oyuncu {OTHER[side]} düzenini onayladı.")
    st.warning(f"Ekranı sadece Oyuncu {side} görsün.")
    render_squad(side, state, state["setups"][side]["formation_id"])
    render_arrange_controls(state, side)
    if st.button("Düzeni onayla", type="primary"):
        try:
            st.session_state.state = confirm_arrange(state, side)
        except ValueError as e:
            st.error(str(e))
            return
        st.rerun()


# ---------------------------------------------------------------- sonuç
def screen_done(state):
    res = result(state)
    setups = state["setups"]
    st.title("Sonuç")
    col_a, col_b = st.columns(2)
    col_a.metric("Oyuncu A", res["A"])
    col_b.metric("Oyuncu B", res["B"])
    if res["winner"] == "draw":
        st.success("Berabere!")
    else:
        st.success(f"Oyuncu {res['winner']} kazandı!")
    first = state["sides"]["A"]
    st.caption(
        f"Takım puanı, ilk {len(first['slots'])} ve {len(first['bench'])} yedeğin ortalamasıdır "
        f"({len(first['slots']) + len(first['bench'])} oyuncu). "
        f"{len(first['reserves'])} rezerv puana dahil değildir."
    )
    with st.expander("Son kadrolar"):
        for side in SIDE_ORDER:
            st.markdown(
                f"**Oyuncu {side}** · {setups[side]['formation_id']} "
                f"(takım puanı {team_rating(state, side)})"
            )
            for slot in state["sides"][side]["slots"]:
                p = slot["player"]
                st.write(f"{slot['pos']} — {p['name']} ({p['rating']})")
            st.markdown("Yedekler (puana dahil):")
            for p in state["sides"][side]["bench"]:
                st.write(label(p))
            st.markdown("Rezervler (puana dahil değil):")
            for p in state["sides"][side]["reserves"]:
                st.write(label(p))
    if st.button("Yeni maç", type="primary"):
        reset_match()
        st.rerun()


def main():
    stage = st.session_state.get("stage", "setup")
    state = st.session_state.get("state")
    if stage == "setup" or state is None:
        screen_setup()
    elif stage == "squads":
        screen_squads()
    elif state["phase"] == "steal":
        screen_steal(state)
    elif state["phase"] == "arrange":
        screen_arrange(state)
    else:
        screen_done(state)


main()

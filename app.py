"""Rastgele Seçimli Maç - Streamlit arayüzü (hot-seat).

Çalıştırma: streamlit run app.py
Oyun kuralları engine.py içinde; bu dosya yalnızca arayüzü yönetir.
"""

import json
import random
from pathlib import Path

import streamlit as st

from engine import create_match, protect, result, steal, team_rating

DATA_DIR = Path(__file__).resolve().parent / "data"
TYPE_LABELS = {"club": "Kulüp", "league": "Lig", "nation": "Ülke"}
PROTECT_COUNT = 3
STEALS_PER_SIDE = 3
OTHER = {"A": "B", "B": "A"}

st.set_page_config(page_title="Rastgele Seçimli Maç", layout="centered")


@st.cache_data
def load_data():
    def read(name):
        with open(DATA_DIR / name, encoding="utf-8") as f:
            return json.load(f)

    return read("players.json"), read("categories.json"), read("formations.json")


PLAYERS, CATEGORIES, FORMATIONS = load_data()
PLAYERS_BY_ID = {p["id"]: p for p in PLAYERS}


def label(p, protected=False):
    text = f"{p['name']} · {p['pos']} · {p['rating']}"
    return text + " [korumalı]" if protected else text


def pool_size(chosen):
    """Seçilen kategorilerden herhangi birine uyan oyuncu sayısı (yalnızca gösterim için)."""
    fields = {"club", "league", "nation"}
    wanted = [(c["type"], c["value"]) for c in chosen if c["type"] in fields]
    return sum(1 for p in PLAYERS if any(p.get(t) == v for t, v in wanted))


def reset_match():
    for key in ("stage", "state", "seed"):
        st.session_state.pop(key, None)


def render_squad(side_name, side):
    st.subheader(f"Oyuncu {side_name}")
    for slot in side["slots"]:
        p = slot["player"]
        st.write(f"**{slot['pos']}** — {p['name']} ({p['rating']}) · {p['club']}")


# ---------------------------------------------------------------- kurulum
def screen_setup():
    st.title("Rastgele Seçimli Maç")
    st.caption("İki oyuncu aynı cihazda sırayla oynar.")

    if "chosen" not in st.session_state:
        st.session_state.chosen = []
    chosen = st.session_state.chosen

    st.subheader("1. Kategori seç")
    st.caption("Kategori türünü seçip değerleri arayarak ekleyin. Farklı türlerden de seçebilirsiniz.")
    ctype = st.selectbox(
        "Kategori türü",
        options=list(TYPE_LABELS),
        format_func=TYPE_LABELS.get,
        key="cat_type",
    )
    options = CATEGORIES.get(ctype, [])
    counts = {o["value"]: o["count"] for o in options}
    current = [c["value"] for c in chosen if c["type"] == ctype]
    picked = st.multiselect(
        f"{TYPE_LABELS[ctype]} seç",
        options=[o["value"] for o in options],
        default=current,
        format_func=lambda v: f"{v} ({counts.get(v, 0)})",
        placeholder="Yazarak arayın",
        key=f"cat_pick_{ctype}",
    )
    # Bu türün seçimlerini genel listeye yaz (başka türe geçince kaybolmasın).
    st.session_state.chosen = [c for c in chosen if c["type"] != ctype] + [
        {"type": ctype, "value": v} for v in picked
    ]
    chosen = st.session_state.chosen

    if chosen:
        st.write("Seçilenler: " + ", ".join(f"{c['value']} ({TYPE_LABELS[c['type']]})" for c in chosen))
        st.info(f"Havuz: {pool_size(chosen)} oyuncu")
    else:
        st.write("Henüz kategori seçilmedi.")

    st.subheader("2. Formasyon")
    formation_ids = [f["id"] for f in FORMATIONS]
    formation_id = st.selectbox("Formasyon", options=formation_ids, index=0, key="formation")
    formation = next(f for f in FORMATIONS if f["id"] == formation_id)

    if st.button("Maçı başlat", type="primary", disabled=not chosen):
        seed = random.randrange(1, 2**31)
        try:
            st.session_state.state = create_match(
                PLAYERS,
                chosen,
                formation,
                protect_count=PROTECT_COUNT,
                steals_per_side=STEALS_PER_SIDE,
                seed=seed,
            )
        except ValueError as e:
            st.error(f"Maç oluşturulamadı: {e}. Daha fazla kategori seçin.")
            return
        st.session_state.seed = seed
        st.session_state.stage = "squads"
        st.rerun()


# ---------------------------------------------------------------- kadrolar
def screen_squads():
    state = st.session_state.state
    st.title("Kadrolar")
    col_a, col_b = st.columns(2)
    with col_a:
        render_squad("A", state["sides"]["A"])
    with col_b:
        render_squad("B", state["sides"]["B"])

    if st.button("Koruma aşamasına geç", type="primary"):
        st.session_state.stage = "play"
        st.rerun()
    if st.button("Yeni maç"):
        reset_match()
        st.rerun()


# ---------------------------------------------------------------- koruma
def screen_protect(state):
    # İlk koruma yapan A; A'nın korumaları kaydedilince sıra B'ye geçer.
    side = "B" if state["sides"]["A"]["protected_ids"] else "A"
    st.title("Koruma")
    st.subheader(f"Sıra: Oyuncu {side}")
    st.warning(
        f"Oyuncu {side} dışındakiler ekrana bakmasın. Kadrosundan tam {PROTECT_COUNT} oyuncu koruyun."
    )
    squad = state["sides"][side]["slots"]
    options = [slot["player"]["id"] for slot in squad]
    names = {slot["player"]["id"]: label(slot["player"]) for slot in squad}
    ids = st.multiselect(
        "Korunacak oyuncular",
        options=options,
        format_func=names.get,
        max_selections=PROTECT_COUNT,
        key=f"protect_{side}",
    )
    if st.button(
        "Korumayı onayla",
        type="primary",
        disabled=len(ids) != PROTECT_COUNT,
    ):
        try:
            st.session_state.state = protect(state, side, ids)
        except ValueError as e:
            st.error(str(e))
            return
        st.rerun()


# ---------------------------------------------------------------- takas
def screen_steal(state):
    turn = state["turn"]
    other = OTHER[turn]
    left = state["steals_left"][turn]
    st.title("Takas")
    st.subheader(f"Sıra: Oyuncu {turn}")
    st.write(f"Kalan takas hakkı: **{left}** (bu taraf) · **{state['steals_left'][other]}** (rakip)")
    st.warning("Ekranı sadece sırası olan oyuncu görsün.")

    me = state["sides"][turn]
    rival = state["sides"][other]
    rival_prot = set(rival["protected_ids"])
    my_prot = set(me["protected_ids"])

    target_slots = [s["player"] for s in rival["slots"]]
    give_slots = [s["player"] for s in me["slots"]]
    target_names = {p["id"]: label(p, p["id"] in rival_prot) for p in target_slots}
    give_names = {p["id"]: label(p, p["id"] in my_prot) for p in give_slots}
    target_opts = [p["id"] for p in target_slots if p["id"] not in rival_prot]
    give_opts = [p["id"] for p in give_slots if p["id"] not in my_prot]

    with st.expander("Rakip kadrosu (korumalılar işaretli)"):
        for p in target_slots:
            st.write(label(p, p["id"] in rival_prot))

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
        st.rerun()


# ---------------------------------------------------------------- sonuç
def screen_done(state):
    res = result(state)
    st.title("Sonuç")
    col_a, col_b = st.columns(2)
    col_a.metric("Oyuncu A", res["A"])
    col_b.metric("Oyuncu B", res["B"])
    if res["winner"] == "draw":
        st.success("Berabere!")
    else:
        st.success(f"Oyuncu {res['winner']} kazandı!")
    with st.expander("Son kadrolar"):
        for side in ("A", "B"):
            st.markdown(f"**Oyuncu {side}** (takım puanı {team_rating(state, side)})")
            for slot in state["sides"][side]["slots"]:
                p = slot["player"]
                st.write(f"{slot['pos']} — {p['name']} ({p['rating']})")
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
    elif state["phase"] == "protect":
        screen_protect(state)
    elif state["phase"] == "steal":
        screen_steal(state)
    else:
        screen_done(state)


main()

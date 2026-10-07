#!/usr/bin/env python3
"""Ham EA FC 27 CSV'sinden oyun verisini uretir (docs/CONTRACT.md semasi).

Girdi : data/raw/players.csv
Cikti : data/players.json, data/categories.json, data/formations.json

Yalnizca standart kutuphane kullanir. Calistirma:
    python3 data/build_data.py
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_CSV = os.path.join(HERE, "raw", "players.csv")
OUT_PLAYERS = os.path.join(HERE, "players.json")
OUT_CATEGORIES = os.path.join(HERE, "categories.json")
OUT_FORMATIONS = os.path.join(HERE, "formations.json")

GENDER = "Men's Football"
MIN_RATING = 65          # overall_rating alt siniri (dahil)
MIN_CATEGORY_COUNT = 15  # kategori listesine girmek icin en az oyuncu sayisi
MIN_SLOT_POOL = 30       # her formasyon slotu icin en az oyuncu (pos veya alt)

# Formasyonlar: EA pozisyon etiketleri, tam 11 slot.
FORMATIONS = [
    {"id": "4-3-3",   "slots": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"]},
    {"id": "4-4-2",   "slots": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"]},
    {"id": "3-5-2",   "slots": ["GK", "CB", "CB", "CB", "LM", "CDM", "CAM", "CM", "RM", "ST", "ST"]},
    {"id": "4-2-3-1", "slots": ["GK", "LB", "CB", "CB", "RB", "CDM", "CDM", "LW", "CAM", "RW", "ST"]},
]


def display_name(row):
    common = row["common_name"].strip()
    if common:
        return common
    return " ".join(p for p in (row["first_name"].strip(), row["last_name"].strip()) if p)


def build_players(rows):
    players = []
    seen = set()
    for row in rows:
        if row["gender"] != GENDER:
            continue
        if int(row["overall_rating"]) < MIN_RATING:
            continue
        pid = row["player_id"].strip()
        if pid in seen:
            raise SystemExit(f"Yinelenen player_id: {pid}")
        seen.add(pid)
        players.append({
            "id": pid,
            "name": display_name(row),
            "pos": row["position"].strip(),
            "alt": row["alternate_positions"].split(),
            "rating": int(row["overall_rating"]),
            "club": row["club"].strip(),
            "league": row["league"].strip(),
            "nation": row["nationality"].strip(),
            "pac": int(row["pace"]),
            "sho": int(row["shooting"]),
            "pas": int(row["passing"]),
            "dri": int(row["dribbling"]),
            "def": int(row["defending"]),
            "phy": int(row["physicality"]),
        })
    players.sort(key=lambda p: int(p["id"]))
    return players


def build_categories(players):
    out = {}
    for key, field in (("club", "club"), ("league", "league"), ("nation", "nation")):
        counts = {}
        for p in players:
            value = p[field]
            if value:  # bos degerler kategori degildir
                counts[value] = counts.get(value, 0) + 1
        entries = [{"value": v, "count": c} for v, c in counts.items() if c >= MIN_CATEGORY_COUNT]
        entries.sort(key=lambda e: (-e["count"], e["value"]))
        out[key] = entries
    return out


def pool_for_label(players, label):
    return sum(1 for p in players if p["pos"] == label or label in p["alt"])


def check_formations(players):
    for f in FORMATIONS:
        if len(f["slots"]) != 11:
            raise SystemExit(f"{f['id']}: 11 slot olmali, {len(f['slots'])} var")
        for label in sorted(set(f["slots"])):
            n = pool_for_label(players, label)
            if n < MIN_SLOT_POOL:
                raise SystemExit(f"{f['id']} slot {label}: havuz {n} < {MIN_SLOT_POOL}")


def dump_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")


def main():
    with open(RAW_CSV, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    players = build_players(rows)
    categories = build_categories(players)
    check_formations(players)

    dump_json(OUT_PLAYERS, players)
    dump_json(OUT_CATEGORIES, categories)
    dump_json(OUT_FORMATIONS, FORMATIONS)

    print(f"players: {len(players)}")
    for key in ("club", "league", "nation"):
        print(f"categories.{key}: {len(categories[key])}")
    for f in FORMATIONS:
        print(f"formation {f['id']}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Sözleşme (tüm işçiler uyar; değişiklik yalnızca şef/kullanıcı onayıyla)

Proje: PES "Rastgele Seçimli Maç" (Random Selection Match) tarzı oyun. Saf HTML + ES modülleri, build yok, tarayıcıda çalışır. Testler `node --test`. İki kişi aynı cihazda sırayla oynar (hot-seat).

## Oyun akışı
1. Kurulum: iki oyuncu kategori seçer (kulüp / lig / ülke, birden fazla) + formasyon.
2. Dağıtım: havuz = seçilen kategorilerden herhangi birine uyan oyuncular. Her iki tarafa, formasyonun her slotu için havuzdan rastgele ve tekrarsız bir oyuncu dağıtılır (slot pozisyonu = oyuncunun `pos`'u; yetmezse `alt` pozisyonlarından).
3. Koruma: her taraf kendi kadrosundan tam `protectCount` (varsayılan 3) oyuncuyu korumaya alır.
4. Takas turları: taraflar sırayla (A, B, A, B…) toplam `stealsPerSide` (varsayılan 3) kez rakibin korumasız bir oyuncusunu alır, karşılığında kendi oyuncularından birini verir. Alınan oyuncu kalan turlarda korumalı olur (geri çalınamaz).
5. Bitiş: iki takımın puanı karşılaştırılır.

## Veri (`data/players.json`, `data/categories.json`, `data/formations.json`)
Ham kaynak: `data/raw/players.csv` (EA FC 27, açıklama `data/raw/README.md`). Sadece `gender == "Men's Football"` ve `overall_rating >= 65` oyuncular kullanılır.
players.json: dizi. Eleman:
`{ "id": "231747", "name": "Kylian Mbappé", "pos": "ST", "alt": ["LW"], "rating": 91, "club": "Real Madrid", "league": "LALIGA EA SPORTS", "nation": "France", "pac": 96, "sho": 91, "pas": 80, "dri": 92, "def": 36, "phy": 78 }`
- `id` = `player_id` (string). `name` = `common_name` doluysa o, değilse `first_name last_name`. `alt` = `alternate_positions` boşlukla ayrılmış -> dizi.
- Pozisyon etiketleri EA'nın etiketleri (GK, CB, LB, RB, LWB, RWB, CDM, CM, CAM, LM, RM, LW, RW, ST, CF…). Formasyon slotları bu etiketleri kullanır.
categories.json: `{ "club": [{"value":"Real Madrid","count":30}], "league": [...], "nation": [...] }` (count = players.json içindeki oyuncu sayısı; en az 15 oyunculu olanlar listelenir).
formations.json: dizi `{ "id": "4-3-3", "slots": ["GK","LB","CB","CB","RB","CM","CM","CM","LW","ST","RW"] }` (tam 11 slot; 4-3-3, 4-4-2, 3-5-2, 4-2-3-1 ve slotlar EA etiketlerine göre).

## Motor (`src/engine.js`, ES modül, DOM yok, saf fonksiyonlar, state değiştirilmez, `Error` fırlatır)
- `createMatch({ players, categories, formation, protectCount = 3, stealsPerSide = 3, seed = 1 })`
  - `categories`: `[{ type: "club"|"league"|"nation", value: string }]`. Havuz yetersizse (her iki taraf için de slotları dolduramıyorsa) `Error`.
  - state: `{ phase: "protect"|"steal"|"done", sides: { A: Side, B: Side }, turn: "A"|"B", stealsLeft: { A: n, B: n }, protectCount, log: [] }`
  - `Side = { slots: [{ pos, player: Player }], protectedIds: string[] }`
- `protect(state, side, playerIds)` -> yeni state. Tam `protectCount` id, hepsi o tarafın kadrosunda. İki taraf da koruyunca `phase = "steal"`, `turn = "A"`.
- `steal(state, side, targetId, giveId)` -> yeni state. Sadece `phase=="steal"` ve `turn==side`. `targetId` rakipte olmalı ve korumasız; `giveId` kendi kadroda. İki oyuncu birbirinin slotuna geçer; `targetId` thief'in `protectedIds`'ine eklenir. Sıra değişir, `stealsLeft` azalır; ikisi de 0 olunca `phase="done"`.
- `slotScore(slotPos, player)` -> `player.pos === slotPos` ise `rating`; `alt` içinde ise `rating`; değilse `rating - 10` (alt sıfırın altına inmez).
- `teamRating(state, side)` -> 11 slotun `slotScore` ortalaması, tam sayıya yuvarlanmış.
- `result(state)` -> `{ A, B, winner: "A"|"B"|"draw" }` (yalnızca `phase=="done"`).
- Aynı seed + aynı hamleler -> aynı sonuç (deterministik; küçük bir PRNG).

## UI (`index.html`, `src/ui.js`, `styles.css`)
Motoru `import { createMatch, protect, steal, teamRating, result } from './engine.js'` ile kullanır; veriyi `fetch('data/…json')` ile yükler. Ekranlar: kurulum (kategori arama/seçme) -> kadro gösterimi -> koruma (sıra A sonra B) -> takas turları -> sonuç. Motor kodunu kopyalamaz.

## Dosya sahipliği
w1: `data/**` (ham CSV dahil), `docs/data-notes.md` | w2: `src/engine.js` | w3: `index.html`, `src/ui.js`, `styles.css` | w4: `tests/**`

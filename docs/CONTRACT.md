# Sözleşme (tüm işçiler uyar; değişiklik yalnızca şef/kullanıcı onayıyla)

Proje: PES tarzı draft oyunu. Saf HTML + ES modülleri, build yok, tarayıcıda çalışır. Testler `node --test`.

## Oyun akışı
Formasyon seç -> her turda rastgele `packSize` (5) oyuncu paketi gösterilir -> kullanıcı pozisyonuna uyan boş slot için 1 oyuncu seçer -> 11 slot dolunca biter -> takım puanı hesaplanır.

## Veri (`data/players.json`, `data/formations.json`)
players.json: dizi. Her eleman:
`{ "id": "p001", "name": "Ad Soyad", "pos": "GK|CB|LB|RB|CM|DM|AM|LW|RW|ST", "rating": 60-95, "club": "…", "nation": "…" }`
formations.json: dizi. Her eleman:
`{ "id": "4-3-3", "slots": ["GK","LB","CB","CB","RB","CM","CM","CM","LW","ST","RW"] }` (tam 11 slot)

## Motor (`src/engine.js`, ES modül, DOM yok, saf fonksiyonlar, state değiştirilmez)
- `createDraft({ players, formation, packSize = 5, seed = 1 })` -> state
- `state = { formation, slots: [{pos, player: null|Player}], pack: Player[], used: string[], seed, packSize }`
- `pick(state, playerId, slotIndex)` -> yeni state. Hata: oyuncu pakette yoksa, slot doluysa veya `pos` uyuşmuyorsa `Error` fırlatır. Başarılıysa yeni pak üretir (kullanılmış oyuncular çıkmaz).
- `isComplete(state)` -> boolean
- `teamRating(state)` -> doluların rating ortalaması, tam sayıya yuvarlanmış (boş slot varsa 0 sayılmaz, sadece doluların ortalaması; hiç yoksa 0)
- Aynı seed + aynı hamleler -> aynı sonuç (deterministik).

## UI (`index.html`, `src/ui.js`, `styles.css`)
Motoru `import { createDraft, pick, isComplete, teamRating } from './engine.js'` ile kullanır; verileri `fetch('data/…json')` ile yükler. Motor kodunu kopyalamaz.

## Dosya sahipliği
w1: `data/**`, `docs/data-notes.md` | w2: `src/engine.js` | w3: `index.html`, `src/ui.js`, `styles.css` | w4: `tests/**`

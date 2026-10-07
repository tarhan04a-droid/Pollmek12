# Sözleşme (tüm işçiler uyar; değişiklik yalnızca şef/kullanıcı onayıyla)

> NOT: JS sürümü (`src/`, `index.html`) silindi. Güncel kurallar dosyanın sonundaki Streamlit bölümleridir (en son: "Güncelleme 3"). İlk bölümler tarihsel kayıttır.

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
- `steal(state, side, targetId, giveId)` -> yeni state. Sadece `phase=="steal"` ve `turn==side`. `targetId` rakipte olmalı ve korumasız; `giveId` kendi kadroda ve kendi korumalı oyuncularından biri OLMAMALI (korumalı oyuncu verilemez; motor `Error` fırlatır). İki oyuncu birbirinin slotuna geçer; `targetId` thief'in `protectedIds`'ine eklenir. Sıra değişir, `stealsLeft` azalır; ikisi de 0 olunca `phase="done"`.
- `slotScore(slotPos, player)` -> `player.pos === slotPos` ise `rating`; `alt` içinde ise `rating`; değilse `rating - 10` (alt sıfırın altına inmez).
- `teamRating(state, side)` -> 11 slotun `slotScore` ortalaması, tam sayıya yuvarlanmış.
- `result(state)` -> `{ A, B, winner: "A"|"B"|"draw" }` (yalnızca `phase=="done"`).
- Aynı seed + aynı hamleler -> aynı sonuç (deterministik; küçük bir PRNG).

## UI (`index.html`, `src/ui.js`, `styles.css`)
Motoru `import { createMatch, protect, steal, teamRating, result } from './engine.js'` ile kullanır; veriyi `fetch('data/…json')` ile yükler. Takas ekranında kendi korumalı oyuncular "ver" listesinde devre dışı ve "korumalı" etiketli gösterilir (yalnızca onayda hata çıkmasın). Kurulumda varsayılan formasyon önceden seçilidir (ilk formasyon). Ekranlar: kurulum (kategori arama/seçme) -> kadro gösterimi -> koruma (sıra A sonra B) -> takas turları -> sonuç. Motor kodunu kopyalamaz.

## Dosya sahipliği
w1: `data/**` (ham CSV dahil), `docs/data-notes.md` | w2: `src/engine.js` | w3: `index.html`, `src/ui.js`, `styles.css` | w4: `tests/**`

---
# Streamlit sürümü (yeni; JS sürümüyle aynı oyun kuralları, aynı veri dosyaları)
Veri: `data/players.json`, `data/categories.json`, `data/formations.json` aynen kullanılır. Kural ve akış yukarıdaki gibi (kategori -> dağıtım -> koruma -> takas -> sonuç). JS dosyaları (`src/`, `index.html`) değişmez.

## Motor (`engine.py`, saf Python, standart kütüphane, Streamlit'e bağımlı değil)
State düz `dict`; her fonksiyon girdiyi değiştirmez (`copy.deepcopy`), hata durumunda `ValueError` fırlatır. Anahtarlar snake_case:
- `create_match(players, categories, formation, protect_count=3, steals_per_side=3, seed=1)` -> state
  - `categories`: `[{"type": "club"|"league"|"nation", "value": str}]`; `formation`: `{"id","slots":[...]}`
  - state: `{"phase": "protect"|"steal"|"done", "sides": {"A": side, "B": side}, "turn": "A"|"B", "steals_left": {"A": n, "B": n}, "protect_count": n}`; `side = {"slots": [{"pos": str, "player": dict}], "protected_ids": [str]}`
  - Dağıtım: havuz = kategorilerden herhangi birine uyan oyuncular; her iki tarafa her slot için tekrarsız, rastgele (`random.Random(seed)`) oyuncu; önce `pos == slot`, yetmezse `alt` içinde slot olanlar; yetmezse `ValueError`. İki tarafta aynı oyuncu olmaz.
- `protect(state, side, player_ids)`: tam `protect_count` id, hepsi o tarafın kadrosunda; iki taraf da koruyunca `phase="steal"`, `turn="A"`.
- `steal(state, side, target_id, give_id)`: yalnızca `phase=="steal"` ve `turn==side`; `target_id` rakipte ve korumasız; `give_id` kendi kadroda ve kendi korumalısı değil; iki oyuncu birbirinin slotuna geçer; `target_id` thief'in `protected_ids`'ine eklenir; sıra değişir, `steals_left[side]` azalır; ikisi de 0 olunca `phase="done"`.
- `slot_score(slot_pos, player)`: `pos == slot_pos` veya `slot_pos in alt` ise `rating`, değilse `max(0, rating - 10)`.
- `team_rating(state, side)`: 11 slotun `slot_score` ortalaması, `round()` ile tam sayı.
- `result(state)`: `{"A": int, "B": int, "winner": "A"|"B"|"draw"}`; yalnızca `phase=="done"`.
- Aynı seed + aynı hamleler -> aynı sonuç.

## Uygulama (`app.py`, `requirements.txt`)
`streamlit run app.py`. `engine.py`'yi import eder, motoru kopyalamaz. Veri `@st.cache_data` ile `data/*.json`'dan yüklenir. Durum `st.session_state`'te. Hot-seat. Ekranlar: kurulum (kategori türü seç, arama, çoklu seçim, formasyon; varsayılan ilk formasyon) -> kadrolar -> koruma (A sonra B, tam 3 seçim) -> takas turları (rakipten korumasız al, kendinden korumasız ver; korumalılar listede devre dışı/etiketli) -> sonuç ve "Yeni maç". `requirements.txt`: yalnızca `streamlit`. Telefonda da rahat okunmalı (`st.columns` az, uzun listeler `st.selectbox`/`st.multiselect`).

## Dosya sahipliği (Streamlit)
st-engine: `engine.py` | st-app: `app.py`, `requirements.txt`, `.streamlit/**` | st-tests: `tests/test_engine.py`, `tests/test_app.py`

---
# Güncelleme 2 (Streamlit): her oyuncunun kendi kategorisi ve formasyonu
Bu bölüm, yukarıdaki Streamlit bölümünün ilgili maddelerini geçersiz kılar. JS sürümü (`src/`, `index.html`) artık güncellenmez (eski/legacy).

## Kurallar
- İki oyuncunun seçim ekranı birebir aynıdır; sırayla yapılır: önce Oyuncu A, sonra Oyuncu B.
- Her oyuncu **en az 1, en fazla 4** kategori seçer (ülke / kulüp / lig, karışık olabilir; toplam 4). Her oyuncu **kendi formasyonunu** seçer; ikisi farklı olabilir.
- Oyuncu X'in kadrosu yalnızca X'in kategorilerinden oluşan havuzdan dağıtılır. Aynı oyuncu iki takımda birden bulunmaz (iki havuz kesişiyorsa oyuncu yalnızca birine verilir).
- Koruma, takas, puan ve sonuç kuralları değişmez (takaslarda iki takımın slot dizilimi farklı olabilir; `slot_score` cezası aynen geçerli).

## Motor (`engine.py`)
- Yeni imza: `create_match(players, setups, protect_count=3, steals_per_side=3, seed=1)`
  - `setups = {"A": {"categories": [...], "formation": {...}}, "B": {"categories": [...], "formation": {...}}}`; `categories` elemanları `{"type","value"}`; formasyon `{"id","slots":[11 etiket]}`.
  - Doğrulama (`ValueError`, mesajda hangi taraf olduğu yazar): bir tarafta 0 veya 4'ten fazla kategori; havuz yetersiz.
  - Dağıtım: slotlar iki taraf için dönüşümlü (A slot1, B slot1, A slot2, …) seed'li `random.Random` ile doldurulur; slot için önce `pos == slot`, yetmezse `alt` içinde slot olan; kullanılmış oyuncu tekrar verilmez. Dağıtım tıkanırsa seed'den türetilen yeni karıştırmayla en fazla 50 kez yeniden dener (deterministik); hâlâ olmazsa `ValueError`.
  - State'e eklenir: `state["setups"] = {"A": {"categories": [...], "formation_id": str}, "B": {...}}`. Diğer alanlar aynı.
- Diğer fonksiyonlar (`protect`, `steal`, `slot_score`, `team_rating`, `result`) aynı imzada.

## Uygulama (`app.py`)
- Kurulum iki adımdır ve aynı ekran bileşenini kullanır: "Oyuncu A: kategorilerini ve formasyonunu seç" -> "Oyuncu B'ye geç" -> "Oyuncu B: …" -> "Maçı başlat".
- Her ekranda kategori türü seçilir, çoklu seçilir; **toplam 4**'ü geçemez (4'e ulaşınca yeni seçim engellenir ve uyarı gösterilir). Havuz büyüklüğü gösterilir. Formasyon listesi `data/formations.json`'dan gelir; varsayılan ilk formasyon.
- Kadro ekranında her taraf kendi formasyon adıyla gösterilir.
- Yeni maçta iki oyuncunun seçimleri sıfırlanır.

## Veri (`data/formations.json`)
Mevcut 4 formasyona ek olarak en az şunlar eklenir: 4-1-4-1, 4-5-1, 5-3-2, 3-4-3, 4-3-2-1, 4-4-1-1, 5-4-1, 3-4-2-1. Slot etiketleri EA etiketleridir; her slot etiketi için `players.json`'da (pos veya alt) en az 30 oyuncu olmalı (olmayan etiketi kullanma, başka bir uygun etiketle değiştir). `players.json` ve `categories.json` değişmez.

## Dosya sahipliği (Güncelleme 2)
v2-engine: `engine.py` | v2-app: `app.py` | v2-data: `data/formations.json`, `data/build_data.py` (yalnızca formasyon kısmı), `docs/data-notes.md` | v2-tests: `tests/test_engine.py`, `tests/test_app.py`

---
# Güncelleme 3 (Streamlit): koruma takas turunun içinde
Bu bölüm önceki bölümlerin koruma ile ilgili maddelerini geçersiz kılar (ayrı bir "koruma aşaması" yok; takasta alınan oyuncu artık otomatik korumalı olmaz).

## Kural
- Maç, iki taraf da hiç korumasız başlar. Ayrı koruma aşaması yoktur: `phase` yalnızca `"steal"` ve `"done"`.
- Sıra A, B, A, B… Her sıra iki adımdır: (1) **takas**: rakipten korumasız birini al, kendi korumasız oyuncunla değiştir; (2) **koruma**: oyuncuların arasından (yeni aldığın dahil) en fazla `protect_count` (3) oyuncuyu korumalı olarak belirle; bu liste önceki korumanı tamamen değiştirir (3 doluysa birini bırakıp yenisini seçebilirsin; boş bırakmak da serbest).
- Korumalı oyuncu rakip tarafından alınamaz ve sahibi tarafından verilemez (kendi korumalısı takasta verilemez; önce korumayı değiştirmen gerekir).
- Son takastan sonra (iki tarafın `steals_left` değeri 0) koruma adımı atlanır, maç biter.

## Motor (`engine.py`)
- `create_match(...)` imzası aynı; state: `phase="steal"`, `step="steal"`, `turn="A"`, `sides[X].protected_ids=[]`; `protect_count` aynı.
- `steal(state, side, target_id, give_id)`: yalnızca `phase=="steal"`, `step=="steal"`, `turn==side`. `target_id` rakipte ve korumasız; `give_id` kendi kadroda ve korumasız. İki oyuncu slotlarını değiştirir. **Otomatik koruma eklenmez.** `steals_left[side]` azalır. İkisi de 0 ise `phase="done"`; değilse `step="protect"` (sıra aynı tarafta kalır).
- `protect(state, side, player_ids)`: yalnızca `phase=="steal"`, `step=="protect"`, `turn==side`. En fazla `protect_count` id, tekrarsız, hepsi kendi kadrosunda; `protected_ids` bu listeyle değiştirilir. Sonra `turn` rakibe geçer, `step="steal"`.
- `slot_score`, `team_rating`, `result` aynı.
- Aynı seed + aynı hamleler -> aynı sonuç.

## Uygulama (`app.py`)
- Kurulumdan sonra (kadro ekranı) doğrudan takas ekranı başlar; "Koruma aşamasına geç" ve ayrı koruma ekranı kalkar. Kadro ekranındaki buton "Takas turlarını başlat" olur.
- Takas ekranı sıra sahibine göre iki adımlıdır: önce "Takas" (rakipten korumasız al, kendinden korumasız ver; korumalılar listede devre dışı ve etiketli), takas yapılınca aynı ekranda "Koruma": kendi 11 oyuncun (yeni alınan "yeni" etiketli) içinden en fazla 3 seçip "Korumayı onayla"; seçimsiz de onaylanabilir ("Koruma yapma" ayrı bir seçim gerekmez, boş onay yeter). Sıra bilgisi ve kalan takas hakkı görünür; mevcut korumalar önceden seçili gelir.
- Son takastan sonra koruma adımı gösterilmeden sonuç ekranına geçilir.

## Dosya sahipliği (Güncelleme 3)
v3-engine: `engine.py` | v3-app: `app.py` | v3-tests: `tests/test_engine.py`, `tests/test_app.py`

---
# Güncelleme 4 (Streamlit): 8 yedek oyuncu
Bu bölüm önceki bölümlerin ilgili maddelerini geçersiz kılar.

## Kural
- Her taraf, ilk 11'e ek olarak **8 yedek** alır (toplam 19 oyuncu). Yedekler, ilk 11 dağıtıldıktan sonra tarafın kendi kategori havuzundan, pozisyon fark etmeksizin rastgele ve tekrarsız dağıtılır (iki taraf ve ilk 11 ile çakışmaz; iki taraf dönüşümlü seed'li).
- **Takas** yedekleri de kapsar: rakibin korumasız herhangi bir oyuncusu (ilk 11 veya yedek) alınabilir, kendi korumasız herhangi bir oyuncun (ilk 11 veya yedek) verilebilir. Oyuncular birbirinin yerine (slot veya yedek sırası) geçer.
- **Koruma** 19 oyuncunun hepsini kapsar (yine en fazla `protect_count` = 3).
- **Yerleştirme:** taraf kendi ilk 11'indeki bir oyuncuyu bir yedekle yer değiştirebilir (sınırsız, mülkiyet değişmez, korumalılar da yer değiştirebilir). Takas turunda yalnızca sırası gelen taraf, kendi sırası boyunca (takas veya koruma adımında) yerleştirme yapabilir.
- Son takastan sonra maç hemen bitmez: `phase="arrange"` olur, iki taraf da son kez dizilişini düzenler ve onaylar; ikisi de onaylayınca `phase="done"`.
- Puan: yalnızca ilk 11 (`slot_score` cezası aynı). Yedekler puana katılmaz.

## Motor (`engine.py`)
- `create_match(players, setups, protect_count=3, steals_per_side=3, bench_size=8, seed=1)`; havuz ilk 11 + yedek için yetmezse `ValueError` (mesajda taraf).
- state eklenir: `sides[X]["bench"]` (`bench_size` uzunlukta oyuncu dict listesi), `state["arranged"] = {"A": False, "B": False}`; `phase`: `"steal"|"arrange"|"done"`. Diğer alanlar aynı (`step`, `turn`, `steals_left`, `protected_ids`...).
- `steal(state, side, target_id, give_id)`: `target_id` rakibin ilk 11'inde veya yedeğinde, korumasız; `give_id` kendi ilk 11'inde veya yedeğinde, korumasız. Yer değişimi: hedef oyuncu verenin bulunduğu yere (slot veya yedek sırası), verilen oyuncu hedefin bulunduğu yere geçer. Son takas sonrası `phase="arrange"` (koruma adımı atlanır), değilse `step="protect"`.
- `protect(state, side, player_ids)`: id'ler kendi 19 oyuncusundan; diğer kurallar aynı.
- `swap_bench(state, side, slot_index, bench_index)` (yeni): `phase=="steal"` ise `turn==side` olmalı; `phase=="arrange"` ise `arranged[side]` False olmalı; aksi halde `ValueError`. İlk 11'deki `slot_index` oyuncusu ile `bench_index` yedeği yer değiştirir. İndeks aralık dışıysa `ValueError`.
- `confirm_arrange(state, side)` (yeni): yalnızca `phase=="arrange"` ve `arranged[side]` False iken; `arranged[side]=True`; ikisi de True ise `phase="done"`.
- `slot_score`, `team_rating` (yalnız ilk 11), `result` aynı; `result` yalnızca `phase=="done"`.

## Uygulama (`app.py`)
- Kadro ekranı her tarafın ilk 11'ini (formasyon adıyla) ve **Yedekler** listesini (8 oyuncu: ad, poz, puan) gösterir.
- Takas ekranında rakipten alınacak ve kendinden verilecek listeler 19 oyuncuyu içerir; yedekler "Yedek" etiketlidir, korumalılar devre dışıdır. Koruma çoklu seçimi 19 oyuncudan seçer.
- Sırası gelen taraf, sıra boyunca "Kadro düzeni" bölümünde bir ilk 11 oyuncusu ve bir yedek seçip "Yer değiştir" ile değişimi yapar (pozisyon uyumsuzsa uyarı gösterilir: puandan −10).
- `phase=="arrange"`: önce Oyuncu A sonra Oyuncu B (sıra sırayla, `arranged` bayraklarına göre) aynı yerleştirme bölümüyle düzenini yapar ve "Düzeni onayla" der; ikisi de onaylayınca sonuç ekranı. Sonuç ekranı iki tarafın ilk 11'ini ve yedeklerini gösterir.

## Dosya sahipliği (Güncelleme 4)
v4-engine: `engine.py` | v4-app: `app.py` | v4-tests: `tests/test_engine.py`, `tests/test_app.py`

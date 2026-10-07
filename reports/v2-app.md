Durum: bitti

# v2-app raporu (Güncelleme 2: Streamlit arayüzü)

## Yapılan
- `app.py` yalnızca sözleşmedeki "Güncelleme 2 > Uygulama" maddelerine göre güncellendi.
- Kurulum iki adımlı, aynı bileşen: "Oyuncu A: kategorilerini ve formasyonunu seç" -> "Oyuncu B'ye geç" -> "Oyuncu B: ..." -> "Maçı başlat".
- Her oyuncu en fazla 4 kategori seçer (`MAX_CATEGORIES = 4`). Kalan hak `multiselect`'in `max_selections` değeriyle sınırlanır; hak bittiğinde tür seçimi devre dışı kalır ve uyarı gösterilir. Havuz büyüklüğü gösterilir.
- Her oyuncu kendi formasyonunu seçer (varsayılan ilk formasyon). Kadro başlıklarında ve sonuç ekranındaki "Son kadrolar" bölümünde formasyon adı yazılır.
- `create_match(PLAYERS, setups, protect_count=3, steals_per_side=3, seed=...)` yeni imzayla çağrılır; `setups = {"A": {"categories", "formation"}, "B": {...}}`.
- Kadro ekranı `state["setups"][side]["formation_id"]` alanını okur.
- "Yeni maç" hem maç durumunu hem iki oyuncunun kurulum seçimlerini (A_/B_ önekli widget anahtarları dahil) sıfırlar.
- Koruma, takas ve sonuç ekranlarının mantığı değişmedi.

## Doğrulama
- `engine.py` henüz yeni imzada değil (v2-engine işi). Bu yüzden gerçek motor yerine, eski motoru yeni imzaya saran geçici bir gölge `engine.py` kullanıldı. Gölge dosya ve test betikleri scratchpad'te; repoya girmedi.
- `streamlit.testing.v1.AppTest` (streamlit 1.65.0) ile üç senaryo geçti:
  1. A kategori seçimi -> "Oyuncu B'ye geç" aktif; B'de seçim yokken "Maçı başlat" pasif.
  2. B'de 4 kategori seçilince sınır uyarısı görünür; B formasyonu A'dan farklı (4-4-2) seçilir ve kadro başlığına yansır.
  3. Tam maç akışı: kurulum -> kadrolar -> koruma (A, B) -> takas turları -> sonuç -> "Yeni maç" ile A kurulumuna dönüş.
- Commit'e yalnızca `app.py` ve bu rapor girer. `tests/test_app.py` v2-tests sahibinde olduğu için dokunulmadı.

## Açık noktalar / şef için
- Gerçek `engine.py` yeni imzayla gelince `app.py` tekrar test edilmeli (sözleşmedeki `create_match` imzası ve `state["setups"][side]["formation_id"]` alanı bağımlılık).
- `formations.json`'a eklenecek yeni formasyonlar (v2-data) gelince kurulum listesi otomatik genişler; kod değişikliği gerekmez.
- Mevcut dal adı `worktree-agent-a535820355687d86d`; WORKFLOW'daki `w/…` adlandırması kullanılmadı (dal değiştirilmedi).

Durum: bitti

# v2-tests raporu

## Yapılanlar
- `tests/test_engine.py` yeni sözleşmeye göre yeniden yazıldı (`docs/CONTRACT.md` > "Güncelleme 2"):
  - Yeni imza `create_match(players, setups, protect_count, steals_per_side, seed)`; `setups = {"A": {"categories", "formation"}, "B": {...}}`.
  - 0 kategori ve 5 kategori hataları: `ValueError`, mesajda hangi taraf olduğu (A/B) regex ile kontrol ediliyor. 4 kategori kabul ediliyor.
  - Farklı formasyonlu iki taraf (4-3-3 / 4-4-2 / 3-5-2): her tarafın 11 slotu kendi dizilimiyle geliyor; `state["setups"]` kaydı kontrol ediliyor.
  - Tarafların kadrosu yalnızca kendi kategorilerinden geliyor; havuzlar kesişince oyuncu tek tarafta (iki taraf kesişimi boş).
  - Determinizm: aynı seed + aynı setup -> aynı state (farklı formasyonla dahil).
  - Koruma/takas/puan/sonuç testleri aynen korundu; takasta slot etiketlerinin her tarafın kendi dizilimine göre kaldığı ayrıca test ediliyor.
  - Gerçek veri (`data/players.json`, `formations.json`): İngiltere ulusu 4-3-3 vs Premier League 4-4-2, 3 koruma + 6 takas uçtan uca.
- `tests/test_app.py` yeniden yazıldı (AppTest, `streamlit.testing.v1`):
  - Açılış (istisna yok), varsayılan formasyon = `data/formations.json`'un ilk elemanı.
  - İki adımlı kurulum: A kategori+formasyon seç -> "Oyuncu B'ye geç" -> B kategori+formasyon seç -> "Maçı başlat"; kadro ekranında iki formasyon adı görünüyor.
  - "Maçı başlat" B hazır değilken yok; B'de 0 kategoriyle başlatılamıyor (buton disabled ya da hata).
  - 5. kategori engelleniyor: toplam seçim 4'te kalıyor ve uyarı (`warning`) gösteriliyor.

## Varsayımlar (app testleri için)
Widget'lar etiketle bulunuyor (anahtar adına bağlı değil). Beklenen etiketler:
- selectbox "Kategori türü" (değerler `club`/`league`/`nation`), multiselect "Kulüp seç" / "Lig seç" / "Ülke seç"
- selectbox "Formasyon"
- butonlar "Oyuncu B'ye geç", "Maçı başlat"
Bu etiketler `app.py` tarafında farklıysa `tests/test_app.py` içindeki `pick`, `set_formation`, `find` çağrılarında güncellenmeli.

## Doğrulama
- Repo'nun mevcut `engine.py` ve `app.py` dosyaları hâlâ eski sürümde (eski imza, tek kategori seti), bu yüzden şu an 51 testten 46'sı kırmızı: 42'si `create_match` imza hatası (`setups` anahtar argümanı), 4'ü eski `app.py` arayüzü (yeni etiketler yok). Bu beklenen durum; v2-engine ve v2-app birleşince geçmeli.
- Sözleşmeye uyan geçici bir motor (yalnızca scratchpad'de, repoya girmedi) ile `tests/test_engine.py`: 45/45 geçti (gerçek `data/*.json` dahil).
- AppTest API'si (`at.get`, `label`, `value`, `disabled`, `set_value`, `click`) küçük bir sahte uygulamayla denendi; çalışıyor. `tests/test_app.py` gerçek yeni `app.py` ile henüz koşmadı.
- Çalıştırma: `python3 -m unittest discover -s tests -p "test_*.py"` (repo kökünden).

## Dosyalar
- `tests/test_engine.py`
- `tests/test_app.py`
- `reports/v2-tests.md` (bu dosya)

Dokunulmayan: `engine.py`, `app.py`, `data/*`, `docs/*`, `WORKFLOW.md`.

## Commit'ler
- `2368400` test_engine yeni create_match imzası
- `e6ff3ae` test_engine 4-kategori testi havuzu tüketmesin
- `670779d` test_app iki adımlı kurulum ve 5. kategori engeli
- (rapor commit'i ayrıca atıldı)

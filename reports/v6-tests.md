Durum: bitti

# v6-tests raporu (Güncelleme 6: 8 yedek + 4 rezerv, yedekler puana dahil)

## Yapılanlar
- `tests/test_engine.py` (73 test) Güncelleme 6 sözleşmesine göre yeniden yazıldı:
  - create_match: her tarafta 11 + 8 yedek + 4 rezerv = 23 oyuncu, taraflar arası ve gruplar arası çakışma yok, formasyon slotları, başlangıç alanları (phase/step/turn/steals_left/arranged), kategori dışı oyuncu yok, havuz yetersizse ValueError (A, B ve ortak havuz), kategori sayısı 0/5 hatası, determinizm, girdinin değişmemesi, bench/reserve boyut parametreleri.
  - Kalite penceresi: kaleci 90/80/71/68 ile (ayrı havuzlarda 50 seed: yalnızca 90/80; ortak havuzda 20 seed: [80, 90]; `quality_window=None` ile 71/68 görülür; `quality_window=0` ile geri çekilme yolu: [90] ve [80]; varsayılan = 10).
  - Gerçek veri: Real Madrid (4-3-3) vs Chelsea (4-4-2), 20 seed, 23'er oyuncu, çakışma yok.
  - team_rating: 19 oyunculu ortalama (11 slot_score + 8 yedek rating), tam sayı yuvarlama, sayısal örnekler (72, 71), rezerv değişince puan sabit, yedek değişince yeniden hesap, yedekte pozisyon cezası yok.
  - slot_score: pos, alt, −10 cezası, sıfırın altına inmeme.
  - steal: sıra kontrolü, üç gruptan karışık yer değişimleri (slot<->yedek, rezerv<->slot, yedek<->rezerv; slot pozisyon etiketleri yerinde), alınan oyuncu korumasız, adım (step) protect/steal geçişi, korumalı hedef ve korumalı verilen oyuncu hataları, kadro dışı hedef/verilen hataları, girdi değişmez.
  - protect: en fazla 3, tekrar/yabancı id hataları, 23 oyuncudan (yedek ve rezerv dahil) seçim, listenin önceki korumanın yerine geçmesi, boş liste, korumalı oyuncunun yer değiştirebilmesi.
  - swap_bench: yer değiştirme, aralık dışı indeks hataları (−1 ve üst sınır dahil), sıra kontrolü, rezervlere dokunmaz.
  - swap_reserve: yer değiştirme, aralık hataları, sıra hatası, korumalı rezerv yer değiştirebilir ve koruma aynı kalır, arrange'de onaydan önce serbest / sonra hata.
  - Akış: son takas koruma adımı olmadan arrange; confirm A sonra B -> done; onay hataları; steals=0 ile arrange'de başlama; result (done değilken hata, team_rating ile tutarlılık, kazanan/berabere); tam maç determinizmi.
- `tests/test_app.py` (17 test) Güncelleme 6 etiketlerine göre yeniden yazıldı:
  - Sabitler: "Yedekler", "Rezervler", "Kadro düzeni", "İlk 11'den oyuncu", "Yedekten oyuncu", "Rezervden oyuncu", "Yer değiştir", etiketler "[yedek]" ve "[rezerv]" (küçük harf), 23 kişilik kadro (8 yedek, 4 rezerv).
  - Kadro ekranında Yedekler ve Rezervler ayrı listeler; takas/koruma seçicileri 23 oyuncu; korumada yedek ve rezerv seçilebilir.
  - İki yerleştirme aracı: 1) "İlk 11'den oyuncu" <-> "Yedekten oyuncu", 2) "Yedekten oyuncu" <-> "Rezervden oyuncu". Selectbox değerleri indeks, takas/koruma id.
  - Akış: son takas -> arrange, A sonra B onayı, düzen değişimleri (iki araç, iki taraf), sonuç ekranında ilk 11, Yedekler ve Rezervler.

## Doğrulama
- Engine testleri, repo dışındaki scratchpad'de Güncelleme 6'yı minimal uygulayan bir referans motorla çalıştırıldı (`engine.py` v5 üzerine: 8 yedek, rezerv dağıtımı, swap_reserve, steal/protect üç grup, 19 oyunculu team_rating): 73/73 OK.
- Mutasyon kontrolü: kalite penceresi kapatılınca (aday filtresi kaldırılınca) 3 test kırmızı; geri alınınca 73/73 OK.
- Repo'daki `engine.py` ve `app.py` henüz Güncelleme 6'ya geçmediği için repo üzerinde beklenen durum:
  - `tests/test_engine.py`: import hatası (`swap_reserve` v5 engine'de yok). Güncel engine'e karşı tamamı kırmızı olur.
  - `tests/test_app.py`: 17 testten 6'sı hata, 3'ü başarısız; 8'i geçiyor (kurulum akışı). Başarısızlıklar v5 uygulamasından: tek "Yedekler" listesi, 4 yedek, rezerv bölümü ve ikinci yerleştirme aracı yok.

## Uygulama için notlar (app.py / v6-app)
- Kadro düzeni bölümünde iki araç aynı etiketleri paylaşıyor: "Yedekten oyuncu" selectbox'ı ve "Yer değiştir" düğmesi iki kez geçer. Test, sayfadaki sırayla ayırır (1. araç önce, 2. araç sonra). Uygulama iki widget'a farklı `key` vermeli (aynı etiket+parametre Streamlit'te DuplicateWidgetID üretir) ve araçların sırası bu sıra olmalı.
- Testler `session_state["state"]` anahtarını kullanır (mevcut app ile aynı).

## Commit
- tests/test_engine.py, tests/test_app.py, reports/v6-tests.md (commit hash aşağıda).

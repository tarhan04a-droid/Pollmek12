Durum: bitti

# v4-tests raporu

Kaynak: `docs/CONTRACT.md` > "Güncelleme 4" (en alttaki bölüm). Sahip dosyalar: `tests/test_engine.py`, `tests/test_app.py`. Başka dosyaya dokunulmadı.

## Yapılanlar
- `tests/test_engine.py` Güncelleme 4'e göre yeniden yazıldı:
  - create_match: her tarafta 11 + 8 yedek, 19 oyuncu tekrarsız, taraflar arası çakışma yok; havuz 18 ise hata (taraf A), 19 ise yeterli; bench_size; determinizm.
  - steal: yedek-ilk11, ilk11-yedek, yedek-yedek yer değişimleri; korumalı hedef/veren hatası (yedekler dahil); bilinmeyen id; takas sonrası koruma adımı.
  - protect: 19 oyuncudan (yedek dahil), en fazla 3, tekrar/başka taraf id'si hatası, faz "arrange" iken hata.
  - Son takas sonrası phase "arrange" (step koruma yok); 6 takas, sıra A,B,A,B,A,B.
  - swap_bench: doğru takas, slot pozisyonları ve taraf üyeliği değişmez, korumalı oyuncu da yer değiştirebilir, yanlış sıra hatası (takas adımında rakip taraf, koruma adımında rakip taraf), aralık hatası (slot 11, yedek 8), arrange'de onaylı taraf hatası.
  - confirm_arrange: yalnız arrange'de, iki kez onay hatası, tek onayda arrange kalır, ikisi onaylayınca "done"; sıra farkı önemsiz.
  - team_rating yalnız ilk 11 (yedek puanı değişince değişmez); result yalnız done'da.
  - Determinizm: aynı seed + aynı hamleler = aynı state ve sonuç. Gerçek data/*.json ile tam maç (6 takas, arrange, sonuç).
- `tests/test_app.py` Güncelleme 4'e göre yeniden yazıldı:
  - Kadro ekranında "Yedekler" (8 oyuncu, ad metinde), takas ve koruma seçicilerinde 19 oyuncu.
  - Korumada yedek oyuncu seçilebilir.
  - "Kadro düzeni" bölümünde ilk 11 + yedek seçip "Yer değiştir" ile değişim; pozisyon uyumsuzluğunda uyarı.
  - Son takastan sonra koruma yok, arrange ekranı; "Düzeni onayla" A sonra B; sonuç ekranında kazanan, "Yedekler" ve "Yeni maç".

## Etiket sözleşmesi (app.py ile eşleşmeli)
Sözleşmede adı geçmeyen etiketler test sabitlerinde bu isimlerle tanımlandı; app.py farklı kullanırsa yalnızca `tests/test_app.py` başındaki sabitler güncellenir:
- `HDR_BENCH = "Yedekler"`, `HDR_LAYOUT = "Kadro düzeni"`
- `SEL_SLOT = "İlk 11'den oyuncu"`, `SEL_BENCH = "Yedekten oyuncu"`
- `BTN_SWAP = "Yer değiştir"`, `BTN_CONFIRM_ARRANGE = "Düzeni onayla"`, `BTN_NEW_MATCH = "Yeni maç"`
- Selectbox seçimlerinde `set_value` oyuncu id'si alır (id'ler `session_state["state"]` üzerinden okunur).

## Mevcut durum (kırmızı, beklenen)
- `engine.py` hâlâ Güncelleme 3 sürümünde: `swap_bench` ve `confirm_arrange` yok, `test_engine.py` import hatasıyla düşüyor (1 hata).
- `app.py` hâlâ eski sürümde: `tests/test_app.py` içinde 4 başarısızlık ve 6 hata. Bunlar bekleniyor.
- `python3 -m unittest discover -s tests -p "test_*.py"` yeşil olması için v4-engine ve v4-app birleşmeli.
- Testler sözleşmeye göre yazıldı; motor/uygulama çalıştırılarak doğrulanmadı.

## Commit
- `4e40f91`'den sonra: `b8a388f` (test_engine), `c7d8473` (test_app).
- Not (test düzeltmesi): test_app.py 5 hatası giderildi; selectbox indeksleri (`SEL_SLOT`/`SEL_BENCH`) indeksle, takas seçimleri id ile yapılıyor, yedek araması büyük/küçük harf duyarsız; `play_full_match` önce takas turlarını başlatıyor.
- Sonuç: `python3 -m unittest discover -s tests -p "test_*.py"` 108/108 geçiyor (app.py ve engine.py değiştirilmedi).

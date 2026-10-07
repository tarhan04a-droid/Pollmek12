Durum: bitti

# v4-app raporu (Streamlit yedekler, Güncelleme 4)

## Yapılanlar
- `app.py` sözleşmenin "Güncelleme 4 > Uygulama" bölümüne göre güncellendi. Dosya dışına dokunulmadı.
- `create_match` çağrısına `bench_size=8` eklendi.
- Kadro ekranı: ilk 11 (formasyon adıyla) + "Yedekler" listesi (ad · poz · puan), yedek sayısı `side["bench"]`'ten okunur.
- Takas ekranı: rakip ve kendi listeleri 19 oyuncuyu içerir; yedekler "[yedek]", korumalılar "[korumalı]" etiketli ve devre dışı. Koruma çoklu seçimi 19 oyuncudan seçer.
- "Kadro düzeni" bölümü (`render_arrange_controls`): sırası gelen taraf takas ve koruma adımlarında ilk 11 oyuncuyu bir yedekle `swap_bench` ile değiştirir. Pozisyon uyumsuzsa uyarı gösterilir (puandan -10, `slot_score` ile hesaplanır).
- `phase == "arrange"` için yeni ekran (`screen_arrange`): önce Oyuncu A, sonra B (`arranged` bayraklarına göre) düzenini yapıp `confirm_arrange` ile onaylar. Sıradaki oyuncuya "Oyuncu A düzenini onayladı" bilgisi gösterilir.
- Sonuç ekranı her iki tarafın ilk 11'ini ve yedeklerini gösterir.
- `reset_match` artık takas/koruma/yer değiştirme widget anahtarlarını da temizler (`WIDGET_PREFIXES`); yeni maçta eski seçimler kalmaz.
- Import'a `confirm_arrange`, `swap_bench`, `slot_score` eklendi.

## Doğrulama
- `python3 -m py_compile app.py` geçti.
- Repodaki `engine.py` henüz Güncelleme 4 sürümü değil (`swap_bench`, `confirm_arrange`, `bench`, `arranged`, `phase="arrange"` yok). Bu yüzden repo `engine.py` ve `tests/` dosyalarına dokunulmadı.
- Sözleşmeye uyan geçici bir motor taslağı yalnızca scratchpad'te (repo dışında) yazıldı ve `streamlit.testing.v1.AppTest` (streamlit 1.65.0) ile çalıştırıldı. Akış baştan sona geçti: kurulum (A kulüp, B ülke), kadro (yedek başlığı görünüyor), yedek yerleştirme, 19 oyunculu takas (yedek alındı), koruma (19 seçenek), kalan takaslar, `arrange` ekranında A ve B onayı, sonuç, "Yeni maç". Hata çıkmadı.
- Not: Oyuncu A ve B aynı kategoriyle (ör. aynı kulüp) kurulursa 19+19 oyuncu havuzu yetmeyebilir; uygulama bunu `ValueError` mesajıyla ("havuz yetersiz") gösterir. Bu motor kuralıdır, arayüz hatası değildir.

## Açık noktalar (şef için)
- Gerçek `engine.py` (v4-engine) birleşince `app.py` ile tek bir AppTest koşulmalı; taslakta olmayan bir imza farkı varsa yalnızca `app.py` içindeki çağrılar düzeltilir.
- `tests/test_app.py` (v4-tests) yeni widget anahtarlarını kullanmalı: `sw_slot_{A|B}`, `sw_bench_{A|B}`, `sw_btn_{A|B}`, `target_{turn}_{left}`, `give_{turn}_{left}`, `protect_{turn}_{left}`, kurulum için `{A|B}_cat_type`, `{A|B}_cat_pick_{tür}`, `{A|B}_formation`.

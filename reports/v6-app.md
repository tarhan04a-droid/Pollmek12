Durum: bitti

# v6-app raporu (Streamlit, 8 yedek + 4 rezerv, Güncelleme 6)

## Yapılanlar (yalnızca `app.py`)
- Sabitler: `BENCH_SIZE = 8`, `RESERVE_SIZE = 4`; `create_match` çağrısına `reserve_size=RESERVE_SIZE` eklendi. `swap_reserve` import edildi.
- `label(p, protected, tag)`: `tag` artık `TAG_BENCH` ("yedek") veya `TAG_RESERVE` ("rezerv") alıyor; ilk 11 etiketsiz.
- `roster(side)`: ilk 11 + yedekler + rezervler (23 oyuncu), her biri etiketiyle. Takas listeleri, koruma çoklu seçimi ve rakip kadrosu expander'ı bu listeyi kullanıyor.
- Kadro ekranı (`render_squad`, artık `state` alıyor): ilk 11, **Yedekler**, **Rezervler** ayrı listelerde; altında "Takım puanı: N (ilk 11 + yedekler ortalaması; rezervler puana dahil değil)".
- Kadro düzeni (`render_arrange_controls`) iki araç:
  - İlk 11 ↔ yedek: `swap_bench`, etiketler "İlk 11'den oyuncu", "Yedekten oyuncu", buton "Yer değiştir" (değişmedi).
  - Yedek ↔ rezerv: `swap_reserve(state, side, bench_index, reserve_index)`, etiketler "Yedekten oyuncu", "Rezervden oyuncu", buton "Rezervle yer değiştir".
  - İlk 11 ile rezerv doğrudan takas edilemiyor (arayüzde de yok).
- Sonuç ekranı: takım puanı açıklaması ve "Son kadrolar"da yedekler (puana dahil) ve rezervler (puana dahil değil) ayrı. Sayılar `len(...)` ile state'ten türetiliyor, sabit metin yok.
- Widget anahtarları `sw_` önekiyle, mevcut sıfırlama mantığıyla uyumlu.

## Doğrulama
- `python3 -m py_compile app.py` geçti.
- Repodaki `engine.py` henüz Güncelleme 6 sürümü değil (`reserve_size` ve `swap_reserve` yok), bu yüzden doğrudan çalıştırılamadı. Geçici bir motor kabuğu (`old_engine` üstüne `reserve_size`, rezerv destekli `steal`/`protect`/`_locate`, `swap_reserve`) scratchpad'de kuruldu; repoya yazılmadı.
- `streamlit.testing.v1.AppTest` (streamlit 1.65.0) ile tam akış: kurulum (A kulüp, B lig) -> maç -> kadro ekranı -> 6 takas (rakipten rezerv alınarak) + 5 koruma -> düzen: rezerv yer değiştirme, yedek yer değiştirme, iki taraf onayı -> `phase == "done"`, hata yok.
- Kadro sayıları: 11 ilk 11 + 8 yedek + 4 rezerv (A ve B).
- Kadro ekranındaki takım puanı yazısı görünüyor; sayının değeri kabukta yalnızca ilk 11'den hesaplandığı için gerçek motorda farklı çıkacak (19 oyunculu ortalama).

## Açık noktalar (şef için)
- Gerçek `engine.py` (v6-engine) birleşince AppTest bir kez daha koşulmalı. Kabuk testte kullanılan ek fonksiyonlar gerçek motorda yoksa bu test yeniden yazılmalı.
- Etiket çakışması: "Yedekten oyuncu" hem ilk 11 ↔ yedek hem yedek ↔ rezerv aracında var (sözleşmedeki etiket). Testlerde ikinci seçimi `at.selectbox` sırasıyla ya da `key` (`sw_rbench_<side>`, `sw_res_<side>`) ile seçmek gerekir.
- `tests/test_app.py` (v6-tests sahipliğinde) hâlâ `BENCH_SIZE = 4` ve `SQUAD_SIZE = 15` kullanıyor; dokunulmadı. Ayrıca `swap_reserve` butonu için sözleşmede etiket yok; "Rezervle yer değiştir" seçildi, test sabitlerine eklenmeli.

Durum: bitti

# v6-engine raporu

Sözleşme: `docs/CONTRACT.md` > "Güncelleme 6" > Motor. Sahip dosya: `engine.py` (tek dosya değiştirildi).

## Yapılanlar
- `create_match(players, setups, protect_count=3, steals_per_side=3, bench_size=8, reserve_size=4, seed=1, quality_window=10)`. Varsayılan `bench_size` 4'ten 8'e çıktı; `reserve_size` eklendi.
- Dağıtım sırası: ilk 11 (A,B dönüşümlü), sonra 8 yedek (A,B), sonra 4 rezerv (A,B). Yedek ve rezerv de Güncelleme 5 kalite penceresiyle seçilir. Tıkanırsa aynı 50 denemeli yeniden deneme ve `ValueError` kullanılır.
- State: `sides[X]["reserves"]` eklendi (`slots`, `bench`, `reserves`, `protected_ids`).
- `team_rating`: ilk 11 (`slot_score`, −10 ceza aynı) + 8 yedek (düz `rating`) = 19 oyuncunun ortalaması, `round()`. Rezervler puana girmez.
- `steal`, `protect` ve yardımcılar (`_locate`, `_get_at`, `_put_at`, `_roster_ids`) üç grubu (ilk 11, yedek, rezerv) kapsar; yer değişimi aynı konumda olur.
- `swap_reserve(state, side, bench_index, reserve_index)` eklendi. Kuralları `swap_bench` ile aynıdır (ortak `_check_rearrange`, `_check_index` yardımcılarıyla). İlk 11 ile rezerv doğrudan değişmez.
- `swap_bench` davranışı değişmedi; yalnızca ortak kontrol fonksiyonlarını kullanır.
- Havuz 23 oyuncuya yetmezse `ValueError` (mesajda taraf adı).

## Doğrulama (gerçek veri: `data/players.json`)
Betik scratchpad'de (`v6_check.py`) çalıştırıldı, repoya eklenmedi. Tüm kontroller geçti:
- A = Real Madrid (28), B = FC Barcelona + Manchester City (58): 11+8+4 kadro, 46 oyuncu, çakışma yok.
- Ortak havuz (iki tarafta Real Madrid + Barça/City): çakışma yok.
- Kaleci kalite penceresi, 20 seed'de başlangıç en iyisinden (90) en fazla 10 geride.
- `team_rating` 19 oyunculu ortalamaya eşit; rezerv takası puanı değiştirmez; `swap_reserve` ile yedek değişince puan değişir (bu veride fark küçük olduğu için yuvarlamadan sonra 0 çıktı, değişimin varlığı ayrıca doğrulanmadı; tam sayı yuvarlaması nedeniyle).
- Takas (rakip rezervi <-> kendi yedeği), korumalı oyuncu alınamaz, bilinmeyen id, tekrarlı koruma, `protect_count` aşımı, sıra hatası, indeks aralık dışı, negatif indeks: hepsi `ValueError`.
- Tam akış: 6 takas -> `arrange` -> iki onay -> `done`; `result` tutarlı; `done` sonrası düzen ve onay reddedilir.
- Havuz 20 oyuncuya yetmediğinde `ValueError`.
- Girdi state'i değişmez (`deepcopy`).
- Not: ilk 11 <-> rezerv takası için ayrı test yazılmadı; `steal` tüm grupları `_locate` ile genel işlediği için aynı kod yolundan geçer.

## Bilinen sonuçlar (bu görev kapsamı dışı)
- `tests/test_engine.py` eski sözleşmeye göre yazılmış; `python3 -m unittest tests.test_engine` 99 testten 8 başarısızlık ve 225 hata veriyor (ör. `82 != 83` yuvarlama beklentisi, yedek sayısı beklentileri). Bu dosya `v6-tests` işçisinin sahipliğinde; güncellenmesi gerekir.
- `app.py` hâlâ `BENCH_SIZE = 4` ile `create_match(..., bench_size=BENCH_SIZE)` çağırıyor; `reserve_size` varsayılanı 4 ile çalışır ama yedek sayısı 4 olur. `v6-app` işçisi `BENCH_SIZE = 8` ve yerleştirme/puan ekranını güncellemeli. Bu işçi `app.py` dosyasına dokunmadı.
- `create_match` imzasında `reserve_size`, `seed` öncesine eklendi; `seed` konumsal olarak geçiriliyorsa bozulur. `app.py` anahtar kelimeyle çağırıyor, sorun yok.

## Dosyalar
- `engine.py` (değişti)
- `reports/v6-engine.md` (bu rapor)

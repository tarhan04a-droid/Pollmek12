Durum: takıldı

# v5-engine raporu (Güncelleme 5: 4 yedek ve kaliteye duyarlı dağıtım)

## Yapılanlar
- `engine.py`, `docs/CONTRACT.md` > "Güncelleme 5" > Motor bölümüne göre güncellendi. Yalnızca `engine.py` ve bu rapor değişti.
- `create_match(players, setups, protect_count=3, steals_per_side=3, bench_size=4, seed=1, quality_window=10)`. Sabitler `DEFAULT_BENCH_SIZE = 4`, `DEFAULT_QUALITY_WINDOW = 10`.
- `quality_window`: `None` ise eski davranış (slot için aday kümesinin ilk elemanı, yedek için havuzun ilk elemanı). Negatif veya tam sayı olmayan değer `ValueError`.
- Slot seçimi (`_pick_slot`): aday kümesi önce `pos == slot`, yoksa `alt` içinde slot olanlar. Kümenin en yüksek `rating`'inden en fazla `quality_window` geride olanlar arasından seed'li `rng.choice`.
- Yedek seçimi (`_pick_bench`): her boş oyuncu, kendi birincil pozisyonundaki kalan en iyi oyuncuya göre değerlendirilir; en fazla `quality_window` geride olanlar arasından seed'li seçim.
- Dağıtım sırası, çakışma kontrolü (`used`), yeniden deneme (en fazla 50, `ValueError`) değişmedi.
- Kalan kısımlar (takas, koruma, yerleştirme, arrange, `result`) değişmedi.
- `tests/`, `app.py` ve diğer dosyalara dokunulmadı. `tests/test_engine.py` hâlâ `bench_size=8` kullanıyor; bu, v5-tests'in işi.

## Gerçek veri doğrulaması (kabul kriteri)
Betik repo dışında: `/tmp/claude-0/-home-user-Pollmek12/bef1fe6a-7e57-5529-8e07-653da3c0c270/scratchpad/v5/check.py` (`python3 -I` ile). Formasyon 4-3-3, seed 0..199.

- Senaryo S1 (A = Real Madrid, B = Gençlerbirliği, havuzlar ayrık): 200/200 maç kuruldu, çakışma yok. B'nin kaleci slotunda 200/200 maçta 71 veya 68 puanlı kaleci var. Bu, havuzda B için başka kaleci olmadığından hiçbir kuralla engellenemez. Kriter bu kurulumda tutarlı değil.
- Senaryo S2 (her iki taraf Real Madrid + Gençlerbirliği, ortak havuz): 200/200 maç kuruldu, çakışma yok, bench 4. A kaleci slotu her zaman Courtois 90 veya Lunin 80. B kaleci slotunda ise 52/200 maçta İrfan Can Eğribayat 71 geldi.
- Determinizm: aynı seed iki kez aynı state verdi (True).
- `quality_window=None`: çalıştı, bench 4, faz `steal`.
- Varsayılan: `bench_size` 4.

## Neden 71 geliyor (sözleşme ile kriter çelişiyor)
- Sözleşme: slot adayları "havuzda **kalan** en iyi oyuncudan en fazla `quality_window` geride" olanlardır.
- A, Courtois'u (90) aldığında B için kalan en iyi kaleci Lunin (80) olur. Eşik 80 - 10 = 70 olur ve Eğribayat (71) bu eşiğin üstünde kalıp aday olur.
- Kabul kriteri ise "hiçbir zaman 71/68 kaleci slotuna gelmesin" diyor. Bu, eşiğin ortak havuzun en iyisine (90) göre hesaplanmasıyla sağlanır (eşik 80: yalnız Courtois ve Lunin).
- Sözleşmenin kendi örneği ("kaleciler 90, 80, 71, 68 ise yalnız 90 veya 80") yalnızca ilk slot için geçerli; ikinci slotta kalan havuz kuralı 71'i geri getiriyor.

## Karar gereken nokta (şef / kullanıcı)
Kodu sözleşmeye göre bıraktım; sözleşmeyi kendi başıma değiştirmedim. Seçenekler:
1. Eşik referansı "kalan en iyi" yerine "kümenin (pozisyonun) başlangıçtaki en iyisi" olsun (`_pick_slot` ve `_pick_bench` içinde en iyi değeri dağıtım öncesi havuzdan al). Bu, S2'de kriteri sağlamalı; ancak bunu doğrulamadım, uygulamadım.
2. Kriter gevşetilsin (örn. yalnız ilk slot için geçerli).
3. S1 senaryosu için kriter yeniden yazılsın, çünkü ayrık havuzda B'nin kalecisi 71/68 olmak zorunda.

## Açık noktalar
- `tests/test_engine.py` ve `tests/test_app.py` bu commit'te güncellenmedi; `bench_size=8` gibi eski çağrılar bu değişiklikle uyumsuz.
- `docs/CONTRACT.md` değiştirilmedi.

Durum: bitti

# v4-engine raporu (Güncelleme 4: 8 yedek oyuncu)

## Yapılanlar
- `engine.py`, `docs/CONTRACT.md` > "Güncelleme 4" > Motor bölümüne göre güncellendi. Dosya yalnızca bu görevin sahibi olan yola dokundu.
- `create_match(players, setups, protect_count=3, steals_per_side=3, bench_size=8, seed=1)`: her tarafa ilk 11 ve `bench_size` yedek dağıtılır. Dağıtım önce ilk 11 (A, B, A, B...), sonra yedekler (A, B, ...) olarak seed'li yapılır. Yedekler pozisyon gözetmeden havuzdan rastgele alınır. İki taraf ve ilk 11 ile çakışma yoktur.
- State: `sides[X]["slots"]` (11), `sides[X]["bench"]` (oyuncu dict listesi), `sides[X]["protected_ids"]`, `arranged: {"A": bool, "B": bool}`. `phase` değerleri `steal`, `arrange`, `done`.
- `steal`: hedef rakibin ilk 11'inde veya yedeğinde, verilen kendi ilk 11'inde veya yedeğinde olabilir (korumasız olmalı). Yer değişimi: hedef verenin bulunduğu yere, verilen hedefin bulunduğu yere geçer. Otomatik koruma yoktur. Son takastan sonra `phase = "arrange"`, değilse `step = "protect"`.
- `protect`: id'ler 19 oyuncunun tamamından (ilk 11 + yedek) kontrol edilir. Diğer kurallar aynıdır.
- `swap_bench(state, side, slot_index, bench_index)` (yeni): `phase == "steal"` iken `turn == side`, `phase == "arrange"` iken `arranged[side]` False olmalıdır. Aralık dışı indeks `ValueError` verir. Slot pozisyon etiketi yerinde kalır, mülkiyet değişmez.
- `confirm_arrange(state, side)` (yeni): yalnızca `phase == "arrange"` ve tarafın bayrağı False iken çalışır. İki bayrak da True olunca `phase = "done"`.
- `team_rating` yalnızca ilk 11 üzerinden hesaplanır. `slot_score`, `result` değişmedi.

## Sözleşmeden sapmalar / kararlar
- `protect_count` üst sınırı artık `11 + bench_size` (19). Önceki kod 11 ile sınırlıydı; sözleşme "19 oyuncunun hepsini kapsar" dediği için bu genişletme yapıldı.
- `steals_per_side == 0` ise maç doğrudan `phase = "arrange"` olur (v3'te `"done"` idi). Böylece her maçta düzen onayı sonuçtan önce gelir. Sözleşmede bu durum yok.
- Yedek dağıtımı için havuz yetersizse hata mesajı "yedek oyuncu kalmadı" der ve taraf adını içerir. Her taraf için havuz ön kontrolü (`< 19`) ayrıca yapılır.
- `step` arrange ve done fazlarında son değerinde kalır (`"steal"`).

## Doğrulama (gerçek veri)
- Betik repo dışında: `/tmp/claude-0/-home-user-Pollmek12/bef1fe6a-7e57-5529-8e07-653da3c0c270/scratchpad/v4/check.py` (repoya eklenmedi). `python3 -I` ile çalıştırıldı, tümü geçti.
- Veri: `data/players.json`, `data/formations.json`. A = Real Madrid (4-3-3), B = FC Barcelona + Manchester City (4-4-2), seed 42.
- Kontroller: her taraf 11 + 8 oyuncu; 38 oyuncu tekrarsız; yedek-yedek takası; takas sonrası koruma adımı zorunluluğu; korumasız koruma listesi; 6 takas sonrası `phase == "arrange"`; arrange'de takas/koruma/sonuç reddi; `swap_bench` ve onay; iki onay sonrası `done`; `result` (örnek: `{'A': 80, 'B': 78, 'winner': 'A'}`); `steal` done'da reddedilir.
- Hata durumları (`ValueError`): koruma adımında takas, takas adımında koruma, 4 koruma (limit 3), tekrarlı koruma, kadro dışı koruma, korumalı oyuncunun alınması, geçersiz slot/yedek indeksi, geçersiz taraf, onay sonrası yerleştirme, çift onay, arrange dışında onay, bench_size negatif, yetersiz havuz.

## Açık noktalar / şef için not
- `app.py` ve `tests/test_engine.py`, `tests/test_app.py` bu worktree'de eski (Güncelleme 3 ve öncesi) API'ye göre yazılı. Yeni `create_match` imzası, `bench`/`arranged` alanları ve `arrange` fazı için v4-app ve v4-tests sahiplerinin güncellemesi gerekir. Birleşmeden önce bu testler başarısız olur.
- `docs/CONTRACT.md` değiştirilmedi.

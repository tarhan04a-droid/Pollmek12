Durum: bitti

# st-engine raporu

## Yapılan
- `engine.py` yazıldı (saf Python, yalnızca `copy` ve `random`). Altı fonksiyon sözleşmeye uygun: `create_match`, `protect`, `steal`, `slot_score`, `team_rating`, `result`.
- Girdi değiştirilmez (`copy.deepcopy`), hata `ValueError` ile fırlatılır. Dağıtım `random.Random(seed)` ile yapılır, aynı seed ve aynı hamleler aynı sonucu verir.
- `src/engine.js` kopyalanmadı, kurallar Python'a uyarlandı. Doğrulamalar (kategori, formasyon, protect_count, steals_per_side, havuz yetersizliği) JS sürümüyle aynı.

## Sözleşmeden tek sapma
- Sözleşmede state'te `log` yok, bu yüzden "bu taraf zaten korudu mu" bilgisi için state'e `"protected": {"A": bool, "B": bool}` anahtarı eklendi. Diğer anahtarlar sözleşmedeki gibi: `phase`, `sides`, `turn`, `steals_left`, `protect_count`. Uygulama (`app.py`) bu anahtarı okumak zorunda değil; ama state'i serileştirip karşılaştırıyorsa farkın farkında olsun.
- Her iki taraf korumayı bitirdiğinde `steals_per_side == 0` ise faz doğrudan `done` olur (JS sürümündeki davranış).

## Uçtan uca deneme (gerçek veri)
Betik repoya eklenmedi, scratchpad'de çalıştırıldı. Veri: `data/players.json` (Real Madrid, FC Barcelona, Manchester City, havuz 86 oyuncu), formasyon: `data/formations.json` ilk kayıt (4-3-3), seed 42.
- create -> A ve B protect (3'er) -> 6 steal -> result: `{'A': 77, 'B': 80, 'winner': 'B'}`. Hatasız.
- Kontroller geçti: iki tarafta aynı oyuncu yok; aynı tarafın ikinci kez korumaya çalışması reddedildi; aynı seed iki kez çalıştırılınca aynı sonuç; girdi state'i sonuç hesabından sonra değişmedi; takas fazı dışında steal, faz dışında result, boş kategori hata verdi.

## Dosyalar
- Değişen: `engine.py` (yeni)
- Rapor: `reports/st-engine.md`
- Dokunulmadı: `data/**`, `src/**`, `docs/**`, `tasks/**`, `WORKFLOW.md`

# v5-engine — 4 yedek ve kaliteye duyarlı dağıtım
Rapor: `reports/v5-engine.md`
`docs/CONTRACT.md` > "Güncelleme 5" bölümüne göre `engine.py`'yi güncelle (bench_size=4, quality_window). Gerçek veriyle dene: havuz Real Madrid + Gençlerbirliği, 4-3-3, 200 farklı seed: kaleci slotuna hiçbir zaman 71 veya 68 puanlı Gençlerbirliği kalecisi gelmesin (yalnız Courtois 90 / Lunin 80); iki tarafta çakışma yok; determinizm; quality_window=None eski davranış.
Sahip: `engine.py`.

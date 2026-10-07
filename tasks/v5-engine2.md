# v5-engine2 — kalite penceresini düzelt
Rapor: `reports/v5-engine2.md`
`docs/CONTRACT.md` > "Güncelleme 5 > Kurallar" bölümündeki (güncellenmiş) kalite penceresi kuralına göre `engine.py`'yi düzelt: pencere havuzun BAŞLANGIÇTAKİ en iyisine göre, fallback kademeli (kalan en iyiye göre pencere, o da boşsa kalan herkes). Gerçek veriyle doğrula: havuz Real Madrid + Gençlerbirliği, 4-3-3, her iki tarafın kategorisi aynı (ortak havuz) ve ayrıca yalnız A için tek havuz; 300 farklı seed: kaleci slotuna HİÇBİR ZAMAN 71 veya 68 puanlı Gençlerbirliği kalecisi gelmesin (A ve B için ayrı ayrı say, sonuçları rapora yaz); iki tarafta çakışma yok; determinizm; quality_window=None eski davranış; tıkanma yok (havuz 15+15 oyuncuya yetmiyorsa ValueError mantığı aynı).
Sahip: `engine.py`.

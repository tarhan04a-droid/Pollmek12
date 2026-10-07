# v6-engine — 8 yedek + 4 rezerv
Rapor: `reports/v6-engine.md`
`docs/CONTRACT.md` > "Güncelleme 6 > Motor" bölümüne göre `engine.py`'yi güncelle (reserve_size, reserves, team_rating 19 oyuncu, steal/protect 23 oyuncu, swap_reserve). Gerçek veriyle dene: havuz Real Madrid + FC Barcelona + Manchester City (iki tarafta farklı kategori de), 11+8+4 oyuncu, çakışma yok, kaleci kalite penceresi hâlâ çalışıyor, team_rating yalnızca ilk 11+8 yedeği sayıyor (rezervi değiştirince puan değişmez, yedeği değiştirince değişir), takas rezerv/yedek/ilk11 karışık, swap_reserve doğru ve hata durumları, 6 takas sonrası arrange -> done. Havuz 23 oyuncuya yetmiyorsa ValueError.
Sahip: `engine.py`.

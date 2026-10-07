# v2-engine — Python motoru güncellemesi
Rapor: `reports/v2-engine.md`
`docs/CONTRACT.md` > "Güncelleme 2 > Motor" bölümüne göre `engine.py`'yi güncelle (yeni `create_match` imzası, kategori sayısı doğrulaması, iki havuzdan çakışmasız dağıtım, `state["setups"]`). Gerçek veriyle dene: A = Real Madrid + Brezilya (nation) 4-3-3, B = Premier League + Fransa, 4-4-2; 6 takas; ayrıca iki havuzun kesiştiği durumda aynı oyuncunun iki tarafta olmadığını doğrula.
Sahip: `engine.py`.

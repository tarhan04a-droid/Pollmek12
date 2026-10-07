# v2-tests — Python testleri güncellemesi
Rapor: `reports/v2-tests.md`
`docs/CONTRACT.md` > "Güncelleme 2" bölümüne göre `tests/test_engine.py` ve `tests/test_app.py`'yi güncelle: yeni `create_match` imzası, 0 ve 5 kategori hatası (mesajda taraf), farklı formasyonlu iki taraf (11 slot, kendi dizilimleri), iki havuz kesişince oyuncunun tek tarafta olması, determinizm, takas/koruma kuralları aynen; app testi iki adımlı kurulum akışını (A seç -> B'ye geç -> B seç -> başlat) ve 5. kategorinin engellenmesini dener. `engine.py`/`app.py` henüz sende olmayabilir: sözleşmeye göre yaz. Çalıştırma: `python3 -m unittest discover -s tests -p "test_*.py"`.
Sahip: `tests/test_engine.py`, `tests/test_app.py`.

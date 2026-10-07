# v3-tests — Python testleri
Rapor: `reports/v3-tests.md`
`docs/CONTRACT.md` > "Güncelleme 3" bölümüne göre `tests/test_engine.py` ve `tests/test_app.py`'yi güncelle: başlangıçta korumasız ve phase "steal"/step "steal"; steal sonrası step "protect", otomatik koruma yok; protect (en fazla 3, kendi kadro, tekrarsız, yanlış adım hatası, önceki korumayı değiştirir, boş liste serbest); korumalı hedef/give hatası; son takastan sonra protect adımı olmadan phase "done"; yeni alınan oyuncunun korunabilmesi; determinizm. App testi: kurulum -> kadro -> "Takas turlarını başlat" -> takas -> koruma -> ... -> sonuç. `engine.py`/`app.py` henüz sende olmayabilir: sözleşmeye göre yaz. Çalıştırma: `python3 -m unittest discover -s tests -p "test_*.py"`.
Sahip: `tests/test_engine.py`, `tests/test_app.py`.

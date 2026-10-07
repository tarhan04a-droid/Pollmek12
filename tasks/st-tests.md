# İşçi st-tests — Python testleri
Rapor: `reports/st-tests.md`
## Görev
`docs/CONTRACT.md` içindeki "Streamlit sürümü > Motor" bölümüne göre `tests/test_engine.py` (standart `unittest`, ek paket yok): dağıtım (iki tarafa aynı oyuncu yok, havuz yetersizse ValueError), protect doğrulamaları, steal kuralları (korumalı hedef, korumalı give, yanlış sıra, swap doğru slotlara, alınan oyuncu korumalı, phase geçişleri), slot_score cezası, determinizm; ve gerçek veriyle uçtan uca 6 takas. `engine.py` henüz sende olmayabilir: sözleşmeye göre yaz. İsteğe bağlı `tests/test_app.py`: streamlit kuruluysa `AppTest` ile açılış (`pytest` yoksa `unittest`, yoksa atla). Çalıştırma: `python3 -m unittest discover -s tests -p "test_*.py"`.
## Sahip olunan yollar
- tests/test_engine.py, tests/test_app.py
## Bitti koşulu
- engine.py birleşince testler yeşil. Rapor yaz.

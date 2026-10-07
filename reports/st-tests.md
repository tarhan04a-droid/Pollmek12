Durum: takıldı
Özet: tests/test_engine.py ve tests/test_app.py yazıldı; engine.py bu dalda yok, bu yüzden gerçek motorla koşulamadı. Sözleşmeye uyan geçici bir motorla (repo dışında) 35 testten 34'ü geçti, 1'i (app.py yok) atlandı.

## Yapılanlar
- tests/test_engine.py (unittest, ek paket yok):
  - Dağıtım: iki tarafta aynı oyuncu yok, slot sırası formasyonla aynı, alt pozisyon yedeği, havuz yetersiz ve kategori boş -> ValueError, determinizm, girdilerin değişmemesi.
  - protect: yanlış sayı, başka tarafın oyuncusu, faz geçişi yalnızca iki taraf korudukta.
  - steal: faz ve sıra kontrolü, korumalı hedef, korumalı give, kendi kadrosundan hedef, rakip kadrosundan give, swap'ın doğru slotlara yapılması, alınan oyuncunun korumalı olması ve geri alınamaması, sıra/stealsLeft güncellemesi, 6 takas sonunda phase "done" ve sonrasında ValueError.
  - slot_score: pos, alt, cezalı (rating-10) ve sıfır tabanı.
  - team_rating ve result: yuvarlanmış ortalama, done dışında ValueError, kazanan mantığı.
  - Gerçek veriyle uçtan uca: data/players.json + formations.json (4-3-3), Premier League kategorisi, 3 koruma + 6 takas; her takasta iki kadronun 11 kalması ve tam 2 oyuncu değişimi kontrol edilir.
- tests/test_app.py: streamlit ve app.py yoksa atlanır; varsa AppTest ile açılışta istisna olmadığını kontrol eder.
- Çalıştırma: `python3 -m unittest discover -s tests -p "test_*.py"` (repo kökünden; engine.py kökte olmalı).

## Doğrulama
- Geçici motor (repo dışında, scratchpad) ile: `Ran 35 tests ... OK (skipped=1)`.
- Repo'da engine.py yok: gerçek koşum ImportError verir (beklenen).

## Açık nokta / sonraki adım
- engine.py birleşince yukarıdaki komut yeşil olmalı. Yeşil olmazsa fark, sözleşmeyle motor arasındaki yorumdan kaynaklanıyor olabilir; testler sözleşmeye göre yazıldı.
- Görev "bitti" koşulu (engine.py birleşince yeşil) henüz sağlanmadığı için durum "takıldı".

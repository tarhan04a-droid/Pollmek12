Durum: bitti
# v5-engine2 raporu: kalite penceresi başlangıç en iyisine göre

## Ne değişti (engine.py)
- Eski kod pencereyi aday kümesinin KALAN en iyisine göre ölçüyordu. En iyi oyuncu alındıkça pencere kayıyor ve zayıf kaleci (71/68) ilk 11'e girebiliyordu.
- Yeni kod, CONTRACT "Güncelleme 5 > Kurallar" maddesine göre:
  - `_start_bests(pool)`: havuzun başlangıç en iyilerini hesaplar (pozisyon ve alt etiketi bazında). Her taraf kendi havuzuyla hesaplanır; ortak havuzda iki taraf aynı değeri alır.
  - İlk 11 slotu: aday kümesi önce `pos == slot`, yoksa `alt` içinde slot olan oyunculardır (eskisi gibi). Pencere, kümenin BAŞLANGIÇ en iyisine göre uygulanır. Kümede kullanılmamış oyuncu pencerede kalmazsa pencere kümenin KALAN en iyisine göre uygulanır (geri çekilme).
  - Yedek: her aday kendi birincil pozisyonunun BAŞLANGIÇ en iyisine göre değerlendirilir; pozisyon fark etmez. Pencerede kimse kalmazsa pencere her pozisyonun KALAN en iyisine göre uygulanır.
- Değişmeyenler: dönüşümlü dağıtım, seed'li `random.Random`, çakışma kontrolü, en fazla 50 yeniden deneme, `ValueError` yolları, takas/koruma/yerleştirme/arrange kodu.
- `quality_window=None` yolu, eski davranışla aynı rng çağrılarını yapar ve aynı sonucu verir.
- Commit: `3afd9e3` (engine.py). Tests ve app dosyalarına dokunulmadı.

## Doğrulama (gerçek veri: data/players.json, 4-3-3, seed 1..300, her senaryo)
Kaleci kontrolü: ilk 11'deki GK slotuna Gençlerbirliği'nin 71 (İrfan Can Eğribayat) veya 68 (Gökhan Akkan) puanlı kalecisi gelen seed sayısı.

| Senaryo | Eski motor (HEAD) | Yeni motor |
|---|---|---|
| S1 ortak havuz: A ve B = Real Madrid + Gençlerbirliği | A=0, B=80 | A=0, B=0 |
| S2 A = RM+GB (tek havuz), B = Brezilya | A=0, B=0 | A=0, B=0 |
| S3 A = yalnız Gençlerbirliği, B = yalnız RM | A=300, B=0 | A=300, B=0 |

- S3 beklenen sonuçtur: A'nın havuzunda başka kaleci yok, 71/68 o havuzun başlangıç en iyisi. Kural bunu engellemez; ihlal değildir.
- Çakışma (aynı oyuncu iki yerde): 0 seed, tüm senaryolarda.
- Tıkanma/`ValueError`: 0 seed, tüm senaryolarda.
- Determinizm (aynı seed, aynı sonuç): 300/300 her senaryoda, sapma 0.
- `quality_window=None`: eski motorla birebir aynı, 150/150 (3 senaryo x 50 seed).
- Ortak kural örneği (CONTRACT): RM+GB havuzunda kaleciler 90, 80, 71, 68. Yeni kodla S1'de GK slotu: A = 90 (153 seed) veya 80 (147 seed); B = 80 (153) veya 90 (147). Başka değer yok.

## Birim testleri
- `python3 -m unittest discover -s tests -p "test_*.py"`: 92 test, 5 FAIL + 5 ERROR.
- Aynı 10 test, değişiklikten ÖNCE de başarısızdı (taban çizgisi aynı). Sebep: testler v4 dönemi varsayımlarını kullanıyor (yedek 8 bekliyor, CONTRACT Güncelleme 5 yedeği 4 yapıyor). Testler `tests/` altında olduğu için bu görevde düzeltilmedi; ayrı bir `tests` işi gerekir.

## Açık noktalar / yorum
- Bench geri çekilmesinde "kalan en iyi" her pozisyon için ayrı alındı (bench kuralı zaten pozisyon bazlı). CONTRACT tek bir "kalan en iyi" demiyor; bu bir yorumdur. Farklı okunursa `_pick_bench` içinde tek satır değişir.
- Slot alt-kademesinde (pos'u eşleşen kalmadığında) başlangıç en iyisi, alt etiketiyle eşleşen ve pos'u o etiket olmayan başlangıç oyuncuları üzerinden alındı.
- `ValueError` kodu değişmedi ve ayrıca test edilmedi (havuz 15+15'e yetmediğinde mevcut mantık korunuyor).

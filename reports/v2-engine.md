Durum: bitti

# v2-engine raporu (Güncelleme 2, Python motoru)

## Yapılan
- `engine.py` `docs/CONTRACT.md` > "Güncelleme 2 > Motor" bölümüne göre güncellendi.
- Yeni imza: `create_match(players, setups, protect_count=3, steals_per_side=3, seed=1)`. `setups = {"A": {"categories", "formation"}, "B": {...}}`.
- Doğrulama (`ValueError`, mesajda taraf adı var): kategori sayısı 1..4 dışındaysa; formasyonda 11 slot yoksa; havuz boşsa; dağıtım tıkanırsa.
- Havuz: her taraf kendi kategorilerinden kurulur. İki havuz kesişebilir; `used` kümesi iki taraf için ortak olduğundan aynı oyuncu iki tarafta bulunmaz.
- Dağıtım sırası A slot1, B slot1, A slot2, ... Her slot için önce `pos == slot`, yoksa `alt` içinde slot olan. Tıkanırsa seed'den türetilen `random.Random(f"{seed}:{k}")` ile en fazla 50 deneme; hâlâ olmazsa `ValueError`.
- State'e `setups` eklendi: `{"A": {"categories": [...], "formation_id": str}, "B": {...}}`. Diğer alanlar (`phase`, `sides`, `turn`, `steals_left`, `protect_count`, `protected`) öncekiyle aynı.
- `protect`, `steal`, `slot_score`, `team_rating`, `result` imzası ve davranışı değişmedi.

## Doğrulama (gerçek veri, scratchpad betiği, repoya eklenmedi)
- Senaryo: A = Real Madrid + Brazil (nation), 4-3-3; B = Premier League + France (nation), 4-4-2; seed 42; 3+3 koruma, 6 takas. Hatasız tamamlandı. Sonuç: `{'A': 73, 'B': 71, 'winner': 'A'}`. Her iki tarafın slot dizilimi kendi formasyonuna uygun (A 4-3-3, B 4-4-2).
- Aynı seed ile iki kez create: state birebir aynı (deterministik).
- Kesişen havuz: A = Brazil + France, B = France (4-3-3 vs 4-4-2), seed 7: 22 oyuncunun tamamı benzersiz; 6 takas ile tamamlandı.
- Kesişen küçük havuz: A ve B ikisi de Real Madrid (28 oyuncu, 22 slot): başarılı, benzersiz.
- Hata durumları: 5 kategori (A) -> "A tarafı: 1-4 kategori seçilmeli"; 0 kategori (B) -> "B tarafı..."; boş havuz -> "B tarafı: seçilen kategorilerde oyuncu yok"; 15 oyunculuk sentetik havuz -> "Havuz yetersiz: A tarafının \"GK\" slotu...".
- Takas kuralları: korumalı oyuncu verilemedi, korumalı oyuncu alınamadı, sıra dışında takas reddedildi.

## Sözleşmeden sapmalar / notlar
- Formasyon doğrulaması tam 11 slot istiyor (sözleşme "tam 11 slot" diyor).
- Dağıtım tıkanma kontrolü: her denemede havuz seed'li karıştırılır, sonra ilk uygun oyuncu seçilir. Sözleşmedeki "rastgele" bu karıştırmayla sağlanır.
- `tests/test_engine.py` ve `app.py` eski imzayı (`create_match(players, categories, formation)`) kullanıyor. Bu dosyalar bu görevin sahibinde değil (v2-tests / v2-app); bu işçi dokunmadı. Onlar güncellenmeden testler ve uygulama eski imzayla çalışmaz.

## Dosyalar
- Değişen: `engine.py` (commit 8586b8a).
- Rapor: `reports/v2-engine.md`.

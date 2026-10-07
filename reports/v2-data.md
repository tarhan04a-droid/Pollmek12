Durum: bitti

# v2-data raporu (Güncelleme 2: formasyonlar)

## Yapılanlar
- `data/formations.json`: 4 mevcut formasyona 8 yenisi eklendi (toplam 12): 4-1-4-1, 4-5-1, 5-3-2, 3-4-3, 4-3-2-1, 4-4-1-1, 5-4-1, 3-4-2-1. Her biri tam 11 slot.
- `data/build_data.py`: yalnızca `FORMATIONS` listesi aynı 12 formasyonla güncellendi. Betik çalıştırıldı; slot kontrolü geçti.
- `players.json` ve `categories.json`: betik yeniden çalıştırıldıktan sonra baytı baytına öncekiyle aynı (md5 ve cmp ile doğrulandı).
- `docs/data-notes.md`: formasyon tablosu ve slot başına havuz sayıları eklendi.

## Slot havuzları
Tüm slot etiketleri için havuz (pos veya alt) >= 30. En küçük havuz GK (961). Ayrıntı: `docs/data-notes.md`.

## Notlar
- Veride LWB, RWB, CF etiketleri yok; wing-back görevleri LB/RB veya LM/RM ile verildi.
- 4-3-2-1 ve 3-4-2-1 iki CAM slotu içeriyor (EA'da LCAM/RCAM ayrımı veride yok).

## Commitler
- fb34d7c data: 8 yeni formasyon
- 54e2749 docs: formasyon listesi ve slot başına havuz sayıları
- 25b1424 docs: havuz notu netleştirildi

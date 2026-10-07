# Veri notları

Üretim: `python3 data/build_data.py` (girdi `data/raw/players.csv`, EA FC 27, snapshot 2026-09-12).

## Filtre ve boyut
- Kaynak: 19.789 satır. `gender == "Men's Football"` (17.849) ve `overall_rating >= 65` filtresinden sonra **10.852 oyuncu** kalır.
- Eşik düşürülmedi/yükseltilmedi; `players.json` yaklaşık **2,1 MB** (3 MB sınırının altında).
- `players.json` 10.852 kayıt, `categories.json` 18 KB, `formations.json` 329 bayt.

## Kategoriler (en az 15 oyunculu)
- club: 404 değer
- league: 47 değer
- nation: 76 değer

Boş `club`/`league`/`nation` değeri yok (erkek alt kümede). Kategoriler sayıya göre azalan sıralı.

## Pozisyon dağılımı (birincil `pos`, 10.852 oyuncu)
| pos | oyuncu | pos veya alt (slot havuzu) |
|-----|-------:|---------------------------:|
| CB  | 2.095 | 2.668 |
| ST  | 1.444 | 2.090 |
| CM  | 1.248 | 3.358 |
| CDM | 978 | 2.682 |
| GK  | 961 | 961 |
| RB  | 822 | 1.353 |
| LB  | 783 | 1.336 |
| CAM | 690 | 2.281 |
| LM  | 668 | 2.455 |
| RM  | 619 | 2.390 |
| LW  | 283 | 1.657 |
| RW  | 261 | 1.584 |

Veride LWB, RWB, CF gibi etiketler hiç yok.

## Formasyonlar
Tümü 11 slot, tüm slot etiketleri için havuz >= 30 (build betiği doğrular):
- 4-3-3: GK, LB, CB, CB, RB, CM, CM, CM, LW, ST, RW (sözleşmedeki örnek)
- 4-4-2: GK, LB, CB, CB, RB, LM, CM, CM, RM, ST, ST
- 3-5-2: GK, CB, CB, CB, LM, CDM, CAM, CM, RM, ST, ST
- 4-2-3-1: GK, LB, CB, CB, RB, CDM, CDM, LW, CAM, RW, ST

3-5-2 ve 4-2-3-1 slot seçimleri bu veriye göre yapıldı; EA etiketine uygun ama sözleşmede örnek yoktu.

## Bilinen sorunlar / dikkat
- **Aynı görünen ad:** 79 çift oyuncu aynı `name` değerini taşıyor. Ayırt etmek için `id` kullanılmalı; UI'da ad yanına kulüp veya ulusal takım eklenmesi önerilir.
- **Ad kaynağı:** 1.674 oyuncuda `common_name` dolu (kullanıldı); diğerlerinde `first_name last_name` birleştirildi.
- **GK havuzu:** Kaleciler yalnızca `pos == GK` olarak gelir; `alt` içinde GK yok. Kaleci slotu dışında kaleci alan oyuncu bulunmaz, bu beklenen durum.
- **Boy/kilo:** Kaynakta boş (EA henüz yayımlamadı); `players.json`'a alınmadı.
- **Tarih:** `data/raw/README.md` snapshot tarihini 2026-09-12, dışa aktarımı 2026-09-14 olarak veriyor; fark bilgi amaçlı.
- **Alt pozisyonlar:** `alt` boşluğa göre bölündü; boş ise `[]`.
- **Lisans:** Veri EA'ya aittir; README'deki "kişisel/eğitim amaçlı" kaydına göre kullanılır.

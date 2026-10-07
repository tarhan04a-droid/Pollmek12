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
12 formasyon (11 slot her biri). Tüm slot etiketleri için havuz (`pos` veya `alt`) >= 30; build betiği doğrular. En küçük havuz GK (961).

| id | slotlar |
|----|---------|
| 4-3-3 | GK, LB, CB, CB, RB, CM, CM, CM, LW, ST, RW |
| 4-4-2 | GK, LB, CB, CB, RB, LM, CM, CM, RM, ST, ST |
| 3-5-2 | GK, CB, CB, CB, LM, CDM, CAM, CM, RM, ST, ST |
| 4-2-3-1 | GK, LB, CB, CB, RB, CDM, CDM, LW, CAM, RW, ST |
| 4-1-4-1 | GK, LB, CB, CB, RB, CDM, LM, CM, CM, RM, ST |
| 4-5-1 | GK, LB, CB, CB, RB, LM, CM, CAM, CM, RM, ST |
| 5-3-2 | GK, LB, CB, CB, CB, RB, CM, CM, CM, ST, ST |
| 3-4-3 | GK, CB, CB, CB, LM, CM, CM, RM, LW, ST, RW |
| 4-3-2-1 | GK, LB, CB, CB, RB, CM, CM, CM, CAM, CAM, ST |
| 4-4-1-1 | GK, LB, CB, CB, RB, LM, CM, CM, RM, CAM, ST |
| 5-4-1 | GK, LB, CB, CB, CB, RB, LM, CM, CM, RM, ST |
| 3-4-2-1 | GK, CB, CB, CB, LM, CM, CM, RM, CAM, CAM, ST |

Slot başına havuz (`pos == etiket` veya `etiket ∈ alt`, tüm 10.852 oyuncu üzerinden):

| slot | havuz |
|------|------:|
| GK | 961 |
| LB | 1.336 |
| RB | 1.353 |
| CB | 2.668 |
| CDM | 2.682 |
| CM | 3.358 |
| LM | 2.455 |
| RM | 2.390 |
| CAM | 2.281 |
| LW | 1.657 |
| RW | 1.584 |
| ST | 2.090 |

Notlar:
- Wing-back (LWB/RWB) ve CF etiketleri veride yok; 5-3-2, 5-4-1 ve 3-4-3 kanat görevleri LB/RB veya LM/RM ile verildi.
- 4-3-2-1 ve 3-4-2-1'deki iki "CAM" slotu aynı etiketi taşır (LCAM/RCAM ayrımı EA etiketlerinde yok); havuz iki slot için de yeterli.
- Ortak tekrar: havuz slot sayısına göre değil, oyuncu başına tek kullanım kuralına göre dağıtılır; havuz boyutu yalnızca yeterlilik kontrolüdür.

## Bilinen sorunlar / dikkat
- **Aynı görünen ad:** 79 çift oyuncu aynı `name` değerini taşıyor. Ayırt etmek için `id` kullanılmalı; UI'da ad yanına kulüp veya ulusal takım eklenmesi önerilir.
- **Ad kaynağı:** 1.674 oyuncuda `common_name` dolu (kullanıldı); diğerlerinde `first_name last_name` birleştirildi.
- **GK havuzu:** Kaleciler yalnızca `pos == GK` olarak gelir; `alt` içinde GK yok. Kaleci slotu dışında kaleci alan oyuncu bulunmaz, bu beklenen durum.
- **Boy/kilo:** Kaynakta boş (EA henüz yayımlamadı); `players.json`'a alınmadı.
- **Tarih:** `data/raw/README.md` snapshot tarihini 2026-09-12, dışa aktarımı 2026-09-14 olarak veriyor; fark bilgi amaçlı.
- **Alt pozisyonlar:** `alt` boşluğa göre bölündü; boş ise `[]`.
- **Lisans:** Veri EA'ya aittir; README'deki "kişisel/eğitim amaçlı" kaydına göre kullanılır.

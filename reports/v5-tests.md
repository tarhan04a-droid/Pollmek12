Durum: bitti

# v5-tests raporu (Güncelleme 5: 4 yedek, kalite penceresi)

## Yapılanlar
- `tests/test_engine.py`: 8 yedek varsayımları 4'e çevrildi (BENCH_SIZE=4, SQUAD_SIZE=15). Takas/koruma/arrange/determinizm testlerindeki yedek indeksleri 0..3 aralığına çekildi. Havuz sınırı testleri 14 (hata) ve 15 (yeterli) oyuncuya göre yazıldı.
- Yeni `assert_quality_window` yardımcısı (sıra bağımsız kontrol): ilk 11 slotu için seçilen oyuncu, aynı aday kümesinde (önce pos, yoksa alt) kalan en iyi oyuncunun en fazla `window` (10) geride olmalı; yedek için birincil pozisyonundaki kalan en iyi oyuncuya göre aynı kontrol.
- Yeni `QualityWindowTests` (sentetik havuz, 50 seed): kaleci slotuna 71 ve 68 asla gelmez (90/80 varken); `quality_window=None` eski davranışta 71/68 gelebilir; 50 seed'de iki taraf için pencere kontrolü; `quality_window=0` ile 20 seed; varsayılan = 10; determinizm.
- Yeni `RealClubQualityTests` (gerçek veri): Real Madrid (A, 4-3-3) ve Gençlerbirliği (B, 4-2-3-1), 100 seed; 15'er oyuncu, çakışma yok, pencere kontrolü.
- `tests/test_app.py`: BENCH_SIZE=4, SQUAD_SIZE=15; "eight/nineteen" test adları 4/15 oldu; yedek etiketi '[yedek]' kontrolü korundu.

## Doğrulama
- Repo motoru (`engine.py`, `app.py`) henüz Güncelleme 5'e geçmediği için repo üzerinde testler beklenen şekilde kırmızı (varsayılan yedek 8, `quality_window` parametresi yok).
- Testlerin kendisi, repo dışında (scratchpad kopyası) referans bir Güncelleme 5 uygulamasıyla doğrulandı: motorda varsayılan bench_size=4, quality_window=10 ile aday filtresi ve app'te BENCH_SIZE=4. Sonuç: `test_engine.py` 99/99 OK, `test_app.py` 16/16 OK. Repo dosyalarına bu kopyadan hiçbir şey yazılmadı.

## Bulgu (motor ekibi için)
- Gerçek veride Real Madrid (4-3-3) + Gençlerbirliği (4-4-2) eşleşmesi 100 seed'in tamamında "B tarafının ST slotu için uygun oyuncu kalmadı" ile tıkanıyor. Gençlerbirliği havuzunda yalnızca 1 ST var; ikinci ST slotu alt pozisyonla doldurulamıyor (greedy pos-önce dağıtım). Pencere yokken de (quality_window=None) aynı tıkanma görüldü, yani bu bir pencere hatası değil, dağıtım sırası/ havuz sorunu. Testte B için 4-2-3-1 seçildi (100 seed'de tıkanma yok).
- Bu eşleşme pencere kuralıyla da tıkanabilir; motor ekibi dağıtım sırasını ya da yeniden deneme stratejisini gözden geçirmeli.

## Notlar
- Sözleşmedeki "pencere dışı oyuncu yoksa istisna" maddesi ayrıca test edilmedi: pencere dışı seçim, kalan uygun aday yokken zaten kontrolü geçer.
- `quality_window=None` testi kaleci slotu üzerinden yapıldı (50 seed'de 71/68 gelmesi pratikte kesin).

## Commit
- `41fe0cb` test_engine (Güncelleme 5)
- `ac41091` test_app (4 yedek)

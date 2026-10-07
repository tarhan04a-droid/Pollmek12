Durum: bitti

# v5-app raporu (Streamlit, 4 yedek, Güncelleme 5)

## Yapılanlar
- `app.py`: `BENCH_SIZE` 8'den 4'e indirildi. `create_match(..., bench_size=BENCH_SIZE)` çağrısı zaten vardı, değer artık 4 geçiyor.
- `roster()` docstring'indeki sabit "19 oyuncu" ifadesi "tüm oyuncular" olarak genelleştirildi. Kodda başka sabit "8" veya "19" kalmadı (`grep` ile doğrulandı).
- Kadro ekranı, takas listeleri, koruma çoklu seçimi, kadro düzeni ve sonuç ekranı yedek listesini state'ten okuyor; bu kısımlarda değişiklik gerekmedi.
- Commit: `a92b46c` (yalnızca `app.py`). Bu rapor ayrı bir commit ile eklendi.

## Doğrulama
- `python3 -m py_compile app.py` geçti.
- `streamlit.testing.v1.AppTest` (streamlit 1.65.0) ile tam akış çalıştırıldı (script repo dışında: `/tmp/claude-0/-home-user-Pollmek12/bef1fe6a-7e57-5529-8e07-653da3c0c270/scratchpad/apptest_v5.py`):
  - Kurulum: A kulüp, B ülke; formasyonlar varsayılan.
  - Kadro: her iki tarafta 11 ilk oyuncu + 4 yedek; "Yedekler" başlığı görünüyor.
  - Takas: 6 takas turu (A, B, A, B, A, B), her takasta ardından koruma onayı (boş seçimle).
  - `arrange` aşamasında iki taraf da "Düzeni onayla" ile onayladı, `phase == "done"`, hata çıkmadı.
- Repodaki `engine.py` hâlâ v4 sürümü (`quality_window` yok, `bench_size` parametresi var, varsayılan 8). App `bench_size=4`'ü açıkça geçtiği için bu sürümle çalıştı. v5-engine birleşince AppTest bir kez daha koşulmalı.

## Açık noktalar (şef için)
- `tests/test_app.py` (v5-tests) hâlâ `BENCH_SIZE = 8` sabitini kullanıyor (satır 50). Bu dosya v5-tests'in sahipliğinde olduğu için dokunulmadı; yedek sayısı 4'e güncellenmeli.
- Yeni `engine.py` (Güncelleme 5 kalite penceresi) için app tarafında ek bir değişiklik gerekmiyor; `create_match` imzasına `quality_window` geçilmiyor, varsayılan kullanılıyor.

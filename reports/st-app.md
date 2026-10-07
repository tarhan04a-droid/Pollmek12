Durum: bitti

# st-app raporu (Streamlit arayüzü)

## Yapılanlar
- `app.py`: `docs/CONTRACT.md` "Streamlit sürümü > Uygulama" bölümüne göre yazıldı. `engine.py`'yi import eder (`create_match`, `protect`, `steal`, `result`, `team_rating`), motoru kopyalamaz. Veri `@st.cache_data` ile `data/*.json`'dan yüklenir (yol `__file__`'a göre). Durum `st.session_state` içinde (`stage`: setup / squads / play; `state`: engine dict'i). Ekran sırası `state["phase"]` ile yönlenir.
- Ekranlar: kurulum (kategori türü seçimi, türler arası seçim korunur, çoklu seçim arama destekli, havuz sayısı, formasyon varsayılanı ilk formasyon) -> kadrolar (iki kadro yan yana; telefonda Streamlit alt alta dizer) -> koruma (A, sonra B; tam 3 seçim, onay kilitli) -> takas (sıra olan taraf rakipten korumasız oyuncu alır, kendi korumasız oyuncusunu verir; korumalılar etiketli ve listede yok) -> sonuç (iki takım puanı, kazanan, son kadrolar, "Yeni maç").
- `requirements.txt`: `streamlit>=1.36` (sözleşmede "streamlit"; alt sınır, AppTest için 1.36+ yeterli sayıldı, istenirse düz `streamlit` yapılabilir).
- `.streamlit/` oluşturulmadı (gerekli bir ayar yok).

## Doğrulama
- Python 3.13, streamlit 1.65.0 kuruldu.
- `repo`da `engine.py` henüz yok. Test için `/tmp/.../scratchpad/stub/engine.py` adında geçici bir taklit yazıldı (repoya konmadı; sözleşme imzaları, aynı kurallar). `PYTHONPATH` ile verildi.
- `streamlit.testing.v1.AppTest` ile tam akış geçti: kulüp seçimi -> maç başlat -> kadrolar -> koruma A/B -> 6 takas -> sonuç -> yeni maç. Hata (exception) çıkmadı.
- `streamlit run app.py --server.headless true` ile sunucu açıldı, HTTP 200.
- `py_compile` temiz.

## Açık noktalar / şef için not
- Gerçek `engine.py` birleşince `AppTest` akışı tekrar çalıştırılmalı (taklit engine ile test edildi; gerçek engine'in `steal`/`protect` hata mesajları ve `phase` geçişleri farklıysa UI sadece `ValueError` metnini gösterir).
- Engine'in `protect` sonrası `protected_ids` doldurduğu varsayıldı: sıra B'ye geçişi `state["sides"]["A"]["protected_ids"]` boş mu dolu mu bakarak belirleniyor.
- Engine'in state'inde `log` zorunlu değil; UI kullanmıyor.
- Hot-seat: ekranı çevirme uyarısı metin olarak var; cihaz düzeyinde gizleme yok (sözleşme kapsamı dışı).
- Tests (`tests/test_app.py`) bu görevde yazılmadı (st-tests sahibinde).

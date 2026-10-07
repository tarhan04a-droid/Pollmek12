# v6-app — 8 yedek + 4 rezerv
Rapor: `reports/v6-app.md`
`docs/CONTRACT.md` > "Güncelleme 6 > Uygulama" bölümüne göre `app.py`'yi güncelle (BENCH_SIZE=8, RESERVE_SIZE=4, kadro/takas/koruma/yerleştirme/sonuç ekranları). Gerçek `engine.py` yeni imzayla gelecek; yoksa sözleşmeye göre yaz, AppTest ile dene. AppTest notları: `.options` görünen etiketlerdir; 'İlk 11'den oyuncu' / 'Yedekten oyuncu' / 'Rezervden oyuncu' selectbox'ları İNDEKS ister; takas hedefi/verilen id ister (id'leri at.session_state['state'] üzerinden al).
Sahip: `app.py`.

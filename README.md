# Pollmek12 — Rastgele Seçimli Maç (PES tarzı)

İki oyuncu aynı ekranda sırayla oynar. Her oyuncu en fazla 4 kategori (ülke / kulüp / lig) ve kendi formasyonunu seçer; kadrolar kendi havuzlarından rastgele dağıtılır. Ardından takas turları: her sırada rakipten korumasız bir oyuncuyu alıp kendinden birini verirsin, sonra (yeni aldığın dahil) en fazla 3 oyuncunu korursun.

## Çalıştırma
```
pip install -r requirements.txt
streamlit run app.py
```

## Dosyalar
- `app.py` — Streamlit arayüzü, `engine.py` — oyun kuralları (saf Python)
- `data/` — EA FC 27 verisinden üretilen oyuncu, kategori ve formasyon JSON'ları (`data/build_data.py`, ham kaynak `data/raw/`)
- `tests/` — `python3 -m unittest discover -s tests -p "test_*.py"`; veri şeması testi: `node --test tests/data.test.mjs`
- `docs/CONTRACT.md` — kurallar ve işçiler arası sözleşme (JS sürümüne ait ilk bölümler eskidir, güncel kurallar "Güncelleme 2" ve "Güncelleme 3"), `WORKFLOW.md` — çoklu ajan düzeni

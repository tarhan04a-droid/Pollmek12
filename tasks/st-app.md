# İşçi st-app — Streamlit arayüzü
Rapor: `reports/st-app.md`
## Görev
`docs/CONTRACT.md` içindeki "Streamlit sürümü > Uygulama" bölümüne göre `app.py` ve `requirements.txt` yaz. `engine.py` henüz sende olmayabilir: sözleşmedeki imzalara göre yaz; test için `engine.py`'yi geçici bir yerde kendin kısaca taklit edebilirsin ama repoya koyma. Mümkünse `pip install streamlit` yapıp `streamlit.testing.v1.AppTest` ile akışı dene.
## Sahip olunan yollar
- app.py, requirements.txt, .streamlit/**
## Bitti koşulu
- `streamlit run app.py` hatasız açılır; akış baştan sona çalışır (engine.py birleşince). Rapor yaz.

Durum: bitti

# v3-app raporu (Streamlit akışı, Güncelleme 3)

## Yapılanlar
- `app.py`, `docs/CONTRACT.md` "Güncelleme 3 > Uygulama" bölümüne göre güncellendi.
- Kadro ekranındaki buton "Takas turlarını başlat" oldu; ayrı "Koruma aşamasına geç" ve koruma ekranı kaldırıldı (`screen_protect` silindi, `main()` içinde `phase == "protect"` dalı kalktı).
- `screen_steal` sıra sahibine göre iki adım gösterir:
  - Adım 1/2 "Takas" (`screen_steal_step`): rakipten korumasız oyuncu seçilir, kendi korumasız oyuncusuyla değiştirilir; korumalılar listede yok ve "[korumalı]" etiketli. Takas yapılınca `st.session_state.new_id` alınan oyuncuya set edilir.
  - Adım 2/2 "Koruma" (`screen_protect_step`, `state["step"] == "protect"` iken): kendi 11 oyuncusu listelenir, en fazla 3 seçilir (boş onay serbest), mevcut korumalar önceden seçili gelir, yeni alınan oyuncu "[yeni]" etiketli. Onaylanınca `protect` çağrılır ve `new_id` temizlenir.
- Sıra bilgisi ve kalan takas hakkı her iki adımda görünür.
- Son takastan sonra `phase == "done"` olduğu için koruma adımı gösterilmez, doğrudan sonuç ekranına geçilir.
- Koruma widget anahtarı `protect_{taraf}_{steals_left}` (takas anahtarlarıyla aynı mantık); her adım için yeni widget, bu yüzden varsayılan seçim her seferinde mevcut korumadan gelir.
- `reset_match()` içinde `new_id` de temizleniyor.

## Doğrulama
- Repoda bu dalda `engine.py` hâlâ Güncelleme 2 sürümü (`protect` faz kontrolü ve `step` alanı yok); gerçek v3 motor bu görev kapsamında değil (v3-engine sahibi). Bu yüzden test, sözleşmeye göre yazılmış geçici bir motor taklidiyle yapıldı. Taklit yalnızca `/tmp/.../scratchpad` altında; repoya konmadı.
- Uygulama, repodaki `app.py` ve `data/` kopyalanıp taklit `engine.py` ile çalıştırıldı.
- `streamlit.testing.v1.AppTest` (streamlit 1.65.0) ile tam akış geçti: kategori seçimi (A, B) -> maç başlat -> kadrolar -> takas başlat -> 6 takas, 5 koruma adımı (son takastan sonra koruma yok) -> "Sonuç" ekranı. Exception çıkmadı. Koruma adımında "[yeni]" etiketi tam bir oyuncuda göründü.
- `py_compile app.py` temiz.

## Açık noktalar / şef için not
- Gerçek `engine.py` (Güncelleme 3 imzası: `create_match(players, setups, ...)`, `state["step"]`, `steal` sonrası `step="protect"`, `protect` boş listeyi kabul eder) birleşince `AppTest` akışı tekrar çalıştırılmalı. `app.py` sözleşmedeki alan adlarına (`phase`, `step`, `turn`, `steals_left`, `sides[X].protected_ids`, `setups`) bağlı; bu alanlardan biri farklıysa `KeyError` çıkar.
- `tests/test_app.py` bu görevin sahipliğinde değil (v3-tests); güncellenmedi. Mevcut testlerde koruma ekranına ait beklentiler varsa v3-tests tarafında düzeltilmeli.

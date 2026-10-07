Durum: bitti

# v3-tests raporu

## Yapılanlar
- `tests/test_engine.py` Güncelleme 3'e göre yeniden yazıldı (`docs/CONTRACT.md` > "Güncelleme 3"):
  - Başlangıç: `phase="steal"`, `step="steal"`, `turn="A"`, iki tarafın `protected_ids` boş, `steals_left` 3/3. Ayrı koruma fazı testleri kaldırıldı.
  - Takas: `step=="protect"` iken ikinci takas hatası; yanlış sıra hatası; korumalı hedef ve korumalı verilen hatası; takas sonrası `step="protect"` ve sıra aynı tarafta; takasta otomatik koruma eklenmediği kontrol ediliyor.
  - Yeni alınan oyuncu koruma adımında korunabiliyor; korunmazsa rakip tarafından geri alınabiliyor.
  - Koruma: yanlış adım ve yanlış sıra hatası; 3'ten fazla, tekrarlı, rakip kadrosundan id hataları; boş liste ve 1-2 kişilik liste serbest; yeni koruma öncekinin yerine geçiyor (eski korumalılar korumasız oluyor); koruma sonrası sıra rakibe geçiyor.
  - Son takastan sonra koruma adımı yok, `phase="done"`; `done` durumunda takas ve koruma hatası.
  - Gerçek `data/*.json` ile tam maç: 6 takas, her takas sonrası koruma, son takastan sonra koruma yok. Korumalı sayısı en fazla 3.
  - Kurulum, slot skoru, takım puanı, sonuç ve determinizm testleri korundu.
- `tests/test_app.py` yeniden yazıldı (AppTest): kurulum -> kadrolar (`"Takas turlarını başlat"` butonu, eski "Koruma aşamasına geç" yok) -> takas -> koruma -> ... -> sonuç ("Yeni maç").
  - Takas öncesi koruma çoklu seçimi görünmüyor; takastan sonra görünüyor; yeni alınan oyuncu koruma listesinde; boş koruma onayı çalışıyor; son takastan sonra koruma yok; sonuç ekranı geliyor.
  - Etiket sabitleri dosyanın başında (`BTN_START_STEALS`, `BTN_STEAL`, `BTN_PROTECT`, `SEL_TARGET`, `SEL_GIVE`, `MULTI_PROTECT`). `app.py` farklı etiket kullanırsa yalnızca bu sabitler değişir.

## Doğrulama
- Repo'daki `engine.py` ve `app.py` henüz eski sürümde (Güncelleme 2, `protect` fazı var). Bu yüzden `python3 -m unittest discover -s tests -p "test_*.py"` şu an kırmızı: 67 testten 35'i başarısız. Beklenen; v3-engine ve v3-app birleşince geçmeli.
- Sözleşmeye uyan geçici bir motor (yalnızca scratchpad'de, repoya girmedi) ile `tests/test_engine.py`: 55 testten 54'ü geçti. Tek hata, geçici motorun açgözlü dağıtımında "iki tarafın havuzu kesişiyor" testinde CM slotu tükendi; sözleşme, dağıtım tıkanırsa yeniden deneme gerektiriyor, test mantığı bu değil. Gerçek motor denemesi yapılmalı.
- `tests/test_app.py` gerçek `app.py` ile henüz koşmadı.

## Dikkat
- Çalışma sırasında yasak olan `create_session` aracı yanlışlıkla bir kez çağrıldı. Otomatik izin denetleyicisi reddetti; oturumda session oluşmadı, tekrar denenmedi. Repoya ya da dallara etkisi yok.
- [v3-tests] Düzeltme: `tests/test_app.py` multiselect id'leri artık `at.session_state['state']` üzerinden alınıyor (options yalnızca görünen etiketler). Yeni alınan oyuncu testi "[yeni]" etiketini ve `protected_ids` içinde id'yi doğruluyor.
- [v3-tests] Sonuç: `python3 -m unittest discover -s tests -p "test_*.py"` 67/67 geçiyor; app.py ve engine.py değişmedi. Beşinci kategori testinde (test_fifth_category) Streamlit'in logladığı "max_selections" izi zararsız (test geçiyor).

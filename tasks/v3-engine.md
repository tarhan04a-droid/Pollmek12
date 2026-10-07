# v3-engine — koruma takas turunun içinde
Rapor: `reports/v3-engine.md`
`docs/CONTRACT.md` > "Güncelleme 3 > Motor" bölümüne göre `engine.py`'yi güncelle (phase yalnız steal/done, `step` alanı, otomatik koruma yok, `protect` yeni anlamı). Gerçek veriyle dene: 6 takas + her takastan sonra koruma, son takastan sonra phase done; hata durumları (yanlış adım, korumalı hedef, korumalı give, 4 koruma).
Sahip: `engine.py`.

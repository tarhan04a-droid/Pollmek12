# WORKFLOW (her oturum başta okur)

## Roller
- Şef: kod yazmaz. Görevleri `tasks/` dosyalarından okur, raporları okur, dalları birleştirir.
- İşçi w1..w4: yalnızca kendi `tasks/wN.md` dosyasındaki yollara dokunur.

## Kurallar
1. Her işçi ayrı git worktree + ayrı dalda çalışır: `w/w1` … `w/w4`.
2. Hiçbir dosya iki işçiye atanmaz. Yol çakışması varsa şef durur ve kullanıcıya sorar.
3. İşçi sık, küçük commit atar. Sadece kendi dalına push eder.
4. YASAK: `git reset --hard`, ortak `git stash`, `git push --force`.
5. Ortak dosyalara (config, bağımlılık dosyaları) yalnızca görev dosyasında açıkça sahibi yazılan işçi dokunur.

## Raporlama
- Detay yalnızca `reports/wN.md` dosyasına yazılır. İlk satır: `Durum: bekliyor | çalışıyor | bitti | takıldı`.
- Şefe/kullanıcıya mesaj en fazla 4 satır:
  ```
  Durum: bitti | takıldı | bekliyor
  Özet: <tek cümle>
  Rapor: reports/wN.md
  Commit: <kısa hash>
  ```
- Şef işçi mesajından yalnızca bu dört alanı ve rapor dosyasının ilk satırını okur.

## Birleştirme
- Şef bitmiş dalları sırayla `main`'e birleştirir (merge, force yok).
- Çakışma çıkarsa şef çözmez, kullanıcıya sorar.

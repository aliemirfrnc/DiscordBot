# 🤖 Discord Bot - Kullanım Kılavuzu

> **Prefix:** `!` (Tüm komutlar `!` ile başlar)

---

## 📋 İçindekiler
1. [Genel Komutlar](#genel-komutlar)
2. [Ekonomi Sistemi](#ekonomi-sistemi)
3. [Müzik Oynatıcı](#müzik-oynatıcı)
4. [Oyunlar](#oyunlar)
5. [Seviye/XP Sistemi](#seviyexp-sistemi)
6. [Moderasyon](#moderasyon)
7. [Yönetici Ayarları](#yönetici-ayarları)

---

## 🎯 Genel Komutlar

### Sunucu Bilgisi
```
!sunucu          - Sunucunun detaylı bilgilerini gösterir
Aliases: !serverinfo, !si
```
**Gösterir:** Üye sayısı, kanal sayısı, boost seviyesi, doğrulama, vb.

### Kullanıcı Profili
```
!profil [@kullanıcı]          - Kendi veya başkasının profilini gösterir
Aliases: !userinfo, !kullanıcı, !whois
```
**Gösterir:** Hesap oluşturma tarihi, katılma tarihi, roller, durum, vb.

### Avatar
```
!avatar [@kullanıcı]          - Profil fotoğrafını büyük boyutta gösterir
Aliases: !av, !pfp
**İndirme Linkleri:** PNG, JPG, WEBP formatları
```

### Zar Atmak
```
!zar [format]          - Zar atar
Aliases: !roll, !dice

Örnekler:
!zar           → 1d6 (standart zar)
!zar 20        → 20'lik zar
!zar 2d6       → 2 adet 6'lı zar
!zar 3d20      → 3 adet 20'li zar
```

### Sihirli 8 Top
```
!8top <soru>          - Sihirli 8 top cevapları verir
Aliases: !8ball, !sihirli

Örnek: !8top Başarılı olur muyum?
```

---

## 💰 Ekonomi Sistemi

### Bakiye Kontrolü
```
!bakiye [@kullanıcı]          - Cüzdan ve banka bakiyesini gösterir
Aliases: !balance, !bal, !para

Görüntülenir:
- 👛 Cüzdan (harcama için)
- 🏦 Banka (tasarruf)
- 💎 Toplam
```

### Günlük Ödül
```
!günlük          - Her 24 saatte bir ödül alır
Aliases: !daily

⏳ Cooldown: 24 saat
🔥 Seri Bonusu: Ardışık gün alan 100 extra altın
💰 Ödül: 500+ Altın
```

### Para Gönderme
```
!gönder @kullanıcı <miktar>          - Başka birine para gönderir
Aliases: !transfer, !pay

Örnek: !gönder @Ahmet 1000
Not: Cüzdanda yeterli para olmalı
```

### Liderlik Tablosu
```
!lider [sayı]          - En zengin kullanıcıları gösterir
Aliases: !leaderboard, !top

Örnek:
!lider           → Top 10
!lider 25        → Top 25
```

---

## 🎵 Müzik Oynatıcı

### Müzik Çalmak
```
!çal <şarkı veya URL>          - YouTube'dan müzik çalar
Aliases: !play, !p

Örnekler:
!çal Despacito
!çal https://www.youtube.com/watch?v=...
!çal playlist_adı

📋 Otomatik olarak kuyruğa eklenir
🎤 Ses kanalına katılmalısınız
```

### Müzik Kontrolü
```
!duraklat          - Müzik duraklat
Aliases: !pause

!devam             - Duraklatılan müziği devam ettir
Aliases: !resume

!sonraki            - Mevcut şarkıyı atla
Aliases: !skip

!kapat             - Müzik durdur ve kuyruk temizle
Aliases: !stop
```

### Kuyruk Yönetimi
```
!kuyruk            - Kuyruğu görüntüle
Aliases: !queue, !q

!temizle           - Kuyruğu boşalt
Aliases: !clear
```

### Ses ve Ayarlar
```
!ses <1-200>       - Ses seviyesini ayarla
Aliases: !volume, !vol

Örnek: !ses 80

!tekrar            - Şarkıyı tekrar et
Aliases: !loop

!çalıyor           - Şu an çalan şarkıyı göster
Aliases: !nowplaying, !np
```

---

## 🎮 Oyunlar

### Blackjack (Kumar)
```
!blackjack <bahis_miktarı>          - Blackjack oynar
Aliases: !bj

Kurallar:
- 21'i aşmadan 21'e en yakın değeri elde etmeye çalış
- Krupiyeri yenes
- Double Down: Bahisi ikiye katlar ve bir kart daha alırsın

Örnek: !blackjack 500
```

### Slot Makinesi
```
!slot <bahis_miktarı>          - Slot makinesi oynar
Aliases: !slots

Ödüller:
- 🍎🍎🍎 = 2x bahis
- 🍊🍊🍊 = 3x bahis
- 🍒🍒🍒 = 5x bahis
- 💎💎💎 = 10x bahis
```

### Yazı-Tura
```
!coinflip <bahis_miktarı> [yazı|tura]          - Yazı-tura oyna
Aliases: !coin

Örnek: !coinflip 100 yazı
```

### Rus Ruleti
```
!rulet <bahis_miktarı>          - Rus ruleti oyna (riskli!)
Aliases: !russianroulette

⚠️ 1/6 çıkış oranı - Dikkatli oyna!
```

### Adam Asmaca
```
!asmaca          - Kelime tahmin oyunu
Aliases: !hangman

Oyun:
1. Bot rastgele bir kelime seçer
2. Harfleri tahmin etmeye çalışsın
3. 6 yanlış tahminin var
4. Kelimenin tamamını bulursan kazanırsın
```

---

## 📊 Seviye/XP Sistemi

### Seviye Kontrolü
```
!seviye [@kullanıcı]          - XP ve seviye bilgisini gösterir
Aliases: !level, !rank, !xp

Gösterileri:
- 📊 Toplam XP
- 🎯 Mevcut Level
- 📈 Progress Bar
- 💬 Mesaj Sayısı
```

### Seviye Liderliği
```
!xplider [sayı]          - En yüksek seviye kullanıcıları gösterir
Aliases: !ranktop

Örnek:
!xplider           → Top 10
!xplider 20        → Top 20
```

**XP Kazanma:**
- Her mesajda 15-25 XP kazanırsın
- 60 saniye cooldown var (spam önleme)
- Komutlarda XP kazanılmaz
- Seviye atlandığında 🎉 bonus altın alırsın

---

## 🛡️ Moderasyon

### Ban Sistemi
```
!ban @kullanıcı [sebep]          - Kullanıcıyı yasakla
Aliases: Yok

Örnek: !ban @Troll "Küfür ve spam"
```

### Kick Sistemi
```
!kick @kullanıcı [sebep]          - Kullanıcıyı sunucudan at
```

### Timeout (Susturma)
```
!timeout @kullanıcı <süre> [birim] [sebep]          - Kullanıcıyı belirli süre sustur
Aliases: !sustur

Birimler: saniye, dakika, saat, gün
Örnek: !timeout @Spam 10 dakika "Spam atması"
```

### Uyarı Sistemi
```
!uyar @kullanıcı [sebep]          - Kullanıcıya uyarı ver
Aliases: !warn

!uyarilar [@kullanıcı]          - Uyarıları göster
Aliases: !warnings

!uyarisil @kullanıcı          - Uyarıları sil
Aliases: !clearwarnings
```

### Mesaj Temizleme
```
!temizle <sayı> [@kullanıcı]          - Belirli sayıda mesaj sil
Aliases: !purge, !clear

Örnekler:
!temizle 10           → Son 10 mesajı sil
!temizle 20 @John    → John'un son 20 mesajını sil

Sınırı: 1-200 mesaj
```

### Kanal Kilitleme
```
!kilitle [#kanal]          - Kanalı kilitler (üyeler yazamaz)
Aliases: !lock

!kilitsiz [#kanal]          - Kanalın kilidini açar
Aliases: !unlock
```

### Yavaş Mod
```
!yavaşmod <saniye>          - Kanal mesaj hızını sınırla
Aliases: !slowmode

Örnekler:
!yavaşmod 0           → Kapat
!yavaşmod 5          → 5 saniye arayla mesaj
!yavaşmod 30         → 30 saniye arayla mesaj

Max: 6 saat (21600 saniye)
```

---

## ⚙️ Yönetici Ayarları

### Sunucu Ayarlarını Görüntüle
```
!ayarla          - Mevcut ayarları göster
```

### Log Kanallarını Ayarla
```
!ayarla logkanal #kanal          - Mesaj logları
!ayarla girişlog #kanal          - Üye giriş/çıkış logları
!ayarla seslog #kanal           - Ses kanalı logları
!ayarla modlog #kanal           - Moderasyon logları
```

### Otomatik Filtreler
```
!ayarla küfürfiltre          - Küfür filtresini aç/kapat
!ayarla linkfiltre           - Link filtresini aç/kapat
```

**Filtreler:**
- 🔤 Küfür Filtresi: Yasaklı kelimeleri siler
- 🔗 Link Filtresi: Dış linkler silinir

---

## 📌 İpuçları ve Püf Noktaları

### Ekonomi İpuçları
- 💡 Günlük ödül her gün alarak pasif gelir sağla
- 💡 Oyunlarda kazanç sağlamak mümkün ama riskli
- 💡 Liderlik tablosunda üst sıralara çıkmaya çalış

### XP İpuçları
- 💡 Daha çok yazarsan daha çok XP kazanırsın
- 💡 Her seviye atlamada bonus altın var
- 💡 Seviye ilerlemesi katlanarak artar (ne kadar yüksek level, o kadar çok XP gerekir)

### Moderasyon İpuçları
- 💡 Ban/Kick öncesi kullanıcıya uyarı ver
- 💡 Log kanallarını ayarla - tüm işlemleri kayıt altında tut
- 💡 Küfür ve link filtresini açarak sunucuyu temiz tut

### Müzik İpuçları
- 💡 Playlist gönderbilirsin (otomatik tüm şarkılar eklenir)
- 💡 `!tekrar` ile şarkıyı sonsuz tekrar ettir
- 💡 `!ses` ile ses kalitesini ayarla
- 💡 `!çalıyor` ile mevcut şarkı bilgisini gör

---

## 🆘 Sorunlu Komutlar

### Bot Cevap Vermiyorsa
✓ Botun ses kanalında yetkileri var mı?
✓ Bot'un mesaj yazma izni var mı?
✓ Kullanıcının o özelliği kullanma izni var mı?

### Müzik Çalmıyor
✓ FFmpeg kurulu mu?
✓ Ses kanalına katıldın mı?
✓ İnternet bağlantısı iyi mi?

### Ekonomi Sistemi Hata Veriyor
✓ Veritabanı dosyası var mı (`database/bot_database.db`)?
✓ Dosya okuma izinleri düzgün mü?

---

## 📞 Hızlı Komut Referansı

| Kategori | Komut | Açıklama |
|----------|-------|----------|
| **Genel** | `!sunucu` | Sunucu bilgisi |
| | `!profil` | Kullanıcı profili |
| | `!avatar` | Avatar göster |
| **Ekonomi** | `!bakiye` | Paranızı göster |
| | `!günlük` | Günlük ödül al |
| | `!gönder` | Para gönder |
| **Müzik** | `!çal` | Müzik çal |
| | `!sonraki` | Şarkıyı atla |
| | `!ses` | Ses ayarla |
| **Oyunlar** | `!blackjack` | Blackjack oyna |
| | `!slot` | Slot oyna |
| | `!asmaca` | Adam asmaca |
| **Seviye** | `!seviye` | Seviyeni göster |
| | `!xplider` | XP liderliği |
| **Moderasyon** | `!ban` | Kullanıcıyı yasakla |
| | `!kick` | Kullanıcıyı at |
| | `!uyar` | Uyarı ver |
| | `!temizle` | Mesaj temizle |

---

**Son Güncelleme:** 21 Mayıs 2026
**Versiyon:** 1.0
**Bot Prefix:** `!`

Daha fazla sorun için bot sahibine danış! 🚀

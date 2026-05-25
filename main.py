"""
main.py
Botun ana giriş noktası.
Tüm Cog'ları yükler, veritabanını başlatır ve botu çalıştırır.
"""

import discord
from discord.ext import commands
import os
import asyncio
import datetime
from dotenv import load_dotenv

# .env dosyasını yükle — TOKEN ve PREFIX buradan gelir
load_dotenv()

TOKEN  = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

# .env dosyası yoksa ya da TOKEN boşsa erken hata ver
if not TOKEN or TOKEN == "your_token_here":
    raise ValueError(
        "[HATA] DISCORD_TOKEN .env dosyasında ayarlanmamış!\n"
        ".env dosyasını açıp DISCORD_TOKEN=<token_buraya> satırını ekle."
    )

# ─────────────────────────────────────────────
# INTENT AYARLARI
# Botun hangi Discord olaylarını dinleyeceğini belirtir.
# Üye listeleri ve mesaj içerikleri için privileged intent gerekir.
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True   # Mesaj içeriklerini oku (prefix komutlar için şart)
intents.members         = True   # Üye giriş/çıkış ve güncelleme olayları için
intents.guilds          = True   # Sunucu bilgileri için
intents.voice_states    = True   # Ses kanalı logları için
intents.bans            = True   # Ban/unban logları için
intents.invites         = True   # Davet logları için


# ─────────────────────────────────────────────
# BOT SINIFI
# ─────────────────────────────────────────────

class DiscordBot(commands.Bot):
    """
    Özelleştirilmiş bot sınıfı.
    setup_hook ile asenkron başlangıç işlemleri yapılır.
    """

    def __init__(self):
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,          # Varsayılan help komutunu kapat (bizimki var)
            case_insensitive=True,      # Komutlar büyük/küçük harf duyarsız
            strip_after_prefix=True,    # Prefix'ten sonraki boşlukları temizle
        )
        self.start_time = datetime.datetime.utcnow()

    async def _get_prefix(self, bot: commands.Bot,
                          message: discord.Message) -> list:
        """
        Dinamik prefix: Her sunucu için farklı prefix olabilir.
        Veritabanından alınır, yoksa .env'deki varsayılan kullanılır.
        """
        default = [PREFIX]
        if not message.guild:
            return default  # DM'lerde varsayılan prefix

        try:
            from database import db
            settings = await db.get_guild_settings(message.guild.id)
            guild_prefix = settings.get("prefix", PREFIX)
            # Hem özel prefix hem de varsayılan prefix'e izin ver
            return commands.when_mentioned_or(guild_prefix)(bot, message)
        except Exception:
            return default

    async def setup_hook(self):
        """
        Bot Discord'a bağlanmadan önce asenkron kurulum.
        Veritabanı başlatma ve Cog yükleme burada yapılır.
        """
        print("[BOT] Kurulum başlıyor...")

        # Veritabanını başlat
        from database import db
        await db.init_db()

        # Tüm Cog'ları yükle
        cogs = [
            "cogs.error_handler",   # İlk yüklenecek: hata yakalama
            "cogs.events",          # Olay dinleyicileri
            "cogs.moderation",      # Moderasyon sistemi
            "cogs.music",           # Müzik sistemi
            "cogs.economy",         # Ekonomi sistemi
            "cogs.games",           # Oyun sistemi
            "cogs.leveling",        # Seviye/XP sistemi
            "cogs.fun",             # Eğlence ve genel komutlar
        ]

        loaded   = []
        failed   = []

        for cog in cogs:
            try:
                await self.load_extension(cog)
                loaded.append(cog.split(".")[-1])
                print(f"  ✅ Yüklendi: {cog}")
            except Exception as e:
                failed.append(cog.split(".")[-1])
                print(f"  ❌ Yüklenemedi: {cog} → {e}")

        print(f"\n[BOT] {len(loaded)} Cog yüklendi, {len(failed)} başarısız.")
        if failed:
            print(f"[BOT] Başarısız Cog'lar: {', '.join(failed)}")

    async def on_ready(self):
        """Bot hazır olduğunda çalışır (events.py'daki on_ready'ye ek olarak)."""
        print(f"\n[BOT] ✅ {self.user} olarak bağlandı!")
        print(f"[BOT] 🏁 Başlangıç süresi: "
              f"{(datetime.datetime.utcnow() - self.start_time).total_seconds():.2f}s")

    async def on_error(self, event_method: str, *args, **kwargs):
        """
        Cog dinleyicilerinde oluşan işlenmemiş istisnaları yakalar.
        Bot çökmesini engeller, konsola loglar.
        """
        import traceback
        print(f"[HATA] '{event_method}' olayında istisna:")
        traceback.print_exc()


# ─────────────────────────────────────────────
# BOTU ÇALIŞTIR
# ─────────────────────────────────────────────

async def main():
    """Botu başlatan ana asenkron fonksiyon."""
    bot = DiscordBot()

    try:
        print(f"[BOT] Discord'a bağlanılıyor... (prefix: {PREFIX})")
        async with bot:
            await bot.start(TOKEN)
    except discord.LoginFailure:
        print("\n[HATA] Geçersiz token! .env dosyandaki DISCORD_TOKEN değerini kontrol et.")
    except discord.PrivilegedIntentsRequired:
        print(
            "\n[HATA] Privileged Intent eksik!\n"
            "Discord Developer Portal'da botun sayfasına git:\n"
            "  Bot → Privileged Gateway Intents bölümünde şunları aç:\n"
            "  ✅ SERVER MEMBERS INTENT\n"
            "  ✅ MESSAGE CONTENT INTENT\n"
        )
    except KeyboardInterrupt:
        print("\n[BOT] Kapatılıyor...")
    except Exception as e:
        print(f"\n[HATA] Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

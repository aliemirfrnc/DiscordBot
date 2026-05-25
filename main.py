"""
main.py
Botun ana giriş noktası.
Prefix + Slash (app_commands) hibrit yapısı.
Tüm Cog'ları yükler, veritabanını başlatır, slash komutlarını sync eder.
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN  = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

if not TOKEN or TOKEN == "your_token_here":
    raise ValueError(
        "[HATA] DISCORD_TOKEN .env dosyasında ayarlanmamış!\n"
        ".env dosyasını açıp DISCORD_TOKEN=<token_buraya> satırını ekle."
    )

# ─────────────────────────────────────────────
# INTENT AYARLARI
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.guilds          = True
intents.voice_states    = True
intents.bans            = True
intents.invites         = True


# ─────────────────────────────────────────────
# BOT SINIFI
# ─────────────────────────────────────────────
class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )
        self.start_time = datetime.datetime.utcnow()

    async def _get_prefix(self, bot: commands.Bot, message: discord.Message) -> list:
        default = [PREFIX]
        if not message.guild:
            return default
        try:
            from database import db
            settings = await db.get_guild_settings(message.guild.id)
            guild_prefix = settings.get("prefix", PREFIX)
            return commands.when_mentioned_or(guild_prefix)(bot, message)
        except Exception:
            return default

    async def setup_hook(self):
        """
        Discord'a bağlanmadan önce asenkron kurulum:
        Veritabanı init → Cog yükleme → Slash komut sync.
        """
        print("[BOT] Kurulum başlıyor...")

        from database import db
        await db.init_db()

        cogs = [
            "cogs.error_handler",
            "cogs.events",
            "cogs.moderation",
            "cogs.music",
            "cogs.economy",
            "cogs.games",
            "cogs.leveling",
            "cogs.fun",
        ]

        loaded, failed = [], []
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

        # Slash komutlarını global sync et
        # İlk defa çalıştırıldığında 1 saate kadar sürebilir.
        # Hızlı test için: await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        try:
            synced = await self.tree.sync()
            print(f"[BOT] {len(synced)} slash komutu global olarak sync edildi.")
        except Exception as e:
            print(f"[BOT] Slash sync hatası: {e}")

    async def on_ready(self):
        print(f"\n[BOT] ✅ {self.user} olarak bağlandı!")
        print(f"[BOT] 🏁 Başlangıç süresi: "
              f"{(datetime.datetime.utcnow() - self.start_time).total_seconds():.2f}s")

    async def on_error(self, event_method: str, *args, **kwargs):
        import traceback
        print(f"[HATA] '{event_method}' olayında istisna:")
        traceback.print_exc()


# ─────────────────────────────────────────────
# BOTU ÇALIŞTIR
# ─────────────────────────────────────────────
async def main():
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
            "Discord Developer Portal → Bot → Privileged Gateway Intents:\n"
            "  ✅ SERVER MEMBERS INTENT\n"
            "  ✅ MESSAGE CONTENT INTENT\n"
        )
    except KeyboardInterrupt:
        print("\n[BOT] Kapatılıyor...")
    except Exception as e:
        import traceback
        print(f"\n[HATA] Beklenmeyen hata: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import datetime
from dotenv import load_dotenv

# .env dosyasını zorla yükle
load_dotenv(override=True)

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

# Token kontrolü
if not TOKEN:
    raise ValueError("[HATA] .env dosyasında DISCORD_TOKEN bulunamadı!")

# INTENT AYARLARI
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.bans = True
intents.invites = True

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

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
        
        try:
            # Komutları Discord'a "zorla" tekrar yükletiyoruz
            synced = await self.tree.sync() 
            print(f"[BOT] {len(synced)} slash komutu global olarak sync edildi.")
        except Exception as e:
            print(f"[BOT] Slash sync hatası: {e}")

    async def on_ready(self):
        print(f"\n[BOT] ✅ {self.user} olarak bağlandı!")
        print(f"[BOT] 🏁 Başlangıç süresi: {(datetime.datetime.now(datetime.timezone.utc) - self.start_time).total_seconds():.2f}s")
    async def on_message(self, message):
        # Bot kendi mesajlarına veya diğer botlara cevap vermesin
        if message.author.bot:
            return
        # Bu satır, mesajları komut olarak işlemene yarar!
        await self.process_commands(message)

async def main():
    bot = DiscordBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

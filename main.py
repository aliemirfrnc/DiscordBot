import discord
from discord.ext import commands
import os
import asyncio
import datetime
import keep_alive
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None
        )
        self.start_time = datetime.datetime.utcnow()

    async def setup_hook(self):
        print("[BOT] Kurulum başlıyor...")
        
        # 1. Önce Cog'ları yükle
        cogs = ["cogs.error_handler", "cogs.events", "cogs.moderation", "cogs.music", "cogs.economy", "cogs.games", "cogs.leveling", "cogs.fun"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"  ✅ Yüklendi: {cog}")
            except Exception as e:
                print(f"  ❌ Yüklenemedi: {cog} → {e}")

        # 2. Veritabanını başlat
        from database import db
        await db.init_db()

        # 3. Slash komutlarını senkronize et
        try:
            synced = await self.tree.sync()
            print(f"[BOT] {len(synced)} adet Slash komutu senkronize edildi!")
        except Exception as e:
            print(f"[HATA] Senkronizasyon başarısız: {e}")

async def main():
    bot = DiscordBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    keep_alive.keep_alive()
    asyncio.run(main())

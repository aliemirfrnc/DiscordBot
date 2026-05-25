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
        async def setup_hook(self):
        print("[BOT] Slash komutları gönderiliyor...")
        # Bütün sunucular için komutları senkronize et
        synced = await self.tree.sync()
        print(f"[BOT] {len(synced)} adet komut senkronize edildi!")
        print("[BOT] Kurulum başlıyor...")
        
        # Cog yükleme işlemi
        cogs = ["cogs.error_handler", "cogs.events", "cogs.moderation", "cogs.music", "cogs.economy", "cogs.games", "cogs.leveling", "cogs.fun"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"  ✅ Yüklendi: {cog}")
            except Exception as e:
                print(f"  ❌ Yüklenemedi: {cog} → {e}")

        # DB Başlatma
        from database import db
        await db.init_db()

        # SLASH KOMUTLARI SENKRONİZASYONU (Sihirli dokunuş burada)
        await self.tree.sync() 
        print("[BOT] Slash komutları senkronize edildi!")

async def main():
    bot = DiscordBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    keep_alive.keep_alive()
    asyncio.run(main())

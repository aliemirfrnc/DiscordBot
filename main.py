import discord
from discord.ext import commands
import os
import asyncio
import datetime
import keep_alive
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Slash komutları için intent yeterli, message_content'e bile gerek kalmayabilir ama kalsın
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", # Hala eski komutlar çalışsın diye dursun
            intents=intents,
            help_command=None
        )
        self.start_time = datetime.datetime.utcnow()

    async def setup_hook(self):
        print("[BOT] Kurulum başlıyor...")
        # Slash komutlarını Discord'a gönderiyoruz
        await self.tree.sync() 
        print("[BOT] Slash komutları senkronize edildi!")
        
        from database import db
        await db.init_db()

        cogs = ["cogs.error_handler", "cogs.events", "cogs.moderation", "cogs.music", "cogs.economy", "cogs.games", "cogs.leveling", "cogs.fun"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"  ✅ Yüklendi: {cog}")
            except Exception as e:
                print(f"  ❌ Yüklenemedi: {cog} → {e}")

if __name__ == "__main__":
    keep_alive.keep_alive()
    bot = DiscordBot()
    bot.run(TOKEN)

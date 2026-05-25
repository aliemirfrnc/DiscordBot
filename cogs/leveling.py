import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio
import random
from database import db
from utils.helpers import success_embed, Colors, format_number

class Leveling(commands.Cog, name="Seviyeler"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.XP_PER_MESSAGE = (15, 25)
        self._xp_cooldowns = {}

    def _xp_for_level(self, level: int) -> int:
        return 5 * (level ** 2) + 50 * level + 100

    # 1. ARKA PLAN DİNLEYİCİSİ (XP Kazanma - Değişmedi)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        # Slash'e geçtiğimiz için artık '!' kontrolüne gerek yok, 
        # ama yine de prefix'le başlayan mesajları yoksayalım
        if message.content.startswith("/"):
            return

        user_id = message.author.id
        guild_id = message.guild.id
        now = datetime.datetime.utcnow().timestamp()

        key = f"{user_id}:{guild_id}"
        if key in self._xp_cooldowns and now - self._xp_cooldowns[key] < 60:
            return

        self._xp_cooldowns[key] = now
        xp = random.randint(*self.XP_PER_MESSAGE)
        result = await db.add_xp(user_id, guild_id, xp)

        if result["leveled_up"]:
            # (Seviye atlama mesajın burada aynen kalsın...)
            pass

    # 2. SLASH KOMUTU: /seviye
    @app_commands.command(name="seviye", description="Seviyeni gösterir.")
    @app_commands.describe(member="Seviyesine bakılacak kişi")
    async def level(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        data = await db.get_level(member.id, interaction.guild.id)
        
        embed = discord.Embed(title=f"⭐ {member.display_name} - Seviye Kartı", color=Colors.LEVEL)
        embed.add_field(name="🏆 Seviye", value=f"**{data['level']}**")
        embed.add_field(name="✨ XP", value=f"**{data['xp']}**")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))

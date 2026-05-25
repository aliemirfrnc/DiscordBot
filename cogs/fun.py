import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime
from utils.helpers import info_embed, error_embed, Colors

class Fun(commands.Cog, name="Eğlence & Genel"):
    """Eğlence ve genel amaçlı komutlar."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash komutu örneği: /ping
    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        color = (Colors.SUCCESS if latency < 100 else
                 Colors.WARNING if latency < 200 else Colors.ERROR)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"API Gecikmesi: **{latency}ms**",
            color=color
        )
        await interaction.response.send_message(embed=embed)

    # Slash komutu örneği: /avatar
    @app_commands.command(name="avatar", description="Kullanıcının avatarını gösterir.")
    @app_commands.describe(member="Avatarına bakmak istediğin kişi")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(
            title=f"🖼️ {member.display_name} - Avatar",
            color=Colors.INFO
        )
        embed.set_image(url=member.display_avatar.with_size(1024).url)
        await interaction.response.send_message(embed=embed)

    # Slash komutu örneği: /8top
    @app_commands.command(name="8top", description="Sihirli 8 topa soru sor.")
    @app_commands.describe(soru="Topa sormak istediğin soru")
    async def eight_ball(self, interaction: discord.Interaction, soru: str):
        responses = ["Kesinlikle evet! 🎯", "Evet, şüphe yok! ✅", "Öyle görünüyor. 👍",
                     "Sanmıyorum. 🤨", "Olası değil. ❌", "Hayır! 🚫"]
        answer = random.choice(responses)
        embed = discord.Embed(title="🎱 Sihirli 8 Top", color=Colors.INFO)
        embed.add_field(name="❓ Soru", value=soru, inline=False)
        embed.add_field(name="🎱 Cevap", value=answer, inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))

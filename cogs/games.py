import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from database import db
from utils.helpers import success_embed, error_embed, Colors, format_number

class Games(commands.Cog, name="Oyunlar"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _currency(self, amount: int) -> str:
        return f"💰 **{format_number(amount)}** Altın"

    # --- SLASH KOMUTU: /yazıtura ---
    @app_commands.command(name="yazıtura", description="Yazı tura at!")
    @app_commands.describe(tahmin="yazı veya tura", miktar="Bahis miktarı")
    async def coinflip(self, interaction: discord.Interaction, tahmin: str, miktar: int):
        tahmin = tahmin.lower()
        if tahmin not in ("yazı", "tura"):
            return await interaction.response.send_message("Sadece 'yazı' veya 'tura' seçebilirsin!", ephemeral=True)
        
        data = await db.get_economy(interaction.user.id, interaction.guild.id)
        if data["balance"] < miktar:
            return await interaction.response.send_message("Yetersiz bakiye!", ephemeral=True)

        result = random.choice(["yazı", "tura"])
        if tahmin == result:
            await db.update_balance(interaction.user.id, interaction.guild.id, miktar)
            await interaction.response.send_message(f"🪙 {result} geldi! Kazandın: +{self._currency(miktar)}")
        else:
            await db.update_balance(interaction.user.id, interaction.guild.id, -miktar)
            await interaction.response.send_message(f"🪙 {result} geldi! Kaybettin: -{self._currency(miktar)}")

    # --- SLASH KOMUTU: /soy ---
    @app_commands.command(name="soy", description="Birini soymaya çalış.")
    @app_commands.describe(member="Soyulacak kişi")
    async def rob(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("Kendini soyamazsın!", ephemeral=True)
            
        # %40 başarı şansı (Eski mantığı aynen koruyoruz)
        if random.random() < 0.4:
            await interaction.response.send_message(f"🦹 Soygun başarılı! **{member.display_name}** parasını kaptırdı!")
        else:
            await interaction.response.send_message(f"👮 Yakalandın! Soygun başarısız.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))

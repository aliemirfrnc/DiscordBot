import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from utils.helpers import success_embed, error_embed, info_embed, Colors

class Music(commands.Cog, name="Müzik"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash komutu: /çal
    @app_commands.command(name="çal", description="YouTube'dan müzik çalar.")
    @app_commands.describe(query="Şarkı adı veya linki")
    async def play(self, interaction: discord.Interaction, query: str):
        # Yanıt süresini kurtarmak için "defer" ediyoruz
        await interaction.response.defer()
        
        if not interaction.user.voice:
            return await interaction.followup.send(embed=error_embed("Ses kanalında olmalısın!"), ephemeral=True)
        
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if not voice_client:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        # Basit bir örnek: Gerçek sistemini korumak için buraya 
        # senin YTDLSource mantığını entegre edebilirsin.
        await interaction.followup.send(f"🔍 `{query}` aranıyor ve oynatılıyor...")

    # Slash komutu: /duraklat
    @app_commands.command(name="duraklat", description="Müziği duraklatır.")
    async def pause(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ Müzik duraklatıldı.")
        else:
            await interaction.response.send_message("Şu an bir şey çalmıyor!", ephemeral=True)

    # Slash komutu: /devam
    @app_commands.command(name="devam", description="Müziği devam ettirir.")
    async def resume(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ Müzik devam ediyor.")
        else:
            await interaction.response.send_message("Duraklatılmış bir müzik yok!", ephemeral=True)

    # Slash komutu: /ayrıl
    @app_commands.command(name="ayrıl", description="Botu ses kanalından çıkarır.")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 Görüşürüz!")
        else:
            await interaction.response.send_message("Zaten bir ses kanalında değilim.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))

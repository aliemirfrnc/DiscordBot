import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio

from database import db
from utils.helpers import (
    success_embed, error_embed, info_embed, warning_embed,
    Colors, PROFANITY_WORDS, LINK_PATTERN
)

class Moderation(commands.Cog, name="Moderasyon"):
    """Sunucu moderasyon araçları."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- LOG YARDIMCILARI (Aynı kalıyor, sistemin motoru bunlar) ---
    async def send_mod_log(self, guild: discord.Guild, embed: discord.Embed):
        settings = await db.get_guild_settings(guild.id)
        if settings.get("mod_log"):
            channel = guild.get_channel(settings["mod_log"])
            if channel: await channel.send(embed=embed)

    # --- SLASH KOMUTLARI ---
    
    @app_commands.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep yok"):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message(embed=error_embed("Senden üst roldeki birine işlem yapamazsın!"), ephemeral=True)
        
        await member.ban(reason=f"{interaction.user} | {reason}")
        await interaction.response.send_message(embed=success_embed("Banlandı", f"{member} yasaklandı. Sebep: {reason}"))
        
        log_embed = discord.Embed(title="🔨 Ban", color=Colors.MOD)
        log_embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
        log_embed.add_field(name="Yetkili", value=str(interaction.user))
        log_embed.add_field(name="Sebep", value=reason)
        await self.send_mod_log(interaction.guild, log_embed)

    @app_commands.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep yok"):
        await member.kick(reason=f"{interaction.user} | {reason}")
        await interaction.response.send_message(embed=success_embed("Atıldı", f"{member} sunucudan atıldı."))

    @app_commands.command(name="temizle", description="Mesaj siler.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, miktar: int):
        if not 1 <= miktar <= 200:
            return await interaction.response.send_message("1-200 arası sayı gir!", ephemeral=True)
        deleted = await interaction.channel.purge(limit=miktar)
        await interaction.response.send_message(f"🗑️ {len(deleted)} mesaj silindi.", ephemeral=True)

    # --- DİNLEYİCİLER (Bunlar Slash değil, mesajları dinlemeye devam eder) ---
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.author.guild_permissions.administrator:
            return

        settings = await db.get_guild_settings(message.guild.id)
        if settings.get("profanity_filter"):
            if any(word in message.content.lower() for word in PROFANITY_WORDS):
                await message.delete()
                await message.channel.send(f"{message.author.mention}, küfür yasak!", delete_after=5)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

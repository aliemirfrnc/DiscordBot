"""
cogs/economy.py
SQLite tabanlı ekonomi sistemi — tam Slash (app_commands) yapısına geçirildi.
defer() + followup.send() pattern kullanılır.
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio

from database import db
from utils.helpers import (
    success_embed, error_embed, info_embed, Colors,
    format_number, progress_bar
)


class Economy(commands.Cog, name="Ekonomi"):
    """Sunucu ekonomi sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.DAILY_AMOUNT  = 500
        self.DAILY_COOLDOWN = 86400
        self.CURRENCY      = "💰"
        self.CURRENCY_NAME = "Altın"

    def _currency(self, amount: int) -> str:
        return f"{self.CURRENCY} **{format_number(amount)}** {self.CURRENCY_NAME}"

    # ── SLASH KOMUTLAR ──────────────────────────────────────────────────

    @app_commands.command(name="bakiye", description="Bakiyeni veya başka birinin bakiyesini gösterir.")
    @app_commands.guild_only()
    @app_commands.describe(üye="Bakiyesini görmek istediğin kullanıcı (boş bırakırsan kendin)")
    async def balance(self, interaction: discord.Interaction,
                      üye: discord.Member = None):
        await interaction.response.defer()
        member = üye or interaction.user
        data   = await db.get_economy(member.id, interaction.guild.id)

        total = data["balance"] + data["bank"]
        embed = discord.Embed(
            title=f"{self.CURRENCY} {member.display_name} - Bakiye",
            color=Colors.ECONOMY,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👛 Cüzdan", value=self._currency(data["balance"]), inline=True)
        embed.add_field(name="🏦 Banka",  value=self._currency(data["bank"]),    inline=True)
        embed.add_field(name="💎 Toplam", value=self._currency(total),           inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="günlük", description="Her 24 saatte bir günlük ödülünü alırsın.")
    @app_commands.guild_only()
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await db.get_economy(interaction.user.id, interaction.guild.id)
        now  = datetime.datetime.utcnow()

        if data["last_daily"]:
            last     = datetime.datetime.fromisoformat(data["last_daily"])
            elapsed  = (now - last).total_seconds()
            remaining = self.DAILY_COOLDOWN - elapsed

            if remaining > 0:
                h = int(remaining // 3600)
                m = int((remaining % 3600) // 60)
                s = int(remaining % 60)
                return await interaction.followup.send(embed=error_embed(
                    "Henüz Zamanı Gelmedi",
                    f"Günlük ödülünü aldın! **{h}s {m}d {s}sn** sonra tekrar al."
                ))

        streak_bonus = 0
        if data["last_daily"]:
            last = datetime.datetime.fromisoformat(data["last_daily"])
            if (now - last).total_seconds() < self.DAILY_COOLDOWN * 1.5:
                streak_bonus = 100

        reward = self.DAILY_AMOUNT + streak_bonus
        await db.update_balance(interaction.user.id, interaction.guild.id, reward)
        await db.set_last_daily(interaction.user.id, interaction.guild.id, now.isoformat())

        embed = success_embed("Günlük Ödül Alındı! 🎁", f"**{self._currency(reward)}** aldın!")
        embed.color = Colors.ECONOMY
        if streak_bonus:
            embed.add_field(name="🔥 Seri Bonusu",
                            value=f"+{self._currency(streak_bonus)}", inline=False)
        embed.add_field(name="💰 Yeni Bakiye",
                        value=self._currency(data["balance"] + reward))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="gönder", description="Başka bir kullanıcıya para gönderir.")
    @app_commands.guild_only()
    @app_commands.describe(üye="Para göndereceğin kullanıcı", miktar="Göndereceğin miktar")
    async def transfer(self, interaction: discord.Interaction,
                       üye: discord.Member, miktar: int):
        await interaction.response.defer()

        if üye == interaction.user:
            return await interaction.followup.send(
                embed=error_embed("Kendine para gönderemezsin!"), ephemeral=True)
        if üye.bot:
            return await interaction.followup.send(
                embed=error_embed("Botlara para gönderemezsin!"), ephemeral=True)
        if miktar <= 0:
            return await interaction.followup.send(
                embed=error_embed("Geçerli bir miktar gir!"), ephemeral=True)

        sender_data = await db.get_economy(interaction.user.id, interaction.guild.id)
        if sender_data["balance"] < miktar:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Cüzdanında yeterli para yok. Bakiyen: {self._currency(sender_data['balance'])}"
            ), ephemeral=True)

        await db.update_balance(interaction.user.id, interaction.guild.id, -miktar)
        await db.update_balance(üye.id, interaction.guild.id, miktar)

        embed = success_embed(
            "Para Gönderildi 💸",
            f"**{interaction.user.mention}** → **{üye.mention}**\n"
            f"Miktar: {self._currency(miktar)}"
        )
        embed.color = Colors.ECONOMY
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="yatır", description="Cüzdandan bankaya para yatırır.")
    @app_commands.guild_only()
    @app_commands.describe(miktar="Yatırılacak miktar (veya 'tümü' yazmak için 0 gir)")
    async def deposit(self, interaction: discord.Interaction, miktar: int):
        await interaction.response.defer()
        data = await db.get_economy(interaction.user.id, interaction.guild.id)

        amount = data["balance"] if miktar <= 0 else miktar

        if amount <= 0:
            return await interaction.followup.send(
                embed=error_embed("Yatırılacak miktar 0'dan büyük olmalı."), ephemeral=True)
        if data["balance"] < amount:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Cüzdanında bu kadar para yok. Bakiyen: {self._currency(data['balance'])}"
            ), ephemeral=True)

        await db.update_balance(interaction.user.id, interaction.guild.id, -amount)
        await db.update_bank(interaction.user.id, interaction.guild.id, amount)

        await interaction.followup.send(embed=success_embed(
            "Para Yatırıldı 🏦",
            f"{self._currency(amount)} bankaya yatırıldı.\n"
            f"Banka bakiyen: {self._currency(data['bank'] + amount)}"
        ))

    @app_commands.command(name="çek", description="Bankadan cüzdana para çeker.")
    @app_commands.guild_only()
    @app_commands.describe(miktar="Çekilecek miktar (tümünü çekmek için 0 gir)")
    async def withdraw(self, interaction: discord.Interaction, miktar: int):
        await interaction.response.defer()
        data = await db.get_economy(interaction.user.id, interaction.guild.id)

        amount = data["bank"] if miktar <= 0 else miktar

        if amount <= 0:
            return await interaction.followup.send(
                embed=error_embed("Çekilecek miktar 0'dan büyük olmalı."), ephemeral=True)
        if data["bank"] < amount:
            return await interaction.followup.send(embed=error_embed(
                "Yetersiz Banka Bakiyesi",
                f"Bankanda bu kadar para yok. Banka bakiyen: {self._currency(data['bank'])}"
            ), ephemeral=True)

        await db.update_bank(interaction.user.id, interaction.guild.id, -amount)
        await db.update_balance(interaction.user.id, interaction.guild.id, amount)

        await interaction.followup.send(embed=success_embed(
            "Para Çekildi 💵",
            f"{self._currency(amount)} bankadan çekildi.\n"
            f"Cüzdan bakiyen: {self._currency(data['balance'] + amount)}"
        ))

    @app_commands.command(name="zenginler", description="Sunucunun para sıralamasını gösterir.")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await db.get_leaderboard(interaction.guild.id, limit=10)

        if not rows:
            return await interaction.followup.send(embed=info_embed(
                "Sıralama Boş", "Henüz kimse ekonomi sistemini kullanmamış!"))

        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} - Para Sıralaması",
            color=Colors.ECONOMY,
            timestamp=datetime.datetime.utcnow()
        )
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, 1):
            member = interaction.guild.get_member(row["user_id"])
            name   = member.display_name if member else f"ID: {row['user_id']}"
            medal  = medals[i - 1] if i <= 3 else f"`{i}.`"
            embed.add_field(
                name=f"{medal} {name}",
                value=self._currency(row["total"]),
                inline=False
            )
        await interaction.followup.send(embed=embed)

    # ── ADMIN SLASH KOMUTLARI ────────────────────────────────────────────

    @app_commands.command(name="para-ver", description="[ADMIN] Kullanıcıya para verir.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(üye="Para verilecek kullanıcı", miktar="Verilecek miktar")
    async def admin_give(self, interaction: discord.Interaction,
                         üye: discord.Member, miktar: int):
        await interaction.response.defer(ephemeral=True)
        if miktar <= 0:
            return await interaction.followup.send(
                embed=error_embed("Geçerli bir miktar gir!"), ephemeral=True)
        await db.get_economy(üye.id, interaction.guild.id)
        await db.update_balance(üye.id, interaction.guild.id, miktar)
        await interaction.followup.send(embed=success_embed(
            "Para Verildi",
            f"**{üye.mention}** kullanıcısına {self._currency(miktar)} verildi."
        ))

    @app_commands.command(name="bakiye-sıfırla", description="[ADMIN] Kullanıcının bakiyesini sıfırlar.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(üye="Bakiyesi sıfırlanacak kullanıcı")
    async def admin_reset(self, interaction: discord.Interaction, üye: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await db.set_balance(üye.id, interaction.guild.id, 0)
        await interaction.followup.send(embed=success_embed(
            "Bakiye Sıfırlandı",
            f"**{üye.mention}** kullanıcısının bakiyesi sıfırlandı."
        ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))

"""
cogs/economy.py
SQLite tabanlı ekonomi sistemi.
Bakiye, banka, günlük ödül, para transferi ve liderlik tablosu içerir.
"""

import discord
from discord.ext import commands
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
        self.DAILY_AMOUNT  = 500    # Günlük ödül miktarı
        self.DAILY_COOLDOWN = 86400  # 24 saat (saniye)
        self.CURRENCY      = "💰"    # Para birimi simgesi
        self.CURRENCY_NAME = "Altın"

    def _currency(self, amount: int) -> str:
        """Para miktarını formatlar."""
        return f"{self.CURRENCY} **{format_number(amount)}** {self.CURRENCY_NAME}"

    # ─────────────────────────────────────────────
    # BAKİYE KOMUTLARI
    # ─────────────────────────────────────────────

    @commands.command(name="bakiye", aliases=["balance", "bal", "para"],
                      help="Bakiyeni veya başka birinin bakiyesini gösterir.")
    @commands.guild_only()
    async def balance(self, ctx: commands.Context,
                      member: discord.Member = None):
        """
        Bakiyeyi gösterir.
        Kullanım: !bakiye veya !bakiye @kullanıcı
        """
        member = member or ctx.author
        data   = await db.get_economy(member.id, ctx.guild.id)

        total = data["balance"] + data["bank"]
        embed = discord.Embed(
            title=f"{self.CURRENCY} {member.display_name} - Bakiye",
            color=Colors.ECONOMY,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👛 Cüzdan",
                        value=self._currency(data["balance"]), inline=True)
        embed.add_field(name="🏦 Banka",
                        value=self._currency(data["bank"]), inline=True)
        embed.add_field(name="💎 Toplam",
                        value=self._currency(total), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="günlük", aliases=["daily"],
                      help="Günlük ödülünü alır.")
    @commands.guild_only()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def daily(self, ctx: commands.Context):
        """
        Her 24 saatte bir günlük ödül alırsın.
        Kullanım: !günlük
        """
        data = await db.get_economy(ctx.author.id, ctx.guild.id)
        now  = datetime.datetime.utcnow()

        if data["last_daily"]:
            last = datetime.datetime.fromisoformat(data["last_daily"])
            elapsed = (now - last).total_seconds()
            remaining = self.DAILY_COOLDOWN - elapsed

            if remaining > 0:
                hours   = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                seconds = int(remaining % 60)
                return await ctx.send(embed=error_embed(
                    "Henüz Zamanı Gelmedi",
                    f"Günlük ödülünü aldın! **{hours}s {minutes}d {seconds}sn** sonra tekrar al."
                ))

        # Streak hesaplama (ardışık gün bonusu)
        streak_bonus = 0
        if data["last_daily"]:
            last = datetime.datetime.fromisoformat(data["last_daily"])
            if (now - last).total_seconds() < self.DAILY_COOLDOWN * 1.5:
                streak_bonus = 100  # Ardışık gün bonusu

        reward = self.DAILY_AMOUNT + streak_bonus
        await db.update_balance(ctx.author.id, ctx.guild.id, reward)
        await db.set_last_daily(ctx.author.id, ctx.guild.id, now.isoformat())

        embed = success_embed(
            "Günlük Ödül Alındı! 🎁",
            f"**{self._currency(reward)}** aldın!"
        )
        embed.color = Colors.ECONOMY
        if streak_bonus:
            embed.add_field(name="🔥 Seri Bonusu",
                            value=f"+{self._currency(streak_bonus)}", inline=False)
        embed.add_field(name="💰 Yeni Bakiye",
                        value=self._currency(data["balance"] + reward))
        await ctx.send(embed=embed)

    @commands.command(name="gönder", aliases=["transfer", "pay"],
                      help="Başka bir kullanıcıya para gönderir.")
    @commands.guild_only()
    async def transfer(self, ctx: commands.Context,
                       member: discord.Member, amount: int):
        """
        Başka birine para gönderir.
        Kullanım: !gönder @kullanıcı 1000
        """
        if member == ctx.author:
            return await ctx.send(embed=error_embed("Kendine para gönderemezsin!"))
        if member.bot:
            return await ctx.send(embed=error_embed("Botlara para gönderemezsin!"))
        if amount <= 0:
            return await ctx.send(embed=error_embed("Geçerli bir miktar gir!"))

        sender_data = await db.get_economy(ctx.author.id, ctx.guild.id)
        if sender_data["balance"] < amount:
            return await ctx.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Cüzdanında yeterli para yok. Bakiyen: {self._currency(sender_data['balance'])}"
            ))

        # Para transferi
        await db.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await db.update_balance(member.id, ctx.guild.id, amount)
        await db.get_economy(member.id, ctx.guild.id)  # Alıcı kaydı oluştur

        embed = success_embed(
            "Para Gönderildi 💸",
            f"**{ctx.author.mention}** → **{member.mention}**\n"
            f"Miktar: {self._currency(amount)}"
        )
        embed.color = Colors.ECONOMY
        await ctx.send(embed=embed)

    @commands.command(name="yatır", aliases=["deposit"],
                      help="Cüzdandan bankaya para yatırır.")
    @commands.guild_only()
    async def deposit(self, ctx: commands.Context, amount):
        """
        Bankaya para yatırır.
        Kullanım: !yatır 1000 veya !yatır tümü
        """
        data = await db.get_economy(ctx.author.id, ctx.guild.id)

        if str(amount).lower() in ("tümü", "all", "hepsi"):
            amount = data["balance"]
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send(embed=error_embed("Geçerli bir miktar gir!"))

        if amount <= 0:
            return await ctx.send(embed=error_embed("Yatırılacak miktar 0'dan büyük olmalı."))
        if data["balance"] < amount:
            return await ctx.send(embed=error_embed(
                "Yetersiz Bakiye",
                f"Cüzdanında bu kadar para yok. Bakiyen: {self._currency(data['balance'])}"
            ))

        await db.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await db.update_bank(ctx.author.id, ctx.guild.id, amount)

        await ctx.send(embed=success_embed(
            "Para Yatırıldı 🏦",
            f"{self._currency(amount)} bankaya yatırıldı.\n"
            f"Banka bakiyen: {self._currency(data['bank'] + amount)}"
        ))

    @commands.command(name="çek", aliases=["withdraw"],
                      help="Bankadan cüzdana para çeker.")
    @commands.guild_only()
    async def withdraw(self, ctx: commands.Context, amount):
        """
        Bankadan para çeker.
        Kullanım: !çek 1000 veya !çek tümü
        """
        data = await db.get_economy(ctx.author.id, ctx.guild.id)

        if str(amount).lower() in ("tümü", "all", "hepsi"):
            amount = data["bank"]
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send(embed=error_embed("Geçerli bir miktar gir!"))

        if amount <= 0:
            return await ctx.send(embed=error_embed("Çekilecek miktar 0'dan büyük olmalı."))
        if data["bank"] < amount:
            return await ctx.send(embed=error_embed(
                "Yetersiz Banka Bakiyesi",
                f"Bankanda bu kadar para yok. Banka bakiyen: {self._currency(data['bank'])}"
            ))

        await db.update_bank(ctx.author.id, ctx.guild.id, -amount)
        await db.update_balance(ctx.author.id, ctx.guild.id, amount)

        await ctx.send(embed=success_embed(
            "Para Çekildi 💵",
            f"{self._currency(amount)} bankadan çekildi.\n"
            f"Cüzdan bakiyen: {self._currency(data['balance'] + amount)}"
        ))

    @commands.command(name="zenginler", aliases=["leaderboard", "lb", "sıralama"],
                      help="Sunucunun para sıralamasını gösterir.")
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context):
        """Sunucunun en zengin kullanıcılarını listeler."""
        rows = await db.get_leaderboard(ctx.guild.id, limit=10)

        if not rows:
            return await ctx.send(embed=info_embed(
                "Sıralama Boş",
                "Henüz kimse ekonomi sistemini kullanmamış!"
            ))

        embed = discord.Embed(
            title=f"🏆 {ctx.guild.name} - Para Sıralaması",
            color=Colors.ECONOMY,
            timestamp=datetime.datetime.utcnow()
        )

        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, 1):
            member = ctx.guild.get_member(row["user_id"])
            name   = member.display_name if member else f"ID: {row['user_id']}"
            medal  = medals[i - 1] if i <= 3 else f"`{i}.`"
            embed.add_field(
                name=f"{medal} {name}",
                value=self._currency(row["total"]),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="vermek", aliases=["give"],
                      help="[ADMIN] Kullanıcıya para verir.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def admin_give(self, ctx: commands.Context,
                         member: discord.Member, amount: int):
        """Admin komutu: Kullanıcıya para verir."""
        if amount <= 0:
            return await ctx.send(embed=error_embed("Geçerli bir miktar gir!"))
        await db.get_economy(member.id, ctx.guild.id)
        await db.update_balance(member.id, ctx.guild.id, amount)
        await ctx.send(embed=success_embed(
            "Para Verildi",
            f"**{member.mention}** kullanıcısına {self._currency(amount)} verildi."
        ))

    @commands.command(name="sıfırla", aliases=["resetbalance"],
                      help="[ADMIN] Kullanıcının bakiyesini sıfırlar.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def admin_reset(self, ctx: commands.Context, member: discord.Member):
        """Admin komutu: Kullanıcının bakiyesini sıfırlar."""
        await db.set_balance(member.id, ctx.guild.id, 0)
        await ctx.send(embed=success_embed(
            "Bakiye Sıfırlandı",
            f"**{member.mention}** kullanıcısının bakiyesi sıfırlandı."
        ))


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(Economy(bot))
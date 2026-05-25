"""
cogs/leveling.py
Mesaj bazlı XP ve seviye sistemi.
Her mesajda XP kazanılır, belirli eşikte seviye atlanır.
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


class Leveling(commands.Cog, name="Seviyeler"):
    """XP ve seviye yükseltme sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.XP_PER_MESSAGE = (15, 25)  # Her mesajda kazanılacak XP aralığı
        self._xp_cooldowns  = {}         # Spam koruması: {user_id: last_xp_time}

    def _xp_for_level(self, level: int) -> int:
        """Belirli seviyeye ulaşmak için gereken XP."""
        return 5 * (level ** 2) + 50 * level + 100

    def _total_xp_for_level(self, level: int) -> int:
        """O seviyeye kadar gereken toplam XP."""
        return sum(self._xp_for_level(i) for i in range(level))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Her mesajda XP kazandırır.
        60 saniyelik cooldown ile spam önlenir.
        """
        if message.author.bot or not message.guild:
            return
        # Eski hali: if message.content.startswith(self.bot.command_prefix):
# Yeni hali:
        if message.content.startswith(self.bot.command_prefix if isinstance(self.bot.command_prefix, str) else "!"):
            return  # Komutlarda XP kazanılmasın

        user_id  = message.author.id
        guild_id = message.guild.id
        now      = datetime.datetime.utcnow().timestamp()

        # Cooldown kontrolü (60 saniye)
        key = f"{user_id}:{guild_id}"
        if key in self._xp_cooldowns:
            if now - self._xp_cooldowns[key] < 60:
                return

        self._xp_cooldowns[key] = now

        # Rastgele XP ver
        import random
        xp = random.randint(*self.XP_PER_MESSAGE)
        result = await db.add_xp(user_id, guild_id, xp)

        # Seviye atlandıysa kutla
        if result["leveled_up"]:
            new_level = result["new_level"]
            embed = discord.Embed(
                title="🎉 Seviye Atlandı!",
                description=(
                    f"Tebrikler {message.author.mention}!\n"
                    f"**Seviye {new_level - 1}** → **Seviye {new_level}** 🚀"
                ),
                color=Colors.LEVEL,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)

            # Seviye ödülü (ekonomi ile entegre)
            reward = new_level * 100
            await db.get_economy(user_id, guild_id)
            await db.update_balance(user_id, guild_id, reward)
            embed.add_field(
                name="🎁 Seviye Ödülü",
                value=f"+💰 **{format_number(reward)}** Altın"
            )

            try:
                lvl_msg = await message.channel.send(embed=embed)
                await asyncio.sleep(10)
                await lvl_msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

    # ─────────────────────────────────────────────
    # KOMUTLAR
    # ─────────────────────────────────────────────

    @commands.command(name="seviye", aliases=["level", "rank", "xp"],
                      help="Kendi veya başkasının seviyesini gösterir.")
    @commands.guild_only()
    async def level(self, ctx: commands.Context,
                    member: discord.Member = None):
        """
        Kullanıcının seviyesini ve XP bilgisini gösterir.
        Kullanım: !seviye veya !seviye @kullanıcı
        """
        member = member or ctx.author
        data   = await db.get_level(member.id, ctx.guild.id)

        current_level = data["level"]
        current_xp    = data["xp"]
        needed_xp     = self._xp_for_level(current_level)

        # Sıralama hesapla
        leaderboard = await db.get_level_leaderboard(ctx.guild.id, limit=100)
        rank = next((i + 1 for i, r in enumerate(leaderboard)
                     if r["user_id"] == member.id), "?")

        embed = discord.Embed(
            title=f"⭐ {member.display_name} - Seviye Kartı",
            color=Colors.LEVEL,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🏆 Seviye",
                        value=f"**{current_level}**", inline=True)
        embed.add_field(name="📊 Sıralama",
                        value=f"**#{rank}**", inline=True)
        embed.add_field(name="💬 Mesaj",
                        value=f"**{format_number(data['messages'])}**", inline=True)
        embed.add_field(
            name=f"✨ XP - {current_xp}/{needed_xp}",
            value=f"```{progress_bar(current_xp, needed_xp, 20)}```",
            inline=False
        )
        embed.add_field(
            name="📈 Toplam XP",
            value=f"**{format_number(self._total_xp_for_level(current_level) + current_xp)}**"
        )
        await ctx.send(embed=embed)

    @commands.command(name="seviyeliderlik", aliases=["levelboard", "xpboard"],
                      help="XP liderlik tablosunu gösterir.")
    @commands.guild_only()
    async def level_leaderboard(self, ctx: commands.Context):
        """Sunucunun XP sıralamasını gösterir."""
        rows = await db.get_level_leaderboard(ctx.guild.id, limit=10)

        if not rows:
            return await ctx.send(embed=info_embed(
                "Liderlik Tablosu Boş",
                "Henüz kimse XP kazanmamış!"
            ))

        embed = discord.Embed(
            title=f"⭐ {ctx.guild.name} - XP Sıralaması",
            color=Colors.LEVEL,
            timestamp=datetime.datetime.utcnow()
        )

        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, 1):
            member = ctx.guild.get_member(row["user_id"])
            name   = member.display_name if member else f"ID: {row['user_id']}"
            medal  = medals[i - 1] if i <= 3 else f"`{i}.`"
            embed.add_field(
                name=f"{medal} {name}",
                value=f"Seviye **{row['level']}** | XP: {format_number(row['xp'])} | "
                      f"Mesaj: {format_number(row['messages'])}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="xpver", aliases=["givexp"],
                      help="[ADMIN] Kullanıcıya XP verir.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give_xp(self, ctx: commands.Context,
                      member: discord.Member, amount: int):
        """Admin komutu: Kullanıcıya XP verir."""
        for _ in range(amount // 20 + 1):
            await db.add_xp(member.id, ctx.guild.id, min(amount, 20))
        await ctx.send(embed=success_embed(
            "XP Verildi",
            f"**{member.mention}** kullanıcısına **{amount}** XP verildi."
        ))

    @commands.command(name="seviyelesifirla", aliases=["resetlevel"],
                      help="[ADMIN] Kullanıcının seviyesini sıfırlar.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def reset_level(self, ctx: commands.Context, member: discord.Member):
        """Admin komutu: Kullanıcının XP ve seviyesini sıfırlar."""
        import aiosqlite
        async with aiosqlite.connect("database/bot_database.db") as db_conn:
            await db_conn.execute(
                "UPDATE levels SET xp=0, level=0, messages=0 WHERE user_id=? AND guild_id=?",
                (member.id, ctx.guild.id)
            )
            await db_conn.commit()
        await ctx.send(embed=success_embed(
            "Seviye Sıfırlandı",
            f"**{member.mention}** kullanıcısının seviyesi sıfırlandı."
        ))


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(Leveling(bot))

"""
cogs/leveling.py
Mesaj bazlı XP ve seviye sistemi — Slash komutlarına geçirildi.
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random

from database import db
from utils.helpers import (
    success_embed, error_embed, info_embed, Colors,
    format_number, progress_bar
)


class Leveling(commands.Cog, name="Seviyeler"):
    """XP ve seviye yükseltme sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.XP_PER_MESSAGE = (15, 25)
        self._xp_cooldowns  = {}

    def _xp_for_level(self, level: int) -> int:
        return 5 * (level ** 2) + 50 * level + 100

    def _total_xp_for_level(self, level: int) -> int:
        return sum(self._xp_for_level(i) for i in range(level))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Her mesajda XP kazandırır (60 saniyelik cooldown)."""
        if message.author.bot or not message.guild:
            return

        # Prefix ile başlayan komut mesajlarında XP verme
        try:
            prefixes = await self.bot.get_prefix(message)
            if isinstance(prefixes, str):
                prefixes = [prefixes]
            if any(message.content.startswith(p) for p in prefixes):
                return
        except Exception:
            pass

        user_id  = message.author.id
        guild_id = message.guild.id
        now      = datetime.datetime.utcnow().timestamp()

        key = f"{user_id}:{guild_id}"
        if key in self._xp_cooldowns:
            if now - self._xp_cooldowns[key] < 60:
                return

        self._xp_cooldowns[key] = now

        xp     = random.randint(*self.XP_PER_MESSAGE)
        result = await db.add_xp(user_id, guild_id, xp)

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

    # ── SLASH KOMUTLAR ───────────────────────────────────────────────────

    @app_commands.command(name="seviye", description="Kendi veya başkasının seviyesini gösterir.")
    @app_commands.guild_only()
    @app_commands.describe(üye="Seviyesini görmek istediğin kullanıcı")
    async def level(self, interaction: discord.Interaction,
                    üye: discord.Member = None):
        await interaction.response.defer()
        member = üye or interaction.user
        data   = await db.get_level(member.id, interaction.guild.id)

        current_level = data["level"]
        current_xp    = data["xp"]
        needed_xp     = self._xp_for_level(current_level)

        leaderboard = await db.get_level_leaderboard(interaction.guild.id, limit=100)
        rank = next((i + 1 for i, r in enumerate(leaderboard)
                     if r["user_id"] == member.id), "?")

        embed = discord.Embed(
            title=f"⭐ {member.display_name} - Seviye Kartı",
            color=Colors.LEVEL,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🏆 Seviye", value=f"**{current_level}**", inline=True)
        embed.add_field(name="📊 Sıralama", value=f"**#{rank}**",       inline=True)
        embed.add_field(name="💬 Mesaj",
                        value=f"**{format_number(data['messages'])}**",  inline=True)
        embed.add_field(
            name=f"✨ XP - {current_xp}/{needed_xp}",
            value=f"```{progress_bar(current_xp, needed_xp, 20)}```",
            inline=False
        )
        embed.add_field(
            name="📈 Toplam XP",
            value=f"**{format_number(self._total_xp_for_level(current_level) + current_xp)}**"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="xp-sıralama", description="XP liderlik tablosunu gösterir.")
    @app_commands.guild_only()
    async def level_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await db.get_level_leaderboard(interaction.guild.id, limit=10)

        if not rows:
            return await interaction.followup.send(embed=info_embed(
                "Liderlik Tablosu Boş", "Henüz kimse XP kazanmamış!"))

        embed = discord.Embed(
            title=f"⭐ {interaction.guild.name} - XP Sıralaması",
            color=Colors.LEVEL,
            timestamp=datetime.datetime.utcnow()
        )
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, 1):
            member = interaction.guild.get_member(row["user_id"])
            name   = member.display_name if member else f"ID: {row['user_id']}"
            medal  = medals[i - 1] if i <= 3 else f"`{i}.`"
            embed.add_field(
                name=f"{medal} {name}",
                value=f"Seviye **{row['level']}** | XP: {format_number(row['xp'])} | "
                      f"Mesaj: {format_number(row['messages'])}",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="xp-ver", description="[ADMIN] Kullanıcıya XP verir.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(üye="XP verilecek kullanıcı", miktar="Verilecek XP miktarı")
    async def give_xp(self, interaction: discord.Interaction,
                      üye: discord.Member, miktar: int):
        await interaction.response.defer(ephemeral=True)
        for _ in range(miktar // 20 + 1):
            await db.add_xp(üye.id, interaction.guild.id, min(miktar, 20))
        await interaction.followup.send(embed=success_embed(
            "XP Verildi",
            f"**{üye.mention}** kullanıcısına **{miktar}** XP verildi."
        ))

    @app_commands.command(name="seviye-sıfırla", description="[ADMIN] Kullanıcının seviyesini sıfırlar.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(üye="Seviyesi sıfırlanacak kullanıcı")
    async def reset_level(self, interaction: discord.Interaction, üye: discord.Member):
        await interaction.response.defer(ephemeral=True)
        import aiosqlite
        async with aiosqlite.connect("database/bot_database.db") as db_conn:
            await db_conn.execute(
                "UPDATE levels SET xp=0, level=0, messages=0 WHERE user_id=? AND guild_id=?",
                (üye.id, interaction.guild.id)
            )
            await db_conn.commit()
        await interaction.followup.send(embed=success_embed(
            "Seviye Sıfırlandı",
            f"**{üye.mention}** kullanıcısının seviyesi sıfırlandı."
        ))


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))

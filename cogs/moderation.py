"""
cogs/moderation.py
Gelişmiş moderasyon sistemi.
Ban, kick, mute, timeout, uyarı, küfür/link filtresi ve log sistemi içerir.
"""

import discord
from discord.ext import commands
import datetime
import asyncio

from database import db
from utils.helpers import (
    success_embed, error_embed, info_embed, warning_embed,
    is_mod, is_admin, PROFANITY_WORDS, LINK_PATTERN, Colors
)


class Moderation(commands.Cog, name="Moderasyon"):
    """Sunucu moderasyon araçları."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─────────────────────────────────────────────
    # LOG YARDIMCI FONKSİYONLARI
    # ─────────────────────────────────────────────

    async def send_mod_log(self, guild: discord.Guild, embed: discord.Embed):
        """Moderasyon log kanalına mesaj gönderir."""
        settings = await db.get_guild_settings(guild.id)
        if settings["mod_log"]:
            channel = guild.get_channel(settings["mod_log"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def send_message_log(self, guild: discord.Guild, embed: discord.Embed):
        """Mesaj log kanalına mesaj gönderir."""
        settings = await db.get_guild_settings(guild.id)
        if settings["log_channel"]:
            channel = guild.get_channel(settings["log_channel"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def send_join_leave_log(self, guild: discord.Guild, embed: discord.Embed):
        """Giriş/çıkış log kanalına mesaj gönderir."""
        settings = await db.get_guild_settings(guild.id)
        if settings["join_leave_log"]:
            channel = guild.get_channel(settings["join_leave_log"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def send_voice_log(self, guild: discord.Guild, embed: discord.Embed):
        """Ses kanalı log kanalına mesaj gönderir."""
        settings = await db.get_guild_settings(guild.id)
        if settings["voice_log"]:
            channel = guild.get_channel(settings["voice_log"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    # ─────────────────────────────────────────────
    # MODERASYON KOMUTLARI
    # ─────────────────────────────────────────────

    @commands.command(name="ban", help="Bir kullanıcıyı sunucudan yasaklar.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, member: discord.Member,
                  *, reason: str = "Sebep belirtilmedi"):
        """
        Kullanıcıyı sunucudan banlar.
        Kullanım: !ban @kullanıcı [sebep]
        """
        # Kendini veya botu banlamamayı kontrol et
        if member == ctx.author:
            return await ctx.send(embed=error_embed("Kendini banlayamazsın!"))
        if member == ctx.guild.me:
            return await ctx.send(embed=error_embed("Beni banlayamazsın!"))
        # Rol hiyerarşisi kontrolü
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed(
                "Hedef kişi senden üst veya eşit roldedir, işlem yapılamaz."
            ))

        try:
            # Kullanıcıya DM gönder (ban öncesi)
            try:
                await member.send(embed=warning_embed(
                    "Sunucudan Yasaklandın",
                    f"**{ctx.guild.name}** sunucusundan yasaklandın.\n"
                    f"**Sebep:** {reason}\n"
                    f"**Yetkili:** {ctx.author}"
                ))
            except discord.Forbidden:
                pass  # DM kapalıysa devam et

            await member.ban(reason=f"{ctx.author} | {reason}")

            embed = success_embed(
                "Kullanıcı Yasaklandı",
                f"**{member}** sunucudan yasaklandı.\n"
                f"**Sebep:** {reason}"
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)

            # Mod log'a gönder
            log_embed = discord.Embed(
                title="🔨 Kullanıcı Banlandı",
                color=Colors.MOD,
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            log_embed.add_field(name="Yetkili", value=f"{ctx.author} ({ctx.author.id})")
            log_embed.add_field(name="Sebep", value=reason, inline=False)
            await self.send_mod_log(ctx.guild, log_embed)

        except discord.Forbidden:
            await ctx.send(embed=error_embed("Bu kullanıcıyı banlayacak yetkim yok."))

    @commands.command(name="unban", help="Yasaklı bir kullanıcının yasağını kaldırır.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx: commands.Context, *, user_id_or_name: str):
        """
        Yasaklı kullanıcının yasağını kaldırır.
        Kullanım: !unban 123456789 veya !unban Kullanıcı#0000
        """
        banned_users = [entry async for entry in ctx.guild.bans()]

        # ID ile arama
        target = None
        if user_id_or_name.isdigit():
            user_id = int(user_id_or_name)
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    target = ban_entry.user
                    break
        else:
            # İsim ile arama
            for ban_entry in banned_users:
                if str(ban_entry.user) == user_id_or_name:
                    target = ban_entry.user
                    break

        if target is None:
            return await ctx.send(embed=error_embed(
                "Kullanıcı Bulunamadı",
                "Bu ID veya isimde yasaklı bir kullanıcı bulunamadı."
            ))

        await ctx.guild.unban(target, reason=f"Yasak kaldırıldı | Yetkili: {ctx.author}")
        embed = success_embed(
            "Yasak Kaldırıldı",
            f"**{target}** kullanıcısının yasağı kaldırıldı."
        )
        await ctx.send(embed=embed)

        log_embed = discord.Embed(
            title="🔓 Yasak Kaldırıldı",
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Kullanıcı", value=f"{target} ({target.id})")
        log_embed.add_field(name="Yetkili", value=f"{ctx.author} ({ctx.author.id})")
        await self.send_mod_log(ctx.guild, log_embed)

    @commands.command(name="kick", help="Bir kullanıcıyı sunucudan atar.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, member: discord.Member,
                   *, reason: str = "Sebep belirtilmedi"):
        """
        Kullanıcıyı sunucudan atar.
        Kullanım: !kick @kullanıcı [sebep]
        """
        if member == ctx.author:
            return await ctx.send(embed=error_embed("Kendini atamazsın!"))
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed(
                "Hedef kişi senden üst veya eşit roldedir."
            ))

        try:
            try:
                await member.send(embed=warning_embed(
                    "Sunucudan Atıldın",
                    f"**{ctx.guild.name}** sunucusundan atıldın.\n"
                    f"**Sebep:** {reason}"
                ))
            except discord.Forbidden:
                pass

            await member.kick(reason=f"{ctx.author} | {reason}")
            embed = success_embed(
                "Kullanıcı Atıldı",
                f"**{member}** sunucudan atıldı.\n**Sebep:** {reason}"
            )
            await ctx.send(embed=embed)

            log_embed = discord.Embed(
                title="👢 Kullanıcı Atıldı",
                color=Colors.WARNING,
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            log_embed.add_field(name="Yetkili", value=str(ctx.author))
            log_embed.add_field(name="Sebep", value=reason, inline=False)
            await self.send_mod_log(ctx.guild, log_embed)

        except discord.Forbidden:
            await ctx.send(embed=error_embed("Bu kullanıcıyı atma yetkim yok."))

    @commands.command(name="timeout", aliases=["sustur"],
                      help="Kullanıcıyı belirli süre susturur.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def timeout_member(self, ctx: commands.Context, member: discord.Member,
                             duration: int, unit: str = "dakika",
                             *, reason: str = "Sebep belirtilmedi"):
        """
        Kullanıcıya timeout uygular.
        Kullanım: !timeout @kullanıcı 10 dakika [sebep]
        Birimler: saniye, dakika, saat, gün
        """
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("Bu kullanıcıya işlem yapamazsın."))

        # Süreyi saniyeye çevir
        unit_map = {
            "saniye": 1, "s": 1,
            "dakika": 60, "d": 60, "dk": 60,
            "saat": 3600, "sa": 3600,
            "gün": 86400, "gun": 86400
        }
        multiplier = unit_map.get(unit.lower(), 60)
        total_seconds = duration * multiplier

        # Discord maksimum timeout süresi: 28 gün
        if total_seconds > 86400 * 28:
            return await ctx.send(embed=error_embed(
                "Maksimum timeout süresi 28 gündür."
            ))

        until = datetime.datetime.utcnow() + datetime.timedelta(seconds=total_seconds)

        try:
            await member.timeout(until, reason=f"{ctx.author} | {reason}")
            embed = success_embed(
                "Kullanıcı Susturuldu",
                f"**{member}** {duration} {unit} süreyle susturuldu.\n"
                f"**Sebep:** {reason}"
            )
            await ctx.send(embed=embed)

            log_embed = discord.Embed(
                title="🔇 Timeout Uygulandı",
                color=Colors.MOD,
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            log_embed.add_field(name="Süre", value=f"{duration} {unit}")
            log_embed.add_field(name="Yetkili", value=str(ctx.author))
            log_embed.add_field(name="Sebep", value=reason, inline=False)
            await self.send_mod_log(ctx.guild, log_embed)

        except discord.Forbidden:
            await ctx.send(embed=error_embed("Bu kullanıcıya timeout uygulayamam."))

    @commands.command(name="untimeout", aliases=["unsustur"],
                      help="Kullanıcının susturmasını kaldırır.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def untimeout_member(self, ctx: commands.Context, member: discord.Member):
        """Kullanıcının timeout'unu kaldırır."""
        try:
            await member.timeout(None, reason=f"Timeout kaldırıldı | {ctx.author}")
            await ctx.send(embed=success_embed(
                "Timeout Kaldırıldı",
                f"**{member}** artık konuşabilir."
            ))
        except discord.Forbidden:
            await ctx.send(embed=error_embed("Bu kullanıcının timeout'unu kaldıramam."))

    @commands.command(name="uyar", aliases=["warn"],
                      help="Kullanıcıya uyarı verir.")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def warn(self, ctx: commands.Context, member: discord.Member,
                   *, reason: str = "Sebep belirtilmedi"):
        """
        Kullanıcıya uyarı kaydeder.
        Kullanım: !uyar @kullanıcı [sebep]
        """
        timestamp = datetime.datetime.utcnow().isoformat()
        warn_id = await db.add_warning(member.id, ctx.guild.id,
                                       ctx.author.id, reason, timestamp)

        # Toplam uyarı sayısını getir
        warnings = await db.get_warnings(member.id, ctx.guild.id)

        embed = warning_embed(
            "Uyarı Verildi",
            f"**{member}** uyarıldı.\n"
            f"**Sebep:** {reason}\n"
            f"**Uyarı ID:** #{warn_id}\n"
            f"**Toplam Uyarı:** {len(warnings)}"
        )
        await ctx.send(embed=embed)

        # Kullanıcıya DM
        try:
            await member.send(embed=warning_embed(
                f"{ctx.guild.name} - Uyarı Aldın",
                f"**Sebep:** {reason}\n"
                f"**Yetkili:** {ctx.author}\n"
                f"**Toplam uyarın:** {len(warnings)}"
            ))
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(
            title="⚠️ Uyarı Kaydedildi",
            color=Colors.WARNING,
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
        log_embed.add_field(name="Yetkili", value=str(ctx.author))
        log_embed.add_field(name="Sebep", value=reason, inline=False)
        log_embed.add_field(name="Toplam Uyarı", value=str(len(warnings)))
        await self.send_mod_log(ctx.guild, log_embed)

    @commands.command(name="uyarilar", aliases=["warnings"],
                      help="Bir kullanıcının uyarılarını listeler.")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def warnings_list(self, ctx: commands.Context,
                            member: discord.Member = None):
        """Kullanıcının tüm uyarılarını listeler."""
        if member is None:
            member = ctx.author

        warnings = await db.get_warnings(member.id, ctx.guild.id)

        if not warnings:
            return await ctx.send(embed=info_embed(
                "Uyarı Yok",
                f"**{member}** kullanıcısının hiç uyarısı yok."
            ))

        embed = discord.Embed(
            title=f"⚠️ {member} - Uyarı Listesi",
            color=Colors.WARNING,
            description=f"Toplam **{len(warnings)}** uyarı"
        )

        for w in warnings[:10]:  # En fazla 10 uyarı göster
            mod = ctx.guild.get_member(w["moderator"]) or f"ID: {w['moderator']}"
            embed.add_field(
                name=f"Uyarı #{w['id']}",
                value=f"**Sebep:** {w['reason']}\n"
                      f"**Yetkili:** {mod}\n"
                      f"**Tarih:** {w['timestamp'][:10]}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="uyarisil", aliases=["clearwarnings"],
                      help="Kullanıcının tüm uyarılarını siler.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def clear_warnings(self, ctx: commands.Context, member: discord.Member):
        """Kullanıcının tüm uyarılarını temizler."""
        await db.clear_warnings(member.id, ctx.guild.id)
        await ctx.send(embed=success_embed(
            "Uyarılar Temizlendi",
            f"**{member}** kullanıcısının tüm uyarıları silindi."
        ))

    @commands.command(name="temizle", aliases=["purge", "clear"],
                      help="Belirli sayıda mesajı siler.")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge(self, ctx: commands.Context, amount: int,
                    member: discord.Member = None):
        """
        Kanaldan belirli sayıda mesaj siler.
        Kullanım: !temizle 10 veya !temizle 10 @kullanıcı
        """
        if amount < 1 or amount > 200:
            return await ctx.send(embed=error_embed(
                "1 ile 200 arasında bir sayı gir."
            ), delete_after=5)

        await ctx.message.delete()

        if member:
            # Belirli kullanıcının mesajlarını sil
            def check(m):
                return m.author == member
            deleted = await ctx.channel.purge(limit=amount * 5, check=check,
                                              bulk=True)
            deleted = deleted[:amount]
        else:
            deleted = await ctx.channel.purge(limit=amount, bulk=True)

        msg = await ctx.send(embed=success_embed(
            "Mesajlar Silindi",
            f"**{len(deleted)}** mesaj silindi."
        ))
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(name="yavaşmod", aliases=["slowmode"],
                      help="Kanalda yavaş modu ayarlar.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(self, ctx: commands.Context, seconds: int = 0):
        """
        Kanal yavaş modunu ayarlar.
        Kullanım: !yavaşmod 5 (5 saniye) | !yavaşmod 0 (kapat)
        """
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=error_embed(
                "Süre 0 ile 21600 saniye (6 saat) arasında olmalı."
            ))

        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send(embed=success_embed("Yavaş Mod Kapatıldı"))
        else:
            await ctx.send(embed=success_embed(
                "Yavaş Mod Açıldı",
                f"Bu kanalda mesajlar arası bekleme: **{seconds} saniye**"
            ))

    @commands.command(name="kilitle", aliases=["lock"],
                      help="Kanalı kilitler (üyeler mesaj atamaz).")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def lock_channel(self, ctx: commands.Context,
                           channel: discord.TextChannel = None):
        """Kanalı kilitler."""
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=success_embed(
            "Kanal Kilitlendi",
            f"{channel.mention} kanalı kilitlendi."
        ))

    @commands.command(name="kilitsiz", aliases=["unlock"],
                      help="Kanalın kilidini açar.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unlock_channel(self, ctx: commands.Context,
                             channel: discord.TextChannel = None):
        """Kanal kilidini açar."""
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=success_embed(
            "Kanal Kilidi Açıldı",
            f"{channel.mention} kanalının kilidi açıldı."
        ))

    # ─────────────────────────────────────────────
    # SUNUCU AYARLARI
    # ─────────────────────────────────────────────

    @commands.group(name="ayarla", aliases=["set"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def settings(self, ctx: commands.Context):
        """Sunucu ayarlama komutları grubu."""
        settings = await db.get_guild_settings(ctx.guild.id)
        embed = info_embed(
            "Sunucu Ayarları",
            f"**Prefix:** `{settings['prefix']}`\n"
            f"**Küfür Filtresi:** {'✅' if settings['profanity_filter'] else '❌'}\n"
            f"**Link Filtresi:** {'✅' if settings['link_filter'] else '❌'}\n\n"
            f"Ayar değiştirmek için alt komutları kullan:\n"
            f"`!ayarla logkanal`, `!ayarla küfürfiltre`, `!ayarla linkfiltre`"
        )
        await ctx.send(embed=embed)

    @settings.command(name="logkanal")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx: commands.Context,
                              channel: discord.TextChannel):
        """Mesaj log kanalını ayarlar."""
        await db.update_guild_setting(ctx.guild.id, "log_channel", channel.id)
        await ctx.send(embed=success_embed(
            "Log Kanalı Ayarlandı",
            f"Mesaj logları {channel.mention} kanalına gönderilecek."
        ))

    @settings.command(name="girişlog")
    @commands.has_permissions(administrator=True)
    async def set_join_log(self, ctx: commands.Context,
                           channel: discord.TextChannel):
        """Giriş/çıkış log kanalını ayarlar."""
        await db.update_guild_setting(ctx.guild.id, "join_leave_log", channel.id)
        await ctx.send(embed=success_embed(
            "Giriş/Çıkış Log Kanalı Ayarlandı",
            f"{channel.mention} kanalı kullanılacak."
        ))

    @settings.command(name="seslog")
    @commands.has_permissions(administrator=True)
    async def set_voice_log(self, ctx: commands.Context,
                            channel: discord.TextChannel):
        """Ses kanalı log kanalını ayarlar."""
        await db.update_guild_setting(ctx.guild.id, "voice_log", channel.id)
        await ctx.send(embed=success_embed("Ses Log Kanalı Ayarlandı",
                                           f"{channel.mention} kanalı kullanılacak."))

    @settings.command(name="modlog")
    @commands.has_permissions(administrator=True)
    async def set_mod_log(self, ctx: commands.Context,
                          channel: discord.TextChannel):
        """Moderasyon log kanalını ayarlar."""
        await db.update_guild_setting(ctx.guild.id, "mod_log", channel.id)
        await ctx.send(embed=success_embed("Mod Log Kanalı Ayarlandı",
                                           f"{channel.mention} kanalı kullanılacak."))

    @settings.command(name="küfürfiltre")
    @commands.has_permissions(administrator=True)
    async def toggle_profanity(self, ctx: commands.Context):
        """Küfür filtresini açar/kapatır."""
        settings = await db.get_guild_settings(ctx.guild.id)
        new_val = 0 if settings["profanity_filter"] else 1
        await db.update_guild_setting(ctx.guild.id, "profanity_filter", new_val)
        status = "açıldı ✅" if new_val else "kapatıldı ❌"
        await ctx.send(embed=success_embed(f"Küfür Filtresi {status}"))

    @settings.command(name="linkfiltre")
    @commands.has_permissions(administrator=True)
    async def toggle_link(self, ctx: commands.Context):
        """Link filtresini açar/kapatır."""
        settings = await db.get_guild_settings(ctx.guild.id)
        new_val = 0 if settings["link_filter"] else 1
        await db.update_guild_setting(ctx.guild.id, "link_filter", new_val)
        status = "açıldı ✅" if new_val else "kapatıldı ❌"
        await ctx.send(embed=success_embed(f"Link Filtresi {status}"))

    # ─────────────────────────────────────────────
    # OTOMATİK FİLTRE - MESAJ DİNLEYİCİSİ
    # ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Gelen her mesajı filtre için kontrol eder.
        Küfür veya link içeriyorsa otomatik siler ve uyarı verir.
        """
        # Bot mesajlarını ve DM'leri atla
        if message.author.bot or not message.guild:
            return
        # Adminleri filtreden muaf tut
        if message.author.guild_permissions.administrator:
            return

        settings = await db.get_guild_settings(message.guild.id)

        # ── Küfür Filtresi ────────────────────────────
        if settings["profanity_filter"]:
            content_lower = message.content.lower()
            for word in PROFANITY_WORDS:
                if word in content_lower:
                    try:
                        await message.delete()
                        warn_msg = await message.channel.send(
                            embed=warning_embed(
                                "Uygunsuz İçerik",
                                f"{message.author.mention}, uygunsuz kelime kullandın!"
                            ),
                            delete_after=5
                        )
                    except discord.Forbidden:
                        pass
                    return

        # ── Link Filtresi ─────────────────────────────
        if settings["link_filter"]:
            if LINK_PATTERN.search(message.content):
                try:
                    await message.delete()
                    await message.channel.send(
                        embed=warning_embed(
                            "Link Engellendi",
                            f"{message.author.mention}, bu kanalda link paylaşamazsın!"
                        ),
                        delete_after=5
                    )
                except discord.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Silinen mesajları log kanalına kaydeder."""
        if message.author.bot or not message.guild:
            return
        if not message.content:
            return

        embed = discord.Embed(
            title="🗑️ Mesaj Silindi",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Yazar", value=f"{message.author} ({message.author.id})")
        embed.add_field(name="Kanal", value=message.channel.mention)
        embed.add_field(name="İçerik",
                        value=message.content[:1000] or "*Boş*", inline=False)
        await self.send_message_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Düzenlenen mesajları log kanalına kaydeder."""
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return

        embed = discord.Embed(
            title="✏️ Mesaj Düzenlendi",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Yazar", value=f"{before.author} ({before.author.id})")
        embed.add_field(name="Kanal", value=before.channel.mention)
        embed.add_field(name="Önceki",
                        value=before.content[:500] or "*Boş*", inline=False)
        embed.add_field(name="Sonraki",
                        value=after.content[:500] or "*Boş*", inline=False)
        embed.add_field(name="Mesaj Linki",
                        value=f"[Tıkla]({after.jump_url})", inline=False)
        await self.send_message_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Sunucuya katılan üyeleri log kanalına kaydeder."""
        embed = discord.Embed(
            title="📥 Üye Katıldı",
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
        embed.add_field(name="Hesap Oluşturma",
                        value=member.created_at.strftime("%d/%m/%Y"))
        embed.set_footer(text=f"Sunucuda {member.guild.member_count} üye")
        await self.send_join_leave_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Sunucudan ayrılan üyeleri log kanalına kaydeder."""
        embed = discord.Embed(
            title="📤 Üye Ayrıldı",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
        embed.add_field(name="Katılma Tarihi",
                        value=member.joined_at.strftime("%d/%m/%Y")
                        if member.joined_at else "Bilinmiyor")
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name="Roller",
                        value=", ".join(roles) if roles else "Yok", inline=False)
        await self.send_join_leave_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        """Ses kanalı hareketlerini log kanalına kaydeder."""
        if before.channel == after.channel:
            return  # Sadece ses değiştiyse (mute vb.) kaydetme

        embed = discord.Embed(
            color=Colors.MUSIC,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if before.channel is None and after.channel:
            # Kanala katıldı
            embed.title = "🔊 Ses Kanalına Katıldı"
            embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            embed.add_field(name="Kanal", value=after.channel.name)
        elif before.channel and after.channel is None:
            # Kanaldan ayrıldı
            embed.title = "🔇 Ses Kanalından Ayrıldı"
            embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            embed.add_field(name="Kanal", value=before.channel.name)
        else:
            # Kanal değiştirdi
            embed.title = "🔄 Ses Kanalı Değiştirdi"
            embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            embed.add_field(name="Önceki Kanal", value=before.channel.name)
            embed.add_field(name="Yeni Kanal", value=after.channel.name)

        await self.send_voice_log(member.guild, embed)


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(Moderation(bot))
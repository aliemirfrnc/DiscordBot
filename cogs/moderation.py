"""
cogs/moderation.py
Gelişmiş moderasyon sistemi — Slash (app_commands) yapısına geçirildi.
Tüm komutlarda defer() + followup.send() pattern kullanılır.
"""

import discord
from discord.ext import commands
from discord import app_commands
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

    # ── LOG YARDIMCILARI ─────────────────────────────────────────────────

    async def send_mod_log(self, guild: discord.Guild, embed: discord.Embed):
        settings = await db.get_guild_settings(guild.id)
        if settings["mod_log"]:
            channel = guild.get_channel(settings["mod_log"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def send_message_log(self, guild: discord.Guild, embed: discord.Embed):
        settings = await db.get_guild_settings(guild.id)
        if settings["log_channel"]:
            channel = guild.get_channel(settings["log_channel"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def send_join_leave_log(self, guild: discord.Guild, embed: discord.Embed):
        settings = await db.get_guild_settings(guild.id)
        if settings["join_leave_log"]:
            channel = guild.get_channel(settings["join_leave_log"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def send_voice_log(self, guild: discord.Guild, embed: discord.Embed):
        settings = await db.get_guild_settings(guild.id)
        if settings["voice_log"]:
            channel = guild.get_channel(settings["voice_log"])
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    # ── MODERASYON SLASH KOMUTLARI ───────────────────────────────────────

    @app_commands.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(üye="Yasaklanacak kullanıcı", sebep="Yasaklama sebebi")
    async def ban(self, interaction: discord.Interaction,
                  üye: discord.Member, sebep: str = "Sebep belirtilmedi"):
        await interaction.response.defer()

        if üye == interaction.user:
            return await interaction.followup.send(
                embed=error_embed("Kendini banlayamazsın!"), ephemeral=True)
        if üye == interaction.guild.me:
            return await interaction.followup.send(
                embed=error_embed("Beni banlayamazsın!"), ephemeral=True)
        if üye.top_role >= interaction.user.top_role:
            return await interaction.followup.send(embed=error_embed(
                "Hedef kişi senden üst veya eşit roldedir, işlem yapılamaz."
            ), ephemeral=True)

        try:
            try:
                await üye.send(embed=warning_embed(
                    "Sunucudan Yasaklandın",
                    f"**{interaction.guild.name}** sunucusundan yasaklandın.\n"
                    f"**Sebep:** {sebep}\n**Yetkili:** {interaction.user}"
                ))
            except discord.Forbidden:
                pass

            await üye.ban(reason=f"{interaction.user} | {sebep}")

            embed = success_embed(
                "Kullanıcı Yasaklandı",
                f"**{üye}** sunucudan yasaklandı.\n**Sebep:** {sebep}"
            )
            embed.set_thumbnail(url=üye.display_avatar.url)
            await interaction.followup.send(embed=embed)

            log_embed = discord.Embed(
                title="🔨 Kullanıcı Banlandı",
                color=Colors.MOD,
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="Kullanıcı", value=f"{üye} ({üye.id})")
            log_embed.add_field(name="Yetkili",   value=f"{interaction.user} ({interaction.user.id})")
            log_embed.add_field(name="Sebep",     value=sebep, inline=False)
            await self.send_mod_log(interaction.guild, log_embed)

        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("Bu kullanıcıyı banlayacak yetkim yok."), ephemeral=True)

    @app_commands.command(name="unban", description="Yasaklı bir kullanıcının yasağını kaldırır.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(kullanıcı_id="Yasağı kaldırılacak kullanıcının ID'si")
    async def unban(self, interaction: discord.Interaction, kullanıcı_id: str):
        await interaction.response.defer()

        banned_users = [entry async for entry in interaction.guild.bans()]
        target = None

        if kullanıcı_id.isdigit():
            for entry in banned_users:
                if entry.user.id == int(kullanıcı_id):
                    target = entry.user
                    break
        else:
            for entry in banned_users:
                if str(entry.user) == kullanıcı_id:
                    target = entry.user
                    break

        if target is None:
            return await interaction.followup.send(embed=error_embed(
                "Kullanıcı Bulunamadı",
                "Bu ID veya isimde yasaklı bir kullanıcı bulunamadı."
            ), ephemeral=True)

        await interaction.guild.unban(target,
                                      reason=f"Yasak kaldırıldı | Yetkili: {interaction.user}")
        await interaction.followup.send(embed=success_embed(
            "Yasak Kaldırıldı",
            f"**{target}** kullanıcısının yasağı kaldırıldı."
        ))

        log_embed = discord.Embed(
            title="🔓 Yasak Kaldırıldı",
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Kullanıcı", value=f"{target} ({target.id})")
        log_embed.add_field(name="Yetkili",   value=f"{interaction.user} ({interaction.user.id})")
        await self.send_mod_log(interaction.guild, log_embed)

    @app_commands.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(üye="Atılacak kullanıcı", sebep="Atma sebebi")
    async def kick(self, interaction: discord.Interaction,
                   üye: discord.Member, sebep: str = "Sebep belirtilmedi"):
        await interaction.response.defer()

        if üye == interaction.user:
            return await interaction.followup.send(
                embed=error_embed("Kendini atamazsın!"), ephemeral=True)
        if üye.top_role >= interaction.user.top_role:
            return await interaction.followup.send(
                embed=error_embed("Hedef kişi senden üst veya eşit roldedir."), ephemeral=True)

        try:
            try:
                await üye.send(embed=warning_embed(
                    "Sunucudan Atıldın",
                    f"**{interaction.guild.name}** sunucusundan atıldın.\n**Sebep:** {sebep}"
                ))
            except discord.Forbidden:
                pass

            await üye.kick(reason=f"{interaction.user} | {sebep}")
            await interaction.followup.send(embed=success_embed(
                "Kullanıcı Atıldı",
                f"**{üye}** sunucudan atıldı.\n**Sebep:** {sebep}"
            ))

            log_embed = discord.Embed(
                title="👢 Kullanıcı Atıldı",
                color=Colors.WARNING,
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="Kullanıcı", value=f"{üye} ({üye.id})")
            log_embed.add_field(name="Yetkili",   value=str(interaction.user))
            log_embed.add_field(name="Sebep",     value=sebep, inline=False)
            await self.send_mod_log(interaction.guild, log_embed)

        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("Bu kullanıcıyı atma yetkim yok."), ephemeral=True)

    @app_commands.command(name="timeout", description="Kullanıcıyı belirli süre susturur.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(
        üye="Susturulacak kullanıcı",
        süre="Süre miktarı (sayı)",
        birim="Süre birimi",
        sebep="Susturma sebebi"
    )
    @app_commands.choices(birim=[
        app_commands.Choice(name="Saniye", value="saniye"),
        app_commands.Choice(name="Dakika", value="dakika"),
        app_commands.Choice(name="Saat",   value="saat"),
        app_commands.Choice(name="Gün",    value="gün"),
    ])
    async def timeout_member(self, interaction: discord.Interaction,
                              üye: discord.Member, süre: int,
                              birim: str = "dakika",
                              sebep: str = "Sebep belirtilmedi"):
        await interaction.response.defer()

        if üye.top_role >= interaction.user.top_role:
            return await interaction.followup.send(
                embed=error_embed("Bu kullanıcıya işlem yapamazsın."), ephemeral=True)

        unit_map = {
            "saniye": 1, "dakika": 60, "saat": 3600, "gün": 86400
        }
        total_seconds = süre * unit_map.get(birim, 60)

        if total_seconds > 86400 * 28:
            return await interaction.followup.send(
                embed=error_embed("Maksimum timeout süresi 28 gündür."), ephemeral=True)

        until = datetime.datetime.utcnow() + datetime.timedelta(seconds=total_seconds)

        try:
            await üye.timeout(until, reason=f"{interaction.user} | {sebep}")
            await interaction.followup.send(embed=success_embed(
                "Kullanıcı Susturuldu",
                f"**{üye}** {süre} {birim} süreyle susturuldu.\n**Sebep:** {sebep}"
            ))

            log_embed = discord.Embed(
                title="🔇 Timeout Uygulandı",
                color=Colors.MOD,
                timestamp=datetime.datetime.utcnow()
            )
            log_embed.add_field(name="Kullanıcı", value=f"{üye} ({üye.id})")
            log_embed.add_field(name="Süre",      value=f"{süre} {birim}")
            log_embed.add_field(name="Yetkili",   value=str(interaction.user))
            log_embed.add_field(name="Sebep",     value=sebep, inline=False)
            await self.send_mod_log(interaction.guild, log_embed)

        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("Bu kullanıcıya timeout uygulayamam."), ephemeral=True)

    @app_commands.command(name="untimeout", description="Kullanıcının susturmasını kaldırır.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(üye="Susturması kaldırılacak kullanıcı")
    async def untimeout_member(self, interaction: discord.Interaction, üye: discord.Member):
        await interaction.response.defer()
        try:
            await üye.timeout(None, reason=f"Timeout kaldırıldı | {interaction.user}")
            await interaction.followup.send(embed=success_embed(
                "Timeout Kaldırıldı", f"**{üye}** artık konuşabilir."))
        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("Bu kullanıcının timeout'unu kaldıramam."), ephemeral=True)

    @app_commands.command(name="uyar", description="Kullanıcıya uyarı verir.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(üye="Uyarılacak kullanıcı", sebep="Uyarı sebebi")
    async def warn(self, interaction: discord.Interaction,
                   üye: discord.Member, sebep: str = "Sebep belirtilmedi"):
        await interaction.response.defer()

        timestamp = datetime.datetime.utcnow().isoformat()
        warn_id   = await db.add_warning(
            üye.id, interaction.guild.id, interaction.user.id, sebep, timestamp)
        warnings  = await db.get_warnings(üye.id, interaction.guild.id)

        embed = warning_embed(
            "Uyarı Verildi",
            f"**{üye}** uyarıldı.\n"
            f"**Sebep:** {sebep}\n"
            f"**Uyarı ID:** #{warn_id}\n"
            f"**Toplam Uyarı:** {len(warnings)}"
        )
        await interaction.followup.send(embed=embed)

        try:
            await üye.send(embed=warning_embed(
                f"{interaction.guild.name} - Uyarı Aldın",
                f"**Sebep:** {sebep}\n**Yetkili:** {interaction.user}\n"
                f"**Toplam uyarın:** {len(warnings)}"
            ))
        except discord.Forbidden:
            pass

        log_embed = discord.Embed(
            title="⚠️ Uyarı Kaydedildi",
            color=Colors.WARNING,
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="Kullanıcı",    value=f"{üye} ({üye.id})")
        log_embed.add_field(name="Yetkili",       value=str(interaction.user))
        log_embed.add_field(name="Sebep",         value=sebep, inline=False)
        log_embed.add_field(name="Toplam Uyarı",  value=str(len(warnings)))
        await self.send_mod_log(interaction.guild, log_embed)

    @app_commands.command(name="uyarılar", description="Bir kullanıcının uyarılarını listeler.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(üye="Uyarıları listelenecek kullanıcı")
    async def warnings_list(self, interaction: discord.Interaction,
                            üye: discord.Member = None):
        await interaction.response.defer()
        member = üye or interaction.user
        warnings = await db.get_warnings(member.id, interaction.guild.id)

        if not warnings:
            return await interaction.followup.send(embed=info_embed(
                "Uyarı Yok", f"**{member}** kullanıcısının hiç uyarısı yok."))

        embed = discord.Embed(
            title=f"⚠️ {member} - Uyarı Listesi",
            color=Colors.WARNING,
            description=f"Toplam **{len(warnings)}** uyarı"
        )
        for w in warnings[:10]:
            mod = interaction.guild.get_member(w["moderator"]) or f"ID: {w['moderator']}"
            embed.add_field(
                name=f"Uyarı #{w['id']}",
                value=f"**Sebep:** {w['reason']}\n"
                      f"**Yetkili:** {mod}\n"
                      f"**Tarih:** {w['timestamp'][:10]}",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="uyarı-sil", description="Kullanıcının tüm uyarılarını siler.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(üye="Uyarıları silinecek kullanıcı")
    async def clear_warnings(self, interaction: discord.Interaction, üye: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await db.clear_warnings(üye.id, interaction.guild.id)
        await interaction.followup.send(embed=success_embed(
            "Uyarılar Temizlendi",
            f"**{üye.mention}** kullanıcısının tüm uyarıları silindi."
        ))

    @app_commands.command(name="temizle", description="Belirli sayıda mesajı siler.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(
        miktar="Silinecek mesaj sayısı (1-200)",
        üye="Yalnızca bu kullanıcının mesajlarını sil (opsiyonel)"
    )
    async def purge(self, interaction: discord.Interaction,
                    miktar: int, üye: discord.Member = None):
        await interaction.response.defer(ephemeral=True)

        if miktar < 1 or miktar > 200:
            return await interaction.followup.send(
                embed=error_embed("1 ile 200 arasında bir sayı gir."), ephemeral=True)

        if üye:
            def check(m):
                return m.author == üye
            deleted = await interaction.channel.purge(limit=miktar * 5, check=check, bulk=True)
            deleted = deleted[:miktar]
        else:
            deleted = await interaction.channel.purge(limit=miktar, bulk=True)

        await interaction.followup.send(embed=success_embed(
            "Mesajlar Silindi", f"**{len(deleted)}** mesaj silindi."
        ), ephemeral=True)

    @app_commands.command(name="yavaşmod", description="Kanalda yavaş modu ayarlar.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(
        saniye="Bekleme süresi saniye (0 = kapat, max 21600)",
        kanal="Ayarlanacak kanal (boş = mevcut kanal)"
    )
    async def slowmode(self, interaction: discord.Interaction,
                       saniye: int = 0,
                       kanal: discord.TextChannel = None):
        await interaction.response.defer()
        channel = kanal or interaction.channel

        if saniye < 0 or saniye > 21600:
            return await interaction.followup.send(
                embed=error_embed("Süre 0 ile 21600 saniye arasında olmalı."), ephemeral=True)

        await channel.edit(slowmode_delay=saniye)
        if saniye == 0:
            await interaction.followup.send(embed=success_embed("Yavaş Mod Kapatıldı"))
        else:
            await interaction.followup.send(embed=success_embed(
                "Yavaş Mod Açıldı",
                f"{channel.mention} kanalında mesajlar arası bekleme: **{saniye} saniye**"
            ))

    @app_commands.command(name="kilitle", description="Kanalı kilitler (üyeler mesaj atamaz).")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(kanal="Kilitlenecek kanal (boş = mevcut kanal)")
    async def lock_channel(self, interaction: discord.Interaction,
                           kanal: discord.TextChannel = None):
        await interaction.response.defer()
        channel   = kanal or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(embed=success_embed(
            "Kanal Kilitlendi", f"{channel.mention} kanalı kilitlendi."))

    @app_commands.command(name="kilitsiz", description="Kanalın kilidini açar.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(kanal="Kilidi açılacak kanal (boş = mevcut kanal)")
    async def unlock_channel(self, interaction: discord.Interaction,
                             kanal: discord.TextChannel = None):
        await interaction.response.defer()
        channel   = kanal or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(embed=success_embed(
            "Kanal Kilidi Açıldı", f"{channel.mention} kanalının kilidi açıldı."))

    # ── AYAR GRUBU ──────────────────────────────────────────────────────

    settings_group = app_commands.Group(
        name="ayarla",
        description="Sunucu ayarlama komutları",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True)
    )

    @settings_group.command(name="bilgi", description="Mevcut sunucu ayarlarını gösterir.")
    async def settings_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = await db.get_guild_settings(interaction.guild.id)
        embed = info_embed(
            "Sunucu Ayarları",
            f"**Prefix:** `{settings['prefix']}`\n"
            f"**Küfür Filtresi:** {'✅' if settings['profanity_filter'] else '❌'}\n"
            f"**Link Filtresi:** {'✅' if settings['link_filter'] else '❌'}"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(name="logkanal", description="Mesaj log kanalını ayarlar.")
    @app_commands.describe(kanal="Log mesajlarının gönderileceği kanal")
    async def set_log_channel(self, interaction: discord.Interaction,
                               kanal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await db.update_guild_setting(interaction.guild.id, "log_channel", kanal.id)
        await interaction.followup.send(embed=success_embed(
            "Log Kanalı Ayarlandı",
            f"Mesaj logları {kanal.mention} kanalına gönderilecek."
        ))

    @settings_group.command(name="girişlog", description="Giriş/çıkış log kanalını ayarlar.")
    @app_commands.describe(kanal="Giriş/çıkış mesajlarının gönderileceği kanal")
    async def set_join_log(self, interaction: discord.Interaction,
                            kanal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await db.update_guild_setting(interaction.guild.id, "join_leave_log", kanal.id)
        await interaction.followup.send(embed=success_embed(
            "Giriş/Çıkış Log Kanalı Ayarlandı", f"{kanal.mention} kanalı kullanılacak."))

    @settings_group.command(name="seslog", description="Ses kanalı log kanalını ayarlar.")
    @app_commands.describe(kanal="Ses olaylarının loglanacağı kanal")
    async def set_voice_log(self, interaction: discord.Interaction,
                             kanal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await db.update_guild_setting(interaction.guild.id, "voice_log", kanal.id)
        await interaction.followup.send(embed=success_embed(
            "Ses Log Kanalı Ayarlandı", f"{kanal.mention} kanalı kullanılacak."))

    @settings_group.command(name="modlog", description="Moderasyon log kanalını ayarlar.")
    @app_commands.describe(kanal="Mod olaylarının loglanacağı kanal")
    async def set_mod_log(self, interaction: discord.Interaction,
                           kanal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await db.update_guild_setting(interaction.guild.id, "mod_log", kanal.id)
        await interaction.followup.send(embed=success_embed(
            "Mod Log Kanalı Ayarlandı", f"{kanal.mention} kanalı kullanılacak."))

    @settings_group.command(name="küfürfiltre", description="Küfür filtresini açar/kapatır.")
    async def toggle_profanity(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = await db.get_guild_settings(interaction.guild.id)
        new_val = 0 if settings["profanity_filter"] else 1
        await db.update_guild_setting(interaction.guild.id, "profanity_filter", new_val)
        status = "açıldı ✅" if new_val else "kapatıldı ❌"
        await interaction.followup.send(embed=success_embed(f"Küfür Filtresi {status}"))

    @settings_group.command(name="linkfiltre", description="Link filtresini açar/kapatır.")
    async def toggle_link(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = await db.get_guild_settings(interaction.guild.id)
        new_val = 0 if settings["link_filter"] else 1
        await db.update_guild_setting(interaction.guild.id, "link_filter", new_val)
        status = "açıldı ✅" if new_val else "kapatıldı ❌"
        await interaction.followup.send(embed=success_embed(f"Link Filtresi {status}"))

    # ── OTOMATİK FİLTRE DİNLEYİCİLERİ ─────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.administrator:
            return

        settings = await db.get_guild_settings(message.guild.id)

        if settings["profanity_filter"]:
            content_lower = message.content.lower()
            for word in PROFANITY_WORDS:
                if word in content_lower:
                    try:
                        await message.delete()
                        await message.channel.send(
                            embed=warning_embed(
                                "Uygunsuz İçerik",
                                f"{message.author.mention}, uygunsuz kelime kullandın!"
                            ),
                            delete_after=5
                        )
                    except discord.Forbidden:
                        pass
                    return

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
        if message.author.bot or not message.guild or not message.content:
            return

        embed = discord.Embed(
            title="🗑️ Mesaj Silindi",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Yazar", value=f"{message.author} ({message.author.id})")
        embed.add_field(name="Kanal", value=message.channel.mention)
        embed.add_field(name="İçerik", value=message.content[:1000] or "*Boş*", inline=False)
        await self.send_message_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
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
        embed.add_field(name="Önceki", value=before.content[:500] or "*Boş*", inline=False)
        embed.add_field(name="Sonraki", value=after.content[:500] or "*Boş*", inline=False)
        embed.add_field(name="Mesaj Linki", value=f"[Tıkla]({after.jump_url})", inline=False)
        await self.send_message_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
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
        embed = discord.Embed(
            title="📤 Üye Ayrıldı",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
        embed.add_field(
            name="Katılma Tarihi",
            value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Bilinmiyor"
        )
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name="Roller",
                        value=", ".join(roles) if roles else "Yok", inline=False)
        await self.send_join_leave_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        if before.channel == after.channel:
            return

        embed = discord.Embed(color=Colors.MUSIC, timestamp=datetime.datetime.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)

        if before.channel is None and after.channel:
            embed.title = "🔊 Ses Kanalına Katıldı"
            embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            embed.add_field(name="Kanal", value=after.channel.name)
        elif before.channel and after.channel is None:
            embed.title = "🔇 Ses Kanalından Ayrıldı"
            embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})")
            embed.add_field(name="Kanal", value=before.channel.name)
        else:
            embed.title = "🔄 Ses Kanalı Değiştirdi"
            embed.add_field(name="Kullanıcı",    value=f"{member} ({member.id})")
            embed.add_field(name="Önceki Kanal", value=before.channel.name)
            embed.add_field(name="Yeni Kanal",   value=after.channel.name)

        await self.send_voice_log(member.guild, embed)


async def setup(bot: commands.Bot):
    # Cog'u ekle, otomatik olarak komutları da tree'ye ekler
    await bot.add_cog(Moderation(bot))

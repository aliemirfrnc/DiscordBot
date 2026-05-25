"""
cogs/events.py
Botun genel yaşam döngüsü olaylarını yöneten Cog.
Ready, guild join/leave, rol değişiklikleri ve benzeri olayları içerir.
"""

import discord
from discord.ext import commands
import datetime

from utils.helpers import Colors


class Events(commands.Cog, name="Olaylar"):
    """Bot olay dinleyicileri (arka planda çalışır, komut içermez)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        guild_count  = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)

        print("=" * 50)
        print(f"  ✅ Bot hazır: {self.bot.user} (ID: {self.bot.user.id})")
        print(f"  🏰 Sunucu sayısı: {guild_count}")
        print(f"  👥 Toplam kullanıcı: {member_count}")
        print(f"  📡 Gecikme: {round(self.bot.latency * 1000)}ms")
        print("=" * 50)

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{guild_count} sunucu | /yardım"
        )
        await self.bot.change_presence(status=discord.Status.online, activity=activity)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        print(f"[+] Yeni sunucuya katıldı: {guild.name} (ID: {guild.id}) | {guild.member_count} üye")

        from database import db
        await db.get_guild_settings(guild.id)

        embed = discord.Embed(
            title="👋 Merhaba! Ben buradayım!",
            description=(
                "Beni sunucunuza eklediğiniz için teşekkürler!\n\n"
                "📌 **Slash Komutlar:** `/` yazarak tüm komutlara ulaşabilirsin.\n"
                "📌 **Prefix:** `!`\n\n"
                "**Başlangıç için önerilen ayarlar:**\n"
                "`/ayarla logkanal` → Mesaj logları\n"
                "`/ayarla girişlog` → Giriş/çıkış logları\n"
                "`/ayarla modlog` → Moderasyon logları\n"
                "`/ayarla küfürfiltre` → Küfür filtresini aç\n"
                "`/ayarla linkfiltre` → Link filtresini aç"
            ),
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Toplam {len(self.bot.guilds)} sunucudayım!")

        target_channel = guild.system_channel
        if target_channel is None:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        if target_channel:
            try:
                await target_channel.send(embed=embed)
            except discord.Forbidden:
                pass

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.bot.guilds)} sunucu | /yardım"
            )
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        print(f"[-] Sunucudan çıkarıldı: {guild.name} (ID: {guild.id})")
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.bot.guilds)} sunucu | /yardım"
            )
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        from database import db
        settings = await db.get_guild_settings(after.guild.id)
        if not settings["mod_log"]:
            return

        log_channel = after.guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        added_roles   = set(after.roles) - set(before.roles)
        removed_roles = set(before.roles) - set(after.roles)

        if added_roles or removed_roles:
            embed = discord.Embed(
                title="🎭 Rol Değişikliği",
                color=Colors.INFO,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.add_field(name="Kullanıcı", value=f"{after} ({after.id})", inline=False)
            if added_roles:
                embed.add_field(name="➕ Eklenen Roller",
                                value=", ".join(r.mention for r in added_roles), inline=False)
            if removed_roles:
                embed.add_field(name="➖ Kaldırılan Roller",
                                value=", ".join(r.mention for r in removed_roles), inline=False)
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

        if before.nick != after.nick:
            embed = discord.Embed(
                title="✏️ Takma Ad Değişti",
                color=Colors.INFO,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.add_field(name="Kullanıcı", value=f"{after} ({after.id})", inline=False)
            embed.add_field(name="Önceki", value=before.nick or "*Takma ad yoktu*", inline=True)
            embed.add_field(name="Yeni", value=after.nick or "*Takma ad kaldırıldı*", inline=True)
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        from database import db
        settings = await db.get_guild_settings(channel.guild.id)
        if not settings["mod_log"]:
            return
        log_channel = channel.guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        channel_type = {
            discord.TextChannel:     "💬 Metin",
            discord.VoiceChannel:    "🔊 Ses",
            discord.CategoryChannel: "📁 Kategori",
            discord.StageChannel:    "🎤 Sahne",
            discord.ForumChannel:    "💬 Forum",
        }.get(type(channel), "Bilinmiyor")

        embed = discord.Embed(
            title="📢 Yeni Kanal Oluşturuldu",
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Kanal", value=channel.mention)
        embed.add_field(name="Tür",   value=channel_type)
        embed.add_field(name="ID",    value=str(channel.id))
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        from database import db
        settings = await db.get_guild_settings(channel.guild.id)
        if not settings["mod_log"]:
            return
        log_channel = channel.guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Kanal Silindi",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Kanal Adı", value=channel.name)
        embed.add_field(name="ID",        value=str(channel.id))
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        from database import db
        settings = await db.get_guild_settings(role.guild.id)
        if not settings["mod_log"]:
            return
        log_channel = role.guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🎭 Yeni Rol Oluşturuldu",
            color=role.color if role.color.value != 0 else Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Rol",   value=role.mention)
        embed.add_field(name="Renk",  value=str(role.color))
        embed.add_field(name="ID",    value=str(role.id))
        embed.add_field(name="Konum", value=str(role.position))
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        from database import db
        settings = await db.get_guild_settings(role.guild.id)
        if not settings["mod_log"]:
            return
        log_channel = role.guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Rol Silindi",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Rol Adı", value=role.name)
        embed.add_field(name="ID",      value=str(role.id))
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        from database import db
        settings = await db.get_guild_settings(guild.id)
        if not settings["mod_log"]:
            return
        log_channel = guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🔨 Kullanıcı Yasaklandı",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{user} ({user.id})")
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        from database import db
        settings = await db.get_guild_settings(guild.id)
        if not settings["mod_log"]:
            return
        log_channel = guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🔓 Kullanıcı Yasağı Kaldırıldı",
            color=Colors.SUCCESS,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{user} ({user.id})")
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        print(
            f"[CMD] {ctx.author} ({ctx.author.id}) "
            f"| Guild: {ctx.guild.name if ctx.guild else 'DM'} "
            f"| Komut: {ctx.command} "
            f"| İçerik: {ctx.message.content[:80]}"
        )

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list):
        if not messages:
            return
        guild = messages[0].guild
        if not guild:
            return

        from database import db
        settings = await db.get_guild_settings(guild.id)
        if not settings["log_channel"]:
            return
        log_channel = guild.get_channel(settings["log_channel"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Toplu Mesaj Silindi",
            color=Colors.ERROR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Silinen Mesaj", value=str(len(messages)))
        embed.add_field(
            name="Kanal",
            value=messages[0].channel.mention if messages[0].channel else "Bilinmiyor"
        )
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if not invite.guild:
            return
        from database import db
        settings = await db.get_guild_settings(invite.guild.id)
        if not settings["mod_log"]:
            return
        log_channel = invite.guild.get_channel(settings["mod_log"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🔗 Davet Oluşturuldu",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Oluşturan",
                        value=str(invite.inviter) if invite.inviter else "Bilinmiyor")
        embed.add_field(name="Kod",   value=invite.code)
        embed.add_field(name="Kanal",
                        value=invite.channel.mention if invite.channel else "Bilinmiyor")
        embed.add_field(name="Kullanım",
                        value=f"{invite.max_uses or '∞'} kez")
        embed.add_field(name="Süre",
                        value=f"{invite.max_age // 3600 if invite.max_age else '∞'} saat")
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))

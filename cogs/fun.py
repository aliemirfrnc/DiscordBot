"""
cogs/fun.py
Eğlence komutları: sunucu bilgisi, kullanıcı profili,
avatar, zar, 8top ve sayfalı yardım menüsü.
"""

import discord
from discord.ext import commands
import datetime
import random
import aiohttp

from utils.helpers import info_embed, error_embed, Colors, Paginator


class Fun(commands.Cog, name="Eğlence & Genel"):
    """Eğlence ve genel amaçlı komutlar."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─────────────────────────────────────────────
    # SUNUCU BİLGİSİ
    # ─────────────────────────────────────────────

    @commands.command(name="sunucu", aliases=["serverinfo", "si"],
                      help="Sunucu hakkında detaylı bilgi verir.")
    @commands.guild_only()
    async def server_info(self, ctx: commands.Context):
        """Sunucu bilgilerini gösterir."""
        guild = ctx.guild
        await guild.chunk()  # Tüm üyeleri yükle

        # Üye istatistikleri
        total    = guild.member_count
        bots     = sum(1 for m in guild.members if m.bot)
        humans   = total - bots
        online   = sum(1 for m in guild.members
                       if m.status != discord.Status.offline and not m.bot)

        # Kanal istatistikleri
        text_ch  = len(guild.text_channels)
        voice_ch = len(guild.voice_channels)
        cats     = len(guild.categories)
        stages   = len(guild.stage_channels)
        forums   = len(guild.forums)

        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            description=guild.description or "Açıklama yok",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="🆔 ID", value=str(guild.id), inline=True)
        embed.add_field(name="👑 Sahip",
                        value=str(guild.owner) if guild.owner else "Bilinmiyor",
                        inline=True)
        embed.add_field(name="📅 Oluşturma",
                        value=guild.created_at.strftime("%d/%m/%Y"), inline=True)

        embed.add_field(
            name=f"👥 Üyeler ({total})",
            value=f"👤 İnsan: {humans}\n🤖 Bot: {bots}\n🟢 Çevrimiçi: {online}",
            inline=True
        )
        embed.add_field(
            name=f"📚 Kanallar ({text_ch + voice_ch})",
            value=f"💬 Metin: {text_ch}\n🔊 Ses: {voice_ch}\n"
                  f"📁 Kategori: {cats}\n🎤 Sahne: {stages}\n💬 Forum: {forums}",
            inline=True
        )
        embed.add_field(
            name="🚀 Boost",
            value=f"Seviye: {guild.premium_tier}\n"
                  f"Boost: {guild.premium_subscription_count}",
            inline=True
        )
        embed.add_field(
            name="🔒 Doğrulama",
            value=str(guild.verification_level).capitalize(),
            inline=True
        )
        embed.add_field(name="😄 Emoji", value=f"{len(guild.emojis)}", inline=True)
        embed.add_field(name="📌 Rol", value=f"{len(guild.roles)}", inline=True)

        embed.set_footer(text=f"Bölge: {str(guild.preferred_locale)}")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # KULLANICI PROFİLİ
    # ─────────────────────────────────────────────

    @commands.command(name="profil", aliases=["userinfo", "kullanıcı", "whois"],
                      help="Kullanıcı profil bilgilerini gösterir.")
    @commands.guild_only()
    async def user_info(self, ctx: commands.Context,
                        member: discord.Member = None):
        """Kullanıcı bilgilerini gösterir."""
        member = member or ctx.author

        # Kullanıcı durumu
        status_map = {
            discord.Status.online:    "🟢 Çevrimiçi",
            discord.Status.idle:      "🟡 Boşta",
            discord.Status.dnd:       "🔴 Rahatsız Etme",
            discord.Status.offline:   "⚫ Çevrimdışı",
        }
        status = status_map.get(member.status, "⚫ Bilinmiyor")

        # Roller (en yüksek 10 tane)
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        roles_str = " ".join(roles[:10]) if roles else "Yok"
        if len(roles) > 10:
            roles_str += f" ... (+{len(roles) - 10} daha)"

        embed = discord.Embed(
            title=f"👤 {member}",
            color=member.color if member.color.value != 0 else Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
        embed.add_field(name="📛 Takma Ad",
                        value=member.nick or "Yok", inline=True)
        embed.add_field(name="🤖 Bot", value="✅" if member.bot else "❌", inline=True)
        embed.add_field(name="📅 Hesap Oluşturma",
                        value=member.created_at.strftime("%d/%m/%Y %H:%M"),
                        inline=True)
        embed.add_field(name="📥 Sunucuya Katılma",
                        value=member.joined_at.strftime("%d/%m/%Y %H:%M")
                        if member.joined_at else "Bilinmiyor",
                        inline=True)
        embed.add_field(name="💫 Durum", value=status, inline=True)
        embed.add_field(name=f"🎭 Roller ({len(roles)})",
                        value=roles_str, inline=False)

        # Aktivite
        if member.activities:
            activity = member.activities[0]
            if isinstance(activity, discord.Game):
                embed.add_field(name="🎮 Oyun", value=activity.name, inline=True)
            elif isinstance(activity, discord.Streaming):
                embed.add_field(name="📺 Yayın",
                                value=f"[{activity.name}]({activity.url})", inline=True)
            elif isinstance(activity, discord.Spotify):
                embed.add_field(name="🎵 Spotify",
                                value=f"{activity.title} - {activity.artist}", inline=True)
            elif isinstance(activity, discord.Activity):
                embed.add_field(name="🎯 Aktivite", value=activity.name, inline=True)

        embed.set_footer(text=f"En Yüksek Rol: {member.top_role.name}")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # AVATAR
    # ─────────────────────────────────────────────

    @commands.command(name="avatar", aliases=["av", "pfp"],
                      help="Kullanıcının avatarını büyük boyutta gösterir.")
    async def avatar(self, ctx: commands.Context,
                     member: discord.Member = None):
        """Kullanıcının profil fotoğrafını gösterir."""
        member = member or ctx.author
        embed  = discord.Embed(
            title=f"🖼️ {member.display_name} - Avatar",
            color=Colors.INFO
        )
        embed.set_image(url=member.display_avatar.with_size(1024).url)
        embed.add_field(
            name="İndirme Linkleri",
            value=f"[PNG]({member.display_avatar.with_format('png').url}) | "
                  f"[JPG]({member.display_avatar.with_format('jpg').url}) | "
                  f"[WEBP]({member.display_avatar.with_format('webp').url})"
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # ZAR AT
    # ─────────────────────────────────────────────

    @commands.command(name="zar", aliases=["roll", "dice"],
                      help="Zar atar. !zar veya !zar 6 veya !zar 2d6")
    async def dice(self, ctx: commands.Context, dice_str: str = "1d6"):
        """
        Zar atar.
        Kullanım: !zar → tek 6'lı zar
                  !zar 20 → 20'lik zar
                  !zar 2d6 → 2 adet 6'lı zar
        """
        try:
            if "d" in dice_str.lower():
                parts = dice_str.lower().split("d")
                count = int(parts[0]) if parts[0] else 1
                sides = int(parts[1])
            else:
                count = 1
                sides = int(dice_str)

            if count < 1 or count > 20:
                return await ctx.send(embed=error_embed("1-20 arası zar atabilirsin!"))
            if sides < 2 or sides > 1000:
                return await ctx.send(embed=error_embed("Zar yüzü 2-1000 arasında olmalı!"))

        except ValueError:
            return await ctx.send(embed=error_embed(
                "Geçersiz format! Örn: `!zar 6`, `!zar 2d10`"
            ))

        results = [random.randint(1, sides) for _ in range(count)]
        total   = sum(results)

        embed = info_embed(
            f"🎲 {count}d{sides} Zar Atıldı",
            f"Sonuçlar: {', '.join(f'**{r}**' for r in results)}\n"
            f"Toplam: **{total}**" if count > 1 else f"Sonuç: **{results[0]}**"
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # 8-BALL (Sihirli Top)
    # ─────────────────────────────────────────────

    @commands.command(name="8top", aliases=["8ball", "sihirli"],
                      help="Sihirli 8 top! Soruyu sor, cevabı al.")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        """Sihirli 8 top cevapları verir."""
        responses = [
            # Olumlu
            "Kesinlikle evet! 🎯", "Evet, şüphe yok! ✅", "Öyle görünüyor. 👍",
            "Çok muhtemelen! 🌟", "Buna güvenebilirsin. 💪", "Tahminime göre evet. 😊",
            # Nötr
            "Şu an cevap veremiyorum. 🤔", "Daha sonra sor. ⏰",
            "Tahmin etmeye çalışma. 🎱", "Odaklan ve tekrar sor. 🧘",
            # Olumsuz
            "Sanmıyorum. 🤨", "Olası değil. ❌", "Hayır! 🚫",
            "Öyle görünmüyor. 😬", "Çok şüpheliyim. 🌧️"
        ]
        answer = random.choice(responses)
        embed  = discord.Embed(
            title="🎱 Sihirli 8 Top",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="❓ Soru", value=question, inline=False)
        embed.add_field(name="🎱 Cevap", value=answer, inline=False)
        embed.set_footer(text=f"Soran: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # EMBED OLUŞTUR
    # ─────────────────────────────────────────────

    @commands.command(name="söyle", aliases=["say", "embed"],
                      help="Bot adına özel embed mesaj gönderir.")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx: commands.Context, *, text: str):
        """Bot adına embed mesaj gönderir."""
        await ctx.message.delete()
        embed = discord.Embed(
            description=text,
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # YAZIŞMA (POLL)
    # ─────────────────────────────────────────────

    @commands.command(name="anket", aliases=["poll"],
                      help="Anket oluşturur. !anket Soru | Seçenek1 | Seçenek2")
    @commands.guild_only()
    async def poll(self, ctx: commands.Context, *, content: str):
        """
        Anket oluşturur.
        Kullanım: !anket Pizza mı? | Evet | Hayır | Belki
        """
        parts = [p.strip() for p in content.split("|")]
        if len(parts) < 2:
            return await ctx.send(embed=error_embed(
                "Format Hatası",
                "Kullanım: `!anket Soru | Seçenek1 | Seçenek2 | ...`"
            ))

        question = parts[0]
        options  = parts[1:]

        if len(options) > 9:
            return await ctx.send(embed=error_embed("En fazla 9 seçenek ekleyebilirsin!"))

        # Emoji numaraları
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

        description = "\n\n".join(
            f"{number_emojis[i]} {opt}" for i, opt in enumerate(options)
        )
        embed = discord.Embed(
            title=f"📊 {question}",
            description=description,
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Anket: {ctx.author.display_name}")
        await ctx.message.delete()

        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(number_emojis[i])

    # ─────────────────────────────────────────────
    # GELİŞMİŞ YARDIM MENÜSÜ
    # ─────────────────────────────────────────────

    @commands.command(name="yardım", aliases=["help", "komutlar"],
                      help="Sayfalı yardım menüsünü gösterir.")
    async def help_command(self, ctx: commands.Context,
                           command_name: str = None):
        """
        Dinamik ve sayfalı yardım menüsü.
        Kullanım: !yardım veya !yardım <komut adı>
        """
        prefix = ctx.prefix

        # Belirli komut hakkında bilgi iste
        if command_name:
            cmd = self.bot.get_command(command_name)
            if cmd is None:
                return await ctx.send(embed=error_embed(
                    "Komut Bulunamadı",
                    f"`{command_name}` adında bir komut yok. `{prefix}yardım` ile tümünü gör."
                ))
            embed = discord.Embed(
                title=f"📖 Komut: {prefix}{cmd.qualified_name}",
                description=cmd.help or "Açıklama yok.",
                color=Colors.INFO
            )
            embed.add_field(name="Kullanım",
                            value=f"`{prefix}{cmd.qualified_name} {cmd.signature}`",
                            inline=False)
            if cmd.aliases:
                embed.add_field(name="Takma Adlar",
                                value=", ".join(f"`{a}`" for a in cmd.aliases),
                                inline=False)
            cog_name = cmd.cog_name or "Genel"
            embed.set_footer(text=f"Kategori: {cog_name}")
            return await ctx.send(embed=embed)

        # Tüm kategorileri sayfalara böl
        pages = []

        # Sayfa 1: Genel bilgi
        intro = discord.Embed(
            title="🤖 Bot Yardım Menüsü",
            description=(
                f"Merhaba! Ben bir Discord botuyum.\n"
                f"**Prefix:** `{prefix}`\n\n"
                f"Aşağıdaki ▶ butonuyla kategorileri gezebilirsin.\n"
                f"Belirli bir komut için: `{prefix}yardım <komut>`"
            ),
            color=Colors.INFO
        )
        intro.add_field(
            name="📂 Kategoriler",
            value=(
                "🛡️ Moderasyon\n"
                "🎵 Müzik\n"
                "💰 Ekonomi\n"
                "🎮 Oyunlar\n"
                "⭐ Seviyeler\n"
                "🎉 Eğlence & Genel"
            ),
            inline=False
        )
        intro.set_thumbnail(url=self.bot.user.display_avatar.url)
        pages.append(intro)

        # Her Cog için bir sayfa oluştur
        for cog_name, cog in self.bot.cogs.items():
            cmds = [c for c in cog.get_commands()
                    if not c.hidden and c.name not in ("yardım",)]
            if not cmds:
                continue

            embed = discord.Embed(
                title=f"📂 {cog.qualified_name}",
                description=cog.description or "Bu kategorideki komutlar:",
                color=Colors.INFO
            )
            for cmd in cmds:
                embed.add_field(
                    name=f"`{prefix}{cmd.name}`",
                    value=cmd.help or "Açıklama yok.",
                    inline=False
                )
            embed.set_footer(text=f"Sayfa {len(pages) + 1} | {prefix}yardım <komut>")
            pages.append(embed)

        # Numaralı footer ekle
        for i, page in enumerate(pages):
            page.set_footer(text=f"Sayfa {i + 1}/{len(pages)} | {prefix}yardım <komut>")

        view = Paginator(pages, ctx.author)
        await ctx.send(embed=pages[0], view=view)

    # ─────────────────────────────────────────────
    # PİNG
    # ─────────────────────────────────────────────

    @commands.command(name="ping", help="Botun gecikme süresini gösterir.")
    async def ping(self, ctx: commands.Context):
        """Bot ping/gecikme bilgisi."""
        latency = round(self.bot.latency * 1000)
        color   = (Colors.SUCCESS if latency < 100 else
                   Colors.WARNING if latency < 200 else Colors.ERROR)
        embed   = discord.Embed(
            title="🏓 Pong!",
            description=f"API Gecikmesi: **{latency}ms**",
            color=color
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # RASTGELE ŞAKA
    # ─────────────────────────────────────────────

    @commands.command(name="şaka", aliases=["joke"],
                      help="Rastgele bir şaka söyler.")
    async def joke(self, ctx: commands.Context):
        """Rastgele bir şaka söyler."""
        jokes = [
            ("Bir programcı neden dışarı çıkmıyor?", "Çünkü 'goto' komutu yasaklandı!"),
            ("Python neden mutlu?", "Çünkü her zaman indent'li!"),
            ("Git neden üzgün?", "Çünkü hep 'pull request' bekliyor..."),
            ("Discord botu neden yorulmuyor?", "Çünkü asenkron!"),
            ("Veritabanı neden yalnız?", "Çünkü hep 'NULL' ilişkiler kuruyor."),
            ("Programcı kaç tane soru sorar?", "1, hep 0'dan başlar."),
        ]
        setup, punchline = random.choice(jokes)
        embed = discord.Embed(color=Colors.INFO)
        embed.add_field(name="😄 " + setup, value=punchline, inline=False)
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # BOT BİLGİSİ
    # ─────────────────────────────────────────────

    @commands.command(name="botbilgi", aliases=["about", "botinfo"],
                      help="Bot hakkında bilgi verir.")
    async def bot_info(self, ctx: commands.Context):
        """Bot istatistiklerini gösterir."""
        embed = discord.Embed(
            title=f"🤖 {self.bot.user.name} Hakkında",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="👥 Sunucu",
                        value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👤 Kullanıcı",
                        value=str(sum(g.member_count for g in self.bot.guilds)),
                        inline=True)
        embed.add_field(name="📡 Gecikme",
                        value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="⚙️ Komut",
                        value=str(len(list(self.bot.commands))), inline=True)
        embed.add_field(name="📦 Cog",
                        value=str(len(self.bot.cogs)), inline=True)
        embed.add_field(name="🐍 Kütüphane",
                        value="discord.py 2.x", inline=True)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(Fun(bot))
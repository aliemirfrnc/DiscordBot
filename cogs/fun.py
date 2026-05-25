"""
cogs/fun.py
Eğlence komutları — Slash (app_commands) yapısına geçirildi.
Sunucu bilgisi, kullanıcı profili, avatar, zar, 8top, anket, yardım, ping.
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random

from utils.helpers import info_embed, error_embed, Colors, Paginator


class Fun(commands.Cog, name="Eğlence & Genel"):
    """Eğlence ve genel amaçlı komutlar."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── SUNUCU BİLGİSİ ──────────────────────────────────────────────────

    @app_commands.command(name="sunucu", description="Sunucu hakkında detaylı bilgi verir.")
    @app_commands.guild_only()
    async def server_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        await guild.chunk()

        total    = guild.member_count
        bots     = sum(1 for m in guild.members if m.bot)
        humans   = total - bots
        online   = sum(1 for m in guild.members
                       if m.status != discord.Status.offline and not m.bot)

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
                        value=str(guild.owner) if guild.owner else "Bilinmiyor", inline=True)
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
            value=f"Seviye: {guild.premium_tier}\nBoost: {guild.premium_subscription_count}",
            inline=True
        )
        embed.add_field(name="🔒 Doğrulama",
                        value=str(guild.verification_level).capitalize(), inline=True)
        embed.add_field(name="😄 Emoji", value=f"{len(guild.emojis)}", inline=True)
        embed.add_field(name="📌 Rol",   value=f"{len(guild.roles)}",   inline=True)
        embed.set_footer(text=f"Bölge: {str(guild.preferred_locale)}")
        await interaction.followup.send(embed=embed)

    # ── KULLANICI PROFİLİ ────────────────────────────────────────────────

    @app_commands.command(name="profil", description="Kullanıcı profil bilgilerini gösterir.")
    @app_commands.guild_only()
    @app_commands.describe(üye="Profili görüntülenecek kullanıcı")
    async def user_info(self, interaction: discord.Interaction,
                        üye: discord.Member = None):
        await interaction.response.defer()
        member = üye or interaction.user

        status_map = {
            discord.Status.online:  "🟢 Çevrimiçi",
            discord.Status.idle:    "🟡 Boşta",
            discord.Status.dnd:     "🔴 Rahatsız Etme",
            discord.Status.offline: "⚫ Çevrimdışı",
        }
        status = status_map.get(member.status, "⚫ Bilinmiyor")

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
        embed.add_field(name="🆔 ID",   value=str(member.id), inline=True)
        embed.add_field(name="📛 Takma Ad", value=member.nick or "Yok", inline=True)
        embed.add_field(name="🤖 Bot",  value="✅" if member.bot else "❌", inline=True)
        embed.add_field(name="📅 Hesap Oluşturma",
                        value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="📥 Sunucuya Katılma",
                        value=member.joined_at.strftime("%d/%m/%Y %H:%M")
                        if member.joined_at else "Bilinmiyor", inline=True)
        embed.add_field(name="💫 Durum", value=status, inline=True)
        embed.add_field(name=f"🎭 Roller ({len(roles)})", value=roles_str, inline=False)

        if member.activities:
            act = member.activities[0]
            if isinstance(act, discord.Game):
                embed.add_field(name="🎮 Oyun", value=act.name, inline=True)
            elif isinstance(act, discord.Streaming):
                embed.add_field(name="📺 Yayın",
                                value=f"[{act.name}]({act.url})", inline=True)
            elif isinstance(act, discord.Spotify):
                embed.add_field(name="🎵 Spotify",
                                value=f"{act.title} - {act.artist}", inline=True)
            elif isinstance(act, discord.Activity):
                embed.add_field(name="🎯 Aktivite", value=act.name, inline=True)

        embed.set_footer(text=f"En Yüksek Rol: {member.top_role.name}")
        await interaction.followup.send(embed=embed)

    # ── AVATAR ───────────────────────────────────────────────────────────

    @app_commands.command(name="avatar", description="Kullanıcının avatarını büyük boyutta gösterir.")
    @app_commands.describe(üye="Avatarı görüntülenecek kullanıcı")
    async def avatar(self, interaction: discord.Interaction,
                     üye: discord.Member = None):
        await interaction.response.defer()
        member = üye or interaction.user
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
        await interaction.followup.send(embed=embed)

    # ── ZAR ─────────────────────────────────────────────────────────────

    @app_commands.command(name="zar", description="Zar atar. Örn: 1d6, 2d10, 20")
    @app_commands.describe(format="Zar formatı — '1d6', '2d10' veya sadece '20'")
    async def dice(self, interaction: discord.Interaction, format: str = "1d6"):
        await interaction.response.defer()
        try:
            if "d" in format.lower():
                parts = format.lower().split("d")
                count = int(parts[0]) if parts[0] else 1
                sides = int(parts[1])
            else:
                count = 1
                sides = int(format)

            if count < 1 or count > 20:
                return await interaction.followup.send(
                    embed=error_embed("1-20 arası zar atabilirsin!"), ephemeral=True)
            if sides < 2 or sides > 1000:
                return await interaction.followup.send(
                    embed=error_embed("Zar yüzü 2-1000 arasında olmalı!"), ephemeral=True)
        except ValueError:
            return await interaction.followup.send(
                embed=error_embed("Geçersiz format! Örn: `1d6`, `2d10`, `20`"), ephemeral=True)

        results = [random.randint(1, sides) for _ in range(count)]
        total   = sum(results)

        embed = info_embed(
            f"🎲 {count}d{sides} Zar Atıldı",
            f"Sonuçlar: {', '.join(f'**{r}**' for r in results)}\n"
            f"Toplam: **{total}**" if count > 1 else f"Sonuç: **{results[0]}**"
        )
        await interaction.followup.send(embed=embed)

    # ── 8-BALL ───────────────────────────────────────────────────────────

    @app_commands.command(name="8top", description="Sihirli 8 top! Soruyu sor, cevabı al.")
    @app_commands.describe(soru="Sormak istediğin soru")
    async def eight_ball(self, interaction: discord.Interaction, soru: str):
        await interaction.response.defer()
        responses = [
            "Kesinlikle evet! 🎯", "Evet, şüphe yok! ✅", "Öyle görünüyor. 👍",
            "Çok muhtemelen! 🌟", "Buna güvenebilirsin. 💪", "Tahminime göre evet. 😊",
            "Şu an cevap veremiyorum. 🤔", "Daha sonra sor. ⏰",
            "Tahmin etmeye çalışma. 🎱", "Odaklan ve tekrar sor. 🧘",
            "Sanmıyorum. 🤨", "Olası değil. ❌", "Hayır! 🚫",
            "Öyle görünmüyor. 😬", "Çok şüpheliyim. 🌧️"
        ]
        embed = discord.Embed(
            title="🎱 Sihirli 8 Top",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="❓ Soru",  value=soru,                      inline=False)
        embed.add_field(name="🎱 Cevap", value=random.choice(responses),  inline=False)
        embed.set_footer(text=f"Soran: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    # ── ANKET ────────────────────────────────────────────────────────────

    @app_commands.command(name="anket", description="Anket oluşturur. Soru | Seçenek1 | Seçenek2")
    @app_commands.guild_only()
    @app_commands.describe(içerik="Anket içeriği: Soru | Seçenek1 | Seçenek2 | ...")
    async def poll(self, interaction: discord.Interaction, içerik: str):
        await interaction.response.defer()
        parts = [p.strip() for p in içerik.split("|")]
        if len(parts) < 2:
            return await interaction.followup.send(embed=error_embed(
                "Format Hatası",
                "Kullanım: `/anket Soru | Seçenek1 | Seçenek2 | ...`"
            ), ephemeral=True)

        question = parts[0]
        options  = parts[1:]
        if len(options) > 9:
            return await interaction.followup.send(
                embed=error_embed("En fazla 9 seçenek ekleyebilirsin!"), ephemeral=True)

        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        description   = "\n\n".join(
            f"{number_emojis[i]} {opt}" for i, opt in enumerate(options)
        )
        embed = discord.Embed(
            title=f"📊 {question}",
            description=description,
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Anket: {interaction.user.display_name}")

        msg = await interaction.followup.send(embed=embed)
        # Fetch the actual message to add reactions
        msg = await interaction.original_response()
        for i in range(len(options)):
            await msg.add_reaction(number_emojis[i])

    # ── SÖYLE ────────────────────────────────────────────────────────────

    @app_commands.command(name="söyle", description="Bot adına özel embed mesaj gönderir.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(metin="Gönderilecek metin")
    async def say(self, interaction: discord.Interaction, metin: str):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            description=metin,
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Mesaj gönderildi.", ephemeral=True)

    # ── YARDIM ───────────────────────────────────────────────────────────

    @app_commands.command(name="yardım", description="Sayfalı yardım menüsünü gösterir.")
    @app_commands.describe(komut="Belirli bir komut hakkında bilgi al")
    async def help_command(self, interaction: discord.Interaction,
                           komut: str = None):
        await interaction.response.defer(ephemeral=True)

        if komut:
            # Slash komut ara
            cmd = self.bot.tree.get_command(komut)
            if cmd is None:
                # Prefix komut da dene
                cmd = self.bot.get_command(komut)
            if cmd is None:
                return await interaction.followup.send(embed=error_embed(
                    "Komut Bulunamadı",
                    f"`{komut}` adında bir komut yok."
                ), ephemeral=True)
            embed = discord.Embed(
                title=f"📖 Komut: /{getattr(cmd, 'qualified_name', komut)}",
                description=getattr(cmd, "description", getattr(cmd, "help", "Açıklama yok.")),
                color=Colors.INFO
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Tüm kategorileri sayfalara böl
        pages = []

        intro = discord.Embed(
            title="🤖 Bot Yardım Menüsü",
            description=(
                "Merhaba! Ben bir Discord botuyum.\n"
                "Tüm komutlarıma `/` yazarak ulaşabilirsin.\n\n"
                "Aşağıdaki ▶ butonuyla kategorileri gezebilirsin."
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

        # Slash komutları kategoriye göre topla
        slash_cmds = {c.name: c for c in self.bot.tree.get_commands()}
        cog_slash: dict[str, list] = {}
        for cog_name, cog in self.bot.cogs.items():
            cog_slash[cog.qualified_name] = []
            for cmd in cog.get_app_commands() if hasattr(cog, "get_app_commands") else []:
                cog_slash[cog.qualified_name].append(cmd)

        for cog_name, cog in self.bot.cogs.items():
            app_cmds = [c for c in self.bot.tree.get_commands()
                        if hasattr(c, "binding") and c.binding is cog]
            if not app_cmds:
                continue

            embed = discord.Embed(
                title=f"📂 {cog.qualified_name}",
                description=cog.description or "Bu kategorideki slash komutlar:",
                color=Colors.INFO
            )
            for cmd in app_cmds[:20]:
                embed.add_field(
                    name=f"`/{cmd.name}`",
                    value=cmd.description or "Açıklama yok.",
                    inline=False
                )
            embed.set_footer(text=f"Sayfa {len(pages) + 1}")
            pages.append(embed)

        for i, page in enumerate(pages):
            page.set_footer(text=f"Sayfa {i + 1}/{len(pages)}")

        view = Paginator(pages, interaction.user)
        await interaction.followup.send(embed=pages[0], view=view, ephemeral=True)

    # ── PİNG ─────────────────────────────────────────────────────────────

    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer()
        latency = round(self.bot.latency * 1000)
        color   = (Colors.SUCCESS if latency < 100 else
                   Colors.WARNING if latency < 200 else Colors.ERROR)
        embed   = discord.Embed(
            title="🏓 Pong!",
            description=f"API Gecikmesi: **{latency}ms**",
            color=color
        )
        await interaction.followup.send(embed=embed)

    # ── ŞAKA ─────────────────────────────────────────────────────────────

    @app_commands.command(name="şaka", description="Rastgele bir yazılım şakası söyler.")
    async def joke(self, interaction: discord.Interaction):
        await interaction.response.defer()
        jokes = [
            ("Bir programcı neden dışarı çıkmıyor?", "Çünkü 'goto' komutu yasaklandı!"),
            ("Python neden mutlu?",                   "Çünkü her zaman indent'li!"),
            ("Git neden üzgün?",                      "Çünkü hep 'pull request' bekliyor..."),
            ("Discord botu neden yorulmuyor?",         "Çünkü asenkron!"),
            ("Veritabanı neden yalnız?",               "Çünkü hep 'NULL' ilişkiler kuruyor."),
            ("Programcı kaç tane soru sorar?",         "1, hep 0'dan başlar."),
        ]
        setup, punchline = random.choice(jokes)
        embed = discord.Embed(color=Colors.INFO)
        embed.add_field(name="😄 " + setup, value=punchline, inline=False)
        await interaction.followup.send(embed=embed)

    # ── BOT BİLGİ ────────────────────────────────────────────────────────

    @app_commands.command(name="botbilgi", description="Bot hakkında bilgi verir.")
    async def bot_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title=f"🤖 {self.bot.user.name} Hakkında",
            color=Colors.INFO,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="👥 Sunucu",
                        value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👤 Kullanıcı",
                        value=str(sum(g.member_count for g in self.bot.guilds)), inline=True)
        embed.add_field(name="📡 Gecikme",
                        value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="⚙️ Slash Komut",
                        value=str(len(self.bot.tree.get_commands())), inline=True)
        embed.add_field(name="📦 Cog",
                        value=str(len(self.bot.cogs)), inline=True)
        embed.add_field(name="🐍 Kütüphane",
                        value="discord.py 2.x", inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))

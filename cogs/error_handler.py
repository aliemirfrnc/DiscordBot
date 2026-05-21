"""
cogs/error_handler.py
Tüm hataları merkezi olarak yakalayan ve kullanıcıya anlaşılır mesajlar gösteren Cog.
Bot bu sayede beklenmedik hatalar yüzünden çökmez.
"""

import discord
from discord.ext import commands
import traceback
import sys

from utils.helpers import error_embed


class ErrorHandler(commands.Cog, name="Hata Yöneticisi"):
    """Global hata yakalama ve yönetme sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context,
                               error: commands.CommandError):
        """
        Tüm komut hatalarını yakalar.
        Her hata türü için kullanıcıya uygun bir mesaj gönderir.
        """
        # Eğer komutun kendi hata işleyicisi varsa, onu kullan
        if hasattr(ctx.command, "on_error"):
            return

        # Eğer Cog'un kendi hata işleyicisi varsa, onu kullan
        if ctx.cog and ctx.cog.has_error_handler():
            return

        # Hatayı orijinal haline getir (wrapped ise)
        error = getattr(error, "original", error)

        # ── Komut Bulunamadı ──────────────────────────────
        if isinstance(error, commands.CommandNotFound):
            return  # Sessizce geç, her yanlış yazımda spam olmasın

        # ── Yetki Hatası ─────────────────────────────────
        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            embed = error_embed(
                "Yetersiz Yetki",
                f"Bu komutu kullanmak için şu izinlere ihtiyacın var:\n`{perms}`"
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Bot'un Yetkisi Yok ───────────────────────────
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            embed = error_embed(
                "Bot Yetersiz Yetki",
                f"Bu işlemi yapabilmem için şu izinlere ihtiyacım var:\n`{perms}`"
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Sadece Sunucuda Kullanılabilir ───────────────
        elif isinstance(error, commands.NoPrivateMessage):
            embed = error_embed(
                "Sunucu Gerekli",
                "Bu komut yalnızca sunucularda kullanılabilir, DM'de değil."
            )
            await ctx.author.send(embed=embed)

        # ── Üye Bulunamadı ───────────────────────────────
        elif isinstance(error, commands.MemberNotFound):
            embed = error_embed(
                "Üye Bulunamadı",
                f"**{error.argument}** adında bir üye bulunamadı."
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Eksik Argüman ────────────────────────────────
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = error_embed(
                "Eksik Argüman",
                f"Komutu kullanmak için `{error.param.name}` parametresini girmelisin.\n"
                f"Kullanım: `{ctx.prefix}{ctx.command.qualified_name} "
                f"{ctx.command.signature}`"
            )
            await ctx.send(embed=embed, delete_after=15)

        # ── Yanlış Argüman Tipi ───────────────────────────
        elif isinstance(error, commands.BadArgument):
            embed = error_embed(
                "Hatalı Argüman",
                f"Girdiğin değer hatalı. `{ctx.prefix}yardım {ctx.command.qualified_name}` "
                f"komutuna bakabilirsin."
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Cooldown (Bekleme Süresi) ─────────────────────
        elif isinstance(error, commands.CommandOnCooldown):
            embed = error_embed(
                "Bekleme Süresi",
                f"Bu komutu çok sık kullandın! "
                f"**{error.retry_after:.1f} saniye** sonra tekrar dene."
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Kontrol Hatası (Check Failure) ───────────────
        elif isinstance(error, commands.CheckFailure):
            embed = error_embed(
                "Erişim Reddedildi",
                "Bu komutu kullanma yetkin yok."
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Kanal Bulunamadı ──────────────────────────────
        elif isinstance(error, commands.ChannelNotFound):
            embed = error_embed(
                "Kanal Bulunamadı",
                f"**{error.argument}** adında bir kanal bulunamadı."
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Rol Bulunamadı ────────────────────────────────
        elif isinstance(error, commands.RoleNotFound):
            embed = error_embed(
                "Rol Bulunamadı",
                f"**{error.argument}** adında bir rol bulunamadı."
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Beklenmeyen Hatalar ───────────────────────────
        else:
            embed = error_embed(
                "Beklenmeyen Hata",
                f"Beklenmedik bir hata oluştu. Geliştiriciye bildir.\n"
                f"```{type(error).__name__}: {error}```"
            )
            await ctx.send(embed=embed, delete_after=30)
            # Hatayı konsola da yazdır (geliştiriciler için)
            print(f"[HATA] '{ctx.command}' komutunda işlenmemiş hata:",
                  file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__,
                                      file=sys.stderr)


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(ErrorHandler(bot))
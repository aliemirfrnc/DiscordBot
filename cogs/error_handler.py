"""
cogs/error_handler.py
Prefix komutları ve slash komutları için merkezi hata yönetimi.
"""

import discord
from discord.ext import commands
from discord import app_commands
import traceback
import sys

from utils.helpers import error_embed


class ErrorHandler(commands.Cog, name="Hata Yöneticisi"):
    """Global hata yakalama ve yönetme sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Slash komut hata yakalayıcısını tree'ye bağla
        bot.tree.on_error = self.on_app_command_error

    # ── PREFIX KOMUT HATALARI ─────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context,
                               error: commands.CommandError):
        if hasattr(ctx.command, "on_error"):
            return
        if ctx.cog and ctx.cog.has_error_handler():
            return

        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(embed=error_embed(
                "Yetersiz Yetki",
                f"Bu komutu kullanmak için gerekli izinler:\n`{perms}`"
            ), delete_after=10)

        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(embed=error_embed(
                "Bot Yetersiz Yetki",
                f"Bu işlem için şu izinlere ihtiyacım var:\n`{perms}`"
            ), delete_after=10)

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send(embed=error_embed(
                "Sunucu Gerekli",
                "Bu komut yalnızca sunucularda kullanılabilir."
            ))

        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=error_embed(
                "Üye Bulunamadı",
                f"**{error.argument}** adında bir üye bulunamadı."
            ), delete_after=10)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(
                "Eksik Argüman",
                f"`{error.param.name}` parametresini girmelisin.\n"
                f"Kullanım: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            ), delete_after=15)

        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=error_embed(
                "Hatalı Argüman",
                f"`{ctx.prefix}yardım {ctx.command.qualified_name}` ile kullanıma bakabilirsin."
            ), delete_after=10)

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=error_embed(
                "Bekleme Süresi",
                f"**{error.retry_after:.1f} saniye** sonra tekrar dene."
            ), delete_after=10)

        elif isinstance(error, commands.CheckFailure):
            await ctx.send(embed=error_embed(
                "Erişim Reddedildi",
                "Bu komutu kullanma yetkin yok."
            ), delete_after=10)

        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(embed=error_embed(
                "Kanal Bulunamadı",
                f"**{error.argument}** adında bir kanal bulunamadı."
            ), delete_after=10)

        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(embed=error_embed(
                "Rol Bulunamadı",
                f"**{error.argument}** adında bir rol bulunamadı."
            ), delete_after=10)

        else:
            await ctx.send(embed=error_embed(
                "Beklenmeyen Hata",
                f"Beklenmedik bir hata oluştu.\n"
                f"```{type(error).__name__}: {str(error)[:200]}```"
            ), delete_after=30)
            print(f"[HATA] '{ctx.command}' komutunda işlenmemiş hata:", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    # ── SLASH KOMUT HATALARI ──────────────────────────────────────────────
    async def on_app_command_error(self,
                                   interaction: discord.Interaction,
                                   error: app_commands.AppCommandError):
        """Slash komut hatalarını yakalar."""

        async def send_error(title: str, desc: str):
            embed = error_embed(title, desc)
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass

        error = getattr(error, "original", error)

        if isinstance(error, app_commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await send_error("Yetersiz Yetki", f"Gerekli izinler:\n`{perms}`")

        elif isinstance(error, app_commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await send_error("Bot Yetersiz Yetki", f"Gerekli izinlerim:\n`{perms}`")

        elif isinstance(error, app_commands.CommandOnCooldown):
            await send_error("Bekleme Süresi",
                             f"**{error.retry_after:.1f} saniye** sonra tekrar dene.")

        elif isinstance(error, app_commands.CheckFailure):
            await send_error("Erişim Reddedildi", "Bu komutu kullanma yetkin yok.")

        elif isinstance(error, app_commands.NoPrivateMessage):
            await send_error("Sunucu Gerekli", "Bu komut yalnızca sunucularda kullanılabilir.")

        else:
            await send_error("Beklenmeyen Hata",
                             f"```{type(error).__name__}: {str(error)[:200]}```")
            print(f"[HATA] Slash komut hatası ({interaction.command}):", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))

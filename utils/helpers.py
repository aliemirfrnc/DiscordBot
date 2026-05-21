"""
utils/helpers.py
Botun genelinde kullanılan yardımcı fonksiyonlar ve sabitler.
"""

import discord
from discord.ext import commands
import datetime
import asyncio
import re


# ─────────────────────────────────────────────
# RENK PALETİ (Embed'lerde kullanılır)
# ─────────────────────────────────────────────
class Colors:
    SUCCESS  = 0x2ECC71   # Yeşil - Başarılı işlemler
    ERROR    = 0xE74C3C   # Kırmızı - Hata mesajları
    WARNING  = 0xF39C12   # Turuncu - Uyarılar
    INFO     = 0x3498DB   # Mavi - Bilgilendirme
    MUSIC    = 0x9B59B6   # Mor - Müzik komutları
    ECONOMY  = 0xF1C40F   # Altın - Ekonomi komutları
    MOD      = 0xE67E22   # Turuncu-kırmızı - Moderasyon
    LEVEL    = 0x1ABC9C   # Turkuaz - Seviye sistemi


# ─────────────────────────────────────────────
# EMBED OLUŞTURUCU YARDIMCILARI
# ─────────────────────────────────────────────

def success_embed(title: str, description: str = None) -> discord.Embed:
    """Başarı embed'i oluşturur."""
    embed = discord.Embed(title=f"✅ {title}", description=description,
                          color=Colors.SUCCESS,
                          timestamp=datetime.datetime.utcnow())
    return embed


def error_embed(title: str, description: str = None) -> discord.Embed:
    """Hata embed'i oluşturur."""
    embed = discord.Embed(title=f"❌ {title}", description=description,
                          color=Colors.ERROR,
                          timestamp=datetime.datetime.utcnow())
    return embed


def info_embed(title: str, description: str = None) -> discord.Embed:
    """Bilgilendirme embed'i oluşturur."""
    embed = discord.Embed(title=f"ℹ️ {title}", description=description,
                          color=Colors.INFO,
                          timestamp=datetime.datetime.utcnow())
    return embed


def warning_embed(title: str, description: str = None) -> discord.Embed:
    """Uyarı embed'i oluşturur."""
    embed = discord.Embed(title=f"⚠️ {title}", description=description,
                          color=Colors.WARNING,
                          timestamp=datetime.datetime.utcnow())
    return embed


# ─────────────────────────────────────────────
# İZİN KONTROLÜ YARDIMCILARI
# ─────────────────────────────────────────────

def is_mod():
    """Kullanıcının moderatör yetkisi olup olmadığını kontrol eden dekoratör."""
    async def predicate(ctx):
        return (ctx.author.guild_permissions.manage_messages or
                ctx.author.guild_permissions.administrator)
    return commands.check(predicate)


def is_admin():
    """Kullanıcının admin yetkisi olup olmadığını kontrol eden dekoratör."""
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)


# ─────────────────────────────────────────────
# FORMAT YARDIMCILARI
# ─────────────────────────────────────────────

def format_duration(seconds: int) -> str:
    """Saniyeyi MM:SS veya HH:MM:SS formatına çevirir."""
    hours   = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs    = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_number(num: int) -> str:
    """Büyük sayıları okunabilir formata çevirir (örn: 1,000,000)."""
    return f"{num:,}"


def progress_bar(current: int, maximum: int, length: int = 10) -> str:
    """XP veya benzeri değerler için metin progress bar oluşturur."""
    if maximum == 0:
        percentage = 0
    else:
        percentage = int((current / maximum) * 100)

    filled = int((current / maximum) * length) if maximum > 0 else 0
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {percentage}%"


def time_remaining(target: datetime.datetime) -> str:
    """Belirli bir zamana kalan süreyi formatlar."""
    now = datetime.datetime.utcnow()
    delta = target - now
    if delta.total_seconds() <= 0:
        return "Şimdi"
    hours   = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    seconds = int(delta.total_seconds() % 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours} saat")
    if minutes > 0:
        parts.append(f"{minutes} dakika")
    if seconds > 0:
        parts.append(f"{seconds} saniye")
    return " ".join(parts)


# ─────────────────────────────────────────────
# MODERASYON SABİTLERİ
# ─────────────────────────────────────────────

# Küfür filtrelemesi için yasaklı kelimeler
PROFANITY_WORDS = [
    "küfür1", "küfür2", "küfür3", "bok", "siktir", "orospu",
]

# Link filtrelemesi için regex deseni
LINK_PATTERN = re.compile(
    r"(https?://|www\.|discord\.gg/|youtu\.be/)"
    r"[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
)


# ─────────────────────────────────────────────
# PAGINATOR - SAYFALANMIŞ GÖRÜNÜM
# ─────────────────────────────────────────────

class Paginator(discord.ui.View):
    """
    Birden fazla sayfayı düğmelerle gezdirmeye yarayan View bileşeni.
    Help menüsü ve listeler için kullanılır.
    """

    def __init__(self, embeds: list, author: discord.Member, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.embeds  = embeds
        self.current = 0
        self.author  = author
        self._update_buttons()

    def _update_buttons(self):
        """Sayfa durumuna göre düğmeleri güncelle."""
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current == len(self.embeds) - 1
        self.page_button.label = f"{self.current + 1}/{len(self.embeds)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Sadece komut sahibi etkileşime girebilir."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Bu menüyü yalnızca komut kullanan kişi kontrol edebilir!",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label="✖ Kapat", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        self.stop()
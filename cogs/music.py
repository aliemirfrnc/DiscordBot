"""
cogs/music.py
FFmpeg + yt-dlp tabanlı gelişmiş müzik sistemi — Slash komutlarına geçirildi.
"""

import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import datetime
from collections import deque

from utils.helpers import error_embed, success_embed, info_embed, Colors, format_duration


# ─────────────────────────────────────────────
# YT-DLP VE FFMPEG AYARLARI
# ─────────────────────────────────────────────
FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin"
    ),
    "options": "-vn -filter:a 'volume=0.5'"
}

YTDL_FORMAT_OPTIONS = {
    "format":             "bestaudio/best",
    "outtmpl":            "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames":  True,
    "noplaylist":         False,
    "nocheckcertificate": True,
    "ignoreerrors":       False,
    "logtostderr":        False,
    "quiet":              True,
    "no_warnings":        True,
    "default_search":     "auto",
    "source_address":     "0.0.0.0",
}

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)
        self.data      = data
        self.title     = data.get("title", "Bilinmiyor")
        self.url       = data.get("webpage_url", "")
        self.duration  = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail", "")
        self.uploader  = data.get("uploader", "Bilinmiyor")
        self.requester = None

    @classmethod
    async def from_url(cls, url: str, *, loop: asyncio.AbstractEventLoop = None,
                       stream: bool = True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )
        if "entries" in data:
            entries = list(data["entries"])
            if not entries:
                raise ValueError("Playlist boş veya erişilemiyor.")
            return entries, data.get("title", "Playlist")

        audio_url = data["url"] if stream else ytdl.prepare_filename(data)
        return [data], data.get("title", "Bilinmiyor")

    @classmethod
    def build_source(cls, data: dict, volume: float = 0.5) -> "YTDLSource":
        source = discord.FFmpegPCMAudio(data["url"], **FFMPEG_OPTIONS)
        return cls(source, data=data, volume=volume)


class GuildMusicState:
    def __init__(self):
        self.queue: deque  = deque()
        self.current       = None
        self.voice_client  = None
        self.loop          = False
        self.volume: float = 0.5
        self.text_channel  = None

    def is_playing(self) -> bool:
        return self.voice_client and self.voice_client.is_playing()

    def is_paused(self) -> bool:
        return self.voice_client and self.voice_client.is_paused()

    def skip(self):
        if self.voice_client:
            self.voice_client.stop()

    async def cleanup(self):
        self.queue.clear()
        self.current = None
        if self.voice_client:
            try:
                await self.voice_client.disconnect()
            except Exception:
                pass
            self.voice_client = None


class Music(commands.Cog, name="Müzik"):
    """Gelişmiş müzik sistemi. YouTube ve diğer kaynaklardan müzik çalar."""

    def __init__(self, bot: commands.Bot):
        self.bot    = bot
        self.states: dict[int, GuildMusicState] = {}

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState()
        return self.states[guild_id]

    def _build_now_playing_embed(self, state: GuildMusicState) -> discord.Embed:
        track = state.current
        embed = discord.Embed(
            title="🎵 Şu An Çalıyor",
            description=f"**[{track.title}]({track.url})**",
            color=Colors.MUSIC,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=track.thumbnail or "")
        embed.add_field(name="⏱ Süre",
                        value=format_duration(track.duration) if track.duration else "Bilinmiyor")
        embed.add_field(name="🎤 Yükleyen", value=track.uploader)
        embed.add_field(name="👤 İsteyen",  value=str(track.requester))
        embed.add_field(name="🔁 Tekrar",   value="Açık ✅" if state.loop else "Kapalı ❌")
        embed.add_field(name="🔊 Ses",      value=f"%{int(state.volume * 100)}")
        embed.add_field(name="📋 Kuyruk",   value=f"{len(state.queue)} şarkı")
        return embed

    async def _play_next(self, guild: discord.Guild):
        state = self.get_state(guild.id)

        if state.loop and state.current:
            try:
                new_source = YTDLSource.build_source(state.current.data, state.volume)
                new_source.requester = state.current.requester
                state.current = new_source
                state.voice_client.play(
                    new_source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self._play_next(guild), self.bot.loop
                    )
                )
                return
            except Exception:
                pass

        if state.queue:
            data = state.queue.popleft()
            try:
                source = YTDLSource.build_source(data["data"], state.volume)
                source.requester = data["requester"]
                state.current = source
                state.voice_client.play(
                    source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self._play_next(guild), self.bot.loop
                    )
                )
                if state.text_channel:
                    await state.text_channel.send(
                        embed=self._build_now_playing_embed(state), delete_after=30)
            except Exception as e:
                if state.text_channel:
                    await state.text_channel.send(
                        embed=error_embed("Çalma Hatası", str(e)), delete_after=10)
                await self._play_next(guild)
        else:
            state.current = None
            if state.text_channel:
                await state.text_channel.send(
                    embed=info_embed("Kuyruk Bitti", "Çalacak başka şarkı kalmadı."),
                    delete_after=15
                )

    # ── SLASH KOMUTLAR ───────────────────────────────────────────────────

    @app_commands.command(name="çal", description="YouTube'dan şarkı çalar veya kuyruğa ekler.")
    @app_commands.guild_only()
    @app_commands.describe(sorgu="Şarkı adı veya YouTube linki")
    async def play(self, interaction: discord.Interaction, sorgu: str):
        await interaction.response.defer()

        state = self.get_state(interaction.guild.id)
        state.text_channel = interaction.channel

        if not interaction.user.voice:
            return await interaction.followup.send(embed=error_embed(
                "Ses Kanalı Gerekli", "Önce bir ses kanalına katılmalısın!"
            ), ephemeral=True)

        voice_channel = interaction.user.voice.channel

        if not state.voice_client or not state.voice_client.is_connected():
            try:
                state.voice_client = await voice_channel.connect()
            except discord.ClientException:
                return await interaction.followup.send(embed=error_embed(
                    "Bağlantı Hatası", "Ses kanalına bağlanırken bir hata oluştu."
                ), ephemeral=True)
        elif state.voice_client.channel != voice_channel:
            await state.voice_client.move_to(voice_channel)

        try:
            query = sorgu if sorgu.startswith("http") else f"ytsearch:{sorgu}"
            entries, playlist_title = await YTDLSource.from_url(
                query, loop=self.bot.loop, stream=True)

            added_count = 0
            for entry in entries:
                if "url" not in entry:
                    try:
                        entry = await self.bot.loop.run_in_executor(
                            None, lambda e=entry: ytdl.extract_info(
                                e["webpage_url"], download=False)
                        )
                    except Exception:
                        continue

                state.queue.append({"data": entry, "requester": interaction.user})
                added_count += 1

            if added_count == 0:
                return await interaction.followup.send(embed=error_embed(
                    "Bulunamadı", "Bu sorgu için sonuç bulunamadı."
                ))

            if added_count == 1:
                entry = entries[0]
                embed = success_embed(
                    "Kuyruğa Eklendi" if state.is_playing() else "Çalınıyor",
                    f"**[{entry.get('title', 'Bilinmiyor')}]"
                    f"({entry.get('webpage_url', '')})**\n"
                    f"⏱ Süre: {format_duration(entry.get('duration', 0))}"
                )
            else:
                embed = success_embed(
                    "Playlist Kuyruğa Eklendi",
                    f"**{playlist_title}** listesinden **{added_count}** şarkı kuyruğa eklendi."
                )
            embed.color = Colors.MUSIC
            await interaction.followup.send(embed=embed)

            if not state.is_playing() and not state.is_paused():
                await self._play_next(interaction.guild)

        except yt_dlp.utils.DownloadError as e:
            await interaction.followup.send(embed=error_embed(
                "İndirme Hatası", f"`{str(e)[:200]}`"))
        except Exception as e:
            await interaction.followup.send(embed=error_embed("Hata", str(e)[:300]))

    @app_commands.command(name="dur", description="Çalmayı duraklatır.")
    @app_commands.guild_only()
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        if state.is_playing():
            state.voice_client.pause()
            await interaction.followup.send(
                embed=success_embed("⏸ Duraklatıldı", "Şarkı duraklatıldı."), ephemeral=True)
        else:
            await interaction.followup.send(
                embed=error_embed("Şu an bir şey çalmıyor."), ephemeral=True)

    @app_commands.command(name="devam", description="Duraklatılmış şarkıyı devam ettirir.")
    @app_commands.guild_only()
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        if state.is_paused():
            state.voice_client.resume()
            await interaction.followup.send(
                embed=success_embed("▶️ Devam Edildi", "Şarkı devam ediyor."), ephemeral=True)
        else:
            await interaction.followup.send(
                embed=error_embed("Duraklatılmış şarkı yok."), ephemeral=True)

    @app_commands.command(name="atla", description="Mevcut şarkıyı atlar.")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        if not state.is_playing() and not state.is_paused():
            return await interaction.followup.send(
                embed=error_embed("Atlanacak bir şarkı yok."), ephemeral=True)

        title = state.current.title if state.current else "Bilinmiyor"
        state.skip()
        await interaction.followup.send(embed=success_embed("⏭ Atlandı", f"**{title}** atlandı."))

    @app_commands.command(name="durdur", description="Çalmayı durdurur ve kuyruğu temizler.")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        await state.cleanup()
        if interaction.guild.id in self.states:
            del self.states[interaction.guild.id]
        await interaction.followup.send(embed=success_embed(
            "⏹ Durduruldu", "Müzik durduruldu ve kuyruk temizlendi."))

    @app_commands.command(name="kuyruk", description="Müzik kuyruğunu gösterir.")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)

        if not state.current and not state.queue:
            return await interaction.followup.send(embed=info_embed(
                "Kuyruk Boş", "Şu an çalan şarkı yok. `/çal <şarkı>` komutuyla başlat!"))

        embed = discord.Embed(
            title="🎵 Müzik Kuyruğu",
            color=Colors.MUSIC,
            timestamp=datetime.datetime.utcnow()
        )
        if state.current:
            embed.add_field(
                name="▶️ Şu An Çalıyor",
                value=f"**[{state.current.title}]({state.current.url})**\n"
                      f"⏱ {format_duration(state.current.duration)} | 👤 {state.current.requester}",
                inline=False
            )

        if state.queue:
            queue_list = []
            for i, item in enumerate(list(state.queue)[:10], 1):
                data = item["data"]
                dur  = format_duration(data.get("duration", 0))
                queue_list.append(
                    f"`{i}.` **{data.get('title', 'Bilinmiyor')[:50]}** "
                    f"| ⏱ {dur} | 👤 {item['requester']}"
                )
            embed.add_field(
                name=f"📋 Sıradaki Şarkılar ({len(state.queue)} toplam)",
                value="\n".join(queue_list),
                inline=False
            )
            if len(state.queue) > 10:
                embed.set_footer(text=f"... ve {len(state.queue) - 10} şarkı daha")

        embed.add_field(name="🔁 Tekrar", value="Açık" if state.loop else "Kapalı")
        embed.add_field(name="🔊 Ses",    value=f"%{int(state.volume * 100)}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tekrar", description="Tekrar modunu açar/kapatır.")
    @app_commands.guild_only()
    async def loop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        state.loop = not state.loop
        status = "açıldı 🔁" if state.loop else "kapatıldı"
        await interaction.followup.send(embed=success_embed(
            f"Tekrar Modu {status}",
            "Şarkı sürekli tekrarlanacak." if state.loop else "Şarkı bir kez çalınacak."
        ))

    @app_commands.command(name="ses", description="Ses seviyesini ayarlar (1-200).")
    @app_commands.guild_only()
    @app_commands.describe(seviye="Ses seviyesi (1-200 arası)")
    async def volume(self, interaction: discord.Interaction, seviye: int):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)

        if seviye < 1 or seviye > 200:
            return await interaction.followup.send(
                embed=error_embed("Ses seviyesi 1 ile 200 arasında olmalı."), ephemeral=True)

        state.volume = seviye / 100
        if state.current:
            state.current.volume = state.volume

        await interaction.followup.send(embed=success_embed(
            "🔊 Ses Ayarlandı", f"Ses seviyesi **%{seviye}** olarak ayarlandı."))

    @app_commands.command(name="çalıyor", description="Şu an çalan şarkıyı gösterir.")
    @app_commands.guild_only()
    async def now_playing(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        if not state.current:
            return await interaction.followup.send(embed=info_embed(
                "Şu an bir şey çalmıyor.", "`/çal <şarkı>` komutuyla müzik başlatabilirsin."))
        await interaction.followup.send(embed=self._build_now_playing_embed(state))

    @app_commands.command(name="karıştır", description="Kuyruğu rastgele karıştırır.")
    @app_commands.guild_only()
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        import random
        state = self.get_state(interaction.guild.id)
        if len(state.queue) < 2:
            return await interaction.followup.send(
                embed=error_embed("Karıştırmak için en az 2 şarkı gerekli."), ephemeral=True)
        queue_list = list(state.queue)
        random.shuffle(queue_list)
        state.queue = deque(queue_list)
        await interaction.followup.send(embed=success_embed(
            "🔀 Kuyruk Karıştırıldı", f"{len(state.queue)} şarkı rastgele sıralandı."))

    @app_commands.command(name="kuyruk-temizle", description="Müzik kuyruğunu temizler.")
    @app_commands.guild_only()
    async def clear_queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        count = len(state.queue)
        state.queue.clear()
        await interaction.followup.send(embed=success_embed(
            "Kuyruk Temizlendi", f"{count} şarkı kuyruğu silindi."))

    @app_commands.command(name="kuyruk-sil", description="Kuyruktaki belirli bir şarkıyı siler.")
    @app_commands.guild_only()
    @app_commands.describe(sıra="Silinecek şarkının sıra numarası (1'den başlar)")
    async def remove_from_queue(self, interaction: discord.Interaction, sıra: int):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        if sıra < 1 or sıra > len(state.queue):
            return await interaction.followup.send(
                embed=error_embed(f"Geçerli bir sıra gir (1-{len(state.queue)})."), ephemeral=True)

        queue_list = list(state.queue)
        removed    = queue_list.pop(sıra - 1)
        state.queue = deque(queue_list)
        await interaction.followup.send(embed=success_embed(
            "Şarkı Silindi",
            f"**{removed['data'].get('title', 'Bilinmiyor')}** kuyruğdan silindi."))

    @app_commands.command(name="bağlan", description="Ses kanalına bağlanır.")
    @app_commands.guild_only()
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not interaction.user.voice:
            return await interaction.followup.send(
                embed=error_embed("Ses kanalında değilsin!"), ephemeral=True)
        state   = self.get_state(interaction.guild.id)
        channel = interaction.user.voice.channel
        if state.voice_client and state.voice_client.is_connected():
            await state.voice_client.move_to(channel)
        else:
            state.voice_client = await channel.connect()
        await interaction.followup.send(embed=success_embed(
            "Bağlandı", f"**{channel.name}** kanalına bağlandım."))

    @app_commands.command(name="ayrıl", description="Ses kanalından ayrılır.")
    @app_commands.guild_only()
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        await state.cleanup()
        if interaction.guild.id in self.states:
            del self.states[interaction.guild.id]
        await interaction.followup.send(embed=success_embed("👋 Ayrıldım", "Görüşürüz!"))


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))

"""
cogs/music.py
FFmpeg + yt-dlp tabanlı gelişmiş müzik sistemi.
Wavelink yerine doğrudan discord.py voice client kullanılır (daha taşınabilir).
Play, pause, resume, skip, queue, loop, volume, now-playing komutlarını içerir.
"""

import discord
from discord.ext import commands
import yt_dlp
import asyncio
import datetime
from collections import deque

from utils.helpers import error_embed, success_embed, info_embed, Colors, format_duration


# ─────────────────────────────────────────────
# YT-DLP VE FFMPEG AYARLARI
# ─────────────────────────────────────────────

# FFmpeg ses seçenekleri - ses kalitesi için optimize edilmiş
FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
        "-nostdin"
    ),
    "options": "-vn -filter:a 'volume=0.5'"
}

# yt-dlp ayarları
YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,        # Playlist desteği açık
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",   # Arama sorgusu için "ytsearch:" otomatik eklenir
    "source_address": "0.0.0.0",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "opus",
        "preferredquality": "192",
    }],
}

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    """
    yt-dlp ile ses kaynağı oluşturan sınıf.
    discord.PCMVolumeTransformer kullanarak anlık ses seviyesi ayarı sağlar.
    """

    def __init__(self, source: discord.FFmpegPCMAudio, *, data: dict,
                 volume: float = 0.5):
        super().__init__(source, volume)
        self.data     = data
        self.title    = data.get("title", "Bilinmiyor")
        self.url      = data.get("webpage_url", "")
        self.duration = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail", "")
        self.uploader  = data.get("uploader", "Bilinmiyor")
        self.requester = None  # Komutu veren kişi (dışarıdan atanır)

    @classmethod
    async def from_url(cls, url: str, *, loop: asyncio.AbstractEventLoop = None,
                       stream: bool = True):
        """
        URL veya arama sorgusundan ses kaynağı oluşturur.
        stream=True ile dosya indirmeden direkt akış sağlanır.
        """
        loop = loop or asyncio.get_event_loop()

        # yt-dlp'yi asenkron çalıştır (blocking olduğu için thread'de)
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(url, download=not stream)
        )

        # Playlist ise ilk parçayı al
        if "entries" in data:
            entries = list(data["entries"])
            if not entries:
                raise ValueError("Playlist boş veya erişilemiyor.")
            # Playlist için tüm entry'leri döndür
            return entries, data.get("title", "Playlist")

        # Tek parça için ses URL'si al
        audio_url = data["url"] if stream else ytdl.prepare_filename(data)
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        return [data], data.get("title", "Bilinmiyor")

    @classmethod
    def build_source(cls, data: dict, volume: float = 0.5) -> "YTDLSource":
        """Veri sözlüğünden ses kaynağı oluşturur."""
        audio_url = data["url"]
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        return cls(source, data=data, volume=volume)


# ─────────────────────────────────────────────
# MÜZIK DURUMU (Her sunucu için ayrı)
# ─────────────────────────────────────────────

class GuildMusicState:
    """Bir sunucunun müzik durumunu tutar."""

    def __init__(self):
        self.queue: deque     = deque()        # Şarkı sırası
        self.current          = None           # Şu an çalan şarkı (YTDLSource)
        self.voice_client     = None           # Ses bağlantısı
        self.loop             = False          # Tekrar modu
        self.volume: float    = 0.5            # Ses seviyesi (0.0 - 2.0)
        self.text_channel     = None           # Komut yazılan kanal
        self._skip_flag       = False          # Skip sinyali

    def is_playing(self) -> bool:
        return self.voice_client and self.voice_client.is_playing()

    def is_paused(self) -> bool:
        return self.voice_client and self.voice_client.is_paused()

    def skip(self):
        """Mevcut şarkıyı atlar."""
        self._skip_flag = True
        if self.voice_client:
            self.voice_client.stop()

    async def cleanup(self):
        """Ses bağlantısını kapatır ve sırayı temizler."""
        self.queue.clear()
        self.current = None
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None


# ─────────────────────────────────────────────
# MÜZİK COG
# ─────────────────────────────────────────────

class Music(commands.Cog, name="Müzik"):
    """Gelişmiş müzik sistemi. YouTube ve diğer kaynaklardan müzik çalar."""

    def __init__(self, bot: commands.Bot):
        self.bot    = bot
        self.states: dict[int, GuildMusicState] = {}  # guild_id -> state

    def get_state(self, guild_id: int) -> GuildMusicState:
        """Sunucunun müzik durumunu döndürür, yoksa oluşturur."""
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState()
        return self.states[guild_id]

    def _build_now_playing_embed(self, state: GuildMusicState) -> discord.Embed:
        """'Şu an çalıyor' embed'i oluşturur."""
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
        embed.add_field(name="👤 İsteyen", value=str(track.requester))
        embed.add_field(name="🔁 Tekrar",  value="Açık ✅" if state.loop else "Kapalı ❌")
        embed.add_field(name="🔊 Ses",     value=f"%{int(state.volume * 100)}")
        embed.add_field(name="📋 Kuyruk",  value=f"{len(state.queue)} şarkı")
        return embed

    async def _play_next(self, guild: discord.Guild):
        """
        Kuyruktaki bir sonraki şarkıyı çalar.
        Tekrar modu açıksa aynı şarkıyı tekrar başlatır.
        """
        state = self.get_state(guild.id)

        # Tekrar modu: mevcut şarkıyı yeniden başlat
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

        # Kuyrukta şarkı varsa sıradakini çal
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
                # Çalma başladığında kanala bildir
                if state.text_channel:
                    await state.text_channel.send(
                        embed=self._build_now_playing_embed(state),
                        delete_after=30
                    )
            except Exception as e:
                if state.text_channel:
                    await state.text_channel.send(
                        embed=error_embed("Çalma Hatası", str(e)),
                        delete_after=10
                    )
                await self._play_next(guild)
        else:
            # Kuyruk bitti
            state.current = None
            if state.text_channel:
                await state.text_channel.send(
                    embed=info_embed("Kuyruk Bitti", "Çalacak başka şarkı kalmadı."),
                    delete_after=15
                )

    # ─────────────────────────────────────────────
    # KOMUTLAR
    # ─────────────────────────────────────────────

    @commands.command(name="çal", aliases=["play", "p"],
                      help="YouTube'dan şarkı çalar veya kuyruğa ekler.")
    @commands.guild_only()
    async def play(self, ctx: commands.Context, *, query: str):
        """
        Şarkı çalar veya kuyruğa ekler.
        Kullanım: !çal <şarkı adı veya YouTube linki>
        """
        state = self.get_state(ctx.guild.id)
        state.text_channel = ctx.channel

        # Ses kanalı kontrolü
        if not ctx.author.voice:
            return await ctx.send(embed=error_embed(
                "Ses Kanalı Gerekli",
                "Önce bir ses kanalına katılmalısın!"
            ))

        voice_channel = ctx.author.voice.channel

        # Bağlan veya mevcut bağlantıyı kullan
        if not state.voice_client or not state.voice_client.is_connected():
            try:
                state.voice_client = await voice_channel.connect()
            except discord.ClientException:
                return await ctx.send(embed=error_embed(
                    "Bağlantı Hatası",
                    "Ses kanalına bağlanırken bir hata oluştu."
                ))
        elif state.voice_client.channel != voice_channel:
            await state.voice_client.move_to(voice_channel)

        # Yükleniyor mesajı göster
        loading_msg = await ctx.send(embed=info_embed(
            "🔍 Aranıyor...",
            f"`{query}` aranıyor, lütfen bekle..."
        ))

        try:
            # URL yoksa YouTube'da ara
            if not query.startswith("http"):
                query = f"ytsearch:{query}"

            entries, playlist_title = await YTDLSource.from_url(
                query, loop=self.bot.loop, stream=True
            )

            added_count = 0
            for entry in entries:
                # Her entry için ses URL'si al
                if "url" not in entry:
                    # Bazen entry sadece meta data içerir, tam bilgi lazım
                    try:
                        full_data = await self.bot.loop.run_in_executor(
                            None,
                            lambda e=entry: ytdl.extract_info(e["webpage_url"],
                                                               download=False)
                        )
                        entry = full_data
                    except Exception:
                        continue

                state.queue.append({
                    "data": entry,
                    "requester": ctx.author
                })
                added_count += 1

            await loading_msg.delete()

            if added_count == 0:
                return await ctx.send(embed=error_embed(
                    "Bulunamadı",
                    "Bu sorgu için sonuç bulunamadı."
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
                    f"**{playlist_title}** listesinden "
                    f"**{added_count}** şarkı kuyruğa eklendi."
                )
            embed.color = Colors.MUSIC
            await ctx.send(embed=embed, delete_after=20)

            # Eğer şu an bir şey çalmıyorsa çalmaya başla
            if not state.is_playing() and not state.is_paused():
                await self._play_next(ctx.guild)

        except yt_dlp.utils.DownloadError as e:
            await loading_msg.delete()
            await ctx.send(embed=error_embed(
                "İndirme Hatası",
                f"Şarkı yüklenirken hata oluştu: `{str(e)[:200]}`"
            ))
        except Exception as e:
            await loading_msg.delete()
            await ctx.send(embed=error_embed("Hata", str(e)[:300]))

    @commands.command(name="dur", aliases=["pause"],
                      help="Çalmayı duraklatır.")
    @commands.guild_only()
    async def pause(self, ctx: commands.Context):
        """Şarkıyı duraklatır."""
        state = self.get_state(ctx.guild.id)
        if state.is_playing():
            state.voice_client.pause()
            await ctx.send(embed=success_embed("⏸ Duraklatıldı",
                                               "Şarkı duraklatıldı."), delete_after=10)
        else:
            await ctx.send(embed=error_embed("Şu an bir şey çalmıyor."),
                           delete_after=5)

    @commands.command(name="devam", aliases=["resume"],
                      help="Duraklatılmış şarkıyı devam ettirir.")
    @commands.guild_only()
    async def resume(self, ctx: commands.Context):
        """Duraklatılmış şarkıyı devam ettirir."""
        state = self.get_state(ctx.guild.id)
        if state.is_paused():
            state.voice_client.resume()
            await ctx.send(embed=success_embed("▶️ Devam Edildi",
                                               "Şarkı devam ediyor."), delete_after=10)
        else:
            await ctx.send(embed=error_embed("Duraklatılmış şarkı yok."),
                           delete_after=5)

    @commands.command(name="atla", aliases=["skip", "s"],
                      help="Mevcut şarkıyı atlar.")
    @commands.guild_only()
    async def skip(self, ctx: commands.Context):
        """Mevcut şarkıyı atlar ve sıradakini çalar."""
        state = self.get_state(ctx.guild.id)
        if not state.is_playing() and not state.is_paused():
            return await ctx.send(embed=error_embed("Atlanacak bir şarkı yok."),
                                  delete_after=5)

        title = state.current.title if state.current else "Bilinmiyor"
        state.skip()
        await ctx.send(embed=success_embed(
            "⏭ Atlandı",
            f"**{title}** atlandı."
        ), delete_after=10)

    @commands.command(name="durdur", aliases=["stop"],
                      help="Çalmayı durdurur ve kuyruğu temizler.")
    @commands.guild_only()
    async def stop(self, ctx: commands.Context):
        """Müziği durdurur, kuyruğu temizler ve kanaldan ayrılır."""
        state = self.get_state(ctx.guild.id)
        await state.cleanup()
        if ctx.guild.id in self.states:
            del self.states[ctx.guild.id]
        await ctx.send(embed=success_embed("⏹ Durduruldu",
                                           "Müzik durduruldu ve kuyruk temizlendi."),
                       delete_after=10)

    @commands.command(name="kuyruk", aliases=["queue", "q"],
                      help="Müzik kuyruğunu gösterir.")
    @commands.guild_only()
    async def queue(self, ctx: commands.Context):
        """Mevcut müzik kuyruğunu listeler."""
        state = self.get_state(ctx.guild.id)

        if not state.current and not state.queue:
            return await ctx.send(embed=info_embed(
                "Kuyruk Boş",
                "Şu an çalan şarkı yok. `!çal <şarkı>` komutuyla başlat!"
            ))

        embed = discord.Embed(title="🎵 Müzik Kuyruğu",
                              color=Colors.MUSIC,
                              timestamp=datetime.datetime.utcnow())

        if state.current:
            embed.add_field(
                name="▶️ Şu An Çalıyor",
                value=f"**[{state.current.title}]({state.current.url})**\n"
                      f"⏱ {format_duration(state.current.duration)} | "
                      f"👤 {state.current.requester}",
                inline=False
            )

        if state.queue:
            queue_list = []
            for i, item in enumerate(list(state.queue)[:10], 1):
                data = item["data"]
                dur = format_duration(data.get("duration", 0))
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
        embed.add_field(name="🔊 Ses", value=f"%{int(state.volume * 100)}")
        await ctx.send(embed=embed)

    @commands.command(name="tekrar", aliases=["loop"],
                      help="Tekrar modunu açar/kapatır.")
    @commands.guild_only()
    async def loop(self, ctx: commands.Context):
        """Mevcut şarkının tekrar modunu açar/kapatır."""
        state = self.get_state(ctx.guild.id)
        state.loop = not state.loop
        status = "açıldı 🔁" if state.loop else "kapatıldı"
        await ctx.send(embed=success_embed(
            f"Tekrar Modu {status}",
            "Şarkı sürekli tekrarlanacak." if state.loop else
            "Şarkı bir kez çalınacak."
        ), delete_after=10)

    @commands.command(name="ses", aliases=["volume", "vol"],
                      help="Ses seviyesini ayarlar (1-200).")
    @commands.guild_only()
    async def volume(self, ctx: commands.Context, vol: int):
        """
        Ses seviyesini ayarlar.
        Kullanım: !ses 80 (% cinsinden, 1-200 arası)
        """
        state = self.get_state(ctx.guild.id)

        if vol < 1 or vol > 200:
            return await ctx.send(embed=error_embed(
                "Ses seviyesi 1 ile 200 arasında olmalı."
            ))

        state.volume = vol / 100
        if state.current:
            state.current.volume = state.volume

        await ctx.send(embed=success_embed(
            "🔊 Ses Ayarlandı",
            f"Ses seviyesi **%{vol}** olarak ayarlandı."
        ), delete_after=10)

    @commands.command(name="çalıyor", aliases=["nowplaying", "np"],
                      help="Şu an çalan şarkıyı gösterir.")
    @commands.guild_only()
    async def now_playing(self, ctx: commands.Context):
        """Şu an çalan şarkının bilgilerini gösterir."""
        state = self.get_state(ctx.guild.id)
        if not state.current:
            return await ctx.send(embed=info_embed(
                "Şu an bir şey çalmıyor.",
                "`!çal <şarkı>` komutuyla müzik başlatabilirsin."
            ))
        await ctx.send(embed=self._build_now_playing_embed(state))

    @commands.command(name="karıştır", aliases=["shuffle"],
                      help="Kuyruğu rastgele karıştırır.")
    @commands.guild_only()
    async def shuffle(self, ctx: commands.Context):
        """Şarkı kuyruğunu karıştırır."""
        import random
        state = self.get_state(ctx.guild.id)
        if len(state.queue) < 2:
            return await ctx.send(embed=error_embed(
                "Karıştırmak için en az 2 şarkı gerekli."
            ))
        queue_list = list(state.queue)
        random.shuffle(queue_list)
        state.queue = deque(queue_list)
        await ctx.send(embed=success_embed(
            "🔀 Kuyruk Karıştırıldı",
            f"{len(state.queue)} şarkı rastgele sıralandı."
        ), delete_after=10)

    @commands.command(name="temizlekuyruk", aliases=["clearqueue", "cq"],
                      help="Müzik kuyruğunu temizler.")
    @commands.guild_only()
    async def clear_queue(self, ctx: commands.Context):
        """Kuyruktaki tüm şarkıları siler (mevcut şarkı devam eder)."""
        state = self.get_state(ctx.guild.id)
        count = len(state.queue)
        state.queue.clear()
        await ctx.send(embed=success_embed(
            "Kuyruk Temizlendi",
            f"{count} şarkı kuyruğu silindi."
        ), delete_after=10)

    @commands.command(name="atsıkuyruk", aliases=["remove"],
                      help="Kuyruktaki belirli bir şarkıyı siler.")
    @commands.guild_only()
    async def remove_from_queue(self, ctx: commands.Context, index: int):
        """
        Kuyruktan belirli indexli şarkıyı siler.
        Kullanım: !atsıkuyruk 3 (3. şarkıyı sil)
        """
        state = self.get_state(ctx.guild.id)
        if index < 1 or index > len(state.queue):
            return await ctx.send(embed=error_embed(
                f"Geçerli bir index gir (1-{len(state.queue)})."
            ))

        queue_list = list(state.queue)
        removed = queue_list.pop(index - 1)
        state.queue = deque(queue_list)
        await ctx.send(embed=success_embed(
            "Şarkı Silindi",
            f"**{removed['data'].get('title', 'Bilinmiyor')}** kuyruğdan silindi."
        ), delete_after=10)

    @commands.command(name="bağlan", aliases=["join"],
                      help="Ses kanalına bağlanır.")
    @commands.guild_only()
    async def join(self, ctx: commands.Context):
        """Kullanıcının bulunduğu ses kanalına bağlanır."""
        if not ctx.author.voice:
            return await ctx.send(embed=error_embed(
                "Ses kanalında değilsin!"
            ))
        state = self.get_state(ctx.guild.id)
        channel = ctx.author.voice.channel
        if state.voice_client and state.voice_client.is_connected():
            await state.voice_client.move_to(channel)
        else:
            state.voice_client = await channel.connect()
        await ctx.send(embed=success_embed(
            "Bağlandı",
            f"**{channel.name}** kanalına bağlandım."
        ), delete_after=10)

    @commands.command(name="ayrıl", aliases=["leave", "disconnect", "dc"],
                      help="Ses kanalından ayrılır.")
    @commands.guild_only()
    async def leave(self, ctx: commands.Context):
        """Ses kanalından ayrılır."""
        state = self.get_state(ctx.guild.id)
        await state.cleanup()
        if ctx.guild.id in self.states:
            del self.states[ctx.guild.id]
        await ctx.send(embed=success_embed("👋 Ayrıldım",
                                           "Görüşürüz!"), delete_after=5)


async def setup(bot: commands.Bot):
    """Cog'u bota yükle."""
    await bot.add_cog(Music(bot))
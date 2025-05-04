import discord
from discord.ext import commands
import asyncio
import yt_dlp
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do yt-dlp e ffmpeg
ytdl_format_options = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": False,
    "noplaylist": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "cookiefile": "./cookies.txt"
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []                # fila de (url, title)
        self.is_playing = False
        self.current = None            # título da música atual
        self.volume = 0.5              # volume padrão (50%)
        self.cache = {}                # cache: query -> (url, title, timestamp)
        self.cache_timeout = 10 * 60   # 10 minutos
        self.voice_client = None

    async def search_yt(self, query: str):
        now = datetime.datetime.utcnow()
        if query in self.cache:
            url, title, ts = self.cache[query]
            if (now - ts).total_seconds() < self.cache_timeout:
                return url, title
            else:
                del self.cache[query]

        try:
            data = ytdl.extract_info(f"ytsearch:{query}", download=False)
            entry = data["entries"][0]
            url = entry["url"]
            title = entry["title"]
            self.cache[query] = (url, title, now)
            return url, title
        except Exception:
            return None, None

    async def play_music(self, ctx):
        if not self.queue:
            self.is_playing = False
            # desconecta após 10s sem tocar nada
            await asyncio.sleep(10)
            if not self.is_playing and self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
            return

        self.is_playing = True
        url, title = self.queue.pop(0)
        self.current = title

        # envia mensagem de now playing
        await ctx.send(f"🎶 Agora tocando: **{title}**")

        # prepara e toca
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url, **ffmpeg_options),
            volume=self.volume
        )
        self.voice_client.play(
            source,
            after=lambda e, _ctx=ctx: asyncio.run_coroutine_threadsafe(self.play_next(_ctx), self.bot.loop)
        )

    async def play_next(self, ctx):
        await self.play_music(ctx)

    @commands.command(name="play")
    async def cmd_play(self, ctx, *, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Você precisa estar em um canal de voz!")

        # conecta/move o bot
        channel = ctx.author.voice.channel
        if not self.voice_client or not self.voice_client.is_connected():
            self.voice_client = await channel.connect()
        elif self.voice_client.channel != channel:
            await self.voice_client.move_to(channel)

        # busca no YouTube
        url, title = await self.search_yt(query)
        if not url:
            return await ctx.send("❌ Música não encontrada.")

        # adiciona à fila e inicia se estiver livre
        self.queue.append((url, title))
        await ctx.send(f"✅ Adicionado à fila: **{title}**")
        if not self.is_playing:
            await self.play_music(ctx)

    @commands.command(name="skip")
    async def cmd_skip(self, ctx):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            await ctx.send("⏭️ Música pulada!")
        else:
            await ctx.send("⚠️ Não há música tocando.")

    @commands.command(name="stop")
    async def cmd_stop(self, ctx):
        self.queue.clear()
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
        self.is_playing = False
        await ctx.send("🛑 Parado e desconectado.")

    @commands.command(name="pause")
    async def cmd_pause(self, ctx):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            await ctx.send("⏸️ Pausado.")
        else:
            await ctx.send("⚠️ Nada para pausar.")

    @commands.command(name="resume")
    async def cmd_resume(self, ctx):
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            await ctx.send("▶️ Retomado.")
        else:
            await ctx.send("⚠️ Nada para retomar.")

    @commands.command(name="queue")
    async def cmd_queue(self, ctx):
        if not self.queue:
            return await ctx.send("📭 Fila vazia.")
        msg = "🎵 **Fila de reprodução:**\n"
        for i, (_url, title) in enumerate(self.queue, 1):
            msg += f"{i}. {title}\n"
        await ctx.send(msg)

    @commands.command(name="nowplaying")
    async def cmd_nowplaying(self, ctx):
        if self.current:
            await ctx.send(f"▶️ Tocando agora: **{self.current}**")
        else:
            await ctx.send("❌ Nenhuma música tocando.")

    @commands.command(name="volume")
    async def cmd_volume(self, ctx, vol: int):
        if not self.voice_client or not self.voice_client.source:
            return await ctx.send("❌ Nada tocando no momento.")
        if vol < 1 or vol > 100:
            return await ctx.send("⚠️ Defina entre 1 e 100.")
        self.volume = vol / 100
        self.voice_client.source.volume = self.volume
        await ctx.send(f"🔊 Volume ajustado para {vol}%")

async def setup(bot):
    await bot.add_cog(Music(bot))

import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

# Setup Spotify (Client Credentials Flow)
sp = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

# Opções do yt-dlp
ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'source_address': '0.0.0.0',
}
ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
ytdl = youtube_dl.YoutubeDL(ytdl_opts)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}   # guild_id -> [(title, stream_url)]
        self.current = {}  # guild_id -> title

    async def ensure_voice(self, ctx):
        if not (ctx.author.voice and ctx.author.voice.channel):
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return False
        vc = ctx.voice_client
        channel = ctx.author.voice.channel
        if not vc:
            await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)
        return True

    def _extract_info(self, query: str):
        """Tenta extrair info do link; em falha retorna None."""
        try:
            info = ytdl.extract_info(query, download=False)
            if isinstance(info, dict) and info.get('entries'):
                info = info['entries'][0]
            return info
        except Exception:
            return None

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Adiciona à fila ou toca imediatamente."""
        if not await self.ensure_voice(ctx):
            return

        gid = ctx.guild.id
        self.queues.setdefault(gid, [])

        # Converte link Spotify em termos de busca
        if "open.spotify.com/track" in query:
            try:
                track = sp.track(query)
                query = f"{track['name']} {track['artists'][0]['name']}"
                await ctx.send(f"🔄 Convertendo Spotify → YouTube: **{query}**")
            except Exception:
                return await ctx.send("⚠️ Não consegui buscar essa faixa no Spotify.")

        info = None
        # Tenta link direto
        if query.startswith("http"):
            info = self._extract_info(query)

        # Fallback para busca de 1 resultado no YouTube
        if not info:
            try:
                search = f"ytsearch1:{query}"
                data = ytdl.extract_info(search, download=False)
                entries = data.get('entries') or []
                info = entries[0] if entries else None
            except Exception:
                info = None

        if not info:
            return await ctx.send("❌ Não encontrei essa música no YouTube.")

        title = info.get('title', 'Unknown Title')
        stream_url = info.get('url')  # link de áudio processado

        vc = ctx.voice_client
        queue = self.queues[gid]

        # Se já estiver tocando, adiciona à fila
        if vc.is_playing() or vc.is_paused():
            queue.append((title, stream_url))
            return await ctx.send(f"✅ **{title}** adicionada à fila (posição {len(queue)}).")

        # Caso contrário, insere e toca
        queue.insert(0, (title, stream_url))
        await self._play_next(ctx)

    async def _play_next(self, ctx):
        gid = ctx.guild.id
        q = self.queues.get(gid)
        if not q:
            await ctx.voice_client.disconnect()
            self.current.pop(gid, None)
            return

        title, stream_url = q.pop(0)
        self.current[gid] = title

        try:
            source = await discord.FFmpegOpusAudio.from_probe(stream_url, **ffmpeg_opts)
            ctx.voice_client.play(
                source,
                after=lambda e: self.bot.loop.create_task(self._play_next(ctx))
            )
            await ctx.send(f"🎶 Tocando agora: **{title}**")
        except Exception as e:
            await ctx.send(f"❌ Erro ao tocar **{title}**. Pulando para a próxima.\n`{e}`")
            await self._play_next(ctx)

    @commands.command()
    async def skip(self, ctx):
        vc = ctx.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await ctx.send("⏭️ Música pulada.")
        else:
            await ctx.send("❌ Nada para pular.")

    @commands.command()
    async def stop(self, ctx):
        vc = ctx.voice_client
        if vc:
            self.queues.pop(ctx.guild.id, None)
            self.current.pop(ctx.guild.id, None)
            await vc.disconnect()
            await ctx.send("🛑 Parado e desconectado.")
        else:
            await ctx.send("❌ Não estou em um canal de voz.")

    @commands.command()
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Pausado.")
        else:
            await ctx.send("❌ Nada para pausar.")

    @commands.command()
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Retomado.")
        else:
            await ctx.send("❌ Nenhuma música pausada.")

    @commands.command(name="queue")
    async def show_queue(self, ctx):
        q = self.queues.get(ctx.guild.id, [])
        if not q:
            return await ctx.send("📭 Fila vazia.")
        embed = discord.Embed(title="📜 Fila", color=discord.Color.blurple())
        for i, (t, _) in enumerate(q, 1):
            embed.add_field(name=f"{i}.", value=t, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying")
    async def now_playing(self, ctx):
        title = self.current.get(ctx.guild.id)
        if title:
            await ctx.send(f"▶️ Tocando: **{title}**")
        else:
            await ctx.send("❌ Nenhuma música tocando.")
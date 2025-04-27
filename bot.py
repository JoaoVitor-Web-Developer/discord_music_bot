import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from cogs.music import Music

load_dotenv()

intents = discord.Intents.all()

# Criação do bot
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

@bot.event
async def on_ready():
    print(f"⚡ Bot conectado como {bot.user} (ID: {bot.user.id})")
    await bot.add_cog(Music(bot))


# View com botões de página
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.page = 0
        self.embeds = self.generate_embeds()

    def generate_embeds(self):
        embed1 = discord.Embed(
            title="🎵 Comandos de Música - Página 1",
            description="Comandos para curtir seu som!",
            color=discord.Color.purple()
        )
        embed1.add_field(name="▶️ !play `<nome ou link>`", value="Toca uma música ou adiciona à fila.", inline=False)
        embed1.add_field(name="⏸️ !pause", value="Pausa a música atual.", inline=True)
        embed1.add_field(name="▶️ !resume", value="Retoma a música pausada.", inline=True)
        embed1.add_field(name="⏭️ !next", value="Pula para a próxima música.", inline=True)
        embed1.add_field(name="🛑 !stop", value="Para a música e desconecta o bot.", inline=True)
        embed1.add_field(name="📜 !queue", value="Mostra a fila de músicas.", inline=True)
        embed1.add_field(name="🎶 !nowplaying", value="Mostra a música que está tocando agora.", inline=True)
        embed1.add_field(name="🔊 !volume `<1-100>`", value="Ajusta o volume da música atual.", inline=True)
        embed1.set_thumbnail(url="https://cdn-icons-png.flaticon.com/128/2871/2871323.png")
        embed1.set_footer(text="Página 1/2 — Feito com ❤️ por João Vitor")

        embed2 = discord.Embed(
            title="ℹ️ Informações Gerais - Página 2",
            description="Dicas e ajuda extra sobre o uso do bot.",
            color=discord.Color.blue()
        )
        embed2.add_field(name="📌 Como usar", value="Entre em um canal de voz e use `!play <nome>` para começar!",
                         inline=False)
        # embed2.add_field(name="🎧 Spotify", value="Links do Spotify são automaticamente convertidos!", inline=False)
        embed2.add_field(name="🎧 Spotify", value="Links do spotify ainda não estão funcionando!!", inline=False)
        support_id = os.getenv("SUPPORT_ID")
        embed2.add_field(
            name="📥 Suporte",
            value=f"Chame o <@{support_id}> se precisar de ajuda 😉",
            inline=False
        )
        embed2.set_footer(text="Página 2/2 — Feito com ❤️ por João Vitor")
        embed2.set_thumbnail(url="https://cdn-icons-png.flaticon.com/128/2871/2871323.png")

        return [embed1, embed2]

    @discord.ui.button(label="⏮ Página anterior", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="⏭ Próxima página", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

# Comando de help com botões
@bot.command(name="help")
async def help_command(ctx):
    view = HelpView()
    await ctx.send(embed=view.embeds[0], view=view)

# Rodando o bot
bot.run(os.getenv("DISCORD_TOKEN"))

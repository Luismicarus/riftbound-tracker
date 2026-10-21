"""Comandos para registrar, consultar y borrar partidas."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..db import RESULTADOS
from .comun import COLOR_BOT, COLOR_RESULTADO, EMOJI_RESULTADO, autocompletar_leyenda

if TYPE_CHECKING:
    from ..main import RiftboundBot


class Partidas(commands.Cog):
    def __init__(self, bot: RiftboundBot) -> None:
        self.bot = bot

    @app_commands.command(name="partida", description="Registra una partida de testeo")
    @app_commands.guild_only()
    @app_commands.describe(
        leyenda="Tu leyenda",
        rival="La leyenda de tu rival",
        resultado="Cómo acabó la partida",
        primero="¿Empezabas tú?",
        notas="Algo que quieras recordar: mulligan, carta clave, error...",
    )
    @app_commands.choices(
        resultado=[app_commands.Choice(name=texto, value=clave) for clave, texto in RESULTADOS.items()]
    )
    @app_commands.autocomplete(leyenda=autocompletar_leyenda, rival=autocompletar_leyenda)
    async def partida(
        self,
        interaction: discord.Interaction,
        leyenda: str,
        rival: str,
        resultado: app_commands.Choice[str],
        primero: bool,
        notas: app_commands.Range[str, 1, 300] | None = None,
    ) -> None:
        # El autocompletado solo sugiere: el usuario puede escribir cualquier cosa.
        mia = self.bot.legends.resolver(leyenda)
        suya = self.bot.legends.resolver(rival)
        desconocidas = [texto for texto, valor in ((leyenda, mia), (rival, suya)) if valor is None]
        if mia is None or suya is None:
            await interaction.response.send_message(
                "No reconozco " + " ni ".join(f"**{t}**" for t in desconocidas)
                + ". Elige una de las sugerencias o añádela a `data/legends.yaml`.",
                ephemeral=True,
            )
            return

        partida_id = self.bot.db.registrar(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            user_name=interaction.user.display_name,
            leyenda=mia,
            rival=suya,
            resultado=resultado.value,
            primero=primero,
            notas=notas,
        )

        embed = discord.Embed(
            title=f"{EMOJI_RESULTADO[resultado.value]} {mia} vs {suya}",
            description=f"**{resultado.name}** {'empezando' if primero else 'yendo segundo'}",
            color=COLOR_RESULTADO[resultado.value],
        )
        if notas:
            embed.add_field(name="Notas", value=notas, inline=False)
        embed.set_footer(text=f"Partida #{partida_id} · {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="historial", description="Últimas partidas registradas")
    @app_commands.guild_only()
    @app_commands.describe(jugador="De quién (por defecto, tú)")
    async def historial(
        self, interaction: discord.Interaction, jugador: discord.Member | None = None
    ) -> None:
        objetivo = jugador or interaction.user
        partidas = self.bot.db.historial(guild_id=interaction.guild_id, user_id=objetivo.id)
        if not partidas:
            await interaction.response.send_message(
                f"**{objetivo.display_name}** aún no tiene partidas registradas.", ephemeral=True
            )
            return

        lineas = []
        for p in partidas:
            linea = f"`#{p.id}` {EMOJI_RESULTADO[p.resultado]} {p.leyenda} vs {p.rival} · {'1º' if p.primero else '2º'}"
            if p.notas:
                linea += f" · _{p.notas}_"
            lineas.append(linea)

        embed = discord.Embed(
            title=f"Historial de {objetivo.display_name}",
            description="\n".join(lineas),
            color=COLOR_BOT,
        )
        embed.set_footer(text="¿Te has equivocado? /borrar con el número de la partida")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="borrar", description="Borra una partida tuya (por si te equivocaste)")
    @app_commands.guild_only()
    @app_commands.describe(numero="Número de la partida: sale en el mensaje y en /historial")
    async def borrar(self, interaction: discord.Interaction, numero: app_commands.Range[int, 1]) -> None:
        borrada = self.bot.db.borrar(
            guild_id=interaction.guild_id, partida_id=numero, user_id=interaction.user.id
        )
        mensaje = (
            f"Partida #{numero} borrada."
            if borrada
            else f"No encuentro la partida #{numero} entre las tuyas."
        )
        await interaction.response.send_message(mensaje, ephemeral=True)


async def setup(bot: RiftboundBot) -> None:
    await bot.add_cog(Partidas(bot))

"""Comandos de estadísticas: stats por jugador, matchups y ranking del grupo."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..db import Balance
from .comun import COLOR_BOT, autocompletar_leyenda, pct, recortar, tabla

if TYPE_CHECKING:
    from ..main import RiftboundBot

MAX_FILAS = 20


def _filas_balance(datos: list[tuple[str, Balance]], ancho_nombre: int = 16) -> list[list[str]]:
    return [
        [recortar(nombre, ancho_nombre), str(b.partidas), b.marcador, pct(b.winrate)]
        for nombre, b in datos[:MAX_FILAS]
    ]


def _resumen(b: Balance) -> str:
    return f"**{pct(b.winrate)}** · {b.marcador} en {b.partidas} partida{'s' if b.partidas != 1 else ''}"


class Estadisticas(commands.Cog):
    def __init__(self, bot: RiftboundBot) -> None:
        self.bot = bot

    async def _resolver_o_avisar(self, interaction: discord.Interaction, texto: str) -> str | None:
        nombre = self.bot.legends.resolver(texto)
        if nombre is None:
            await interaction.response.send_message(
                f"No reconozco **{texto}**. Elige una de las sugerencias.", ephemeral=True
            )
        return nombre

    @app_commands.command(name="stats", description="Estadísticas de un jugador")
    @app_commands.guild_only()
    @app_commands.describe(
        jugador="De quién (por defecto, tú)",
        leyenda="Ver solo una leyenda, con sus matchups",
    )
    @app_commands.autocomplete(leyenda=autocompletar_leyenda)
    async def stats(
        self,
        interaction: discord.Interaction,
        jugador: discord.Member | None = None,
        leyenda: str | None = None,
    ) -> None:
        objetivo = jugador or interaction.user
        guild_id = interaction.guild_id

        nombre_leyenda = None
        if leyenda:
            nombre_leyenda = await self._resolver_o_avisar(interaction, leyenda)
            if nombre_leyenda is None:
                return

        total = self.bot.db.balance(guild_id=guild_id, user_id=objetivo.id, leyenda=nombre_leyenda)
        if total.partidas == 0:
            con = f" con {nombre_leyenda}" if nombre_leyenda else ""
            await interaction.response.send_message(
                f"**{objetivo.display_name}** no tiene partidas registradas{con}.", ephemeral=True
            )
            return

        turno = self.bot.db.por_turno(guild_id=guild_id, user_id=objetivo.id, leyenda=nombre_leyenda)

        if nombre_leyenda:
            titulo = f"{objetivo.display_name} con {nombre_leyenda}"
            datos = self.bot.db.matchups(guild_id=guild_id, leyenda=nombre_leyenda, user_id=objetivo.id)
            cabeceras = ["Rival", "P", "V-D-E", "WR"]
        else:
            titulo = f"Stats de {objetivo.display_name}"
            datos = self.bot.db.por_leyenda(guild_id=guild_id, user_id=objetivo.id)
            cabeceras = ["Leyenda", "P", "V-D-E", "WR"]

        embed = discord.Embed(
            title=titulo,
            description=tabla(cabeceras, _filas_balance(datos), alinear_derecha={1, 2, 3}),
            color=COLOR_BOT,
        )
        embed.add_field(name="Total", value=_resumen(total), inline=False)
        embed.add_field(name="Empezando", value=_resumen(turno[True]), inline=True)
        embed.add_field(name="Yendo segundo", value=_resumen(turno[False]), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="matchups", description="Cómo le va a una leyenda contra cada rival (todo el grupo)")
    @app_commands.guild_only()
    @app_commands.describe(leyenda="La leyenda que quieres analizar")
    @app_commands.autocomplete(leyenda=autocompletar_leyenda)
    async def matchups(self, interaction: discord.Interaction, leyenda: str) -> None:
        nombre = await self._resolver_o_avisar(interaction, leyenda)
        if nombre is None:
            return

        datos = self.bot.db.matchups(guild_id=interaction.guild_id, leyenda=nombre)
        if not datos:
            await interaction.response.send_message(
                f"Nadie ha registrado partidas con **{nombre}** todavía.", ephemeral=True
            )
            return

        total = self.bot.db.balance(guild_id=interaction.guild_id, leyenda=nombre)
        embed = discord.Embed(
            title=f"Matchups de {nombre}",
            description=tabla(["Rival", "P", "V-D-E", "WR"], _filas_balance(datos), alinear_derecha={1, 2, 3}),
            color=COLOR_BOT,
        )
        embed.add_field(name="Total del grupo", value=_resumen(total), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ranking", description="Clasificación del grupo por winrate")
    @app_commands.guild_only()
    async def ranking(self, interaction: discord.Interaction) -> None:
        minimo = self.bot.config.min_partidas_ranking
        datos = self.bot.db.ranking(guild_id=interaction.guild_id, min_partidas=minimo)
        if not datos:
            await interaction.response.send_message(
                f"Aún nadie llega a {minimo} partidas. ¡A testear!", ephemeral=True
            )
            return

        filas = [[str(i), *fila] for i, fila in enumerate(_filas_balance(datos), start=1)]
        embed = discord.Embed(
            title="🏆 Ranking del grupo",
            description=tabla(["#", "Jugador", "P", "V-D-E", "WR"], filas, alinear_derecha={0, 2, 3, 4}),
            color=COLOR_BOT,
        )
        embed.set_footer(text=f"Mínimo {minimo} partidas para aparecer")
        await interaction.response.send_message(embed=embed)


async def setup(bot: RiftboundBot) -> None:
    await bot.add_cog(Estadisticas(bot))

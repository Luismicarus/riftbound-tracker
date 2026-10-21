"""Utilidades compartidas por los comandos: autocompletado y formato de tablas."""

from __future__ import annotations

import discord
from discord import app_commands

EMOJI_RESULTADO = {"V": "🟢", "D": "🔴", "E": "⚪"}
COLOR_RESULTADO = {
    "V": discord.Color.green(),
    "D": discord.Color.red(),
    "E": discord.Color.light_grey(),
}
COLOR_BOT = discord.Color.from_rgb(201, 162, 74)


async def autocompletar_leyenda(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    legends = interaction.client.legends  # type: ignore[attr-defined]
    return [app_commands.Choice(name=n, value=n) for n in legends.sugerir(current)]


def pct(valor: float) -> str:
    return f"{valor:.0%}"


def recortar(texto: str, largo: int) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def tabla(cabeceras: list[str], filas: list[list[str]], alinear_derecha: set[int] | None = None) -> str:
    """Tabla en texto monoespaciado dentro de un bloque de código de Discord."""
    alinear_derecha = alinear_derecha or set()
    anchos = [max(len(str(c)) for c in col) for col in zip(cabeceras, *filas)]

    def linea(celdas: list[str]) -> str:
        partes = [
            str(c).rjust(a) if i in alinear_derecha else str(c).ljust(a)
            for i, (c, a) in enumerate(zip(celdas, anchos))
        ]
        return "  ".join(partes).rstrip()

    separador = "  ".join("─" * a for a in anchos)
    return "```\n" + "\n".join([linea(cabeceras), separador, *map(linea, filas)]) + "\n```"

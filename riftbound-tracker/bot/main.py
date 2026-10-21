"""Punto de entrada: crea el bot, carga los comandos y lo conecta a Discord."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .config import Config, load_config
from .db import Database
from .legends import Legends

log = logging.getLogger("riftbound")

EXTENSIONES = ("bot.cogs.partidas", "bot.cogs.estadisticas")


class RiftboundBot(commands.Bot):
    def __init__(self, config: Config) -> None:
        # Solo usamos comandos de barra: no hace falta ningún intent privilegiado.
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.config = config
        self.db = Database(config.db_path)
        self.legends = Legends.from_yaml(config.legends_path)

    async def setup_hook(self) -> None:
        for extension in EXTENSIONES:
            await self.load_extension(extension)
        self.tree.error(self._on_tree_error)

        if self.config.guild_id:
            # En un servidor concreto los comandos aparecen al instante.
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            sincronizados = await self.tree.sync(guild=guild)
            log.info("%d comandos sincronizados en el servidor %s", len(sincronizados), guild.id)
        else:
            # Globales: pueden tardar un rato en aparecer en Discord.
            sincronizados = await self.tree.sync()
            log.info("%d comandos sincronizados globalmente", len(sincronizados))

    async def on_ready(self) -> None:
        log.info("Conectado como %s · %d leyendas cargadas", self.user, len(self.legends))

    async def close(self) -> None:
        await super().close()
        self.db.close()

    async def _on_tree_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.NoPrivateMessage):
            mensaje = "Este comando solo funciona dentro de un servidor."
        else:
            comando = interaction.command.name if interaction.command else "?"
            log.error("Error en /%s", comando, exc_info=error)
            mensaje = "Algo ha fallado 😵 Mira los logs del bot."

        if interaction.response.is_done():
            await interaction.followup.send(mensaje, ephemeral=True)
        else:
            await interaction.response.send_message(mensaje, ephemeral=True)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    config = load_config()
    bot = RiftboundBot(config)
    bot.run(config.token, log_handler=None)

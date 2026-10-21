"""Comprueba que el bot arranca y registra sus comandos sin conectarse a Discord."""

import asyncio
from types import SimpleNamespace

import pytest

from bot.config import ROOT, Config
from bot.main import RiftboundBot

COMANDOS = {"partida", "historial", "borrar", "stats", "matchups", "ranking"}


@pytest.fixture
def bot(tmp_path):
    config = Config(
        token="no-se-usa",
        guild_id=None,
        db_path=tmp_path / "test.db",
        legends_path=ROOT / "data" / "legends.yaml",
        min_partidas_ranking=1,
    )

    async def crear():
        b = RiftboundBot(config)
        for extension in ("bot.cogs.partidas", "bot.cogs.estadisticas"):
            await b.load_extension(extension)
        return b

    b = asyncio.run(crear())
    yield b
    b.db.close()


def test_se_registran_todos_los_comandos(bot):
    assert {c.name for c in bot.tree.get_commands()} == COMANDOS


def test_esquemas_validos_para_discord(bot):
    for comando in bot.tree.get_commands():
        datos = comando.to_dict(bot.tree)
        assert 1 <= len(datos["description"]) <= 100
        for opcion in datos.get("options", []):
            assert 1 <= len(opcion["description"]) <= 100, opcion["name"]


def test_partida_tiene_autocompletado_y_opciones(bot):
    datos = bot.tree.get_command("partida").to_dict(bot.tree)
    opciones = {o["name"]: o for o in datos["options"]}
    assert opciones["leyenda"]["autocomplete"] is True
    assert opciones["rival"]["autocomplete"] is True
    assert [c["value"] for c in opciones["resultado"]["choices"]] == ["V", "D", "E"]
    assert opciones["notas"]["required"] is False


def test_autocompletado_sugiere_leyendas(bot):
    from bot.cogs.comun import autocompletar_leyenda

    interaccion = SimpleNamespace(client=bot)
    sugerencias = asyncio.run(autocompletar_leyenda(interaccion, "aka"))
    assert [s.value for s in sugerencias] == ["Akali"]

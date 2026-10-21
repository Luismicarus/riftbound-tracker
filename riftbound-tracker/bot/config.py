"""Configuración del bot, leída de variables de entorno o del fichero .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    token: str
    guild_id: int | None
    db_path: Path
    legends_path: Path
    min_partidas_ranking: int


def load_config() -> Config:
    load_dotenv(ROOT / ".env")

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Falta DISCORD_TOKEN. Copia .env.example a .env y pon el token de tu bot."
        )

    guild = os.getenv("GUILD_ID", "").strip()
    if guild and not guild.isdigit():
        raise SystemExit("GUILD_ID tiene que ser un número (el ID de vuestro servidor).")

    return Config(
        token=token,
        guild_id=int(guild) if guild else None,
        db_path=Path(os.getenv("DB_PATH") or ROOT / "data" / "riftbound.db"),
        legends_path=Path(os.getenv("LEGENDS_PATH") or ROOT / "data" / "legends.yaml"),
        min_partidas_ranking=int(os.getenv("MIN_PARTIDAS_RANKING") or 5),
    )

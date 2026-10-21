"""Capa de datos: SQLite, sin dependencias externas.

Todas las consultas filtran por guild_id, así el mismo bot puede estar en
varios servidores sin mezclar estadísticas.

Cada jugador registra sus propias partidas desde su punto de vista: si Ana
gana con Jinx a Luis con Viktor, Ana apunta "Jinx vs Viktor, victoria" y Luis
"Viktor vs Jinx, derrota".
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

RESULTADOS = {"V": "Victoria", "D": "Derrota", "E": "Empate"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS partidas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    user_name  TEXT    NOT NULL,
    leyenda    TEXT    NOT NULL,
    rival      TEXT    NOT NULL,
    resultado  TEXT    NOT NULL CHECK (resultado IN ('V', 'D', 'E')),
    primero    INTEGER NOT NULL CHECK (primero IN (0, 1)),
    notas      TEXT,
    creado     TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_partidas_jugador ON partidas (guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_partidas_matchup ON partidas (guild_id, leyenda, rival);
"""

# Agregado que usan casi todas las consultas de estadísticas.
_AGREGADO = """
    COUNT(*)                          AS n,
    COALESCE(SUM(resultado = 'V'), 0) AS v,
    COALESCE(SUM(resultado = 'D'), 0) AS d,
    COALESCE(SUM(resultado = 'E'), 0) AS e
"""


@dataclass(frozen=True)
class Balance:
    """Victorias, derrotas y empates de un conjunto de partidas."""

    partidas: int = 0
    victorias: int = 0
    derrotas: int = 0
    empates: int = 0

    @property
    def winrate(self) -> float:
        return self.victorias / self.partidas if self.partidas else 0.0

    @property
    def marcador(self) -> str:
        """Formato V-D-E, p. ej. 7-3-1."""
        return f"{self.victorias}-{self.derrotas}-{self.empates}"

    @classmethod
    def desde_fila(cls, fila: sqlite3.Row) -> Balance:
        return cls(fila["n"], fila["v"], fila["d"], fila["e"])


@dataclass(frozen=True)
class Partida:
    id: int
    user_id: int
    user_name: str
    leyenda: str
    rival: str
    resultado: str
    primero: bool
    notas: str | None
    creado: str

    @property
    def resultado_texto(self) -> str:
        return RESULTADOS[self.resultado]


class Database:
    def __init__(self, path: Path | str = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ escritura

    def registrar(
        self,
        *,
        guild_id: int,
        user_id: int,
        user_name: str,
        leyenda: str,
        rival: str,
        resultado: str,
        primero: bool,
        notas: str | None = None,
    ) -> int:
        """Guarda una partida y devuelve su número."""
        if resultado not in RESULTADOS:
            raise ValueError(f"Resultado no válido: {resultado!r}")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO partidas
                    (guild_id, user_id, user_name, leyenda, rival, resultado, primero, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (guild_id, user_id, user_name, leyenda, rival, resultado, int(primero), notas),
            )
        return int(cur.lastrowid)

    def borrar(self, *, guild_id: int, partida_id: int, user_id: int) -> bool:
        """Borra una partida, solo si es de ese jugador. Devuelve si se borró."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM partidas WHERE id = ? AND guild_id = ? AND user_id = ?",
                (partida_id, guild_id, user_id),
            )
        return cur.rowcount == 1

    # -------------------------------------------------------------------- lectura

    def historial(self, *, guild_id: int, user_id: int, limite: int = 10) -> list[Partida]:
        filas = self._conn.execute(
            """
            SELECT id, user_id, user_name, leyenda, rival, resultado, primero, notas, creado
            FROM partidas
            WHERE guild_id = ? AND user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (guild_id, user_id, limite),
        ).fetchall()
        return [Partida(**{**dict(f), "primero": bool(f["primero"])}) for f in filas]

    def balance(
        self, *, guild_id: int, user_id: int | None = None, leyenda: str | None = None
    ) -> Balance:
        where, params = _filtros(guild_id, user_id, leyenda)
        fila = self._conn.execute(
            f"SELECT {_AGREGADO} FROM partidas WHERE {where}", params
        ).fetchone()
        return Balance.desde_fila(fila)

    def por_leyenda(self, *, guild_id: int, user_id: int | None = None) -> list[tuple[str, Balance]]:
        """Balance con cada leyenda, de la más jugada a la menos."""
        where, params = _filtros(guild_id, user_id)
        filas = self._conn.execute(
            f"""
            SELECT leyenda, {_AGREGADO}
            FROM partidas WHERE {where}
            GROUP BY leyenda
            ORDER BY n DESC, leyenda
            """,
            params,
        ).fetchall()
        return [(f["leyenda"], Balance.desde_fila(f)) for f in filas]

    def por_turno(
        self, *, guild_id: int, user_id: int | None = None, leyenda: str | None = None
    ) -> dict[bool, Balance]:
        """Balance empezando (True) y yendo segundo (False)."""
        where, params = _filtros(guild_id, user_id, leyenda)
        filas = self._conn.execute(
            f"SELECT primero, {_AGREGADO} FROM partidas WHERE {where} GROUP BY primero",
            params,
        ).fetchall()
        resultado = {True: Balance(), False: Balance()}
        for f in filas:
            resultado[bool(f["primero"])] = Balance.desde_fila(f)
        return resultado

    def matchups(
        self, *, guild_id: int, leyenda: str, user_id: int | None = None
    ) -> list[tuple[str, Balance]]:
        """Balance de una leyenda contra cada rival, del más jugado al menos."""
        where, params = _filtros(guild_id, user_id, leyenda)
        filas = self._conn.execute(
            f"""
            SELECT rival, {_AGREGADO}
            FROM partidas WHERE {where}
            GROUP BY rival
            ORDER BY n DESC, rival
            """,
            params,
        ).fetchall()
        return [(f["rival"], Balance.desde_fila(f)) for f in filas]

    def ranking(self, *, guild_id: int, min_partidas: int = 1) -> list[tuple[str, Balance]]:
        """Jugadores con al menos `min_partidas`, ordenados por winrate."""
        filas = self._conn.execute(
            f"""
            SELECT
                (SELECT p2.user_name FROM partidas p2
                 WHERE p2.guild_id = p.guild_id AND p2.user_id = p.user_id
                 ORDER BY p2.id DESC LIMIT 1) AS nombre,
                {_AGREGADO}
            FROM partidas p
            WHERE guild_id = ?
            GROUP BY user_id
            HAVING COUNT(*) >= ?
            """,
            (guild_id, min_partidas),
        ).fetchall()
        tabla = [(f["nombre"], Balance.desde_fila(f)) for f in filas]
        tabla.sort(key=lambda t: (t[1].winrate, t[1].partidas), reverse=True)
        return tabla


def _filtros(
    guild_id: int, user_id: int | None = None, leyenda: str | None = None
) -> tuple[str, list[object]]:
    condiciones, params = ["guild_id = ?"], [guild_id]
    if user_id is not None:
        condiciones.append("user_id = ?")
        params.append(user_id)
    if leyenda is not None:
        condiciones.append("leyenda = ?")
        params.append(leyenda)
    return " AND ".join(condiciones), params

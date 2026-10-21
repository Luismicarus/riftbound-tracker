"""Lista de leyendas: carga desde YAML, reconoce nombres mal escritos y sugiere
opciones para el autocompletado de Discord."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import yaml

# Discord no deja mostrar más de 25 sugerencias en un autocompletado.
DISCORD_MAX_SUGERENCIAS = 25


def normalizar(texto: str) -> str:
    """Quita tildes, mayúsculas y todo lo que no sea letra o número.

    >>> normalizar("Kai'Sa")
    'kaisa'
    """
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sin_tildes.lower())


class Legends:
    def __init__(self, nombres: list[str]) -> None:
        unicos = {n.strip() for n in nombres if n and n.strip()}
        if not unicos:
            raise ValueError("La lista de leyendas está vacía")
        self.nombres: list[str] = sorted(unicos, key=str.casefold)
        self._por_clave = {normalizar(n): n for n in self.nombres}

    @classmethod
    def from_yaml(cls, path: Path | str) -> Legends:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data.get("leyendas", []))

    def resolver(self, texto: str) -> str | None:
        """Devuelve el nombre oficial de la leyenda, o None si no se reconoce.

        Acepta coincidencia exacta normalizada ("lee sin", "LEESIN") o un
        prefijo que solo encaje con una leyenda ("volib" -> "Volibear").
        """
        clave = normalizar(texto)
        if not clave:
            return None
        if clave in self._por_clave:
            return self._por_clave[clave]
        candidatas = [n for k, n in self._por_clave.items() if k.startswith(clave)]
        return candidatas[0] if len(candidatas) == 1 else None

    def sugerir(self, texto: str, limite: int = DISCORD_MAX_SUGERENCIAS) -> list[str]:
        """Sugerencias para el autocompletado: primero las que empiezan por el
        texto y después las que lo contienen."""
        clave = normalizar(texto)
        if not clave:
            return self.nombres[:limite]
        empiezan = [n for n in self.nombres if normalizar(n).startswith(clave)]
        contienen = [n for n in self.nombres if clave in normalizar(n) and n not in empiezan]
        return (empiezan + contienen)[:limite]

    def __len__(self) -> int:
        return len(self.nombres)

    def __contains__(self, nombre: object) -> bool:
        return isinstance(nombre, str) and normalizar(nombre) in self._por_clave

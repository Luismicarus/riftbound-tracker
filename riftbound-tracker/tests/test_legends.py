import pytest

from bot.config import ROOT
from bot.legends import Legends, normalizar


@pytest.fixture
def legends():
    return Legends(["Jinx", "Kai'Sa", "Lee Sin", "Leona", "Volibear", "Viktor", "Vi"])


def test_normalizar():
    assert normalizar("Kai'Sa") == "kaisa"
    assert normalizar("  Lee   Sin ") == "leesin"
    assert normalizar("Rek'Sái") == "reksai"


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("jinx", "Jinx"),
        ("KAISA", "Kai'Sa"),
        ("lee sin", "Lee Sin"),
        ("volib", "Volibear"),  # prefijo único
        ("vi", "Vi"),  # exacto gana aunque "Viktor" también empiece por "vi"
        ("le", None),  # ambiguo: Lee Sin / Leona
        ("teemo", None),
        ("", None),
    ],
)
def test_resolver(legends, texto, esperado):
    assert legends.resolver(texto) == esperado


def test_sugerir_prioriza_los_que_empiezan(legends):
    assert legends.sugerir("vi") == ["Vi", "Viktor"]
    assert legends.sugerir("on")[0] == "Leona"  # solo la contiene


def test_sugerir_vacio_devuelve_todo_con_limite(legends):
    assert legends.sugerir("", limite=3) == ["Jinx", "Kai'Sa", "Lee Sin"]


def test_lista_vacia_falla():
    with pytest.raises(ValueError):
        Legends([])


def test_yaml_del_repo_es_valido():
    legends = Legends.from_yaml(ROOT / "data" / "legends.yaml")
    assert len(legends) > 0
    assert "Akali" in legends
    # Ningún par de leyendas debe colisionar al normalizar el nombre.
    assert len({normalizar(n) for n in legends.nombres}) == len(legends)

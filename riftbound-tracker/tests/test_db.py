import pytest

from bot.db import Balance, Database

GUILD = 1
ANA, LUIS = 100, 200


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


def apuntar(db, user_id, leyenda, rival, resultado, primero=True, guild=GUILD, nombre=None):
    return db.registrar(
        guild_id=guild,
        user_id=user_id,
        user_name=nombre or f"jugador{user_id}",
        leyenda=leyenda,
        rival=rival,
        resultado=resultado,
        primero=primero,
    )


def test_registrar_devuelve_ids_consecutivos(db):
    assert apuntar(db, ANA, "Jinx", "Viktor", "V") == 1
    assert apuntar(db, ANA, "Jinx", "Viktor", "D") == 2


def test_resultado_invalido(db):
    with pytest.raises(ValueError):
        apuntar(db, ANA, "Jinx", "Viktor", "X")


def test_balance_y_winrate(db):
    for resultado in ["V", "V", "D", "E"]:
        apuntar(db, ANA, "Jinx", "Viktor", resultado)
    b = db.balance(guild_id=GUILD, user_id=ANA)
    assert b == Balance(4, 2, 1, 1)
    assert b.winrate == 0.5
    assert b.marcador == "2-1-1"


def test_balance_vacio(db):
    b = db.balance(guild_id=GUILD, user_id=ANA)
    assert b == Balance()
    assert b.winrate == 0.0


def test_servidores_no_se_mezclan(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V", guild=1)
    apuntar(db, ANA, "Jinx", "Viktor", "D", guild=2)
    assert db.balance(guild_id=1, user_id=ANA).victorias == 1
    assert db.balance(guild_id=2, user_id=ANA).derrotas == 1


def test_por_leyenda_ordena_por_partidas(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V")
    apuntar(db, ANA, "Akali", "Viktor", "V")
    apuntar(db, ANA, "Akali", "Sett", "D")
    datos = db.por_leyenda(guild_id=GUILD, user_id=ANA)
    assert [nombre for nombre, _ in datos] == ["Akali", "Jinx"]
    assert datos[0][1] == Balance(2, 1, 1, 0)


def test_por_turno(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V", primero=True)
    apuntar(db, ANA, "Jinx", "Viktor", "D", primero=False)
    apuntar(db, ANA, "Jinx", "Viktor", "D", primero=False)
    turno = db.por_turno(guild_id=GUILD, user_id=ANA)
    assert turno[True] == Balance(1, 1, 0, 0)
    assert turno[False] == Balance(2, 0, 2, 0)


def test_por_turno_sin_partidas_en_un_lado(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V", primero=True)
    assert db.por_turno(guild_id=GUILD, user_id=ANA)[False] == Balance()


def test_matchups_de_grupo_y_de_jugador(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V")
    apuntar(db, LUIS, "Jinx", "Viktor", "D")
    apuntar(db, LUIS, "Jinx", "Sett", "V")
    apuntar(db, LUIS, "Akali", "Sett", "V")  # otra leyenda: no debe contar

    grupo = dict(db.matchups(guild_id=GUILD, leyenda="Jinx"))
    assert grupo == {"Viktor": Balance(2, 1, 1, 0), "Sett": Balance(1, 1, 0, 0)}

    solo_luis = dict(db.matchups(guild_id=GUILD, leyenda="Jinx", user_id=LUIS))
    assert solo_luis["Viktor"] == Balance(1, 0, 1, 0)


def test_ranking_con_minimo_y_nombre_mas_reciente(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V", nombre="Ana")
    apuntar(db, ANA, "Jinx", "Viktor", "V", nombre="Ana la Mejor")
    apuntar(db, LUIS, "Akali", "Sett", "D", nombre="Luis")
    apuntar(db, LUIS, "Akali", "Sett", "V", nombre="Luis")
    apuntar(db, 300, "Teemo", "Sett", "V")  # solo 1 partida

    ranking = db.ranking(guild_id=GUILD, min_partidas=2)
    assert [nombre for nombre, _ in ranking] == ["Ana la Mejor", "Luis"]


def test_historial_mas_reciente_primero(db):
    apuntar(db, ANA, "Jinx", "Viktor", "V")
    apuntar(db, ANA, "Akali", "Sett", "D", primero=False)
    historial = db.historial(guild_id=GUILD, user_id=ANA)
    assert [p.leyenda for p in historial] == ["Akali", "Jinx"]
    assert historial[0].primero is False
    assert historial[0].resultado_texto == "Derrota"


def test_solo_puedes_borrar_tus_partidas(db):
    partida = apuntar(db, ANA, "Jinx", "Viktor", "V")
    assert db.borrar(guild_id=GUILD, partida_id=partida, user_id=LUIS) is False
    assert db.borrar(guild_id=GUILD, partida_id=partida, user_id=ANA) is True
    assert db.balance(guild_id=GUILD, user_id=ANA).partidas == 0


def test_base_de_datos_en_fichero(tmp_path):
    ruta = tmp_path / "sub" / "riftbound.db"
    db = Database(ruta)
    apuntar(db, ANA, "Jinx", "Viktor", "V")
    db.close()

    reabierta = Database(ruta)
    assert reabierta.balance(guild_id=GUILD).partidas == 1
    reabierta.close()

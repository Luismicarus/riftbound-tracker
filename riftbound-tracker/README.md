# Riftbound Tracker

Bot de Discord para que un grupo de testeo de **Riftbound** registre sus partidas y saque estadísticas: winrate por leyenda, por matchup, empezando o yendo segundo, y un ranking del grupo.

Registrar una partida cuesta diez segundos con autocompletado de leyendas, así que apetece hacerlo después de cada una. Con unas semanas de datos, preparar un torneo deja de ser intuición.

## Comandos

| Comando | Qué hace |
|---|---|
| `/partida leyenda rival resultado primero [notas]` | Registra una partida. Las leyendas se autocompletan. |
| `/stats [jugador] [leyenda]` | Winrate total, por leyenda y empezando/yendo segundo. Con `leyenda`, sus matchups. |
| `/matchups leyenda` | Cómo le va a una leyenda contra cada rival, con las partidas de todo el grupo. |
| `/ranking` | Clasificación del grupo por winrate. |
| `/historial [jugador]` | Últimas 10 partidas, con su número. Solo lo ves tú. |
| `/borrar numero` | Borra una partida tuya si te equivocaste al apuntarla. |

Cada jugador apunta sus propias partidas desde su punto de vista: si Ana gana con Jinx a Luis con Viktor, Ana registra *Jinx vs Viktor, victoria* y Luis *Viktor vs Jinx, derrota*.

## Puesta en marcha

### 1. Crea el bot en Discord

1. Entra en el [Discord Developer Portal](https://discord.com/developers/applications) y pulsa **New Application**. El nombre que pongas es el que verá el grupo.
2. En **Bot**, pulsa **Reset Token** y copia el token. Es la contraseña del bot: no lo pegues en ningún sitio público y, si se filtra, regenéralo.
3. No hace falta activar ningún *Privileged Gateway Intent*: el bot solo usa comandos de barra.

### 2. Invítalo a vuestro servidor

En **OAuth2 → URL Generator** marca los scopes `bot` y `applications.commands`, y los permisos *View Channels*, *Send Messages*, *Embed Links* y *Attach Files*. Abre la URL generada y elige el servidor.

O directamente, cambiando `TU_CLIENT_ID` por el *Application ID* (sale en **General Information**):

```
https://discord.com/oauth2/authorize?client_id=TU_CLIENT_ID&scope=bot+applications.commands&permissions=52224
```

Para añadirlo necesitas el permiso **Gestionar servidor** en ese servidor. Si no lo tienes, pásale el enlace a quien lo tenga.

### 3. Configura

```bash
cp .env.example .env
```

Rellena `DISCORD_TOKEN` y `GUILD_ID`. Para sacar el ID del servidor: Discord → Ajustes → Avanzado → activa **Modo desarrollador**; luego clic derecho en el servidor → **Copiar ID del servidor**.

Con `GUILD_ID` los comandos aparecen al momento. Sin él se registran globalmente y Discord puede tardar un rato en mostrarlos.

### 4. Arranca

**En tu PC**, para desarrollar:

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m bot
```

**En una Raspberry (o cualquier servidor) con Docker**, para tenerlo siempre encendido:

```bash
docker compose up -d --build
docker compose logs -f
```

Con Raspberry Pi OS de 64 bits funciona tal cual. La base de datos queda en `data/riftbound.db`; para hacer copia de seguridad basta con copiar ese fichero.

## Leyendas

La lista está en [`data/legends.yaml`](data/legends.yaml). Cuando salga un set nuevo, añade las leyendas y reinicia el bot; no hay que tocar código. Al escribir dan igual mayúsculas, tildes, espacios y apóstrofos: `kaisa` se reconoce como *Kai'Sa* y `volib` como *Volibear*.

## Estructura

```
bot/
├── main.py              # Arranque, carga de comandos y sincronización con Discord
├── config.py            # Lectura del .env
├── db.py                # SQLite: guardar partidas y calcular estadísticas
├── legends.py           # Lista de leyendas, normalización y autocompletado
└── cogs/
    ├── partidas.py      # /partida, /historial, /borrar
    ├── estadisticas.py  # /stats, /matchups, /ranking
    └── comun.py         # Autocompletado y tablas compartidas
data/legends.yaml        # Leyendas aceptadas
tests/                   # pytest, sin conexión a Discord
```

## Tests

```bash
pytest
```

Prueban la base de datos, el reconocimiento de leyendas y que todos los comandos generan un esquema válido para Discord. Se ejecutan solos en cada push con GitHub Actions.

## Ideas para seguir

- [ ] `/matchups` como imagen: mapa de calor con la matriz de matchups del grupo (matplotlib)
- [ ] `/partida contra:@jugador` que guarde también la partida espejo del rival
- [ ] Variante del mazo, para distinguir dos builds de la misma leyenda
- [ ] Rachas y logros absurdos
- [ ] Modo preparación de torneo: qué matchups faltan por testear esta semana
- [ ] Exportar a CSV
- [ ] Marcador físico con ESP32 que mande el resultado al bot

## Aviso

Proyecto de fans sin relación con Riot Games. Riftbound y League of Legends son marcas de Riot Games, Inc.

## Licencia

[MIT](LICENSE)

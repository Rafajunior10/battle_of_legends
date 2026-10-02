"""Mapas do mundo: tiles, prédios, portas, placas, NPCs, treinadores e passagens. Sem Pygame.

Legenda dos tiles: . grama  , mato alto  = caminho  W água  B ponte  f flores  T árvore  F cerca
                   S placa  R pedra
Interiores:        # parede  _ piso de madeira  t piso de azulejo  c carpete  s escada
Cada mapa é um MapDef; as passagens (Warp) levam de um mapa a outro quando o jogador pisa nelas.
Interiores (como a lanchonete) têm `interior`: o chão e as paredes são desenhados por código
(game/graphics/interiors.py) em vez de vir do tileset.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from game.core.tournament import ROUNDS, TOURNAMENT_PRIZE, XP_MULTIPLIER
from game.data.looks import Look
from game.data.opponents import FOREST_WILD_TYPES, WILD_TYPES
from game.data.props import OBJECTS

SOLID_TILES = frozenset("TWFSR#")
WALL, FLOOR, TILE_FLOOR, CARPET, STAIRS = "#", "_", "t", "c", "s"
TALL_GRASS = ","
WATER = "W"

DIR_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}

START_MAP = "vila"


@dataclass(frozen=True)
class Spot:
    x: int
    y: int
    facing: str
    looks_around: bool = False


@dataclass(frozen=True)
class Placed:
    """Objeto do catálogo (props.OBJECTS) colocado no mapa, com o canto de cima à esquerda em (x, y).
    action: o que a porta faz ("home", "shop", "coliseum", "cafe" ou "locked:texto"), se tiver porta;
            "seat:<direção>" num assento (o personagem senta olhando para lá);
            "use:<coisa>" num objeto que faz algo ao apertar A de frente para ele ("use:tv", "use:swap")."""
    name: str
    x: int
    y: int
    action: str | None = None
    label: str | None = None        # nome na placa da construção ({name} = nome do jogador)

    @property
    def door(self) -> tuple[int, int] | None:
        d = OBJECTS[self.name].door
        return (self.x + d[0], self.y + d[1]) if d else None


@dataclass(frozen=True)
class Warp:
    """Pisar em (x, y) leva para `to_map`, na posição (to_x, to_y), olhando para `facing`."""
    x: int
    y: int
    to_map: str
    to_x: int
    to_y: int
    facing: str


@dataclass(frozen=True)
class Helper:
    """NPC que não duela."""
    spot: Spot
    look: Look                      # aparência (game/data/looks.py)
    sitting: bool = False           # sentado num assento (o spot é o do assento)


@dataclass(frozen=True)
class TrainerTalk:
    greet: str                          # primeiro desafio
    rematch: str
    decline: str                        # quando o jogador diz NÃO
    locked: tuple[str, ...] = ()        # quando ainda não pode desafiar
    first_win: tuple[str, ...] = ()     # fala depois da primeira vitória do jogador


@dataclass(frozen=True)
class MapDef:
    id: str
    name: str
    build: Callable[[], list[list[str]]]
    objects: list[Placed] = field(default_factory=list)                   # casas, árvores grandes, enfeites
    signs: dict[tuple[int, int], str] = field(default_factory=dict)       # texto ({name} = jogador)
    trainers: dict[str, Spot] = field(default_factory=dict)
    helpers: dict[str, Helper] = field(default_factory=dict)
    wild_types: list[tuple] = field(default_factory=lambda: list(WILD_TYPES))   # monstros do mato alto
    warps: list[Warp] = field(default_factory=list)
    wild_bonus: int = 0                  # gosmas daqui ficam este tanto de níveis acima do jogador
    interior: str = ""                   # chão desenhado por código (interiors.py); "" = tileset ao ar livre
    private: bool = False                # cada jogador tem o seu (a casa): os outros online não aparecem

    @property
    def doors(self) -> dict[tuple[int, int], str]:
        """Posição de cada porta -> o que ela faz (calculado a partir dos objetos)."""
        return {obj.door: obj.action for obj in self.objects if obj.action and obj.door}

    def door_of(self, action: str) -> tuple[int, int]:
        return next(pos for pos, act in self.doors.items() if act == action)

    def solid_objects(self) -> set[tuple[int, int]]:
        tiles: set[tuple[int, int]] = set()
        for obj in self.objects:
            tiles |= OBJECTS[obj.name].footprint(obj.x, obj.y)
        return tiles

    @property
    def seats(self) -> dict[tuple[int, int], str]:
        """Tiles do assento -> para onde quem senta fica olhando. É a linha de baixo do objeto (ou a
        `seat_row` do catálogo, como no sofá), em toda a largura dele."""
        seats = {}
        for o in self.objects:
            if o.action and o.action.startswith("seat:"):
                d = OBJECTS[o.name]
                row = d.h - 1 if d.seat_row is None else d.seat_row
                seats.update({(o.x + dx, o.y + row): o.action.split(":", 1)[1] for dx in range(d.w)})
        return seats

    @property
    def uses(self) -> dict[tuple[int, int], str]:
        """Cada tile de um objeto "use:..." -> o que ele faz (ex.: "tv")."""
        tiles = {}
        for o in self.objects:
            if o.action and o.action.startswith("use:"):
                d = OBJECTS[o.name]
                tiles.update({(o.x + dx, o.y + dy): o.action[4:] for dy in range(d.h) for dx in range(d.w)})
        return tiles

    def counter_tiles(self) -> set[tuple[int, int]]:
        """Tiles de balcão: dá para falar com quem está do outro lado."""
        tiles: set[tuple[int, int]] = set()
        for obj in self.objects:
            if OBJECTS[obj.name].counter:
                tiles |= OBJECTS[obj.name].footprint(obj.x, obj.y)
        return tiles

    def warp_at(self, x: int, y: int) -> Warp | None:
        return next((w for w in self.warps if (w.x, w.y) == (x, y)), None)


def _grid(w: int, h: int):
    """Grade cheia de grama com borda de árvores; devolve (grade, fill)."""
    g = [["." for _ in range(w)] for _ in range(h)]

    def fill(tile, x, y, fw, fh):
        for yy in range(y, y + fh):
            for xx in range(x, x + fw):
                g[yy][xx] = tile

    fill("T", 0, 0, w, 2)
    fill("T", 0, h - 2, w, 2)
    fill("T", 0, 0, 2, h)
    fill("T", w - 2, 0, 2, h)
    return g, fill


def _place(g, tile, points):
    for x, y in points:
        g[y][x] = tile


# ============================================================ Vila Carta
# 64 x 44 tiles. Norte: casas, Loja de Cartas, a Lanchonete e a Arena. Centro: praça com poço e varal.
# Leste: rio com ponte, sítio cercado e o campo de mato alto. Oeste/sul: casas e o Coliseu.
VILA_SIGNS = {
    (14, 33): f"COLISEU: torneios de {ROUNDS} rodadas. XP x{XP_MULTIPLIER} e {TOURNAMENT_PRIZE} BETS para o campeão!",
    (39, 37): "CUIDADO! Gosmas selvagens vivem no mato alto.",
    (33, 39): "AO SUL: BOSQUE SUSSURRO. Gosmas mais fortes e duelistas experientes.",
}


def build_vila() -> list[list[str]]:
    g, fill = _grid(64, 44)
    fill(".", 30, 42, 2, 2)              # abertura no sul (saída para o bosque)
    fill("=", 3, 15, 58, 2)              # estrada principal (leste-oeste)
    fill("=", 30, 17, 6, 1)              # liga a estrada à praça
    fill("=", 27, 18, 11, 10)            # praça central
    fill("=", 25, 20, 2, 6)
    fill("=", 38, 21, 2, 4)
    fill("=", 30, 28, 2, 16)             # estrada para o sul
    fill("=", 9, 34, 21, 1)              # caminho do Coliseu
    fill("=", 7, 14, 1, 1)               # porta de casa
    fill("=", 13, 14, 1, 1)              # porta do Rafa
    fill("=", 20, 14, 1, 1)              # porta da loja
    fill("=", 26, 11, 2, 4)              # calçada da lanchonete
    fill("=", 36, 14, 1, 1)              # porta da Arena
    fill(WATER, 44, 0, 3, 31)            # rio descendo do norte...
    fill(WATER, 44, 28, 20, 3)           # ...e virando para o leste
    fill("B", 44, 15, 3, 2)              # ponte da estrada principal
    fill("F", 48, 19, 11, 1)             # sítio cercado (porteira em 52, 19)
    fill("F", 48, 26, 11, 1)
    fill("F", 48, 19, 1, 8)
    fill("F", 58, 19, 1, 8)
    g[19][52] = "."
    fill("F", 40, 32, 21, 1)             # campo de mato alto cercado (porteira em 40, 36)
    fill("F", 40, 40, 21, 1)
    fill("F", 40, 32, 1, 9)
    fill("F", 60, 32, 1, 9)
    g[36][40] = "."
    fill(TALL_GRASS, 41, 33, 19, 7)
    _place(g, "T", ((4, 4), (14, 5), (20, 3), (33, 3), (40, 5), (52, 11), (58, 13), (4, 24), (18, 22),
                    (22, 30), (16, 38), (4, 38), (38, 29), (24, 39), (50, 34), (36, 41), (57, 23), (12, 27),
                    (3, 19), (5, 22), (16, 24), (17, 27), (21, 28), (8, 40), (12, 39), (20, 41), (27, 39),
                    (37, 38), (48, 3), (56, 4), (60, 9), (49, 13), (61, 12), (42, 3), (11, 7), (3, 9),
                    (22, 8), (31, 8), (41, 20), (40, 26), (34, 30), (26, 31)))
    _place(g, "f", ((9, 9), (10, 9), (23, 18), (24, 27), (41, 25), (20, 25), (13, 20), (14, 20), (36, 9),
                    (51, 9), (5, 30), (26, 36), (34, 31), (10, 13), (10, 12), (16, 13), (16, 12),
                    (19, 9), (20, 9), (38, 8), (39, 8), (52, 9), (53, 9), (42, 23), (43, 25), (27, 33),
                    (28, 37), (13, 31), (14, 31), (35, 33), (54, 16), (55, 18)))
    _place(g, "R", ((42, 11), (19, 36), (57, 9)))
    _place(g, "S", VILA_SIGNS)
    return g


VILA = MapDef(
    id="vila",
    name="Vila Carta",
    build=build_vila,
    objects=[
        Placed("house_modern_red", 5, 9, "home", "CASA DE {name}"),
        Placed("house_modern_blue", 11, 9, "locked:Casa do Rafa. A porta está trancada.", "CASA DO RAFA"),
        Placed("house_modern_green", 5, 3, "locked:Casa da Vó Rosa. Ela foi passear no bosque.", "CASA DA VÓ ROSA"),
        Placed("card_shop", 17, 10, "shop", "LOJA DE CARTAS"),
        Placed("snack_bar", 24, 6, "cafe", "LANCHONETE"),
        Placed("arena", 33, 9, "locked:A Arena está fechada. Fale com a Mestra Lia, na porta.", "ARENA"),
        Placed("house_modern_gray", 50, 3, "locked:Prefeitura da Vila Carta. Fechada hoje.", "PREFEITURA"),
        Placed("house_wood", 54, 11, "locked:Depósito do sítio. Trancado.", "DEPÓSITO"),
        Placed("coliseum", 6, 30, "coliseum"),
        Placed("lamp", 11, 17),
        Placed("lamp", 26, 17),
        Placed("lamp", 37, 17),
        Placed("lamp", 43, 17),
        Placed("lamp", 52, 17),
        Placed("lamp", 16, 14),
        Placed("lamp", 31, 14),
        Placed("lamp", 41, 14),
        Placed("well", 32, 22),
        Placed("clothesline", 34, 19),
        Placed("laundry", 37, 19),
        Placed("bench", 28, 20),
        Placed("crates", 28, 25),
        Placed("crate", 30, 26),
        Placed("pot", 36, 26),
        Placed("cart", 21, 19),
        Placed("hay", 50, 21),
        Placed("hay", 51, 21),
        Placed("scarecrow", 55, 23),
        Placed("crate", 56, 21),
        Placed("bush", 49, 24),
        Placed("big_rock", 8, 25),
        Placed("stump", 22, 33),
        Placed("sunflower", 53, 25),
        Placed("sunflower", 54, 25),
        Placed("grove", 15, 1),
        Placed("pines", 36, 2),
        Placed("grove", 2, 26),
        Placed("pines", 18, 39),
        Placed("grove", 57, 1),
        Placed("bush", 5, 17),
        Placed("bush", 9, 17),
        Placed("bush", 20, 17),
        Placed("bush", 23, 17),
        Placed("bush", 39, 17),
        Placed("bush", 41, 17),
        Placed("bush", 48, 17),
        Placed("bush", 57, 17),
        Placed("fern", 24, 24),
        Placed("fern", 40, 22),
        Placed("bench", 32, 26),
        Placed("pot", 37, 24),
        Placed("crate", 26, 21),
        Placed("stump", 45, 24),
        Placed("big_rock", 58, 6),
    ],
    signs=VILA_SIGNS,
    trainers={
        "tico": Spot(14, 17, "down", True),
        "rafa": Spot(32, 13, "down", True),
        "lia": Spot(36, 15, "left"),
        "duda": Spot(42, 22, "right"),
        "bruno": Spot(39, 36, "right", True),
        "sofia": Spot(33, 35, "left", True),
        "zeca": Spot(41, 12, "down"),
    },
    helpers={
        "beto": Helper(Spot(25, 26, "right", True),
                       Look("Masculino", "curto", "grisalho", 0, top="camisa", shirt="marrom",
                            bottom="calça", legs="marrom", shoes="marrom")),
        "nina": Helper(Spot(23, 14, "down", True),
                       Look("Feminino", "chanel", "rosa", 0, top="camisa", shirt="vermelho",
                            bottom="vestido", legs="vermelho", shoes="branco")),
    },
    warps=[Warp(30, 43, "bosque", 21, 2, "down"), Warp(31, 43, "bosque", 22, 2, "down")],
)
HOME_DOOR = VILA.door_of("home")
CAFE_DOOR = VILA.door_of("cafe")
HOME_SPOT = (HOME_DOOR[0], HOME_DOOR[1] + 1)
COLISEUM_DOOR = VILA.door_of("coliseum")


# ============================================================ Bosque Sussurro
BOSQUE_SIGNS = {
    (24, 3): "BOSQUE SUSSURRO. As gosmas daqui são mais fortes. Ao norte: Vila Carta.",
    (24, 13): "PONTE DO RIACHO. Não pesque cartas no rio!",
}


def build_bosque() -> list[list[str]]:
    g, fill = _grid(44, 34)
    fill("=", 21, 0, 2, 9)        # entrada vinda da vila
    fill("=", 6, 8, 32, 2)        # trilha que corta o bosque
    fill("=", 21, 10, 2, 20)      # trilha para o sul, passando pela ponte
    fill(WATER, 2, 15, 40, 3)     # riacho
    fill("B", 21, 15, 2, 3)       # ponte
    fill(".", 15, 26, 14, 5)      # clareira
    fill(TALL_GRASS, 4, 3, 11, 4)     # campo do norte
    fill(TALL_GRASS, 30, 20, 10, 8)   # campo do sudeste
    fill(TALL_GRASS, 4, 21, 9, 6)     # campo do sudoeste
    fill("T", 26, 2, 3, 4)        # pequeno bosque fechado
    fill("T", 34, 3, 4, 3)
    fill("T", 4, 11, 3, 3)
    fill("T", 13, 11, 4, 2)
    fill("T", 30, 11, 5, 3)
    _place(g, "T", ((17, 3), (18, 5), (25, 21), (26, 24), (14, 22), (16, 20), (36, 30), (8, 30), (12, 29),
                    (28, 30), (39, 12), (2, 19), (10, 19), (34, 18), (38, 19)))
    _place(g, "R", ((19, 4), (25, 12), (17, 23), (27, 27), (9, 12), (37, 10)))
    _place(g, "f", ((16, 28), (27, 29), (18, 31), (24, 27), (8, 18), (36, 7), (12, 11), (29, 23), (20, 27)))
    _place(g, "S", BOSQUE_SIGNS)
    _forest_edge(g, depth=3)
    return g


def _forest_edge(g, depth):
    """Mata irregular junto à borda: árvores em padrão fixo, sem cobrir trilha, água, ponte ou placa."""
    h, w = len(g), len(g[0])
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            edge = min(x - 2, y - 2, w - 3 - x, h - 3 - y)
            if edge >= depth or g[y][x] != ".":
                continue
            chance = (x * 7 + y * 13 + x * y) % 10
            if chance < 6 - edge * 2:      # mais denso perto da borda, raleando para dentro
                g[y][x] = "T"


BOSQUE = MapDef(
    id="bosque",
    name="Bosque Sussurro",
    build=build_bosque,
    signs=BOSQUE_SIGNS,
    trainers={"kaio": Spot(26, 10, "down", True), "mila": Spot(19, 28, "right")},
    helpers={
        "rosa": Helper(Spot(10, 10, "down", True),
                       Look("Feminino", "chanel", "grisalho", 1, top="manga longa", shirt="roxo",
                            bottom="saia", legs="cinza", shoes="marrom")),
    },
    wild_types=list(FOREST_WILD_TYPES),
    warps=[Warp(21, 0, "vila", 30, 42, "up"), Warp(22, 0, "vila", 31, 42, "up")],
    wild_bonus=2,
)

# ============================================================ Lanchonete (interior)
# 30 x 17 tiles: ocupa a tela inteira. Parede do fundo com cardápio, TV e janela; balcão com a atendente
# à esquerda; puffs de frente para a TV; mesas para comer e a MESA DE TROCA. A porta fica embaixo.
CAFE_W, CAFE_H = 30, 17
CAFE_EXIT = (14, CAFE_H - 1)            # os 2 tiles da porta (x e x + 1) na parede de baixo
CAFE_SPOT = (CAFE_EXIT[0], CAFE_H - 2)  # onde você aparece ao entrar
CAFE_SIGNS = {
    **{(x, y): "BALCÃO: para pedir, fale com a LU no caixa." for x in range(1, 11) for y in (4, 5)},
    (13, 3): "FREEZER: sorvete de chocolate, morango e flocos. Peça para a LU!",
    (14, 3): "FREEZER: sorvete de chocolate, morango e flocos. Peça para a LU!",
    (11, 3): "GELADEIRA: refrigerante de cola, guaraná e laranja. Bem gelado!",
    (12, 3): "GELADEIRA: refrigerante de cola, guaraná e laranja. Bem gelado!",
    (28, 7): "JUKEBOX: tocando 'Lo-fi para montar decks'. Clássico!",
}


def build_cafe() -> list[list[str]]:
    g = [[FLOOR for _ in range(CAFE_W)] for _ in range(CAFE_H)]
    for y in range(CAFE_H):
        for x in range(CAFE_W):
            if y < 3 or x in (0, CAFE_W - 1) or y == CAFE_H - 1:
                g[y][x] = WALL
    g[CAFE_EXIT[1]][CAFE_EXIT[0]] = g[CAFE_EXIT[1]][CAFE_EXIT[0] + 1] = FLOOR
    return g


CAFE = MapDef(
    id="lanchonete",
    name="Lanchonete",
    build=build_cafe,
    interior="lanchonete",
    objects=[
        Placed("counter", 1, 4),
        Placed("soda_fridge", 11, 1),
        Placed("freezer", 13, 2),
        Placed("tv", 18, 1, "use:tv"),
        Placed("puff_red", 17, 6, "seat:up"),
        Placed("puff_yellow", 19, 6, "seat:up"),
        Placed("puff_blue", 21, 6, "seat:up"),
        Placed("plant", 16, 2),
        Placed("plant", 23, 2),
        Placed("plant", 28, 14),
        Placed("plant", 1, 14),
        Placed("jukebox", 28, 6),
        Placed("trade_table", 4, 10, "use:swap"),
        Placed("chair_r", 3, 9, "seat:right"),
        Placed("chair_l", 7, 9, "seat:left"),
        Placed("table", 17, 10),
        Placed("chair_r", 16, 9, "seat:right"),
        Placed("chair_l", 19, 9, "seat:left"),
        Placed("table", 23, 10),
        Placed("chair_r", 22, 9, "seat:right"),
        Placed("chair_l", 25, 9, "seat:left"),
        Placed("table", 25, 3),
        Placed("chair_r", 24, 2, "seat:right"),
        Placed("chair_l", 27, 2, "seat:left"),
    ],
    signs=CAFE_SIGNS,
    helpers={
        "lu": Helper(Spot(5, 3, "down"),
                     Look("Feminino", "chanel", "ruivo", 2, top="camisa", shirt="vermelho",
                          bottom="calça", legs="preto", shoes="preto")),
        "gabi": Helper(Spot(16, 10, "right"),
                       Look("Feminino", "longo", "preto", 4, top="top", shirt="amarelo",
                            bottom="saia", legs="jeans", shoes="branco"), sitting=True),
    },
    warps=[Warp(CAFE_EXIT[0], CAFE_EXIT[1], "vila", CAFE_DOOR[0], CAFE_DOOR[1] + 1, "down"),
           Warp(CAFE_EXIT[0] + 1, CAFE_EXIT[1], "vila", CAFE_DOOR[0], CAFE_DOOR[1] + 1, "down")],
)

# ============================================================ Casa do jogador (2 andares, particular)
# Térreo: cozinha americana com ilha, sala de jantar, sala de TV com sofá e estante de troféus, lavabo.
# Andar de cima: suíte do casal (closet, cama de casal, TV e banheiro com box), quarto de hóspedes e
# banheiro do corredor. A escada liga os dois: pisar no último degrau troca de andar.
HOUSE_W, HOUSE_H = 32, 18
HOUSE_EXIT = (15, HOUSE_H - 1)             # porta da rua (2 tiles) na parede de baixo do térreo
HOUSE_SPOT = (HOUSE_EXIT[0], HOUSE_H - 2)
STAIRS_DOWN_TOP = (13, 3)                  # térreo: a escada sobe pelos tiles (13..14, 3..5)
STAIRS_UP_BOTTOM = (13, 16)                # andar de cima: a escada desce pelos tiles (13..14, 14..16)


def _house_grid(floors, walls):
    """Grade de um andar: paredes em volta (3 linhas no fundo), pisos por região e paredes internas."""
    g = [[FLOOR for _ in range(HOUSE_W)] for _ in range(HOUSE_H)]
    for y in range(HOUSE_H):
        for x in range(HOUSE_W):
            if y < 3 or x in (0, HOUSE_W - 1) or y == HOUSE_H - 1:
                g[y][x] = WALL
    for tile, (x0, y0, w, h) in floors:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                g[y][x] = tile
    for x0, y0, w, h in walls:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                g[y][x] = WALL
    return g


def build_house_ground() -> list[list[str]]:
    g = _house_grid(floors=[(TILE_FLOOR, (1, 3, 12, 7)), (TILE_FLOOR, (27, 12, 4, 5)), (STAIRS, (13, 3, 2, 3))],
                    walls=[(26, 11, 5, 1), (26, 12, 1, 5)])
    g[14][26] = TILE_FLOOR                                  # porta do lavabo
    g[HOUSE_EXIT[1]][HOUSE_EXIT[0]] = g[HOUSE_EXIT[1]][HOUSE_EXIT[0] + 1] = FLOOR
    return g


def build_house_upper() -> list[list[str]]:
    g = _house_grid(floors=[(CARPET, (1, 3, 11, 7)), (TILE_FLOOR, (13, 3, 6, 7)), (CARPET, (20, 3, 11, 7)),
                            (TILE_FLOOR, (24, 11, 7, 6)), (STAIRS, (13, 14, 2, 3))],
                    walls=[(1, 10, 30, 1), (19, 3, 1, 7), (12, 3, 1, 7), (23, 11, 1, 6)])
    g[10][6] = CARPET                                       # porta da suíte
    g[10][25] = CARPET                                      # porta do quarto de hóspedes
    g[7][12] = TILE_FLOOR                                   # porta do banheiro da suíte
    g[14][23] = TILE_FLOOR                                  # porta do banheiro do corredor
    return g


HOUSE_GROUND = MapDef(
    id="casa_terreo",
    name="Sua casa",
    build=build_house_ground,
    interior="casa_terreo",
    private=True,
    objects=[
        # cozinha americana
        Placed("kitchen_counter", 1, 1),
        Placed("fridge", 9, 1),
        Placed("plant", 11, 2),
        Placed("island", 3, 6),
        *(Placed("stool", x, 8, "seat:up") for x in range(3, 7)),
        # sala de jantar
        Placed("dining_table", 3, 12),
        Placed("dchair_d", 4, 10, "seat:down"),
        Placed("dchair_d", 5, 10, "seat:down"),
        Placed("dchair_u", 4, 14, "seat:up"),
        Placed("dchair_u", 5, 14, "seat:up"),
        Placed("dchair_r", 2, 11, "seat:right"),
        Placed("dchair_l", 7, 11, "seat:left"),
        Placed("plant", 1, 15),
        Placed("sideboard", 9, 15),
        # sala de TV
        Placed("tv", 19, 1, "use:tv"),
        Placed("tv_rack", 18, 3, "use:tv"),
        Placed("coffee_table", 19, 6),
        Placed("sofa", 18, 8, "seat:up"),
        Placed("floor_lamp", 17, 7),
        Placed("floor_lamp", 23, 7),
        Placed("trophy_shelf", 25, 1, "use:trophies"),
        Placed("plant", 30, 2),
        Placed("plant", 17, 15),
        # lavabo
        Placed("bath_sink", 27, 11),
        Placed("toilet", 29, 11),
    ],
    signs={
        (9, 3): "GELADEIRA: tem suco, frutas e o bolo que a Rebeca fez.",
        (10, 3): "GELADEIRA: tem suco, frutas e o bolo que a Rebeca fez.",
        **{(x, 3): "COZINHA: fogão, pia e cafeteira. Tudo brilhando!" for x in range(1, 9)},
        **{(x, y): "ILHA DA COZINHA: o lugar do café da manhã." for x in range(3, 7) for y in (6, 7)},
        (27, 12): "PIA DO LAVABO: sabonete de lavanda.",
        (29, 12): "Lavabo limpinho.",
    },
    helpers={
        "rebeca": Helper(Spot(8, 5, "down", True),
                         Look("Feminino", "cacheado", "castanho", 3, top="top", shirt="preto",
                              bottom="shorts", legs="preto", shoes="branco")),
    },
    warps=[Warp(HOUSE_EXIT[0], HOUSE_EXIT[1], "vila", HOME_SPOT[0], HOME_SPOT[1], "down"),
           Warp(HOUSE_EXIT[0] + 1, HOUSE_EXIT[1], "vila", HOME_SPOT[0], HOME_SPOT[1], "down"),
           Warp(STAIRS_DOWN_TOP[0], STAIRS_DOWN_TOP[1], "casa_superior", STAIRS_UP_BOTTOM[0], 13, "up"),
           Warp(STAIRS_DOWN_TOP[0] + 1, STAIRS_DOWN_TOP[1], "casa_superior", STAIRS_UP_BOTTOM[0] + 1, 13, "up")],
)

HOUSE_UPPER = MapDef(
    id="casa_superior",
    name="Andar de cima",
    build=build_house_upper,
    interior="casa_superior",
    private=True,
    objects=[
        # suíte do casal
        Placed("closet", 1, 1, "use:closet"),
        Placed("nightstand", 4, 2),
        Placed("bed_double", 5, 2, "use:bed"),
        Placed("nightstand", 8, 2),
        Placed("tv_small", 10, 1, "use:tv"),
        Placed("dresser", 1, 8),
        Placed("plant", 11, 8),
        # banheiro da suíte
        Placed("toilet", 13, 2),
        Placed("vanity", 15, 2),
        Placed("shower", 17, 2),
        # quarto de hóspedes
        Placed("bed_single", 21, 2, "use:bed"),
        Placed("nightstand", 23, 2),
        Placed("tv_small", 28, 1, "use:tv"),
        Placed("dresser", 26, 8),
        Placed("plant", 20, 8),
        # corredor e banheiro do corredor
        Placed("plant", 1, 15),
        Placed("plant", 21, 15),
        Placed("toilet", 25, 10),
        Placed("bath_sink", 27, 10),
        Placed("bathtub", 28, 15),
    ],
    signs={
        (13, 3): "Banheiro da suíte: tudo cheirando a eucalipto.",
        (15, 3): "PIA DUPLA: uma para você, outra para a Rebeca.",
        (16, 3): "PIA DUPLA: uma para você, outra para a Rebeca.",
        (17, 4): "BOX: chuveiro quentinho com vidro temperado.",
        (18, 4): "BOX: chuveiro quentinho com vidro temperado.",
        (4, 3): "Criado-mudo com abajur e um livro de estratégias de cartas.",
        (8, 3): "Criado-mudo com o porta-retrato do casamento.",
        (23, 3): "Criado-mudo do quarto de hóspedes.",
        (1, 9): "CÔMODA: meias, toalhas e cartas repetidas.",
        (2, 9): "CÔMODA: meias, toalhas e cartas repetidas.",
        (26, 9): "CÔMODA de hóspedes: vazia, esperando visita.",
        (27, 9): "CÔMODA de hóspedes: vazia, esperando visita.",
        (25, 11): "Banheiro do corredor.",
        (27, 11): "Pia do banheiro do corredor.",
        **{(x, y): "BANHEIRA: espuma de morango!" for x in range(28, 31) for y in (15, 16)},
    },
    warps=[Warp(STAIRS_UP_BOTTOM[0], STAIRS_UP_BOTTOM[1], "casa_terreo", STAIRS_DOWN_TOP[0], 6, "down"),
           Warp(STAIRS_UP_BOTTOM[0] + 1, STAIRS_UP_BOTTOM[1], "casa_terreo", STAIRS_DOWN_TOP[0] + 1, 6, "down")],
)

MAPS = {m.id: m for m in (VILA, BOSQUE, CAFE, HOUSE_GROUND, HOUSE_UPPER)}


# ============================================================ falas
TRAINER_TALK = {
    "tico": TrainerTalk("TICO: Oi! Acabei de ganhar meu primeiro deck! Duela comigo?",
                        "TICO: Revanche? Eu treinei bastante!", "TICO: Tá bom... fico treinando aqui."),
    "rafa": TrainerTalk("RAFA: E aí! Você também tem um deck? Bora duelar?",
                        "RAFA: Quer revanche? Dessa vez eu ganho!", "RAFA: Beleza, fico te esperando aqui!",
                        first_win=("RAFA: Você é bom mesmo! Agora desafie a Mestra Lia, na porta da Arena!",)),
    "duda": TrainerTalk("DUDA: Os peixes não estão mordendo... Que tal um duelo enquanto isso?",
                        "DUDA: Voltou para mais uma pescaria de cartas?", "DUDA: Tudo bem, vou continuar pescando."),
    "bruno": TrainerTalk("BRUNO: Eu protejo a entrada do mato alto. Prove que é forte!",
                         "BRUNO: Minha guarda está mais firme. Outro duelo?",
                         "BRUNO: Volte quando estiver preparado."),
    "lia": TrainerTalk("LIA: Então você derrotou o Rafa... Mostre a força do seu deck!",
                       "LIA: Veio para uma revanche? Adoraria!", "LIA: Prepare-se bem. Estarei aqui.",
                       locked=("LIA: Eu sou a Mestra Lia, líder desta Arena.",
                               "LIA: Vença o Rafa primeiro. Depois volte para me desafiar."),
                       first_win=("LIA: Impressionante! Você é o novo campeão da Vila Carta!",
                                  "LIA: Mas cuidado... O Grão-Mestre ZECA chegou à Arena. Ele quer te conhecer.")),
    "sofia": TrainerTalk("SOFIA: Viajei o mundo todo colecionando cartas raras. Quer ver?",
                         "SOFIA: Encontrei cartas novas na estrada. Outro duelo?",
                         "SOFIA: Sem pressa, a estrada é longa."),
    "zeca": TrainerTalk("ZECA: Você venceu a Lia... Então me mostre o que aprendeu.",
                        "ZECA: De novo? Gosto da sua persistência.", "ZECA: Sábia decisão. Volte mais forte.",
                        locked=("ZECA: ...", "ZECA: Só duelo com quem já venceu a Mestra Lia."),
                        first_win=("ZECA: Você é a lenda da Vila Carta!", "Parabéns! Você venceu o Grão-Mestre!")),
    "kaio": TrainerTalk("KAIO: Os raios caem mais rápido no bosque. Aguenta um choque?",
                        "KAIO: Recarreguei as baterias. Mais um duelo?", "KAIO: Volte quando tiver energia de sobra.",
                        first_win=("KAIO: Que reflexo! A MILA, lá na clareira, é ainda mais perigosa.",)),
    "mila": TrainerTalk("MILA: Shhh... Ouça o bosque. Agora sinta o meu veneno!",
                        "MILA: O veneno não esquece. Quer tentar de novo?", "MILA: Fuja enquanto pode.",
                        first_win=("MILA: Você resistiu ao meu veneno... Respeito.",)),
}

# Dicas do Beto. {a}, {b}, {start}, {run} viram as teclas configuradas.
BETO_TIPS = [
    "Cada deck tem de 20 a 30 cartas: só 1 arquétipo (Fogo, Gelo, Raio ou Veneno) mais cartas de Utilidades.",
    "O dano bate primeiro na AURA, depois na DEFESA e só então no PV. As duas somem no seu próximo turno.",
    "O CHUTE VIOLENTO atravessa a aura, e o GOLPE PERFURANTE atravessa a defesa. Os dois anulam a proteção!",
    "Cada marcador de QUEIMADURA faz o oponente sofrer +1 de dano em todo golpe.",
    "Com 4 marcadores de GELO o oponente congela e perde o turno. Aí a contagem recomeça.",
    "O VENENO não passa: no fim de cada turno o oponente perde 1 PV por marcador.",
    "Cada PARALISIA tira 1 de energia do oponente no próximo turno. Elas se acumulam!",
    "No fim do turno você compra cartas até ficar com 5 na mão.",
    "No mato alto vivem Gosmas selvagens. Ótimo lugar para treinar!",
    "Aperte ENTER ou {start} para abrir o menu e montar o seu deck.",
    "Segure {run} ou {b} para correr. As teclas mudam em OPÇÕES, no menu.",
    "Vencer duelos dá BETS e XP. Com BETS você compra cartas na LOJA.",
    "Vencer alguém de nível maior rende mais BETS. Bater em quem é mais fraco rende pouco...",
    "A NINA, perto da loja, troca cartas. Ela só aceita cartas que não estão em nenhum deck.",
    "Dizem que um velho GRÃO-MESTRE aparece na Arena depois que alguém vence a Mestra Lia...",
    f"No COLISEU, ao sul do lago, os torneios dão XP x{XP_MULTIPLIER}. O campeão ganha {TOURNAMENT_PRIZE} BETS!",
    "O XP de batalha serve para EVOLUIR cartas na loja. Cada carta vai até o nível 3.",
    "Ninguém pode ter mais de 3 cópias da mesma carta.",
    "Seguindo a estrada para o sul você chega ao BOSQUE SUSSURRO. Lá as gosmas são bem mais fortes!",
]

ROSA_TIPS = [
    "VÓ ROSA: Ah, um duelista! As gosmas deste bosque são 2 níveis mais fortes que você.",
    "VÓ ROSA: O KAIO joga com Raio. Leve cartas que aguentem ficar com pouca energia.",
    "VÓ ROSA: A MILA, na clareira, acumula veneno. Vencer rápido é o segredo!",
    "VÓ ROSA: Se cansar, volte pela estrada do norte. A Vila Carta fica logo ali.",
]

# Lanchonete: a cliente GABI dá dicas; a TV tem 3 canais (os desenhos ficam em graphics/interiors.py).
GABI_TIPS = [
    "GABI: Eu sempre como um X-BURGUER antes do Coliseu. Dá +12 PV na próxima batalha!",
    "GABI: O lanche só vale para UMA batalha. E de barriga cheia a Lu não vende outro, viu?",
    "GABI: Naquela MESA DE TROCA, dois duelistas online trocam cartas que estão sobrando.",
    "GABI: Os puffs de frente para a TV são os melhores lugares da vila. Sente lá!",
]
TV_SHOWS = [
    "TV: AO VIVO do Coliseu! O desafiante joga um CHOQUE DO TROVÃO... e a torcida vai à loucura!",
    "TV: Previsão do tempo: sol na Vila Carta e névoa no Bosque Sussurro. Cuidado com as gosmas!",
    "TV: CARTA DO DIA! Lembre: com 4 marcadores de gelo, o oponente congela e perde o turno.",
]

# Rebeca, sua esposa (em casa). {name} = seu nome.
REBECA_LINES = [
    "REBECA: Oi, amor! Como foram os duelos hoje?",
    "REBECA: Já viu a estante da sala? Cada troféu do Coliseu vai pra lá. Tô orgulhosa de você!",
    "REBECA: Lá em cima tem o closet do nosso quarto, se quiser trocar de roupa antes de sair.",
    "REBECA: Cansou? Deita um pouco lá no quarto. Eu cuido de tudo aqui embaixo.",
    "REBECA: Traz um X-burguer da lanchonete pra mim depois? Hehe.",
    "REBECA: {name}, vê se não perde pro Zeca, hein! Eu acredito em você.",
]

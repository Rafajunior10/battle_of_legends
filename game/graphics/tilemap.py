"""Mapas desenhados com os tilesets do pacote Ninja Adventure.

Duas camadas:
  * CHÃO (desenhado uma vez só): grama de base + terrenos com AUTOTILE (terra, água, cerca, ponte).
    Autotile = escolher a peça certa olhando os vizinhos. Ex.: um tile de terra com grama em cima e
    à esquerda usa a peça "canto superior esquerdo" da mancha de terra.
  * OBJETOS (casas, árvores, enfeites): figuras de vários tiles, desenhadas junto com os personagens,
    em ordem de altura na tela. Assim, quem passa atrás de uma árvore fica coberto pela copa.

Sem o pacote, nada daqui é usado: o mapa cai na arte desenhada por código (tileset.py).
"""
from __future__ import annotations

import pygame

from game.data.props import OBJECTS, TREE_KINDS
from game.graphics import assets

TILE = 16
TILESET_DIR = "backgrounds/tilesets"

# Legenda do mapa
GRASS, DIRT, WATER, BRIDGE, TALL_GRASS, FENCE, FLOWER = ".", "=", "W", "B", ",", "F", "f"

# Blocos de autotile: (arquivo, coluna, linha) do canto de cima à esquerda do bloco.
# Dentro do bloco, o layout é sempre o mesmo (ver _AUTOTILE).
TERRAINS = {
    DIRT: ("TilesetFloor.png", 0, 7),
    WATER: ("TilesetWater.png", 0, 6),
}
# Peças do bloco, pela posição relativa. N/S/E/W = vizinho do MESMO terreno em cima/baixo/direita/esquerda.
_AUTOTILE = {
    # (N, S, W, E): peça
    (False, True, False, True): (0, 0),    # canto de cima, esquerda
    (False, True, True, True): (1, 0),     # borda de cima
    (False, True, True, False): (2, 0),    # canto de cima, direita
    (True, True, False, True): (0, 1),     # borda esquerda
    (True, True, True, True): (1, 1),      # meio
    (True, True, True, False): (2, 1),     # borda direita
    (True, False, False, True): (0, 2),    # canto de baixo, esquerda
    (True, False, True, True): (1, 2),     # borda de baixo
    (True, False, True, False): (2, 2),    # canto de baixo, direita
    (False, True, False, False): (3, 0),   # faixa vertical: ponta de cima
    (True, True, False, False): (3, 1),    # faixa vertical: meio
    (True, False, False, False): (3, 2),   # faixa vertical: ponta de baixo
    (False, False, False, True): (0, 3),   # faixa horizontal: ponta esquerda
    (False, False, True, True): (1, 3),    # faixa horizontal: meio
    (False, False, True, False): (2, 3),   # faixa horizontal: ponta direita
    (False, False, False, False): (3, 3),  # pedaço isolado
}
# Curvas para dentro: tudo em volta é do terreno, menos UMA diagonal.
_INNER = {"se": (5, 1), "sw": (6, 1), "ne": (5, 2), "nw": (6, 2)}

GRASS_TILES = [("TilesetFloor.png", 0, 12)] * 6 + [("TilesetFloor.png", c, 12) for c in range(1, 5)]
TALL_GRASS_TILE = ("TilesetNature.png", 5, 10)
FLOWER_TILES = [("TilesetNature.png", 0, 11), ("TilesetNature.png", 3, 11), ("TilesetNature.png", 6, 11)]
BRIDGE_TILES = {"top": ("TilesetWater.png", 1, 12), "mid": ("TilesetWater.png", 1, 13),
                "bottom": ("TilesetWater.png", 1, 14)}
# Cerca baixa de trilho: peça pelos vizinhos que também são cerca
FENCE_TILES = {"h": (11, 7), "v": (11, 6), "es": (8, 6), "ws": (9, 6), "en": (8, 7), "wn": (9, 7), "post": (14, 6)}


H = "TilesetHouse.png"
SIGN_TILE = ("TilesetElement.png", 6, 3, 1, 2)       # placa: tábua em cima, poste embaixo
ROCK_TILE = ("TilesetNature.png", 4, 13)


def available() -> bool:
    return assets.pack().available and assets.pack().find(TILESET_DIR, "tilesetfloor.png") is not None


_tiles: dict = {}


def tile(tileset: str, col: int, row: int, w: int = 1, h: int = 1) -> pygame.Surface:
    """Recorte de um tileset (w x h tiles), guardado em cache."""
    key = (tileset, col, row, w, h)
    if key not in _tiles:
        sheet = assets.pack().image(assets.pack().find(TILESET_DIR, tileset))
        _tiles[key] = sheet.subsurface((col * TILE, row * TILE, w * TILE, h * TILE)).copy()
    return _tiles[key]


def object_image(name: str) -> pygame.Surface:
    d = OBJECTS[name]
    return tile(d.tileset, d.col, d.row, d.w, d.h)


def tree_image(x: int, y: int) -> pygame.Surface:
    """Árvore 2x2 para um tile "T", com o tipo variando pela posição (mata mais natural)."""
    return object_image(TREE_KINDS[_variant(x, y, len(TREE_KINDS))])


# ------------------------------------------------------------ autotile
def _same(grid, x, y, kinds) -> bool:
    """O vizinho (x, y) é de um dos tipos `kinds`? Fora do mapa conta como igual (borda sem costura)."""
    if not (0 <= y < len(grid) and 0 <= x < len(grid[0])):
        return True
    return grid[y][x] in kinds


def autotile_piece(grid, x, y, kinds) -> tuple[int, int]:
    """Posição da peça (relativa ao bloco do terreno) para o tile (x, y)."""
    n, s = _same(grid, x, y - 1, kinds), _same(grid, x, y + 1, kinds)
    w, e = _same(grid, x - 1, y, kinds), _same(grid, x + 1, y, kinds)
    if n and s and w and e:
        for corner, (dx, dy) in (("se", (1, 1)), ("sw", (-1, 1)), ("ne", (1, -1)), ("nw", (-1, -1))):
            if not _same(grid, x + dx, y + dy, kinds):
                return _INNER[corner]
    return _AUTOTILE[(n, s, w, e)]


def fence_piece(grid, x, y) -> tuple[int, int]:
    n, s = _same_strict(grid, x, y - 1, FENCE), _same_strict(grid, x, y + 1, FENCE)
    w, e = _same_strict(grid, x - 1, y, FENCE), _same_strict(grid, x + 1, y, FENCE)
    if (w or e) and not (n or s):
        return FENCE_TILES["h"]
    if (n or s) and not (w or e):
        return FENCE_TILES["v"]
    for key, (a, b) in (("es", (e, s)), ("ws", (w, s)), ("en", (e, n)), ("wn", (w, n))):
        if a and b:
            return FENCE_TILES[key]
    return FENCE_TILES["post"]


def _same_strict(grid, x, y, kind) -> bool:
    return 0 <= y < len(grid) and 0 <= x < len(grid[0]) and grid[y][x] == kind


def _variant(x, y, n) -> int:
    return (x * 7 + y * 13 + (x * y) % 5) % n


def ground_tile(grid, x, y) -> list[pygame.Surface]:
    """Camadas do chão de um tile, de baixo para cima."""
    kind = grid[y][x]
    layers = [tile(*GRASS_TILES[_variant(x, y, len(GRASS_TILES))])]
    if kind == DIRT:
        file, c0, r0 = TERRAINS[DIRT]
        dc, dr = autotile_piece(grid, x, y, {DIRT})
        layers.append(tile(file, c0 + dc, r0 + dr))
    elif kind in (WATER, BRIDGE):
        file, c0, r0 = TERRAINS[WATER]
        dc, dr = autotile_piece(grid, x, y, {WATER, BRIDGE})   # a água continua por baixo da ponte
        layers.append(tile(file, c0 + dc, r0 + dr))
        if kind == BRIDGE:
            top = not _same_strict(grid, x, y - 1, BRIDGE)
            bottom = not _same_strict(grid, x, y + 1, BRIDGE)
            layers.append(tile(*BRIDGE_TILES["top" if top else "bottom" if bottom else "mid"]))
    elif kind == TALL_GRASS:
        layers.append(tile(*TALL_GRASS_TILE))
    elif kind == FENCE:
        layers.append(tile(H, *fence_piece(grid, x, y)))
    elif kind == FLOWER:
        layers.append(tile(*FLOWER_TILES[_variant(x, y, len(FLOWER_TILES))]))
    return layers


def render_ground(grid) -> pygame.Surface:
    h, w = len(grid), len(grid[0])
    ground = pygame.Surface((w * TILE, h * TILE))
    for y in range(h):
        for x in range(w):
            for layer in ground_tile(grid, x, y):
                ground.blit(layer, (x * TILE, y * TILE))
    return ground.convert() if pygame.display.get_surface() else ground

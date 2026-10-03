"""Casa do jogador, desenhada por código no estilo de buildings.py/interiors.py: casa moderna "americana".

- `ground(grid, decor)`: o chão e as paredes saem da GRADE do andar (game/data/world.py). Cada tile vira piso
  (madeira, azulejo, carpete, escada) ou parede. Parede com piso embaixo mostra a FRENTE (papel de parede ou
  azulejo, conforme o cômodo, com rodapé); as outras mostram o TOPO escuro (a espessura da parede).
  Depois entram tapetes, janelas e quadros (`decor`), nas posições de cada andar.
- Os móveis (FURNITURE) são figuras do mapa, como os da lanchonete. A estante de troféus é desenhada a partir
  do personagem (`trophy_shelf(ch)`): um troféu para cada título do Coliseu e medalhas dos mestres vencidos.
Tudo é desenhado uma vez (o lobby guarda); nada aqui roda a cada quadro.
"""
from __future__ import annotations

import pygame

from game.engine.settings import TILE
from game.graphics.buildings import OUTLINE, shade
from game.graphics.interiors import CHROME, RED, _box

WALL_KINDS = "#"
OAK = ((170, 120, 78), (206, 158, 108), (222, 178, 128))          # piso de madeira clara
WALL_FACE = {"_": (240, 232, 216), "s": (240, 232, 216), "c": (222, 214, 236), "t": (236, 242, 246)}
WALL_TOP = ((54, 50, 62), (84, 78, 94))
WHITE = ((200, 204, 210), (234, 236, 240), (250, 250, 252))
QUARTZ = ((60, 64, 74), (92, 96, 108))
WALNUT = ((92, 58, 40), (132, 86, 56), (166, 116, 78))
NAVY = ((34, 52, 92), (52, 78, 132), (90, 120, 176))
FABRIC = ((96, 100, 112), (132, 138, 150), (166, 172, 184))       # sofá cinza
GOLD = ((168, 120, 30), (236, 188, 60), (255, 236, 150))
TV_SMALL_SCREEN = pygame.Rect(3, 4, 26, 16)
TV_BIG_SCREEN = pygame.Rect(4, 3, 88, 25)


class BedSpec:
    """Onde quem deita fica numa cama: `slots` = centro (x) de cada lugar, `top` = topo do boneco, `flip` =
    deitado de cabeça para baixo (cama virada para a TV) e `cover` = linhas da cama desenhadas POR CIMA de
    quem está deitado (o edredom)."""

    def __init__(self, slots, top, flip, cover):
        self.slots, self.top, self.flip, self.cover = slots, top, flip, cover


BEDS = {"bed_double": BedSpec((17, 47), 7, True, (0, 26)), "bed_single": BedSpec((16,), 2, False, (28, 48))}
SHOWER = {"center": 16, "top": 2, "glass": (13, 48)}     # o box: onde fica quem toma banho e o vidro na frente


def _is_wall(grid, x, y):
    return not (0 <= y < len(grid) and 0 <= x < len(grid[0])) or grid[y][x] in WALL_KINDS


def _face_kind(grid, x, y):
    """Se a parede em (x, y) mostra a frente, devolve o piso do cômodo à frente dela (decide a cor)."""
    if not _is_wall(grid, x, y + 1):
        return grid[y + 1][x]
    if _is_wall(grid, x, y - 1) and y + 2 < len(grid) and not _is_wall(grid, x, y + 2) and y >= 1:
        return grid[y + 2][x]
    return None


# ============================================================ chão e paredes
def ground(grid, decor=()) -> pygame.Surface:
    h, w = len(grid), len(grid[0])
    s = pygame.Surface((w * TILE, h * TILE))
    for y in range(h):
        for x in range(w):
            if _is_wall(grid, x, y):
                _wall_tile(s, grid, x, y)
            else:
                _floor_tile(s, grid, x, y)
    for y in range(h):                                   # vãos de porta: batentes e capacho na porta da rua
        for x in range(w):
            if not _is_wall(grid, x, y):
                _door_frame(s, grid, x, y)
    for draw, *args in decor:
        draw(s, *args)
    return s


def _floor_tile(s, grid, x, y):
    FLOORS.get(grid[y][x], _wood)(s, grid, x, y, x * TILE, y * TILE)


def _tiles(s, grid, x, y, px, py):
    """Azulejo claro com rejunte."""
    s.fill((226, 230, 234), (px, py, TILE, TILE))
    for k in (0, 8):
        pygame.draw.line(s, (196, 202, 208), (px, py + k), (px + TILE - 1, py + k))
        pygame.draw.line(s, (196, 202, 208), (px + k, py), (px + k, py + TILE - 1))
    s.set_at((px + 2, py + 2), (246, 248, 250))
    s.set_at((px + 10, py + 10), (246, 248, 250))


def _carpet(s, grid, x, y, px, py):
    s.fill((214, 202, 186), (px, py, TILE, TILE))
    for i in range(TILE):
        for j in range(TILE):
            if ((px + i) * 7 + (py + j) * 13) % 11 == 0:
                s.set_at((px + i, py + j), (198, 186, 170))


def _stairs(s, grid, x, y, px, py):
    """Degraus de 8 px, com corrimão escuro nas laterais da escada."""
    for k in range(2):
        top = py + k * 8
        s.fill(OAK[1], (px, top, TILE, 8))
        pygame.draw.line(s, OAK[2], (px, top), (px + TILE - 1, top), 2)
        pygame.draw.line(s, OAK[0], (px, top + 7), (px + TILE - 1, top + 7))
    if grid[y][x - 1] != "s":
        s.fill(WALNUT[0], (px, py, 3, TILE))
    if grid[y][x + 1] != "s":
        s.fill(WALNUT[0], (px + TILE - 3, py, 3, TILE))


def _wood(s, grid, x, y, px, py):
    """Tábuas de 8 px com emendas desencontradas (contadas da casa inteira, então continuam entre os tiles)."""
    for k in range(2):
        row = (py + k * 8) // 8
        top = py + k * 8
        s.fill(OAK[1] if row % 2 else OAK[2], (px, top, TILE, 8))
        pygame.draw.line(s, OAK[0], (px, top + 7), (px + TILE - 1, top + 7))
        for sx in range(px, px + TILE):
            if (sx - row * 13) % 40 == 0:
                pygame.draw.line(s, OAK[0], (sx, top), (sx, top + 6))


FLOORS = {"t": _tiles, "c": _carpet, "s": _stairs, "_": _wood}


def _wall_tile(s, grid, x, y):
    px, py = x * TILE, y * TILE
    kind = _face_kind(grid, x, y)
    if kind is None:                                     # topo da parede: escuro, com borda clara junto ao piso
        s.fill(WALL_TOP[0], (px, py, TILE, TILE))
        for dx, dy, rect in ((-1, 0, (px, py, 2, TILE)), (1, 0, (px + TILE - 2, py, 2, TILE)),
                             (0, -1, (px, py, TILE, 2))):
            if not _is_wall(grid, x + dx, y + dy):
                s.fill(WALL_TOP[1], rect)
        return
    color = WALL_FACE.get(kind, WALL_FACE["_"])
    s.fill(color, (px, py, TILE, TILE))
    if kind == "t":                                      # banheiro/cozinha: azulejo na parede
        for k in (0, 8):
            pygame.draw.line(s, shade(color, -26), (px, py + k), (px + TILE - 1, py + k))
        for k in ((0, 8) if (y % 2) else (4, 12)):
            pygame.draw.line(s, shade(color, -26), (px + k, py), (px + k, py + TILE - 1))
    else:                                                # papel de parede com listras bem suaves
        for k in range(0, TILE, 8):
            pygame.draw.line(s, shade(color, -8), (px + k, py), (px + k, py + TILE - 1))
    if _is_wall(grid, x, y - 1) and _face_kind(grid, x, y - 1) is None:     # moldura no alto da parede
        s.fill(shade(color, 14), (px, py, TILE, 2))
        pygame.draw.line(s, shade(color, -40), (px, py + 2), (px + TILE - 1, py + 2))
    if not _is_wall(grid, x, y + 1):                     # rodapé branco
        s.fill((248, 248, 246), (px, py + TILE - 4, TILE, 3))
        pygame.draw.line(s, OUTLINE, (px, py + TILE - 1), (px + TILE - 1, py + TILE - 1))


def _door_frame(s, grid, x, y):
    px, py = x * TILE, y * TILE
    if y == len(grid) - 1:                               # porta da rua: capacho
        s.fill((120, 76, 50), (px + 1, py + 3, TILE - 2, TILE - 6))
        for k in range(py + 5, py + TILE - 4, 3):
            pygame.draw.line(s, (156, 104, 70), (px + 2, k), (px + TILE - 3, k))
    elif _is_wall(grid, x - 1, y) and _is_wall(grid, x + 1, y) and grid[y][x - 1] == "#":
        for bx in (px, px + TILE - 2):                    # vão numa parede deitada: batentes brancos
            s.fill((246, 246, 244), (bx, py, 2, TILE))
    elif _is_wall(grid, x, y - 1) and _is_wall(grid, x, y + 1):
        for by in (py, py + TILE - 2):                    # vão numa parede em pé: soleira
            s.fill((246, 246, 244), (px, by, TILE, 2))


# ---- decoração das paredes e do chão (posições em tiles)
def rug(s, x, y, w, h, colors):
    rect = pygame.Rect(x * TILE + 4, y * TILE + 4, w * TILE - 8, h * TILE - 8)
    pygame.draw.rect(s, OUTLINE, rect, border_radius=4)
    pygame.draw.rect(s, colors[1], rect.inflate(-2, -2), border_radius=3)
    pygame.draw.rect(s, colors[2], rect.inflate(-8, -8), 1, border_radius=2)
    for k in range(rect.x + 8, rect.right - 6, 10):
        pygame.draw.line(s, colors[0], (k, rect.y + 6), (k + 4, rect.bottom - 7))


def window(s, x, y, w=2, h=2):
    rect = pygame.Rect(x * TILE + 3, y * TILE + 3, w * TILE - 6, h * TILE - 8)
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2))
    pygame.draw.rect(s, (250, 250, 248), rect)
    glass = rect.inflate(-4, -4)
    for i in range(glass.h):
        pygame.draw.line(s, (130 + i * 3, 196 + i, 240), (glass.x, glass.y + i), (glass.right - 1, glass.y + i))
    pygame.draw.ellipse(s, (70, 156, 86), (glass.x - 3, glass.bottom - 7, 18, 12))
    pygame.draw.line(s, (250, 250, 248), (glass.centerx, glass.y), (glass.centerx, glass.bottom - 1), 2)
    pygame.draw.line(s, (220, 240, 250), (glass.x + 2, glass.bottom - 3), (glass.x + 8, glass.y + 2))


def painting(s, x, y, w=1, colors=((236, 120, 80), (250, 210, 90), (80, 150, 200))):
    rect = pygame.Rect(x * TILE + 2, y * TILE + 3, w * TILE - 4, 10)
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2))
    pygame.draw.rect(s, (250, 248, 240), rect)
    inner = rect.inflate(-4, -4)
    third = max(1, inner.w // 3)
    for i, color in enumerate(colors):                   # arte abstrata em 3 blocos
        pygame.draw.rect(s, color, (inner.x + i * third, inner.y, third, inner.h))


def clock(s, x, y):
    cx, cy = x * TILE + 8, y * TILE + 8
    pygame.draw.circle(s, OUTLINE, (cx, cy), 6)
    pygame.draw.circle(s, (250, 250, 246), (cx, cy), 5)
    pygame.draw.line(s, OUTLINE, (cx, cy), (cx, cy - 3))
    pygame.draw.line(s, OUTLINE, (cx, cy), (cx + 2, cy))


def photos(s, x, y):
    """Porta-retratos da família no corredor."""
    for i, color in enumerate(((240, 200, 160), (200, 220, 240))):
        rect = pygame.Rect(x * TILE + 1 + i * 8, y * TILE + 3 + i * 2, 7, 8)
        pygame.draw.rect(s, OUTLINE, rect)
        pygame.draw.rect(s, color, rect.inflate(-2, -2))


LIVING_RUG = ((120, 108, 96), (196, 184, 168), (240, 232, 220))
DINING_RUG = ((90, 60, 50), (150, 100, 80), (220, 180, 140))
SUITE_RUG = ((90, 96, 130), (150, 160, 200), (230, 232, 246))
GUEST_RUG = ((80, 120, 90), (140, 180, 140), (226, 240, 220))
RUNNER = ((120, 60, 60), (170, 80, 76), (240, 200, 150))
GROUND_DECOR = [
    (rug, 17, 5, 7, 3, LIVING_RUG), (rug, 1, 10, 9, 6, DINING_RUG),
    (window, 15, 1), (clock, 17, 1), (painting, 29, 1, 1, ((90, 160, 120), (240, 240, 230), (40, 90, 70))),
]
UPPER_DECOR = [
    (rug, 5, 4, 8, 5, SUITE_RUG), (rug, 20, 5, 4, 3, GUEST_RUG), (rug, 2, 11, 10, 2, RUNNER),
    (painting, 4, 1), (painting, 12, 1), (painting, 23, 1), (window, 29, 1),
    (photos, 8, 10), (painting, 16, 10, 2, ((200, 120, 200), (250, 220, 120), (120, 180, 220))), (photos, 24, 10),
]


# ============================================================ móveis
def _surface(w, h):
    return pygame.Surface((w * TILE, h * TILE), pygame.SRCALPHA)


def _handle(s, x, y, length=3, vertical=False):
    end = (x, y + length) if vertical else (x + length, y)
    pygame.draw.line(s, CHROME[0], (x, y), end)


def kitchen_counter():
    """Bancada da cozinha (8 x 3): armários brancos em cima, coifa, azulejo, tampo escuro, fogão e pia."""
    s = _surface(8, 3)
    w = s.get_width()
    for i, x in enumerate(range(0, w, 16)):              # armários de cima (menos sobre o fogão)
        if i in (2, 3):
            continue
        _box(s, (x, 1, 16, 15), WHITE[1])
        _handle(s, x + 12, 9, 3, vertical=True)
    pygame.draw.polygon(s, OUTLINE, [(28, 16), (34, 2), (60, 2), (66, 16)])   # coifa inox
    pygame.draw.polygon(s, CHROME[1], [(30, 15), (35, 3), (59, 3), (64, 15)])
    pygame.draw.line(s, CHROME[2], (36, 4), (40, 14))
    for y in range(16, 30, 4):                            # azulejo de metrô na parede
        for x in range((y // 4) % 2 * 4, w, 8):
            pygame.draw.rect(s, (236, 240, 242), (x, y, 7, 3))
    _box(s, (0, 29, w, 5), QUARTZ[1])                    # tampo escuro
    pygame.draw.line(s, (130, 136, 150), (2, 30), (w - 3, 30))
    for x in range(0, w, 16):                             # armários de baixo
        if 32 <= x < 64:
            continue
        _box(s, (x, 33, 16, 15), WHITE[1])
        _handle(s, x + 6, 36, 4)
    _box(s, (32, 33, 32, 15), (40, 40, 48))              # forno
    pygame.draw.rect(s, (90, 100, 120), (36, 38, 24, 7))
    _handle(s, 38, 35, 20)
    for bx in (38, 50):                                   # bocas do cooktop
        for by in (29, 31):
            s.set_at((bx, by), (230, 80, 60))
            s.set_at((bx + 6, by), (230, 80, 60))
    pygame.draw.rect(s, OUTLINE, (82, 29, 18, 4))          # pia com torneira
    pygame.draw.rect(s, CHROME[0], (83, 30, 16, 2))
    pygame.draw.line(s, CHROME[1], (91, 23), (91, 29), 2)
    pygame.draw.line(s, CHROME[1], (91, 23), (95, 23), 2)
    _box(s, (108, 21, 8, 9), (40, 40, 48), 1)            # cafeteira
    s.set_at((110, 24), (230, 80, 60))
    pygame.draw.ellipse(s, OUTLINE, (118, 25, 9, 5))      # potinho de frutas
    s.set_at((120, 25), RED[1])
    s.set_at((123, 25), (250, 200, 50))
    return s


def fridge():
    s = _surface(2, 3)
    _box(s, (1, 0, 30, 47), CHROME[1], 2)
    pygame.draw.line(s, OUTLINE, (16, 1), (16, 45))       # porta dupla
    pygame.draw.line(s, CHROME[2], (4, 2), (4, 44))
    for x in (13, 19):
        pygame.draw.line(s, CHROME[0], (x, 14), (x, 26), 2)
    _box(s, (20, 6, 8, 7), (60, 70, 84))                 # dispenser de água
    pygame.draw.rect(s, (120, 200, 240), (22, 8, 4, 2))
    return s


def island():
    """Ilha da cozinha (4 x 2): tampo de mármore branco e frente azul-marinho."""
    s = _surface(4, 2)
    w = s.get_width()
    _box(s, (0, 1, w, 14), (244, 244, 246))
    for x in range(8, w - 8, 18):
        pygame.draw.line(s, (214, 214, 222), (x, 5), (x + 7, 11))
    _box(s, (2, 14, w - 4, 17), NAVY[1])
    for x in range(2, w - 4, 15):
        pygame.draw.line(s, NAVY[0], (x + 15, 15), (x + 15, 29))
        _handle(s, x + 6, 18, 4)
    pygame.draw.ellipse(s, OUTLINE, (12, 2, 14, 8))       # fruteira e vaso
    pygame.draw.ellipse(s, (250, 250, 248), (13, 3, 12, 6))
    for cx, color in ((16, RED[1]), (20, (250, 200, 50)), (23, (90, 180, 70))):
        s.set_at((cx, 4), color)
        s.set_at((cx, 5), color)
    _box(s, (44, 1, 6, 9), (250, 250, 248), 2)
    pygame.draw.line(s, (60, 150, 80), (47, 1), (47, -2))
    return s


def stool():
    s = _surface(1, 1)
    pygame.draw.ellipse(s, OUTLINE, (2, 1, 12, 7))
    pygame.draw.ellipse(s, WALNUT[2], (3, 2, 10, 5))
    for x in (4, 11):
        pygame.draw.line(s, CHROME[0], (x, 7), (x, 15))
    pygame.draw.line(s, CHROME[1], (4, 12), (11, 12))
    return s


def dining_table():
    s = _surface(4, 2)
    w = s.get_width()
    _box(s, (0, 2, w, 20), WALNUT[1], 3)
    for x in range(4, w - 4, 12):
        pygame.draw.line(s, WALNUT[0], (x, 5), (x + 6, 5))
    pygame.draw.line(s, WALNUT[2], (2, 3), (w - 3, 3))
    for x in (3, w - 6):
        pygame.draw.rect(s, WALNUT[0], (x, 22, 3, 9))
    for cx in (20, 44):                                   # pratos
        pygame.draw.circle(s, OUTLINE, (cx, 9), 4)
        pygame.draw.circle(s, (250, 250, 248), (cx, 9), 3)
    for cx in (20, 44):
        pygame.draw.circle(s, OUTLINE, (cx, 17), 4)
        pygame.draw.circle(s, (250, 250, 248), (cx, 17), 3)
    _box(s, (30, 8, 5, 8), (250, 250, 248), 2)            # vaso com flores
    for dx, color in ((-1, RED[1]), (2, (250, 200, 60)), (5, (240, 120, 180))):
        pygame.draw.circle(s, color, (30 + dx, 7), 2)
    return s


def dchair_down():
    """Cadeira de jantar vista de frente (quem senta olha para baixo): encosto no tile de cima."""
    s = _surface(1, 2)
    _box(s, (2, 8, 12, 13), WALNUT[1], 2)
    pygame.draw.rect(s, WALNUT[2], (5, 11, 6, 6))
    _box(s, (2, 19, 12, 7), (226, 216, 196), 2)
    for x in (3, 11):
        pygame.draw.line(s, WALNUT[0], (x, 26), (x, 31))
    return s


def dchair_up():
    """Cadeira de jantar vista de costas (quem senta olha para cima): encosto embaixo."""
    s = _surface(1, 1)
    _box(s, (2, 1, 12, 6), (226, 216, 196), 2)
    _box(s, (2, 5, 12, 10), WALNUT[1], 2)
    pygame.draw.line(s, WALNUT[2], (4, 7), (11, 7))
    return s


def dchair_side(facing_right=True):
    s = _surface(1, 2)
    _box(s, (1, 10, 5, 17), WALNUT[1], 2)
    _box(s, (2, 21, 13, 6), (226, 216, 196), 2)
    for x in (4, 12):
        pygame.draw.line(s, WALNUT[0], (x, 27), (x, 31))
    return s if facing_right else pygame.transform.flip(s, True, False)


def sideboard():
    s = _surface(3, 2)
    _box(s, (0, 14, 48, 18), WALNUT[1])
    for x in (16, 32):
        pygame.draw.line(s, WALNUT[0], (x, 15), (x, 30))
    for x in (6, 22, 38):
        _handle(s, x, 22, 4)
    _box(s, (6, 4, 6, 11), (250, 250, 248), 2)            # vaso
    pygame.draw.line(s, (60, 150, 80), (9, 4), (8, 0))
    for i, color in enumerate(((200, 70, 60), (60, 110, 180), (230, 190, 70))):    # livros
        pygame.draw.rect(s, OUTLINE, (28 + i * 4, 6, 4, 9))
        pygame.draw.rect(s, color, (29 + i * 4, 7, 2, 7))
    return s


def tv_rack():
    """Rack baixo embaixo da TV: soundbar, videogame e plantinha."""
    s = _surface(6, 1)
    w = s.get_width()
    _box(s, (0, 3, w, 13), WHITE[1])
    pygame.draw.line(s, WALNUT[1], (1, 4), (w - 2, 4), 2)
    for x in range(16, w, 24):
        pygame.draw.line(s, WHITE[0], (x, 6), (x, 14))
    _box(s, (30, 0, 36, 4), (40, 40, 48), 1)              # soundbar
    _box(s, (6, 6, 12, 6), (30, 30, 36), 1)               # videogame
    s.set_at((15, 8), (90, 200, 250))
    pygame.draw.circle(s, (60, 150, 80), (86, 2), 3)
    return s


def coffee_table():
    s = _surface(3, 1)
    _box(s, (1, 2, 46, 10), WALNUT[1], 3)
    pygame.draw.rect(s, (200, 228, 236), (4, 4, 40, 6), border_radius=2)       # tampo de vidro
    pygame.draw.line(s, (240, 250, 252), (6, 5), (14, 5))
    for x in (4, 41):
        pygame.draw.rect(s, WALNUT[0], (x, 12, 3, 4))
    pygame.draw.rect(s, (220, 80, 70), (10, 6, 9, 4))     # revista
    _box(s, (30, 4, 5, 5), (250, 250, 248), 1)            # caneca
    return s


def sofa():
    """Sofá cinza visto de COSTAS (quem senta olha para a TV): almofadas no alto, encosto alto embaixo."""
    s = _surface(5, 2)
    w = s.get_width()
    for i, color in enumerate(((240, 200, 90), (90, 160, 200), (240, 130, 120))):   # almofadas aparecendo
        _box(s, (14 + i * 22, 2, 12, 8), color, 3)
    _box(s, (0, 4, w, 26), FABRIC[1], 5)                 # encosto alto
    pygame.draw.line(s, FABRIC[2], (5, 6), (w - 6, 6))
    for x in (w // 3, 2 * w // 3):
        pygame.draw.line(s, FABRIC[0], (x, 8), (x, 26))
    for x in (0, w - 8):                                  # braços
        _box(s, (x, 2, 8, 28), FABRIC[0], 3)
    pygame.draw.rect(s, OUTLINE, (4, 29, w - 8, 3))        # pés
    return s


def floor_lamp():
    s = _surface(1, 2)
    pygame.draw.line(s, (60, 60, 70), (8, 10), (8, 30))
    pygame.draw.rect(s, OUTLINE, (4, 29, 9, 3))
    pygame.draw.polygon(s, OUTLINE, [(3, 11), (5, 2), (11, 2), (13, 11)])
    pygame.draw.polygon(s, (250, 236, 190), [(4, 10), (6, 3), (10, 3), (12, 10)])
    return s


def trophy_shelf(ch=None):
    """Estante de troféus (4 x 2) na parede: 1 troféu por título do Coliseu (até 8) e medalhas dos mestres."""
    s = _surface(4, 2)
    w = s.get_width()
    wins = min(8, getattr(ch, "coliseum_wins", 0))
    beaten = set(getattr(ch, "beaten", []))
    for y in (14, 30):                                    # duas prateleiras
        _box(s, (0, y - 2, w, 4), WALNUT[1])
    for i in range(8):                                    # troféus (os que faltam aparecem só como sombra)
        x, y = 4 + (i % 4) * 15, 1 if i < 4 else 17
        if i < wins:
            pygame.draw.polygon(s, OUTLINE, [(x, y), (x + 9, y), (x + 8, y + 6), (x + 6, y + 8), (x + 6, y + 10),
                                             (x + 8, y + 11), (x + 1, y + 11), (x + 3, y + 10), (x + 3, y + 8),
                                             (x + 1, y + 6)])
            pygame.draw.polygon(s, GOLD[1], [(x + 1, y + 1), (x + 8, y + 1), (x + 7, y + 5), (x + 5, y + 7),
                                             (x + 4, y + 7), (x + 2, y + 5)])
            pygame.draw.line(s, GOLD[2], (x + 2, y + 2), (x + 3, y + 4))
            pygame.draw.rect(s, GOLD[0], (x + 2, y + 10, 6, 1))
        else:
            pygame.draw.rect(s, shade(WALNUT[0], -10), (x + 3, y + 8, 4, 3))
    for i, (who, color) in enumerate((("rafa", (200, 200, 210)), ("lia", (236, 188, 60)), ("zeca", (120, 200, 240)))):
        if who in beaten:                                 # medalhas dos mestres vencidos, penduradas na lateral
            cx = w - 4
            pygame.draw.line(s, RED[1], (cx, 2 + i * 9), (cx, 5 + i * 9))
            pygame.draw.circle(s, OUTLINE, (cx, 8 + i * 9), 3)
            pygame.draw.circle(s, color, (cx, 8 + i * 9), 2)
    return s


def toilet():
    s = _surface(1, 2)
    _box(s, (3, 6, 10, 10), WHITE[2], 2)                 # caixa acoplada na parede
    pygame.draw.rect(s, CHROME[1], (7, 8, 3, 1))
    pygame.draw.ellipse(s, OUTLINE, (2, 15, 12, 14))
    pygame.draw.ellipse(s, WHITE[2], (3, 16, 10, 12))
    pygame.draw.ellipse(s, (210, 226, 236), (5, 18, 6, 7))
    return s


def bath_sink():
    s = _surface(1, 2)
    _box(s, (2, 1, 12, 11), (200, 230, 240), 2)          # espelho
    pygame.draw.line(s, (240, 250, 255), (4, 9), (9, 3))
    _box(s, (1, 16, 14, 6), WHITE[2], 2)                 # cuba
    pygame.draw.line(s, CHROME[1], (8, 14), (8, 17))
    pygame.draw.rect(s, WHITE[1], (6, 22, 4, 9))         # coluna
    pygame.draw.rect(s, OUTLINE, (5, 22, 1, 9))
    pygame.draw.rect(s, OUTLINE, (10, 22, 1, 9))
    return s


def closet():
    """Closet (3 x 3): guarda-roupa de madeira com espelho no meio; dentro, as roupas."""
    s = _surface(3, 3)
    _box(s, (0, 4, 48, 44), WALNUT[1], 2)
    pygame.draw.rect(s, WALNUT[0], (0, 2, 48, 4))
    for x in (16, 32):
        pygame.draw.line(s, OUTLINE, (x, 6), (x, 46))
    _box(s, (19, 9, 10, 32), (200, 230, 240), 1)          # espelho
    pygame.draw.line(s, (240, 250, 255), (21, 36), (26, 14))
    for i, color in enumerate(((220, 70, 60), (60, 110, 200), (240, 200, 70), (40, 40, 48))):   # roupas na porta aberta
        pygame.draw.rect(s, color, (3 + i * 3, 12, 3, 14))
    pygame.draw.line(s, CHROME[1], (2, 11), (14, 11))
    for x in (14, 34):
        _handle(s, x, 24, 5, vertical=True)
    pygame.draw.rect(s, WALNUT[0], (2, 44, 44, 4))
    return s


def nightstand():
    s = _surface(1, 2)
    _box(s, (1, 17, 14, 15), WALNUT[1], 1)
    _handle(s, 6, 23, 4)
    pygame.draw.line(s, (60, 60, 70), (8, 10), (8, 17))   # abajur
    pygame.draw.polygon(s, OUTLINE, [(3, 11), (5, 4), (11, 4), (13, 11)])
    pygame.draw.polygon(s, (250, 236, 190), [(4, 10), (6, 5), (10, 5), (12, 10)])
    return s


def bed(w=3, duvet=((60, 90, 150), (90, 124, 190), (140, 170, 220))):
    """Cama vista de cima: cabeceira estofada na parede, travesseiros, lençol branco e edredom."""
    s = _surface(w, 3)
    width = s.get_width()
    _box(s, (0, 3, width, 16), (150, 136, 124), 3)        # cabeceira
    for x in range(6, width - 4, 8):
        s.set_at((x, 10), (120, 106, 96))
    _box(s, (2, 14, width - 4, 31), (246, 246, 244), 2)   # colchão com lençol
    pillows = 2 if w >= 3 else 1
    pw = (width - 12) // pillows
    for i in range(pillows):
        _box(s, (5 + i * (pw + 2), 16, pw, 8), (252, 252, 250), 3)
    _box(s, (2, 26, width - 4, 19), duvet[1], 2)          # edredom dobrado
    pygame.draw.line(s, duvet[2], (4, 27), (width - 5, 27), 2)
    pygame.draw.line(s, duvet[0], (4, 43), (width - 5, 43))
    pygame.draw.rect(s, OUTLINE, (1, 44, width - 2, 4))
    return s


def bed_facing_tv(w=4):
    """Cama de casal com a CABECEIRA EMBAIXO (quem deita olha para a TV na parede): pé da cama em cima,
    edredom, travesseiros embaixo e a cabeceira estofada."""
    s = _surface(w, 3)
    width = s.get_width()
    _box(s, (0, 0, width, 6), WALNUT[1], 2)               # pé da cama
    _box(s, (2, 4, width - 4, 36), (246, 246, 244), 2)    # colchão com lençol
    _box(s, (2, 4, width - 4, 25), (90, 124, 190), 2)     # edredom
    pygame.draw.line(s, (140, 170, 220), (4, 26), (width - 5, 26), 2)
    for x in range(10, width - 6, 14):
        pygame.draw.line(s, (60, 90, 150), (x, 8), (x + 4, 22))
    half = (width - 8) // 2
    for i in range(2):                                    # travesseiros
        _box(s, (4 + i * (half + 1), 29, half - 1, 9), (252, 252, 250), 3)
    _box(s, (0, 38, width, 10), (150, 136, 124), 3)       # cabeceira
    for x in range(6, width - 4, 8):
        s.set_at((x, 43), (120, 106, 96))
    return s


def tv_big(w=6):
    """TV grande de parede (6 x 2): tela larga com borda fina e uma barra de som embaixo."""
    s = _surface(w, 2)
    width = s.get_width()
    pygame.draw.rect(s, (24, 24, 30), (1, 1, width - 2, 29), border_radius=2)
    pygame.draw.rect(s, OUTLINE, (1, 1, width - 2, 29), 1, border_radius=2)
    pygame.draw.rect(s, (20, 30, 50), TV_BIG_SCREEN)
    s.set_at((width - 6, 27), (90, 230, 120))
    return s


def tv_small():
    s = _surface(2, 2)
    pygame.draw.rect(s, (24, 24, 30), (1, 2, 30, 20), border_radius=2)
    pygame.draw.rect(s, OUTLINE, (1, 2, 30, 20), 1, border_radius=2)
    pygame.draw.rect(s, (20, 30, 50), TV_SMALL_SCREEN)
    s.set_at((28, 20), (90, 230, 120))
    return s


def dresser():
    s = _surface(2, 2)
    _box(s, (0, 12, 32, 20), WALNUT[1], 1)
    for y in (18, 24):
        pygame.draw.line(s, WALNUT[0], (1, y), (30, y))
    for y in (15, 21, 27):
        _handle(s, 14, y, 4)
    _box(s, (4, 4, 7, 8), (250, 230, 200), 1)             # porta-retrato
    _box(s, (20, 6, 6, 6), (240, 140, 180), 2)            # caixinha
    return s


def vanity():
    """Pia dupla do banheiro da suíte: espelho largo na parede, bancada com duas cubas e gabinete."""
    s = _surface(2, 2)
    _box(s, (1, 1, 30, 11), (200, 230, 240), 1)
    pygame.draw.line(s, (240, 250, 255), (4, 9), (9, 3))
    pygame.draw.line(s, (240, 250, 255), (20, 9), (25, 3))
    _box(s, (0, 14, 32, 6), QUARTZ[1])
    for cx in (8, 24):
        pygame.draw.ellipse(s, (240, 244, 248), (cx - 4, 15, 9, 4))
        pygame.draw.line(s, CHROME[1], (cx, 12), (cx, 15))
    _box(s, (1, 19, 30, 13), WHITE[1])
    pygame.draw.line(s, WHITE[0], (16, 20), (16, 30))
    return s


def shower():
    """Box de vidro (2 x 3): chuveiro na parede, piso do box e vidro transparente com reflexo."""
    s = _surface(2, 3)
    pygame.draw.rect(s, (180, 200, 214), (1, 14, 30, 33))   # piso do box
    for y in range(18, 46, 6):
        pygame.draw.line(s, (160, 180, 196), (2, y), (29, y))
    pygame.draw.line(s, CHROME[0], (10, 4), (10, 12), 2)     # chuveiro
    pygame.draw.rect(s, CHROME[1], (7, 11, 8, 3))
    for x in range(8, 15, 2):
        s.set_at((x, 15), (150, 210, 240))
    s.blit(shower_glass(), (0, SHOWER["glass"][0]))
    return s


def shower_glass():
    """Só o vidro do box (transparente), para desenhar POR CIMA de quem está tomando banho."""
    top, bottom = SHOWER["glass"]
    s = pygame.Surface((2 * TILE, bottom - top), pygame.SRCALPHA)
    s.fill((200, 236, 250, 80), (1, 1, 30, bottom - top - 2))
    pygame.draw.rect(s, CHROME[0], s.get_rect(), 1)
    pygame.draw.line(s, (250, 255, 255), (5, 31), (14, 5))
    pygame.draw.line(s, CHROME[0], (16, 1), (16, 33))
    pygame.draw.line(s, CHROME[1], (19, 13), (19, 19), 2)    # puxador
    return s


def bathtub():
    s = _surface(3, 2)
    _box(s, (0, 2, 48, 28), WHITE[2], 8)
    pygame.draw.rect(s, (150, 206, 236), (4, 6, 40, 20), border_radius=6)
    for cx, cy in ((12, 10), (18, 14), (30, 9), (36, 16), (24, 20)):   # espuma
        pygame.draw.circle(s, (252, 252, 255), (cx, cy), 3)
    pygame.draw.line(s, CHROME[1], (42, 2), (42, 6), 2)
    return s


FURNITURE = {
    "kitchen_counter": kitchen_counter,
    "fridge": fridge,
    "island": island,
    "stool": stool,
    "dining_table": dining_table,
    "dchair_d": dchair_down,
    "dchair_u": dchair_up,
    "dchair_r": lambda: dchair_side(True),
    "dchair_l": lambda: dchair_side(False),
    "sideboard": sideboard,
    "tv_rack": tv_rack,
    "coffee_table": coffee_table,
    "sofa": sofa,
    "floor_lamp": floor_lamp,
    "toilet": toilet,
    "bath_sink": bath_sink,
    "closet": closet,
    "nightstand": nightstand,
    "bed_double": bed_facing_tv,
    "tv_big": tv_big,
    "bed_single": lambda: bed(2, ((60, 120, 80), (90, 160, 110), (150, 200, 160))),
    "tv_small": tv_small,
    "dresser": dresser,
    "vanity": vanity,
    "shower": shower,
    "bathtub": bathtub,
}
FROM_CHARACTER = {"trophy_shelf": trophy_shelf}        # móveis desenhados a partir do personagem
GROUNDS = {
    "casa_terreo": lambda grid: ground(grid, GROUND_DECOR),
    "casa_superior": lambda grid: ground(grid, UPPER_DECOR),
}

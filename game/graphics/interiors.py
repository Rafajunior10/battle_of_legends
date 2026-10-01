"""Interiores desenhados por código: o chão e as paredes de cada interior, e os móveis da lanchonete.

Mesmo estilo de buildings.py: contorno escuro (OUTLINE) e 3-4 tons por cor. Tudo aqui é desenhado UMA vez
(o lobby guarda o chão pronto e cada móvel vira uma figura do mapa); o que mexe a cada quadro é só a
tela da TV, que troca entre canais prontos (`tv_channels`).
"""
from __future__ import annotations

import pygame

from game.engine.settings import TILE
from game.engine.ui import draw_text
from game.graphics.buildings import OUTLINE, plaque, shade

WALL_FACE = (246, 234, 208)
WALL_TOP = ((34, 52, 62), (58, 82, 94))          # topo das paredes vistas de cima: escuro, borda
RED = ((150, 34, 34), (214, 58, 52), (240, 104, 92))
TEAL = ((32, 112, 110), (56, 168, 160), (120, 210, 196))
WOOD = ((150, 96, 60), (186, 128, 82), (206, 152, 102))
CHROME = ((120, 126, 140), (190, 196, 206), (236, 240, 246))
CHECKER = ((236, 232, 222), (52, 56, 70))
TV_SCREEN = pygame.Rect(5, 4, 54, 22)             # tela dentro do desenho da TV (para o lobby animar)


def _box(s, rect, color, radius=0):
    """Retângulo com contorno de 1 px."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(s, OUTLINE, rect, border_radius=radius)
    pygame.draw.rect(s, color, rect.inflate(-2, -2), border_radius=max(0, radius - 1))


# ============================================================ chão e paredes
def cafe_ground(w: int, h: int, exit_x: int) -> pygame.Surface:
    """Lanchonete: piso de tábuas, xadrez no balcão, tapetes, parede do fundo decorada e paredes laterais."""
    s = pygame.Surface((w * TILE, h * TILE))
    width, height = w * TILE, h * TILE
    floor = pygame.Rect(TILE, 3 * TILE, width - 2 * TILE, height - 4 * TILE)
    _wood_floor(s, floor)
    _checker(s, pygame.Rect(TILE, 3 * TILE, 12 * TILE, 4 * TILE))
    _rug(s, pygame.Rect(16 * TILE + 8, 5 * TILE + 4, 6 * TILE, 2 * TILE + 4), TEAL, (250, 214, 96))
    green = ((24, 84, 52), (40, 120, 72), (80, 160, 104))
    _rug(s, pygame.Rect(2 * TILE + 8, 9 * TILE + 4, 6 * TILE, 3 * TILE + 4), green, (240, 200, 90))
    _back_wall(s, width)
    for x in (0, width - TILE):                                     # paredes laterais (vistas de cima)
        pygame.draw.rect(s, WALL_TOP[0], (x, 0, TILE, height))
        edge = x + TILE - 2 if x == 0 else x
        pygame.draw.rect(s, WALL_TOP[1], (edge, 3 * TILE, 2, height - 4 * TILE))
    pygame.draw.rect(s, WALL_TOP[0], (0, height - TILE, width, TILE))    # parede de baixo, com a porta
    pygame.draw.line(s, WALL_TOP[1], (TILE, height - TILE), (width - TILE, height - TILE), 2)
    door = pygame.Rect(exit_x * TILE, height - TILE, 2 * TILE, TILE)
    _wood_floor(s, door)
    for i, y in enumerate(range(door.y + 2, door.bottom - 2, 3)):    # capacho listrado
        pygame.draw.line(s, (120, 70, 44) if i % 2 else (160, 100, 60), (door.x + 3, y), (door.right - 4, y), 2)
    for px in (door.x - 2, door.right):                              # batentes da porta
        pygame.draw.rect(s, CHROME[1], (px, door.y, 2, TILE))
    return s


def _wood_floor(s, rect):
    """Tábuas na horizontal: 8 px de altura, emendas desencontradas."""
    for row, y in enumerate(range(rect.y, rect.bottom, 8)):
        pygame.draw.rect(s, WOOD[1] if row % 2 else WOOD[2], (rect.x, y, rect.w, 8))
        pygame.draw.line(s, WOOD[0], (rect.x, y + 7), (rect.right - 1, y + 7))
        for x in range(rect.x + (row * 13) % 40, rect.right, 40):
            pygame.draw.line(s, WOOD[0], (x, y), (x, y + 6))


def _checker(s, rect):
    for y in range(rect.y, rect.bottom, 8):
        for x in range(rect.x, rect.right, 8):
            color = CHECKER[((x - rect.x) // 8 + (y - rect.y) // 8) % 2]
            pygame.draw.rect(s, color, (x, y, 8, 8))


def _rug(s, rect, colors, trim):
    pygame.draw.rect(s, OUTLINE, rect, border_radius=6)
    pygame.draw.rect(s, colors[1], rect.inflate(-2, -2), border_radius=5)
    pygame.draw.rect(s, trim, rect.inflate(-8, -8), 1, border_radius=4)
    for x in range(rect.x + 10, rect.right - 10, 12):
        pygame.draw.rect(s, colors[2], (x, rect.centery - 1, 4, 3))
    pygame.draw.line(s, colors[0], (rect.x + 4, rect.bottom - 3), (rect.right - 5, rect.bottom - 3))


def _back_wall(s, width):
    """Parede do fundo (3 tiles): papel de parede, faixa vermelha, rodapé de azulejo e a decoração."""
    pygame.draw.rect(s, WALL_TOP[0], (0, 0, width, 4))
    for x in range(TILE, width - TILE):
        pygame.draw.line(s, WALL_FACE if (x // 8) % 2 else shade(WALL_FACE, -10), (x, 4), (x, 37))
    pygame.draw.rect(s, RED[1], (TILE, 24, width - 2 * TILE, 4))
    pygame.draw.line(s, RED[2], (TILE, 24), (width - TILE - 1, 24))
    for x in range(TILE, width - TILE, 8):                          # azulejos verde-água embaixo
        pygame.draw.rect(s, TEAL[1], (x, 38, 8, 10))
        pygame.draw.line(s, TEAL[2], (x, 38), (x + 6, 38))
        pygame.draw.line(s, TEAL[0], (x + 7, 38), (x + 7, 47))
    pygame.draw.line(s, OUTLINE, (TILE, 47), (width - TILE - 1, 47))
    _menu_board(s, pygame.Rect(TILE + 26, 3, 10 * TILE - 30, 31))
    _shelf(s, pygame.Rect(TILE, 39, 10 * TILE, 9))
    _neon(s, 222, 8, "CAFÉ")
    _clock(s, 270, 14)
    _window(s, pygame.Rect(24 * TILE + 4, 6, 3 * TILE + 8, 26))


def _shelf(s, rect):
    """Bancada do fundo, atrás da atendente (na frente da lousa): máquina de café, copos, bolo e pães."""
    pygame.draw.rect(s, OUTLINE, rect)
    pygame.draw.rect(s, WOOD[0], rect.inflate(-2, -2))
    pygame.draw.line(s, WOOD[2], (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1))
    base = rect.y + 1
    _box(s, (rect.x + 8, base - 14, 18, 16), CHROME[1], 2)              # máquina de café
    pygame.draw.rect(s, OUTLINE, (rect.x + 11, base - 11, 12, 5))
    s.set_at((rect.x + 13, base - 9), (240, 80, 70))
    pygame.draw.rect(s, (90, 56, 40), (rect.x + 14, base - 4, 6, 4))
    for i in range(4):                                                    # copos
        cx = rect.x + 34 + i * 7
        _box(s, (cx, base - 7, 6, 8), (250, 250, 246))
        pygame.draw.line(s, RED[1], (cx + 1, base - 4), (cx + 4, base - 4))
    _box(s, (rect.x + 70, base - 7, 22, 8), (250, 236, 224), 3)        # bolo
    pygame.draw.rect(s, (240, 140, 170), (rect.x + 71, base - 6, 20, 3))
    _box(s, (rect.x + 100, base - 5, 24, 6), (176, 120, 64), 3)         # cesta de pães
    for i in range(3):
        pygame.draw.ellipse(s, (232, 176, 96), (rect.x + 102 + i * 7, base - 7, 7, 4))


def _menu_board(s, rect):
    """Cardápio de lousa com moldura de madeira (os preços vêm de data/food.py)."""
    from game.data.food import MENU
    pygame.draw.rect(s, OUTLINE, rect.inflate(4, 4))
    pygame.draw.rect(s, WOOD[1], rect.inflate(2, 2))
    pygame.draw.rect(s, (40, 46, 52), rect)
    draw_text(s, "CARDÁPIO", (rect.centerx, rect.y + 1), size=8, color=(250, 214, 96), shadow=None, align="center")
    col_w = rect.w // 2
    for i, item in enumerate(MENU):
        x = rect.x + 4 + (i % 2) * col_w
        y = rect.y + 9 + (i // 2) * 7
        draw_text(s, item.name, (x, y), size=8, color=(240, 240, 236), shadow=None)
        draw_text(s, str(item.price), (x + col_w - 8, y), size=8, color=(130, 220, 140), shadow=None, align="right")


def _neon(s, x, y, text):
    """Letreiro de neon rosa (com um "brilho" mais escuro em volta)."""
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        draw_text(s, text, (x + dx, y + dy), size=16, color=(170, 40, 110), shadow=None)
    draw_text(s, text, (x, y), size=16, color=(255, 150, 214), shadow=None)


def _clock(s, cx, cy):
    pygame.draw.circle(s, OUTLINE, (cx, cy), 7)
    pygame.draw.circle(s, (250, 250, 246), (cx, cy), 6)
    pygame.draw.line(s, OUTLINE, (cx, cy), (cx, cy - 4))
    pygame.draw.line(s, OUTLINE, (cx, cy), (cx + 3, cy))


def _window(s, rect):
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2))
    pygame.draw.rect(s, (250, 250, 246), rect)
    glass = rect.inflate(-4, -4)
    for i in range(glass.h):                                             # céu em degradê
        pygame.draw.line(s, (120 + i * 3, 190 + i, 240), (glass.x, glass.y + i), (glass.right - 1, glass.y + i))
    pygame.draw.ellipse(s, (64, 150, 80), (glass.x - 4, glass.bottom - 8, 26, 14))   # árvore lá fora
    pygame.draw.ellipse(s, (250, 250, 250), (glass.right - 22, glass.y + 3, 14, 6))  # nuvem
    pygame.draw.line(s, (250, 250, 246), (glass.centerx, glass.y), (glass.centerx, glass.bottom - 1), 2)
    for cx in (rect.x - 1, rect.right - 4):                              # cortinas
        pygame.draw.rect(s, RED[1], (cx, rect.y - 1, 5, rect.h + 2))
        pygame.draw.line(s, RED[0], (cx + 3, rect.y), (cx + 3, rect.bottom))


# ============================================================ móveis
def counter() -> pygame.Surface:
    """Balcão 10 x 2: tampo de mármore, frente vermelha com faixa branca e o que fica em cima."""
    s = pygame.Surface((10 * TILE, 2 * TILE), pygame.SRCALPHA)
    w = s.get_width()
    _box(s, (0, 2, w, 12), (236, 236, 242))
    pygame.draw.line(s, (252, 252, 255), (2, 4), (w - 3, 4))
    for x in range(10, w - 4, 26):                                       # veios do mármore
        pygame.draw.line(s, (210, 210, 220), (x, 7), (x + 8, 10))
    _box(s, (0, 13, w, 19), RED[1])
    pygame.draw.rect(s, (250, 246, 236), (1, 20, w - 2, 3))
    pygame.draw.rect(s, CHROME[1], (1, 28, w - 2, 3))
    pygame.draw.line(s, CHROME[2], (1, 28), (w - 2, 28))
    for x in range(32, w, 32):
        pygame.draw.line(s, RED[0], (x, 14), (x, 27))
    # em cima do balcão
    pygame.draw.ellipse(s, OUTLINE, (10, 0, 22, 12))                     # redoma de rosquinhas
    pygame.draw.ellipse(s, (200, 230, 240), (11, 1, 20, 10))
    for dx, color in ((14, (240, 150, 180)), (21, (180, 120, 70))):
        pygame.draw.circle(s, color, (dx + 1, 8), 3)
        s.set_at((dx + 1, 8), (236, 236, 242))
    _box(s, (66, 0, 14, 9), (90, 96, 110), 2)                            # caixa registradora
    pygame.draw.rect(s, (120, 230, 150), (68, 2, 6, 3))
    pygame.draw.ellipse(s, OUTLINE, (100, 3, 22, 9))                     # fruteira
    pygame.draw.ellipse(s, (240, 240, 236), (101, 4, 20, 7))
    for cx in (105, 111):
        pygame.draw.circle(s, RED[1], (cx, 4), 3)
    pygame.draw.arc(s, (250, 210, 60), (112, 0, 10, 8), 3.4, 6.0, 2)
    for i, color in enumerate(((220, 50, 40), (250, 200, 40))):        # ketchup e mostarda
        _box(s, (136 + i * 6, 0, 5, 10), color, 1)
    return s


def soda_fridge() -> pygame.Surface:
    s = pygame.Surface((2 * TILE, 3 * TILE), pygame.SRCALPHA)
    _box(s, (1, 0, 30, 47), (236, 238, 244), 2)
    pygame.draw.rect(s, RED[1], (2, 1, 28, 8))
    draw_text(s, "REFRI", (16, 2), size=8, color=(255, 255, 255), shadow=None, align="center")
    glass = pygame.Rect(4, 11, 24, 32)
    pygame.draw.rect(s, OUTLINE, glass.inflate(2, 2))
    pygame.draw.rect(s, (170, 220, 236), glass)
    cans = ((214, 58, 52), (60, 170, 80), (250, 150, 40))
    for row in range(3):
        y = glass.y + 3 + row * 10
        pygame.draw.line(s, CHROME[0], (glass.x, y + 7), (glass.right - 1, y + 7))
        for i in range(4):
            pygame.draw.rect(s, cans[(row + i) % 3], (glass.x + 2 + i * 6, y, 4, 7))
            s.set_at((glass.x + 3 + i * 6, y + 1), (255, 255, 255))
    pygame.draw.line(s, (240, 250, 255), (glass.x + 2, glass.bottom - 3), (glass.right - 8, glass.y + 2))
    pygame.draw.rect(s, CHROME[0], (26, 22, 2, 10))
    return s


def freezer() -> pygame.Surface:
    s = pygame.Surface((2 * TILE, 2 * TILE), pygame.SRCALPHA)
    _box(s, (1, 10, 30, 22), (246, 248, 250), 2)
    pygame.draw.rect(s, TEAL[1], (2, 22, 28, 4))
    _box(s, (2, 6, 28, 8), (180, 226, 240), 2)                          # tampa de vidro
    for i, color in enumerate(((120, 70, 40), (250, 170, 196), (250, 246, 230), (120, 70, 40))):
        pygame.draw.rect(s, color, (5 + i * 6, 8, 5, 4))
    draw_text(s, "SORVETE", (16, 0), size=8, color=(214, 58, 52), shadow=(250, 250, 250), align="center")
    return s


def tv() -> pygame.Surface:
    """TV de tela plana presa na parede (a tela em si é desenhada a cada quadro pelo lobby)."""
    s = pygame.Surface((4 * TILE, 2 * TILE), pygame.SRCALPHA)
    pygame.draw.rect(s, (24, 24, 30), (1, 1, 62, 29), border_radius=3)
    pygame.draw.rect(s, OUTLINE, (1, 1, 62, 29), 1, border_radius=3)
    pygame.draw.rect(s, (20, 30, 50), TV_SCREEN)
    s.set_at((58, 27), (90, 230, 120))                                  # luz de ligada
    pygame.draw.rect(s, (60, 60, 70), (28, 30, 8, 2))
    return s


def tv_channels() -> list[pygame.Surface]:
    """Os 3 canais da TV (mesma ordem de world.TV_SHOWS): coliseu ao vivo, tempo e carta do dia."""
    w, h = TV_SCREEN.size
    live = pygame.Surface((w, h))
    live.fill((110, 180, 240))
    pygame.draw.rect(live, (220, 190, 130), (0, 13, w, h - 13))
    pygame.draw.ellipse(live, (190, 160, 110), (6, 15, w - 12, 6))
    for x, color in ((16, (214, 58, 52)), (36, (56, 120, 232))):        # dois duelistas
        pygame.draw.rect(live, color, (x, 9, 4, 7))
        pygame.draw.circle(live, (240, 200, 160), (x + 2, 8), 2)
    pygame.draw.rect(live, (255, 240, 120), (26, 9, 3, 4))              # a carta voando
    draw_text(live, "AO VIVO", (3, 1), size=8, color=(255, 255, 255), shadow=(160, 20, 20))
    weather = pygame.Surface((w, h))
    weather.fill((40, 90, 170))
    pygame.draw.circle(weather, (255, 210, 60), (14, 11), 6)
    pygame.draw.ellipse(weather, (240, 244, 250), (20, 9, 16, 7))
    draw_text(weather, "SOL", (38, 2), size=8, color=(255, 255, 255), shadow=None)
    draw_text(weather, "28", (38, 10), size=8, color=(255, 230, 120), shadow=None)
    card = pygame.Surface((w, h))
    card.fill((70, 40, 120))
    pygame.draw.rect(card, (255, 230, 120), (5, 3, 12, 17))
    pygame.draw.rect(card, (90, 60, 160), (6, 4, 10, 15))
    pygame.draw.polygon(card, (255, 230, 80), [(12, 6), (8, 12), (11, 12), (9, 17), (14, 10), (11, 10)])
    draw_text(card, "CARTA", (22, 3), size=8, color=(255, 255, 255), shadow=None)
    draw_text(card, "DO DIA", (22, 11), size=8, color=(255, 230, 120), shadow=None)
    return [live, weather, card]


def puff(color) -> pygame.Surface:
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.ellipse(s, OUTLINE, (1, 3, 14, 13))
    pygame.draw.ellipse(s, color, (2, 4, 12, 11))
    pygame.draw.ellipse(s, shade(color, 40), (4, 5, 6, 4))
    pygame.draw.arc(s, shade(color, -50), (3, 7, 10, 7), 3.5, 6.0)
    return s


def chair(facing_right=True) -> pygame.Surface:
    """Cadeira de lanchonete (1 x 2): encosto alto atrás, assento vermelho e pés cromados."""
    s = pygame.Surface((TILE, 2 * TILE), pygame.SRCALPHA)
    _box(s, (1, 10, 5, 17), RED[1], 2)                                  # encosto (à esquerda)
    pygame.draw.line(s, RED[2], (2, 12), (2, 24))
    _box(s, (2, 21, 13, 6), RED[1], 2)                                  # assento
    pygame.draw.line(s, RED[2], (4, 22), (13, 22))
    for x in (4, 12):
        pygame.draw.line(s, CHROME[0], (x, 27), (x, 31))
    return s if facing_right else pygame.transform.flip(s, True, False)


def table() -> pygame.Surface:
    s = pygame.Surface((2 * TILE, 2 * TILE), pygame.SRCALPHA)
    _box(s, (1, 2, 30, 18), (250, 248, 240), 4)
    pygame.draw.rect(s, RED[1], (2, 15, 28, 4))                          # borda vermelha
    pygame.draw.rect(s, CHROME[1], (14, 20, 4, 9))
    pygame.draw.rect(s, OUTLINE, (9, 28, 14, 3))
    pygame.draw.circle(s, OUTLINE, (10, 9), 5)                           # prato com lanche
    pygame.draw.circle(s, (255, 255, 255), (10, 9), 4)
    pygame.draw.ellipse(s, (200, 130, 60), (7, 6, 7, 5))
    _box(s, (20, 4, 6, 9), (214, 58, 52), 1)                             # copo de refri
    pygame.draw.line(s, (255, 255, 255), (23, 1), (23, 5))
    return s


def trade_table() -> pygame.Surface:
    """Mesa de troca (3 x 2): feltro verde com borda dourada, montinhos de cartas e a plaquinha TROCA."""
    s = pygame.Surface((3 * TILE, 2 * TILE), pygame.SRCALPHA)
    _box(s, (1, 2, 46, 20), (176, 128, 70), 3)
    pygame.draw.rect(s, (40, 120, 72), (3, 4, 42, 15), border_radius=2)
    pygame.draw.rect(s, (240, 200, 90), (3, 4, 42, 15), 1, border_radius=2)
    for x, color in ((8, (214, 58, 52)), (34, (56, 120, 232))):         # montinho de cada jogador
        for i in range(3):
            _box(s, (x + i, 7 - i, 7, 9), color)
    for x, color in ((19, (250, 250, 240)), (25, (250, 220, 120))):     # cartas na mesa
        _box(s, (x, 8, 6, 8), color)
    pygame.draw.rect(s, OUTLINE, (2, 22, 44, 4))
    for x in (4, 41):
        pygame.draw.rect(s, WOOD[0], (x, 26, 3, 6))
    plaque(s, 24, 21, "TROCA", size=8)
    return s


def plant() -> pygame.Surface:
    s = pygame.Surface((TILE, 2 * TILE), pygame.SRCALPHA)
    for (x, y, w, h), color in ((((1, 6, 8, 12)), (40, 130, 70)), (((7, 3, 8, 13)), (60, 160, 84)),
                                (((3, 12, 10, 10)), (80, 180, 96))):
        pygame.draw.ellipse(s, OUTLINE, (x - 1, y - 1, w + 2, h + 2))
        pygame.draw.ellipse(s, color, (x, y, w, h))
    pygame.draw.line(s, (30, 100, 56), (8, 22), (8, 8))
    _box(s, (3, 21, 10, 10), (250, 250, 246), 2)                         # vaso branco
    pygame.draw.line(s, (220, 220, 214), (5, 27), (11, 27))
    return s


def jukebox() -> pygame.Surface:
    s = pygame.Surface((TILE, 2 * TILE), pygame.SRCALPHA)
    pygame.draw.rect(s, OUTLINE, (1, 2, 14, 30), border_radius=6)
    pygame.draw.rect(s, (120, 60, 40), (2, 3, 12, 28), border_radius=5)
    for i, color in enumerate(((240, 80, 80), (250, 180, 60), (250, 240, 100), (90, 210, 120), (90, 160, 250))):
        pygame.draw.arc(s, color, (3 + i, 4 + i, 10 - 2 * i, 12 - 2 * i), 0.1, 3.0, 1)
    pygame.draw.rect(s, (40, 40, 48), (4, 18, 8, 8))
    for y in range(19, 26, 2):
        pygame.draw.line(s, CHROME[0], (5, y), (10, y))
    pygame.draw.rect(s, CHROME[1], (3, 28, 10, 2))
    return s


FURNITURE = {
    "counter": counter,
    "soda_fridge": soda_fridge,
    "freezer": freezer,
    "tv": tv,
    "puff_red": lambda: puff(RED[1]),
    "puff_yellow": lambda: puff((240, 196, 60)),
    "puff_blue": lambda: puff((70, 120, 210)),
    "chair_r": lambda: chair(facing_right=True),
    "chair_l": lambda: chair(facing_right=False),
    "table": table,
    "trade_table": trade_table,
    "plant": plant,
    "jukebox": jukebox,
}
GROUNDS = {"lanchonete": cafe_ground}

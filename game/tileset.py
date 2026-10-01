"""Tiles do mapa em estilo 16 bits: mais tons por cor, pontilhado (dithering), variações e sombras.

Tudo é gerado uma vez (com sorteio fixo, então sempre sai igual) e guardado em cache.
"""
import random

import pygame

K = (40, 40, 48)   # contorno

# grama: do mais escuro ao mais claro
G0, G1, G2, G3, G4 = (56, 120, 64), (88, 160, 80), (120, 192, 96), (160, 220, 120), (200, 240, 152)
TALL0, TALL1, TALL2, TALL3 = (32, 96, 48), (56, 136, 64), (88, 176, 80), (136, 216, 112)
DIRT0, DIRT1, DIRT2, DIRT3 = (168, 128, 88), (200, 164, 112), (224, 196, 144), (240, 220, 176)
WATER0, WATER1, WATER2, WATER3 = (40, 88, 176), (56, 120, 208), (88, 152, 232), (168, 208, 248)
FOAM = (224, 240, 252)
WOOD0, WOOD1, WOOD2 = (96, 56, 32), (144, 96, 56), (192, 140, 88)
LEAF0, LEAF1, LEAF2, LEAF3 = (24, 72, 48), (40, 112, 64), (72, 152, 80), (128, 200, 104)
SHADOW = (24, 40, 32)

GRASS_VARIANTS = 3
_cache = {}


def _put(s, x, y, color):
    """set_at que dá a volta nas bordas: os padrões ficam contínuos entre tiles vizinhos."""
    s.set_at((x % 16, y % 16), color)


def _optimize(surf):
    if pygame.display.get_surface() is None:
        return surf
    return surf.convert_alpha() if surf.get_flags() & pygame.SRCALPHA else surf.convert()


# ------------------------------------------------------------ chão
def _grass(seed):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    s.fill(G2)
    for _ in range(3):   # manchas pontilhadas mais escuras
        cx, cy, r = rng.randrange(16), rng.randrange(16), rng.randint(2, 4)
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (x + y) % 2 == 0:
                    _put(s, x, y, G1)
    for _ in range(5):   # tufos: haste escura com ponta clara
        x, y = rng.randrange(16), rng.randrange(16)
        _put(s, x, y, G0)
        _put(s, x, y - 1, G1)
        _put(s, x + 1, y - 1, G0)
        _put(s, x - 1, y - 2, G3)
    for _ in range(4):
        _put(s, rng.randrange(16), rng.randrange(16), G3 if rng.random() < 0.7 else G4)
    return s


def _tall_grass(front_only):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    if not front_only:
        s.fill(TALL1)
        for y in range(16):
            for x in range(y % 2, 16, 2):
                if (x * 7 + y * 3) % 5 == 0:
                    s.set_at((x, y), TALL0)
    for row, (base_y, shift) in enumerate(((8, 2), (16, 0))):
        if front_only and row == 0:
            continue
        for i in range(-1, 4):
            x = i * 4 + shift
            pygame.draw.polygon(s, TALL0, [(x, base_y), (x + 2, base_y - 8), (x + 4, base_y)])
            pygame.draw.polygon(s, TALL2, [(x + 1, base_y), (x + 2, base_y - 6), (x + 3, base_y)])
            s.set_at((x + 2, base_y - 6), TALL3)
            s.set_at((x + 2, base_y - 5), TALL3)
    return s


def _path(seed):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    s.fill(DIRT2)
    for y in range(16):          # textura pontilhada suave
        for x in range((y // 2) % 2, 16, 4):
            if rng.random() < 0.5:
                s.set_at((x, y), DIRT1)
    for _ in range(4):           # pedrinhas com luz e sombra
        x, y = rng.randrange(1, 15), rng.randrange(1, 15)
        s.set_at((x, y), DIRT0)
        s.set_at((x + 1, y), DIRT0)
        s.set_at((x, y - 1), DIRT3)
    for _ in range(3):
        s.set_at((rng.randrange(16), rng.randrange(16)), DIRT3)
    return s


def _water(frame):
    s = pygame.Surface((16, 16))
    s.fill(WATER1)
    for y in range(9, 16):       # fundo mais escuro, misturado no pontilhado
        for x in range((y + frame) % 2, 16, 2 if y < 12 else 1):
            s.set_at((x, y), WATER0)
    for i, y in enumerate((3, 8, 13)):   # ondas andando
        x0 = (frame * 4 + i * 6) % 16
        for dx in range(5):
            s.set_at(((x0 + dx) % 16, y), WATER2)
        s.set_at(((x0 + 1) % 16, y - 1), WATER3)
        s.set_at(((x0 + 2) % 16, y - 1), WATER3)
    sparkle = ((frame * 5 + 3) % 16, (frame * 7 + 5) % 12)
    s.set_at(sparkle, (255, 255, 255))
    return s


def _flower(frame, seed):
    s = _grass(seed)
    petals = (((4, 5), (232, 72, 72)), ((11, 11), (248, 248, 248)), ((12, 3), (248, 200, 64)),
              ((5, 12), (120, 152, 248)))
    for (x, base_y), color in petals:
        y = base_y - frame   # a flor balança 1 pixel entre os quadros
        s.set_at((x, y + 2 + frame), G0)
        dark = tuple(max(0, c - 64) for c in color)
        for dx, dy in ((0, -1), (-1, 0), (1, 0)):
            s.set_at((x + dx, y + dy), color)
        s.set_at((x, y + 1), dark)
        s.set_at((x, y), (248, 232, 120))
    return s


# ------------------------------------------------------------ objetos
def _tree(seed):
    s = _grass(seed)
    shadow = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (*SHADOW, 90), (2, 11, 14, 5))   # sombra no chão, puxada para a direita
    s.blit(shadow, (0, 0))
    pygame.draw.rect(s, K, (6, 10, 5, 6))
    pygame.draw.rect(s, WOOD1, (7, 10, 3, 6))
    pygame.draw.line(s, WOOD2, (7, 11), (7, 15))
    pygame.draw.circle(s, K, (8, 7), 8)
    pygame.draw.circle(s, LEAF0, (8, 7), 7)
    pygame.draw.circle(s, LEAF1, (7, 6), 6)
    pygame.draw.circle(s, LEAF2, (6, 5), 4)
    pygame.draw.circle(s, LEAF3, (5, 4), 2)
    for x, y in ((10, 9), (12, 6), (4, 9), (9, 11)):   # folhas escuras em pontilhado na parte de baixo
        s.set_at((x, y), LEAF0)
    s.set_at((4, 3), (192, 232, 160))
    return s


def _fence(seed):
    s = _grass(seed)
    for y in (5, 10):
        pygame.draw.rect(s, WOOD0, (0, y - 1, 16, 3))
        pygame.draw.line(s, WOOD2, (0, y - 1), (15, y - 1))
        pygame.draw.line(s, WOOD1, (0, y), (15, y))
    for x in (2, 10):
        pygame.draw.rect(s, WOOD0, (x, 2, 4, 13))
        pygame.draw.rect(s, WOOD1, (x + 1, 3, 2, 11))
        pygame.draw.line(s, WOOD2, (x + 1, 3), (x + 1, 13))
        pygame.draw.line(s, SHADOW, (x + 4, 14), (x + 5, 14))
    return s


def _sign(seed):
    s = _grass(seed)
    pygame.draw.ellipse(s, G1, (3, 13, 11, 3))
    pygame.draw.rect(s, WOOD0, (6, 9, 4, 7))
    pygame.draw.rect(s, WOOD1, (7, 9, 2, 6))
    pygame.draw.rect(s, WOOD0, (1, 2, 14, 9))
    pygame.draw.rect(s, (216, 168, 104), (2, 3, 12, 7))
    pygame.draw.line(s, (240, 204, 144), (2, 3), (13, 3))
    pygame.draw.line(s, (176, 128, 72), (2, 9), (13, 9))
    for y in (5, 7):
        pygame.draw.line(s, (152, 104, 56), (4, y), (11, y))
    return s


def _bridge():
    """Ponte de tábuas atravessando o rio de norte a sul."""
    s = _water(0)
    pygame.draw.rect(s, WOOD0, (0, 0, 16, 16))
    for y in range(0, 16, 4):
        pygame.draw.rect(s, WOOD1, (1, y, 14, 3))
        pygame.draw.line(s, WOOD2, (1, y), (14, y))
        s.set_at((3, y + 1), WOOD0)
        s.set_at((12, y + 1), WOOD0)
    pygame.draw.line(s, K, (0, 0), (0, 15))       # corrimãos
    pygame.draw.line(s, K, (15, 0), (15, 15))
    return s


def _rock(seed):
    s = _grass(seed)
    pygame.draw.ellipse(s, (*SHADOW, 255), (2, 10, 14, 5))
    pygame.draw.ellipse(s, K, (2, 3, 13, 11))
    pygame.draw.ellipse(s, (120, 120, 136), (3, 4, 11, 9))
    pygame.draw.ellipse(s, (160, 160, 176), (4, 4, 7, 5))
    s.set_at((6, 5), (208, 208, 224))
    for x, y in ((10, 10), (12, 8), (8, 11)):
        s.set_at((x, y), (88, 88, 104))
    return s


def tiles():
    """Dicionário de tiles. "grass", "path", "tree", "fence" e "sign" são listas de variações."""
    if "tiles" not in _cache:
        variants = range(GRASS_VARIANTS)
        raw = {
            "grass": [_grass(10 + v) for v in variants],
            "path": [_path(20 + v) for v in variants],
            "tree": [_tree(30 + v) for v in variants],
            "fence": [_fence(40 + v) for v in variants],
            "sign": [_sign(50 + v) for v in variants],
            "tall": [_tall_grass(False)],
            "tall_front": [_tall_grass(True)],
            "water": [_water(i) for i in range(4)],
            "flower": [_flower(i, 60) for i in range(2)],
            "bridge": [_bridge()],
            "rock": [_rock(70 + v) for v in variants],
        }
        _cache["tiles"] = {name: [_optimize(s) for s in surfs] for name, surfs in raw.items()}
    return _cache["tiles"]


def variant(x, y):
    """Variação fixa de um tile pela posição (evita o padrão repetido de grade)."""
    return (x * 7 + y * 13 + (x * y) % 5) % GRASS_VARIANTS


def actor_shadow():
    """Sombra oval embaixo dos personagens."""
    if "actor_shadow" not in _cache:
        s = pygame.Surface((14, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*SHADOW, 80), s.get_rect())
        _cache["actor_shadow"] = _optimize(s)
    return _cache["actor_shadow"]


def draw_path_edges(surf, grid, path_tile="="):
    """Borda irregular de grama sobre o caminho, onde ele encosta em outro chão (feito uma vez no mapa)."""
    h, w = len(grid), len(grid[0])
    for ty in range(h):
        for tx in range(w):
            if grid[ty][tx] != path_tile:
                continue
            px, py = tx * 16, ty * 16
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = tx + dx, ty + dy
                if not (0 <= nx < w and 0 <= ny < h) or grid[ny][nx] == path_tile:
                    continue
                for i in range(16):
                    depth = 1 + (i * 5 + tx * 3 + ty) % 3 // 2   # 1 ou 2 pixels, irregular
                    for d in range(depth):
                        color = G1 if d == depth - 1 else G2
                        if dy:
                            y = py + (d if dy < 0 else 15 - d)
                            surf.set_at((px + i, y), color)
                        else:
                            x = px + (d if dx < 0 else 15 - d)
                            surf.set_at((x, py + i), color)


def shore_edges(grid, water_tile="W"):
    """Lista de bordas da água que encostam em terra: (x, y, direção)."""
    h, w = len(grid), len(grid[0])
    edges = []
    for ty in range(h):
        for tx in range(w):
            if grid[ty][tx] != water_tile:
                continue
            for side, (dx, dy) in (("up", (0, -1)), ("down", (0, 1)), ("left", (-1, 0)), ("right", (1, 0))):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] != water_tile:
                    edges.append((tx, ty, side))
    return edges


def draw_foam(surf, edges, cam, time):
    """Espuma branca na beira da água, piscando devagar."""
    phase = int(time * 3)
    for tx, ty, side in edges:
        x, y = tx * 16 - cam[0], ty * 16 - cam[1]
        if not (-16 < x < surf.get_width() and -16 < y < surf.get_height()):
            continue
        for i in range(0, 16, 2):
            if (i // 2 + phase + tx + ty) % 3 == 0:
                continue
            if side == "up":
                surf.set_at((x + i, y), FOAM)
            elif side == "down":
                surf.set_at((x + i, y + 15), FOAM)
            elif side == "left":
                surf.set_at((x, y + i), FOAM)
            else:
                surf.set_at((x + 15, y + i), FOAM)



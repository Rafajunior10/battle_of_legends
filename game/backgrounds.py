"""Cenários em estilo 16 bits: céu em degradê pontilhado, montanhas em camadas e nuvens com parallax.

O fundo parado é desenhado uma vez; por quadro só as nuvens andam (cada camada numa velocidade).
"""
import math

import pygame

from .settings import GAME_W
from .ui import dither_gradient

BATTLE_H = 168
SKY_TOP, SKY_BOTTOM = (88, 152, 224), (208, 232, 248)
FAR_HILLS, FAR_HILLS_LIGHT = (136, 176, 208), (168, 200, 224)
NEAR_HILLS, NEAR_HILLS_LIGHT = (96, 160, 104), (128, 192, 120)
FIELD_TOP, FIELD_BOTTOM = (168, 216, 128), (120, 184, 96)
PLATFORM = ((72, 128, 72), (112, 168, 88), (152, 204, 120), (192, 228, 152))   # do escuro ao claro

_cache = {}


def _ridge(surf, base_y, amplitude, period, phase, color, light):
    """Silhueta de morros com uma borda iluminada em cima."""
    points = [(0, BATTLE_H)]
    for x in range(0, GAME_W + 8, 4):
        y = base_y - amplitude * (0.6 * math.sin(x / period + phase) + 0.4 * math.sin(x / (period * 0.43) + phase * 2))
        points.append((x, int(y)))
    points.append((GAME_W, BATTLE_H))
    pygame.draw.polygon(surf, color, points)
    pygame.draw.lines(surf, light, False, points[1:-1], 1)


def _platform(surf, rect):
    """Plataforma oval com 4 tons e borda pontilhada, como nas batalhas de 16 bits."""
    rect = pygame.Rect(rect)
    dark, mid, light, top = PLATFORM
    pygame.draw.ellipse(surf, dark, rect)
    pygame.draw.ellipse(surf, mid, rect.inflate(-4, -6).move(0, -2))
    pygame.draw.ellipse(surf, light, rect.inflate(-14, -12).move(-2, -3))
    pygame.draw.ellipse(surf, top, rect.inflate(-rect.w // 2, -rect.h // 2 - 4).move(-8, -4))
    inner = rect.inflate(-4, -6).move(0, -2)
    for x in range(inner.left, inner.right, 2):   # pontilhado na transição do meio para a borda escura
        y = inner.centery + int(inner.h / 2 * math.sqrt(max(0.0, 1 - ((x - inner.centerx) / (inner.w / 2)) ** 2)))
        surf.set_at((x, y - 1), dark)


ENEMY_PLATFORM = pygame.Rect(292, 78, 124, 24)     # onde o oponente fica (os pés no meio da plataforma)
PLAYER_PLATFORM = pygame.Rect(34, 138, 150, 30)    # onde você fica


def battle_background():
    if "battle" not in _cache:
        bg = dither_gradient((GAME_W, BATTLE_H), SKY_TOP, SKY_BOTTOM, bands=10)
        _ridge(bg, 84, 16, 40, 0.5, FAR_HILLS, FAR_HILLS_LIGHT)
        _ridge(bg, 104, 9, 26, 2.1, NEAR_HILLS, NEAR_HILLS_LIGHT)
        field = dither_gradient((GAME_W, BATTLE_H - 108), FIELD_TOP, FIELD_BOTTOM, bands=6)
        bg.blit(field, (0, 108))
        for y in (114, 126, 142):   # sulcos no campo
            for x in range((y // 2) % 4, GAME_W, 4):
                bg.set_at((x, y), FIELD_BOTTOM)
        _platform(bg, ENEMY_PLATFORM)
        _platform(bg, PLAYER_PLATFORM)
        _cache["battle"] = bg.convert() if pygame.display.get_surface() else bg
    return _cache["battle"]


def cloud(size):
    """Nuvem fofa com sombra embaixo (3 tons)."""
    key = ("cloud", size)
    if key not in _cache:
        w, h = size
        s = pygame.Surface((w, h + 2), pygame.SRCALPHA)
        for color, dy in (((184, 208, 232), 2), ((232, 244, 252), 0)):
            pygame.draw.ellipse(s, color, (0, h // 3 + dy, w, h * 2 // 3))
            pygame.draw.ellipse(s, color, (w // 5, dy, w // 2, h * 3 // 4))
            pygame.draw.ellipse(s, color, (w // 2, h // 6 + dy, w * 2 // 5, h * 2 // 3))
        pygame.draw.ellipse(s, (255, 255, 255), (w // 4, 2, w // 4, h // 3))
        _cache[key] = s.convert_alpha() if pygame.display.get_surface() else s
    return _cache[key]


# (x inicial, y, largura, altura, velocidade em pixels por segundo) — mais longe = menor e mais lenta
CLOUDS = [(30, 10, 40, 12, 3.0), (150, 26, 30, 9, 2.0), (250, 6, 48, 14, 4.0), (90, 44, 22, 7, 1.5),
          (380, 18, 36, 11, 2.6), (440, 52, 26, 8, 1.2)]


def draw_clouds(surf, time):
    span = GAME_W + 60
    for x0, y, w, h, speed in CLOUDS:
        x = (x0 + time * speed) % span - 50
        surf.blit(cloud((w, h)), (int(x), y))

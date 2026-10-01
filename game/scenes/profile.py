"""Ficha do duelista: sobreposição desenhada por cima do lobby, com o TEMA do elemento do deck ativo.

Deck de Fogo = ficha em brasa com labaredas, Gelo = ficha congelada com pingentes e neve, e assim por diante.
O fundo decorado é desenhado UMA vez por tema e guardado (`_panels`); por quadro só desenhamos as
partículas animadas (brasas, flocos, faíscas, bolhas) e os textos.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game.data.character import deck_archetype
from game.data.legends import LEGENDS
from game.data.opponents import TRAINERS
from game.engine.config import action_label
from game.engine.settings import GAME_H, GAME_W
from game.engine.ui import dither_gradient, draw_outlined, draw_text, overlay, wrap
from game.graphics import pixelart as art
from game.graphics import sprites

BOX_W, BOX_H = 300, 214
BANNER = pygame.Rect(108, 8, BOX_W - 120, 20)     # à direita: o retrato (alto) fica à esquerda


@dataclass(frozen=True)
class Theme:
    title: str
    icon: str                   # ícone de game/graphics/pixelart.py
    top: tuple                  # degradê do fundo (cima -> baixo)
    bottom: tuple
    border: tuple               # moldura clara
    dark: tuple                 # contorno e placas
    label: tuple                # cor dos rótulos
    particle: tuple
    motion: str                 # "up" (sobe), "down" (cai) ou "flicker" (pisca)
    motif: str                  # decoração fixa: flames, icicles, bolts, drips, stars


THEMES = {
    "fogo": Theme("HERÓI DO FOGO", "flame", (110, 22, 14), (226, 92, 30), (255, 206, 84), (52, 10, 6),
                  (255, 214, 96), (255, 170, 48), "up", "flames"),
    "gelo": Theme("HERÓI DO GELO", "ice", (14, 44, 100), (90, 170, 228), (226, 248, 255), (10, 26, 60),
                  (176, 236, 255), (248, 252, 255), "down", "icicles"),
    "raio": Theme("HERÓI DO RAIO", "bolt", (34, 28, 66), (118, 96, 30), (255, 236, 96), (20, 16, 36),
                  (255, 232, 96), (255, 248, 160), "flicker", "bolts"),
    "veneno": Theme("HERÓI DO VENENO", "poison", (36, 14, 52), (110, 52, 150), (176, 236, 104), (22, 8, 32),
                    (196, 244, 120), (150, 230, 90), "up", "drips"),
}
NEUTRAL = Theme("DUELISTA", "star", (36, 52, 92), (92, 120, 168), (232, 232, 240), (20, 28, 52),
                (248, 216, 120), (255, 244, 180), "flicker", "stars")
TEXT = (250, 246, 236)

_panels: dict = {}


def theme_of(ch) -> Theme:
    """Tema da ficha = elemento do deck ativo (sem elemento ainda, a ficha neutra)."""
    return THEMES.get(deck_archetype(ch.deck), NEUTRAL)


def dim(surf):
    surf.blit(overlay((16, 16, 32), 150), (0, 0))


# ------------------------------------------------------------------ fundo decorado (desenhado uma vez)
def _flames(s, t: Theme, rng):
    for x in range(4, BOX_W - 4, 9):
        h = rng.randint(10, 22)
        base = BOX_H - 5
        pygame.draw.polygon(s, t.particle, [(x - 6, base), (x, base - h), (x + 6, base)])
        pygame.draw.polygon(s, (255, 236, 120), [(x - 3, base), (x, base - h // 2), (x + 3, base)])


def _icicles(s, t: Theme, rng):
    for x in range(8, BOX_W - 8, 10):
        h = rng.randint(6, 16)
        pygame.draw.polygon(s, (190, 232, 252), [(x - 4, 5), (x + 4, 5), (x, 5 + h)])
        pygame.draw.line(s, (255, 255, 255), (x - 2, 6), (x, 4 + h))
    for x, y in ((24, BOX_H - 22), (BOX_W - 26, BOX_H - 24)):
        _snowflake(s, x, y, (226, 246, 255), 5)


def _snowflake(s, x, y, color, r):
    for a in range(0, 180, 60):
        dx, dy = round(math.cos(math.radians(a)) * r), round(math.sin(math.radians(a)) * r)
        pygame.draw.line(s, color, (x - dx, y - dy), (x + dx, y + dy))


def _bolt(s, x, y, size, color):
    pts = [(x, y), (x + size, y), (x + size // 3, y + size), (x + size, y + size),
           (x - size // 3, y + size * 2 + 2), (x + size // 6, y + size + 3), (x - size // 3, y + size + 3)]
    pygame.draw.polygon(s, (40, 30, 10), [(px + 1, py + 1) for px, py in pts])
    pygame.draw.polygon(s, color, pts)


def _bolts(s, t: Theme, rng):
    for x, y in ((12, BOX_H - 38), (BOX_W - 26, BOX_H - 40), (BOX_W // 2 - 4, BOX_H - 24)):
        _bolt(s, x, y, 10, t.border)


def _drips(s, t: Theme, rng):
    for x in range(10, BOX_W - 10, 13):
        h = rng.randint(4, 14)
        pygame.draw.rect(s, t.particle, (x - 2, 5, 4, h))
        pygame.draw.circle(s, t.particle, (x, 5 + h), 3)
        pygame.draw.circle(s, (220, 255, 180), (x - 1, 4 + h), 1)


def _stars(s, t: Theme, rng):
    for _ in range(14):
        x, y = rng.randint(10, BOX_W - 10), rng.randint(BOX_H - 30, BOX_H - 10)
        pygame.draw.line(s, t.border, (x - 2, y), (x + 2, y))
        pygame.draw.line(s, t.border, (x, y - 2), (x, y + 2))


MOTIFS = {"flames": _flames, "icicles": _icicles, "bolts": _bolts, "drips": _drips, "stars": _stars}


def _panel(t: Theme) -> pygame.Surface:
    if t.title in _panels:
        return _panels[t.title]
    s = pygame.Surface((BOX_W, BOX_H), pygame.SRCALPHA)
    rect = s.get_rect()
    pygame.draw.rect(s, t.dark, rect, border_radius=8)
    inner = rect.inflate(-6, -6)
    s.blit(dither_gradient(inner.size, t.top, t.bottom, bands=10), inner)
    MOTIFS[t.motif](s, t, random.Random(t.title))
    pygame.draw.rect(s, t.border, rect.inflate(-4, -4), 2, border_radius=7)     # moldura dupla
    pygame.draw.rect(s, t.dark, rect.inflate(-10, -10), 1, border_radius=5)
    for cx, cy in ((7, 7), (BOX_W - 8, 7), (7, BOX_H - 8), (BOX_W - 8, BOX_H - 8)):  # cantoneiras
        pygame.draw.rect(s, t.border, (cx - 3, cy - 3, 7, 7))
        pygame.draw.rect(s, t.dark, (cx - 1, cy - 1, 3, 3))
    banner = BANNER                                                                 # faixa do título
    pygame.draw.rect(s, t.dark, banner.inflate(4, 4), border_radius=4)
    pygame.draw.rect(s, t.border, banner, border_radius=3)
    pygame.draw.rect(s, t.top, banner.inflate(-4, -4), border_radius=2)
    emblem = art.icon(t.icon)
    for x in (banner.x + 3, banner.right - 3 - emblem.get_width()):
        s.blit(emblem, (x, banner.centery - emblem.get_height() // 2))
    pedestal = pygame.Rect(16, 128, 80, 18)                                         # pedestal do retrato
    pygame.draw.ellipse(s, t.dark, pedestal.inflate(4, 4))
    pygame.draw.ellipse(s, t.border, pedestal)
    pygame.draw.ellipse(s, t.bottom, pedestal.inflate(-8, -6))
    plates = pygame.Surface((BOX_W - 122, 12), pygame.SRCALPHA)                     # placas das linhas
    pygame.draw.rect(plates, (*t.dark, 150), plates.get_rect(), border_radius=3)
    for i in range(9):
        s.blit(plates, (110, 33 + i * 13))
    bottom = pygame.Surface((BOX_W - 24, 34), pygame.SRCALPHA)
    pygame.draw.rect(bottom, (*t.dark, 150), bottom.get_rect(), border_radius=4)
    s.blit(bottom, (12, 150))
    _panels[t.title] = s
    return s


# ------------------------------------------------------------------ partículas animadas
def _particles(surf, t: Theme, box: pygame.Rect, time: float):
    for i in range(16):
        x = box.x + 10 + (i * 53) % (box.w - 20)
        phase = (time * (0.25 + (i % 5) * 0.06) + i * 0.37) % 1.0
        if t.motion == "up":
            y = box.bottom - 8 - phase * (box.h - 16)
            x += round(math.sin(time * 2 + i) * 3)
        elif t.motion == "down":
            y = box.y + 8 + phase * (box.h - 16)
            x += round(math.sin(time * 1.5 + i) * 4)
        else:
            if (int(time * 6) + i * 3) % 7:
                continue
            y = box.y + 16 + (i * 29) % (box.h - 32)
        size = 2 if i % 3 else 1
        pygame.draw.rect(surf, t.particle, (x, int(y), size, size))


# ------------------------------------------------------------------ ficha
def draw_profile(surf, ch, portrait, time: float = 0.0):
    dim(surf)
    t = theme_of(ch)
    box = pygame.Rect(0, 0, BOX_W, BOX_H)
    box.center = (GAME_W // 2, GAME_H // 2 - 6)
    ox, oy = box.topleft
    surf.blit(_panel(t), box)
    _particles(surf, t, box, time)
    draw_outlined(surf, t.title, (ox + BANNER.centerx, oy + 11), TEXT, t.dark, align="center")
    figure = art.scale(portrait, sprites.fit_scale(portrait, 80))
    bob = round(math.sin(time * 2) * 1)
    surf.blit(figure, (ox + 56 - figure.get_width() // 2, oy + 140 - figure.get_height() + bob))
    rows = [
        ("NOME", ch.name),
        ("NÍVEL", str(ch.level)),
        ("XP", f"{ch.xp}/{ch.xp_next}"),
        ("LEGEND", LEGENDS[ch.legend].name),
        ("BETS", str(ch.bets)),
        ("XP BATALHA", str(ch.battle_xp)),
        ("V / D", f"{ch.wins} / {ch.losses}"),
        ("COLISEU", f"{ch.coliseum_wins} vitória" + ("" if ch.coliseum_wins == 1 else "s")),
        ("COLEÇÃO", f"{len(ch.collection)} cartas"),
    ]
    for i, (label, value) in enumerate(rows):
        y = oy + 34 + i * 13
        draw_text(surf, label, (ox + 116, y), color=t.label, shadow=t.dark)
        draw_text(surf, value, (box.right - 18, y), color=TEXT, shadow=t.dark, align="right")
    badges = ", ".join(TRAINERS[name]["name"] for name in ch.beaten if name in TRAINERS) or "nenhum ainda"
    draw_text(surf, "VENCEU:", (ox + 18, oy + 154), color=t.label, shadow=t.dark)
    for i, line in enumerate(wrap(badges, box.w - 40)[:2]):
        draw_text(surf, line, (ox + 18, oy + 166 + i * 10), color=TEXT, shadow=t.dark)
    draw_outlined(surf, f"{action_label('b')} ou {action_label('profile')}: voltar",
                  (box.centerx, box.bottom + 4), TEXT, (20, 20, 32), align="center")

"""Peças de interface usadas pela loja e pelo editor de deck."""
import pygame

from game.data.cards import ARCHETYPE_NAMES, RARITY_NAMES
from game.engine.settings import GAME_W, HIGHLIGHT, TEXT
from game.engine.ui import draw_box, draw_cursor, draw_text, text_width, wrap
from game.graphics import pixelart as art

LIST_RECT = pygame.Rect(4, 48, 220, 218)
INFO_RECT = pygame.Rect(228, 48, GAME_W - 232, 218)
ROW_H = 16
LIST_ROWS = (LIST_RECT.h - 16) // ROW_H
PAPER = (232, 232, 224)


class ScrollList:
    """Índice + rolagem de uma lista vertical que mostra `rows` linhas por vez."""

    def __init__(self, rows):
        self.rows = rows
        self.index = 0
        self.top = 0

    def clamp(self, count):
        self.index = max(0, min(self.index, count - 1)) if count else 0
        self.top = max(0, min(self.top, self.index, max(0, count - self.rows)))
        if self.index >= self.top + self.rows:
            self.top = self.index - self.rows + 1

    def move(self, delta, count):
        if count:
            self.index = (self.index + delta) % count
        self.clamp(count)

    def visible(self, count):
        return range(self.top, min(count, self.top + self.rows))


def draw_coin(surf, x, y):
    pygame.draw.circle(surf, (40, 40, 48), (x + 5, y + 5), 5)
    pygame.draw.circle(surf, (248, 200, 48), (x + 5, y + 5), 4)
    pygame.draw.circle(surf, (200, 144, 24), (x + 5, y + 5), 2, 1)


def draw_bets(surf, bets, right, y):
    w = draw_text(surf, f"{bets} BETS", (right, y), align="right")
    draw_coin(surf, right - w - 14, y + 1)


def draw_row(surf, rect, selected, active=True):
    if selected:
        pygame.draw.rect(surf, (248, 232, 160) if active else PAPER, rect, border_radius=2)
        if active:
            draw_cursor(surf, rect.x + 3, rect.y + 4)


def draw_scrollbar(surf, lst, count, rect):
    if count <= lst.rows:
        return
    bar = pygame.Rect(rect.right - 7, rect.y + 8, 3, rect.h - 16)
    pygame.draw.rect(surf, (208, 208, 200), bar)
    h = max(8, bar.h * lst.rows // count)
    y = bar.y + (bar.h - h) * lst.top // max(1, count - lst.rows)
    pygame.draw.rect(surf, (88, 120, 168), (bar.x, y, 3, h))


def draw_card_info(surf, card, rect=INFO_RECT, extra=None):
    """Carta ampliada 2x à esquerda; nome, arquétipo, raridade, custo e descrição na coluna ao lado."""
    draw_box(surf, rect)
    img = art.card_zoom(card, 2)
    surf.blit(img, (rect.x + 8, rect.y + 8))
    x = rect.x + img.get_width() + 16
    width = rect.right - x - 8
    y = rect.y + 10
    for line in wrap(card.name.upper(), width, 16):
        draw_text(surf, line, (x, y))
        y += 14
    rarity_color = art.RARITY_COLORS[card.rarity]
    for text, color in ((ARCHETYPE_NAMES[card.archetype], TEXT), (RARITY_NAMES[card.rarity], rarity_color),
                        (f"Custo {card.cost}", TEXT)):
        draw_text(surf, text, (x, y + 2), size=12, color=color)
        y += 11
    y += 6
    bottom = rect.bottom - (24 if extra else 10)
    for line in wrap(card.text, width, 12):
        if y > bottom - 10:
            break
        draw_text(surf, line, (x, y), size=12, shadow=None)
        y += 10
    if extra:
        for i, line in enumerate(wrap(extra, rect.w - 16, 12)[:1]):
            draw_text(surf, line, (rect.centerx, rect.bottom - 16 + i * 10), size=12, color=TEXT, align="center")


def draw_tabs(surf, names, current, y=30, focused=False):
    w = (GAME_W - 8) // len(names)
    if focused:
        draw_text(surf, "<", (0, y + 2), color=(248, 248, 248), shadow=None)
        draw_text(surf, ">", (GAME_W - 7, y + 2), color=(248, 248, 248), shadow=None)
    for i, name in enumerate(names):
        rect = pygame.Rect(4 + i * w, y, w - 2, 16)
        on = i == current
        pygame.draw.rect(surf, HIGHLIGHT if on and focused else (56, 88, 120), rect, border_radius=3)
        pygame.draw.rect(surf, HIGHLIGHT if on else (200, 216, 232), rect.inflate(-2, -2), border_radius=3)
        draw_text(surf, name, (rect.centerx, rect.y + 3), size=12 if not on else 16, shadow=None, align="center")


# ------------------------------------------------------------------ sub-abas por tipo de carta
# Com a fileira de sub-abas, a lista e a carta ampliada descem um pouco (cabem 11 linhas).
SUB_LIST_RECT = pygame.Rect(4, 66, 220, 200)
SUB_INFO_RECT = pygame.Rect(228, 66, GAME_W - 232, 200)
SUB_LIST_ROWS = (SUB_LIST_RECT.h - 16) // ROW_H
TYPE_ICONS = {"fogo": "flame", "gelo": "ice", "raio": "bolt", "veneno": "poison", "utilidades": "star"}


def draw_type_tabs(surf, types, current, y=48, focused=False, marked=None):
    """Fileira de abas com o ícone e a cor de cada tipo (Fogo, Gelo...). `marked` ganha uma estrela (ex.: o
    tipo do deck). Com `focused`, a aba atual pisca a borda e aparecem as setas < >."""
    w = (GAME_W - 8) // len(types)
    for i, kind in enumerate(types):
        rect = pygame.Rect(4 + i * w, y, w - 2, 16)
        main, light = art.ARCHETYPE_COLORS[kind]
        on = i == current
        pygame.draw.rect(surf, HIGHLIGHT if on and focused else (56, 72, 96), rect, border_radius=3)
        pygame.draw.rect(surf, main if on else light, rect.inflate(-2, -2), border_radius=3)
        icon = art.icon(TYPE_ICONS[kind])
        label = ARCHETYPE_NAMES[kind].upper() + (" *" if kind == marked else "")
        text_w = text_width(label, 12)
        x = rect.centerx - (text_w + 14) // 2
        surf.blit(icon, (x, rect.y))
        draw_text(surf, label, (x + 14, rect.y + 3), size=12, color=(255, 255, 255) if on else TEXT,
                  shadow=(40, 40, 48) if on else None)
    if focused:
        draw_text(surf, "<", (0, y + 2), color=(248, 248, 248), shadow=None)
        draw_text(surf, ">", (GAME_W - 7, y + 2), color=(248, 248, 248), shadow=None)

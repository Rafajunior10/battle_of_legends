"""Construções modernas desenhadas por código, no estilo do pacote Ninja Adventure.

Mesmo contorno escuro do pacote e 3-4 tons por cor (luz, meio, sombra). Cada construção é montada
com peças simples: telhado, parede, janela, porta e placa com o nome.
Todas as funções devolvem uma Surface do tamanho exato do objeto no catálogo (props.OBJECTS).
"""
from __future__ import annotations

import pygame

from game.engine.ui import draw_text, text_width

OUTLINE = (20, 27, 27)          # o mesmo contorno dos sprites do pacote
GLASS = ((88, 150, 200), (150, 205, 235), (220, 240, 250))   # vidro: escuro, meio, reflexo
WOOD = ((96, 56, 40), (150, 96, 60), (196, 140, 92))
STONE = ((112, 112, 120), (150, 150, 158), (188, 188, 196))
PLAQUE = ((70, 44, 30), (230, 206, 150), (250, 232, 188))     # borda, fundo, brilho


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color)


# ============================================================ peças
def gable_roof(s, rect, color):
    """Telhado de duas águas com fileiras de telhas, cumeeira iluminada e beiral escuro."""
    x, y, w, h = rect
    peak = (x + w // 2, y)
    poly = [(x - 2, y + h), peak, (x + w + 1, y + h)]
    pygame.draw.polygon(s, OUTLINE, [(px, py) for px, py in poly])
    inner = [(x, y + h - 1), (peak[0], y + 2), (x + w - 1, y + h - 1)]
    pygame.draw.polygon(s, color, inner)
    for row_y in range(y + 6, y + h - 1, 4):          # fileiras de telhas
        half = (row_y - y) * (w // 2) / h
        left, right = int(peak[0] - half) + 1, int(peak[0] + half) - 1
        pygame.draw.line(s, shade(color, -40), (left, row_y), (right, row_y))
        for tx in range(left + (row_y // 4) % 2 * 3, right, 6):
            s.set_at((tx, row_y + 1), shade(color, -40))
            s.set_at((tx, row_y + 2), shade(color, -28))
    left_face = [(x + 1, y + h - 2), (peak[0], y + 3), (peak[0], y + h - 2)]   # lado da luz
    light = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(light, (*shade(color, 30), 70), left_face)
    s.blit(light, (0, 0))
    pygame.draw.line(s, shade(color, 70), (peak[0] - 1, y + 3), (peak[0] - 1, y + 5))
    pygame.draw.rect(s, shade(color, -70), (x - 1, y + h - 3, w + 2, 3))       # beiral


def flat_roof(s, rect, color):
    """Laje com mureta (platibanda) iluminada em cima."""
    x, y, w, h = rect
    pygame.draw.rect(s, OUTLINE, (x - 1, y, w + 2, h + 1))
    pygame.draw.rect(s, color, (x, y + 1, w, h - 1))
    pygame.draw.line(s, shade(color, 50), (x + 1, y + 1), (x + w - 2, y + 1))
    pygame.draw.line(s, shade(color, -50), (x, y + h - 1), (x + w - 1, y + h - 1))


def wall(s, rect, color, base=STONE):
    """Parede com leve degradê, lado direito na sombra e rodapé de pedra."""
    x, y, w, h = rect
    pygame.draw.rect(s, OUTLINE, (x - 1, y, w + 2, h))
    for i in range(h - 1):
        pygame.draw.line(s, shade(color, 10 - i * 18 // max(1, h)), (x, y + i), (x + w - 1, y + i))
    pygame.draw.rect(s, shade(color, -28), (x + w - 3, y, 3, h - 1))
    pygame.draw.rect(s, base[0], (x, y + h - 6, w, 5))
    pygame.draw.line(s, base[2], (x, y + h - 6), (x + w - 1, y + h - 6))
    for bx in range(x + 2, x + w - 2, 6):
        s.set_at((bx, y + h - 3), base[1])
        s.set_at((bx + 3, y + h - 5), base[1])


def window(s, x, y, w=12, h=11, frame=(240, 240, 232)):
    """Janela com moldura, vidro em degradê, reflexo em diagonal e peitoril."""
    pygame.draw.rect(s, OUTLINE, (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(s, frame, (x, y, w, h))
    pygame.draw.rect(s, GLASS[0], (x + 1, y + 1, w - 2, h - 2))
    pygame.draw.rect(s, GLASS[1], (x + 1, y + 1, w - 2, (h - 2) // 2))
    pygame.draw.line(s, GLASS[2], (x + 2, y + h - 3), (x + w // 2, y + 2))
    pygame.draw.line(s, frame, (x + w // 2, y + 1), (x + w // 2, y + h - 2))
    pygame.draw.rect(s, OUTLINE, (x - 2, y + h, w + 4, 2))
    pygame.draw.line(s, shade(frame, -30), (x - 1, y + h), (x + w, y + h))


def door(s, x, y, w, h, color=WOOD[1], glass=False):
    """Porta com batente, almofadas (ou vidro), maçaneta e degrau."""
    pygame.draw.rect(s, OUTLINE, (x - 1, y - 1, w + 2, h + 1))
    pygame.draw.rect(s, shade(color, -30), (x, y, w, h))
    if glass:
        pygame.draw.rect(s, GLASS[0], (x + 1, y + 1, w - 2, h - 2))
        pygame.draw.rect(s, GLASS[1], (x + 1, y + 1, w - 2, h // 3))
        pygame.draw.line(s, OUTLINE, (x + w // 2, y), (x + w // 2, y + h - 1))
        pygame.draw.line(s, GLASS[2], (x + 2, y + h - 4), (x + w // 2 - 2, y + 3))
    else:
        pygame.draw.rect(s, color, (x + 2, y + 2, w - 4, h // 2 - 3))
        pygame.draw.rect(s, color, (x + 2, y + h // 2, w - 4, h // 2 - 3))
        s.set_at((x + w - 3, y + h // 2), (248, 216, 96))
    pygame.draw.rect(s, STONE[2], (x - 2, y + h - 2, w + 4, 2))


def plaque_lines(text, max_width, size=12):
    """Quebra o nome em 2 linhas quando ele não cabe na largura (ex.: "CASA DA" / "VÓ ROSA")."""
    if text_width(text, size) + 10 <= max_width or " " not in text:
        return [text]
    words = text.split()
    best = min(range(1, len(words)), key=lambda i: max(text_width(" ".join(words[:i]), size),
                                                         text_width(" ".join(words[i:]), size)))
    return [" ".join(words[:best]), " ".join(words[best:])]


def plaque(s, cx, y, text, size=12, max_width=None):
    """Placa com o nome da construção: borda escura, fundo claro e texto centralizado (1 ou 2 linhas)."""
    lines = plaque_lines(text, max_width or s.get_width() - 6, size)
    w = max(text_width(line, size) for line in lines) + 10
    rect = pygame.Rect(cx - w // 2, y, w, 2 + 9 * len(lines))
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2), border_radius=2)
    pygame.draw.rect(s, PLAQUE[0], rect, border_radius=2)
    pygame.draw.rect(s, PLAQUE[1], rect.inflate(-2, -2), border_radius=1)
    pygame.draw.line(s, PLAQUE[2], (rect.x + 2, rect.y + 1), (rect.right - 3, rect.y + 1))
    for i, line in enumerate(lines):
        draw_text(s, line, (cx, y + 1 + i * 9), color=OUTLINE, size=size, shadow=None, align="center")
    return rect


def chimney(s, x, y, color):
    pygame.draw.rect(s, OUTLINE, (x - 1, y - 1, 8, 13))
    pygame.draw.rect(s, color, (x, y, 6, 11))
    pygame.draw.rect(s, shade(color, 40), (x, y, 2, 11))
    pygame.draw.rect(s, OUTLINE, (x - 2, y - 2, 10, 3))


# ============================================================ construções
def modern_house(roof, wall_color, label="", w=5, h=5, door_col=2):
    """Sobrado: telhado de telhas, dois andares com janelas, porta de madeira e placa com o nome."""
    s = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
    width, height = w * 16, h * 16
    roof_h = 28
    chimney(s, width - 22, 4, shade(roof, -20))
    wall(s, (3, roof_h - 2, width - 6, height - roof_h + 2), wall_color)
    pygame.draw.line(s, shade(wall_color, -36), (3, 50), (width - 4, 50))      # divisa entre os andares
    pygame.draw.line(s, shade(wall_color, 20), (3, 51), (width - 4, 51))
    gable_roof(s, (3, 1, width - 6, roof_h), roof)
    for wx in (9, width // 2 - 6, width - 22):                                 # janelas de cima
        window(s, wx, 31)
    door_x = door_col * 16 + 2
    door(s, door_x, height - 22, 12, 22)
    for wx in (7, width - 20):                                                 # janelas de baixo
        if abs(wx - door_x) > 14:
            window(s, wx, 58)
    if label:
        plaque(s, door_x + 6, 44 if len(plaque_lines(label, width - 6)) == 1 else 40, label, max_width=width - 6)
    return s


def card_shop(label="LOJA DE CARTAS", w=6, h=4):
    """Loja moderna: laje, letreiro grande, toldo listrado, vitrines de vidro e porta de vidro."""
    s = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
    width, height = w * 16, h * 16
    wall(s, (2, 8, width - 4, height - 8), (236, 232, 222), base=((88, 88, 104), (120, 120, 136), (160, 160, 176)))
    flat_roof(s, (2, 2, width - 4, 8), (90, 120, 170))
    sign = pygame.Rect(8, 12, width - 16, 13)                    # letreiro
    pygame.draw.rect(s, OUTLINE, sign.inflate(2, 2), border_radius=2)
    pygame.draw.rect(s, (40, 70, 140), sign, border_radius=2)
    pygame.draw.line(s, (90, 130, 210), (sign.x + 2, sign.y + 1), (sign.right - 3, sign.y + 1))
    draw_text(s, label, (width // 2, sign.y + 2), color=(250, 230, 120), size=12, shadow=OUTLINE, align="center")
    for i, x in enumerate(range(4, width - 4, 6)):              # toldo listrado com borda ondulada
        color = (220, 64, 64) if i % 2 == 0 else (250, 246, 236)
        pygame.draw.rect(s, color, (x, 28, 6, 6))
        pygame.draw.circle(s, color, (x + 3, 34), 3)
    pygame.draw.line(s, OUTLINE, (3, 27), (width - 4, 27))
    for wx in (7, width - 33):                                   # vitrines
        window(s, wx, 39, 26, 17, frame=(70, 70, 82))
        for cx in (wx + 5, wx + 13):                             # cartas expostas na vitrine
            pygame.draw.rect(s, OUTLINE, (cx, 46, 6, 8))
            pygame.draw.rect(s, (240, 200, 90), (cx + 1, 47, 4, 6))
    door(s, 3 * 16 - 7, height - 22, 14, 22, color=(70, 70, 82), glass=True)
    return s


def arena(label="ARENA", w=7, h=5):
    """Arena moderna: telhado curvo vermelho com nervuras, colunas brancas e entrada de vidro."""
    s = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
    width, height = w * 16, h * 16
    wall(s, (4, 26, width - 8, height - 26), (226, 226, 232))
    roof = [(2, 30), (10, 12), (width // 2, 4), (width - 11, 12), (width - 3, 30)]   # arco em segmentos
    pygame.draw.polygon(s, OUTLINE, roof)
    pygame.draw.polygon(s, (196, 56, 56), [(4, 29), (11, 13), (width // 2, 6), (width - 12, 13), (width - 5, 29)])
    pygame.draw.polygon(s, (226, 96, 90), [(8, 27), (13, 15), (width // 2, 8), (width // 2, 27)])
    for rx in range(14, width - 10, 12):                          # nervuras do telhado
        top = 6 + abs(rx - width // 2) // 4
        pygame.draw.line(s, (150, 40, 44), (rx, top + 2), (rx, 28))
    pygame.draw.rect(s, OUTLINE, (2, 28, width - 4, 4))
    pygame.draw.rect(s, (240, 240, 244), (3, 29, width - 6, 2))
    for cx in (8, 32, width - 38, width - 14):                    # colunas
        pygame.draw.rect(s, OUTLINE, (cx - 1, 33, 7, height - 39))
        pygame.draw.rect(s, (248, 248, 250), (cx, 33, 5, height - 40))
        pygame.draw.line(s, (200, 200, 210), (cx + 4, 33), (cx + 4, height - 8))
    for wx in (15, width - 31):
        window(s, wx, 50, 14, 12)
    door(s, 3 * 16 - 2, height - 26, 20, 26, color=(70, 70, 82), glass=True)
    plaque(s, width // 2, 35, label)
    return s


def snack_bar(label="LANCHONETE", w=6, h=5):
    """Lanchonete moderna: letreiro com hambúrguer e copo, toldo listrado, vitrines grandes e porta de vidro."""
    s = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
    width, height = w * 16, h * 16
    wall(s, (2, 30, width - 4, height - 30), (176, 222, 208), base=((180, 50, 46), (214, 58, 52), (240, 104, 92)))
    flat_roof(s, (2, 24, width - 4, 7), (214, 58, 52))
    for px in (20, width - 22):                                  # hastes do letreiro
        pygame.draw.rect(s, OUTLINE, (px, 16, 3, 9))
    sign = pygame.Rect(6, 3, width - 12, 15)                     # letreiro
    pygame.draw.rect(s, OUTLINE, sign.inflate(2, 2), border_radius=4)
    pygame.draw.rect(s, (250, 214, 80), sign, border_radius=4)
    pygame.draw.line(s, (255, 240, 170), (sign.x + 3, sign.y + 1), (sign.right - 4, sign.y + 1))
    draw_text(s, label, (width // 2, sign.y + 3), color=(190, 40, 40), size=12, shadow=None, align="center")
    _burger(s, sign.x + 2, sign.y + 3)
    _cup(s, sign.right - 9, sign.y + 2)
    for i, x in enumerate(range(4, width - 4, 6)):              # toldo listrado amarelo e vermelho
        color = (214, 58, 52) if i % 2 == 0 else (250, 230, 120)
        pygame.draw.rect(s, color, (x, 32, 6, 5))
        pygame.draw.circle(s, color, (x + 3, 37), 3)
    pygame.draw.line(s, OUTLINE, (3, 31), (width - 4, 31))
    for wx, ww in ((6, 30), (width - 36, 30)):                   # vitrines: banquinhos e balcão lá dentro
        window(s, wx, 44, ww, 20, frame=(70, 70, 82))
        pygame.draw.rect(s, (214, 58, 52), (wx + 1, 56, ww - 2, 3))
        for bx in range(wx + 4, wx + ww - 3, 8):
            pygame.draw.rect(s, (240, 80, 70), (bx, 59, 4, 2))
    door(s, 3 * 16 - 7, height - 22, 14, 22, color=(70, 70, 82), glass=True)
    return s


def _burger(s, x, y):
    pygame.draw.ellipse(s, OUTLINE, (x - 1, y - 1, 9, 9))
    pygame.draw.ellipse(s, (226, 160, 70), (x, y, 7, 4))
    pygame.draw.rect(s, (90, 180, 70), (x, y + 4, 7, 1))
    pygame.draw.rect(s, (120, 60, 40), (x, y + 5, 7, 1))
    pygame.draw.rect(s, (226, 160, 70), (x, y + 6, 7, 1))


def _cup(s, x, y):
    pygame.draw.polygon(s, OUTLINE, [(x - 1, y + 1), (x + 7, y + 1), (x + 6, y + 11), (x, y + 11)])
    pygame.draw.polygon(s, (250, 250, 246), [(x, y + 2), (x + 6, y + 2), (x + 5, y + 10), (x + 1, y + 10)])
    pygame.draw.rect(s, (214, 58, 52), (x + 1, y + 5, 5, 2))
    pygame.draw.line(s, (214, 58, 52), (x + 4, y + 2), (x + 6, y - 2))


def _fence_board(s, y, width, label):
    """Tapume da obra com faixas amarelas e a placa com o nome."""
    board = pygame.Rect(0, y, width, 16)
    pygame.draw.rect(s, OUTLINE, board)
    pygame.draw.rect(s, (222, 222, 226), board.inflate(-2, -2))
    for i in range(0, width, 10):
        pygame.draw.polygon(s, (240, 180, 40), [(i, board.bottom - 2), (i + 5, board.y + 2),
                                                 (i + 9, board.y + 2), (i + 4, board.bottom - 2)])
    plaque(s, width // 2, board.y + 3, label)


def _cones(s, width, height):
    for cx in (4, width - 10):
        pygame.draw.polygon(s, OUTLINE, [(cx, height), (cx + 3, height - 9), (cx + 6, height)])
        pygame.draw.polygon(s, (236, 110, 40), [(cx + 1, height - 1), (cx + 3, height - 7), (cx + 5, height - 1)])
        pygame.draw.line(s, (250, 250, 250), (cx + 2, height - 4), (cx + 4, height - 4))


def stable_site(label="ESTÁBULO", w=8, h=6):
    """Estábulo em obras: estrutura de madeira, meia parede vermelha, vigas do telhado sem telhas, feno e tábuas."""
    s = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
    width, height = w * 16, h * 16
    red = ((150, 40, 36), (196, 64, 52), (226, 104, 84))
    pygame.draw.rect(s, OUTLINE, (6, 40, width - 12, height - 58))           # meia parede (só a parte de baixo)
    pygame.draw.rect(s, red[1], (7, 41, width - 14, height - 60))
    for x in range(10, width - 10, 6):
        pygame.draw.line(s, red[0], (x, 42), (x, height - 20))
    peak = (width // 2, 6)
    for x in (6, width // 4, width // 2, 3 * width // 4, width - 7):         # postes e vigas do telhado
        pygame.draw.rect(s, OUTLINE, (x - 2, 24, 5, height - 40))
        pygame.draw.rect(s, WOOD[1], (x - 1, 25, 3, height - 42))
    for side in (6, width - 7):
        pygame.draw.line(s, OUTLINE, (side, 25), peak, 4)
        pygame.draw.line(s, WOOD[2], (side, 25), peak, 2)
    for x in range(14, width - 12, 14):                                       # caibros soltos
        top = 6 + abs(x - width // 2) * 19 // (width // 2)
        pygame.draw.line(s, WOOD[0], (x, top), (x, 26), 2)
    for bx in (14, 30):                                                       # fardos de feno
        pygame.draw.rect(s, OUTLINE, (bx, height - 30, 14, 10), border_radius=2)
        pygame.draw.rect(s, (232, 196, 90), (bx + 1, height - 29, 12, 8), border_radius=2)
        pygame.draw.line(s, (180, 140, 50), (bx + 2, height - 26), (bx + 11, height - 26))
    for i in range(3):                                                        # pilha de tábuas
        pygame.draw.rect(s, OUTLINE, (width - 40, height - 24 - i * 4, 26, 4))
        pygame.draw.rect(s, WOOD[2], (width - 39, height - 23 - i * 4, 24, 2))
    _fence_board(s, height - 18, width, label + " - EM OBRAS")
    _cones(s, width, height)
    return s


def mall_site(label="SHOPPING", w=9, h=6):
    """Shopping em obras: esqueleto de concreto com lajes, andaime, guindaste e tapume."""
    s = pygame.Surface((w * 16, h * 16), pygame.SRCALPHA)
    width, height = w * 16, h * 16
    concrete = ((120, 122, 130), (168, 170, 176), (206, 208, 212))
    for fy in (14, 34, 54):                                                   # lajes
        pygame.draw.rect(s, OUTLINE, (8, fy, width - 16, 5))
        pygame.draw.rect(s, concrete[1], (9, fy + 1, width - 18, 3))
        pygame.draw.line(s, concrete[2], (9, fy + 1), (width - 10, fy + 1))
    for px in range(10, width - 8, 24):                                       # pilares
        pygame.draw.rect(s, OUTLINE, (px - 1, 14, 8, height - 30))
        pygame.draw.rect(s, concrete[0], (px, 15, 6, height - 32))
        pygame.draw.line(s, concrete[2], (px, 15), (px, height - 18))
    for gx in range(14, width - 14, 24):                                      # vidros de algumas lojas já no lugar
        pygame.draw.rect(s, (110, 170, 210), (gx + 4, 40, 12, 12))
        pygame.draw.line(s, (220, 240, 250), (gx + 5, 50), (gx + 14, 41))
    orange = ((176, 86, 30), (236, 136, 52))
    for sx in (3, width - 5):                                                 # andaime
        pygame.draw.line(s, orange[0], (sx, 10), (sx, height - 18), 2)
    for sy in range(18, height - 18, 12):
        pygame.draw.line(s, orange[1], (3, sy), (14, sy))
        pygame.draw.line(s, orange[1], (width - 15, sy), (width - 4, sy))
    pygame.draw.line(s, OUTLINE, (width - 30, 0), (width - 30, 14), 3)       # guindaste
    pygame.draw.line(s, (240, 190, 40), (width - 62, 2), (width - 18, 2), 3)
    pygame.draw.line(s, OUTLINE, (width - 50, 3), (width - 50, 11))
    pygame.draw.rect(s, concrete[0], (width - 53, 11, 7, 4))
    _fence_board(s, height - 18, width, label + " - EM OBRAS")
    _cones(s, width, height)
    return s


def street_lamp():
    """Poste de luz moderno (1 x 2 tiles)."""
    s = pygame.Surface((16, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, OUTLINE, (6, 6, 4, 25))
    pygame.draw.rect(s, (70, 80, 96), (7, 7, 2, 23))
    pygame.draw.rect(s, OUTLINE, (3, 29, 10, 3))
    pygame.draw.rect(s, OUTLINE, (2, 1, 12, 7), border_radius=2)
    pygame.draw.rect(s, (250, 236, 160), (3, 2, 10, 5), border_radius=2)
    pygame.draw.line(s, (255, 255, 230), (4, 3), (11, 3))
    return s


def add_plaque(img, label, door_col=None):
    """Placa colada numa construção pronta (ex.: as do pacote): na parede, acima da porta."""
    out = img.copy()
    cx = door_col * 16 + 8 if door_col is not None else out.get_width() // 2
    cx = max(text_width(label, 12) // 2 + 6, min(out.get_width() - text_width(label, 12) // 2 - 6, cx))
    plaque(out, cx, out.get_height() - 30, label)
    return out

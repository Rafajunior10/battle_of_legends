"""Pixel art gerada por código: personagens, tiles, prédios, ícones e cartas.

Os sprites são desenhados como "mapas de caracteres": cada letra vira uma cor da
paleta e '.' é transparente. Assim dá para editar a arte direto aqui no código.
"""
import pygame

from game.engine.ui import dither_gradient, draw_outlined, draw_text, text_width

K = (40, 40, 48)   # contorno


def from_strings(rows, palette):
    width = max(len(r) for r in rows)
    surf = pygame.Surface((width, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = palette.get(ch)
            if color:
                surf.set_at((x, y), color)
    return surf


def optimize(surf):
    """Converte para o formato do monitor (cópias na tela ficam bem mais rápidas). Sem janela, não mexe."""
    if pygame.display.get_surface() is None:
        return surf
    return surf.convert_alpha() if surf.get_flags() & pygame.SRCALPHA else surf.convert()


def scale(surf, factor):
    return pygame.transform.scale(surf, (surf.get_width() * factor, surf.get_height() * factor))


# ================================================================ gosma
SLIME = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "......KKKK......",
    "....KKGGGGKK....",
    "...KGGWWGGGGK...",
    "..KGGWGGGGGGGK..",
    "..KGGGGGGGGGGK..",
    ".KGGGKGGGGKGGGK.",
    ".KGGGKGGGGKGGGK.",
    ".KGGGGGggGGGGGK.",
    ".KgGGGGGGGGGGgK.",
    "..KggggggggggK..",
    "...KKKKKKKKKK...",
]
SLIME_COLORS = {
    "green": ((104, 200, 96), (56, 136, 64)),
    "blue": ((96, 160, 240), (48, 96, 184)),
    "pink": ((240, 136, 200), (184, 72, 144)),
}


def slime_sprite(color):
    light, dark = SLIME_COLORS[color]
    return from_strings(SLIME, {"K": K, "G": light, "g": dark, "W": (255, 255, 255)})


# ================================================================ prédios
def house(roof, roof_dark):
    """Casa 5x4 tiles (80x64). A porta fica na coluna 2, última linha."""
    w, h = 80, 64
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, K, (4, 26, 72, 38))
    pygame.draw.rect(s, (240, 224, 184), (5, 27, 70, 36))
    pygame.draw.rect(s, (208, 184, 144), (5, 58, 70, 5))
    pygame.draw.rect(s, K, (58, 0, 8, 10))
    pygame.draw.rect(s, (176, 176, 184), (59, 1, 6, 8))
    pygame.draw.polygon(s, K, [(0, 30), (10, 2), (70, 2), (79, 30)])
    pygame.draw.polygon(s, roof, [(2, 29), (11, 3), (69, 3), (77, 29)])
    for y in range(8, 29, 5):
        inset = 11 - (y - 3) * 9 // 26
        pygame.draw.line(s, roof_dark, (inset + 1, y), (w - inset - 3, y))
    for wx in (10, 56):
        pygame.draw.rect(s, K, (wx, 36, 14, 12))
        pygame.draw.rect(s, (152, 208, 248), (wx + 1, 37, 12, 10))
        pygame.draw.line(s, K, (wx + 7, 37), (wx + 7, 46))
        pygame.draw.line(s, K, (wx + 1, 41), (wx + 12, 41))
    pygame.draw.rect(s, K, (32, 40, 16, 24))
    pygame.draw.rect(s, (152, 96, 56), (33, 41, 14, 23))
    pygame.draw.rect(s, (248, 208, 64), (43, 52, 2, 2))
    return s


def arena():
    """Arena 7x5 tiles (112x80). A porta fica na coluna 3, última linha."""
    w, h = 112, 80
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, K, (2, 20, 108, 60))
    pygame.draw.rect(s, (216, 216, 224), (3, 21, 106, 58))
    pygame.draw.rect(s, (184, 184, 200), (3, 70, 106, 9))
    pygame.draw.rect(s, K, (0, 6, 112, 18))
    pygame.draw.rect(s, (208, 64, 64), (1, 7, 110, 16))
    pygame.draw.rect(s, K, (10, 0, 92, 8))
    pygame.draw.rect(s, (240, 240, 240), (11, 1, 90, 6))
    draw_outlined(s, "ARENA", (56, 9), (248, 248, 248), K, size=16, align="center")
    for px in (8, 96):
        pygame.draw.rect(s, K, (px, 24, 8, 56))
        pygame.draw.rect(s, (176, 176, 192), (px + 1, 24, 6, 56))
    for wx in (22, 74):
        pygame.draw.rect(s, K, (wx, 32, 16, 12))
        pygame.draw.rect(s, (152, 208, 248), (wx + 1, 33, 14, 10))
    # emblema de carta acima da porta
    pygame.draw.rect(s, K, (49, 27, 14, 18), border_radius=2)
    pygame.draw.rect(s, (208, 64, 64), (50, 28, 12, 16), border_radius=2)
    pygame.draw.rect(s, (248, 240, 216), (52, 30, 8, 12))
    pygame.draw.circle(s, (208, 64, 64), (56, 36), 2)
    pygame.draw.rect(s, K, (46, 50, 20, 30))
    pygame.draw.rect(s, (88, 96, 136), (47, 51, 18, 29))
    pygame.draw.line(s, K, (56, 51), (56, 79))
    return s


def shop():
    """Loja de cartas 5x4 tiles (80x64). A porta fica na coluna 2, última linha."""
    s = house((64, 176, 104), (40, 128, 72)).copy()
    # toldo listrado
    for i in range(9):
        color = (232, 72, 64) if i % 2 == 0 else (248, 248, 240)
        pygame.draw.rect(s, color, (5 + i * 8, 27, 8, 6))
    pygame.draw.line(s, K, (5, 33), (74, 33))
    # placa com o nome
    pygame.draw.rect(s, K, (19, 8, 42, 15), border_radius=2)
    pygame.draw.rect(s, (248, 216, 96), (20, 9, 40, 13), border_radius=2)
    draw_text(s, "LOJA", (40, 10), color=K, size=16, shadow=None, align="center")
    return s


def coliseum():
    """Coliseu 7x4 tiles (112x64). A porta fica na coluna 3, última linha."""
    w, h = 112, 64
    stone, stone_dark, stone_light = (216, 192, 152), (168, 136, 96), (240, 224, 192)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    # corpo em arco (parte de cima arredondada)
    pygame.draw.ellipse(s, K, (0, 6, w, 40))
    pygame.draw.rect(s, K, (0, 26, w, 38))
    pygame.draw.ellipse(s, stone, (1, 7, w - 2, 38))
    pygame.draw.rect(s, stone, (1, 26, w - 2, 37))
    pygame.draw.rect(s, stone_dark, (1, 56, w - 2, 7))
    for y in (22, 40):   # faixas entre os andares
        pygame.draw.line(s, stone_dark, (4, y), (w - 5, y))
        pygame.draw.line(s, stone_light, (4, y + 1), (w - 5, y + 1))
    for row, (y, n) in enumerate(((26, 8), (44, 7))):   # arcos dos dois andares
        gap = (w - 8) // n
        for i in range(n):
            x = 6 + i * gap + (gap // 2 if row else 0)
            if row and 44 <= x <= 60:
                continue   # espaço da porta
            pygame.draw.rect(s, K, (x, y + 3, 8, 9))
            pygame.draw.circle(s, K, (x + 4, y + 4), 4)
            pygame.draw.rect(s, (72, 56, 48), (x + 1, y + 4, 6, 8))
            pygame.draw.circle(s, (72, 56, 48), (x + 4, y + 4), 3)
    # bandeiras no topo
    for fx, color in ((22, (232, 64, 48)), (56, (248, 200, 48)), (90, (72, 120, 216))):
        top = 0 if fx == 56 else 4
        pygame.draw.line(s, K, (fx, top), (fx, top + 12))
        pygame.draw.polygon(s, K, [(fx + 1, top), (fx + 10, top + 3), (fx + 1, top + 7)])
        pygame.draw.polygon(s, color, [(fx + 1, top + 1), (fx + 8, top + 3), (fx + 1, top + 6)])
    # placa e portão
    pygame.draw.rect(s, K, (30, 10, 52, 12), border_radius=2)
    pygame.draw.rect(s, (248, 216, 96), (31, 11, 50, 10), border_radius=2)
    draw_text(s, "COLISEU", (56, 11), color=K, size=12, shadow=None, align="center")
    pygame.draw.rect(s, K, (47, 44, 18, 20))
    pygame.draw.circle(s, K, (56, 45), 9)
    pygame.draw.rect(s, (120, 72, 40), (48, 46, 16, 18))
    pygame.draw.circle(s, (120, 72, 40), (56, 46), 8)
    for gx in (51, 56, 61):   # grade do portão
        pygame.draw.line(s, (72, 48, 32), (gx, 40), (gx, 63))
    return s


def card_back():
    s = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    rect = s.get_rect()
    pygame.draw.rect(s, K, rect, border_radius=3)
    pygame.draw.rect(s, (56, 72, 152), rect.inflate(-2, -2), border_radius=3)
    pygame.draw.rect(s, (96, 120, 208), rect.inflate(-8, -8), 1, border_radius=2)
    cx, cy = CARD_W // 2, CARD_H // 2
    pygame.draw.polygon(s, K, [(cx, cy - 11), (cx + 9, cy), (cx, cy + 11), (cx - 9, cy)])
    pygame.draw.polygon(s, (248, 200, 48), [(cx, cy - 9), (cx + 7, cy), (cx, cy + 9), (cx - 7, cy)])
    pygame.draw.polygon(s, (232, 64, 48), [(cx, cy - 4), (cx + 3, cy), (cx, cy + 4), (cx - 3, cy)])
    return s


_pack_cache = {}


def pack_image(color):
    """Pacotinho de cartas com as pontas serrilhadas (38x54)."""
    color = tuple(color)
    if color in _pack_cache:
        return _pack_cache[color]
    s = pygame.Surface((PACK_W, PACK_H), pygame.SRCALPHA)
    dark = tuple(max(0, c - 64) for c in color)
    light = tuple(min(255, c + 72) for c in color)
    body = pygame.Rect(1, 5, PACK_W - 2, PACK_H - 10)
    pygame.draw.rect(s, K, body)
    pygame.draw.rect(s, color, body.inflate(-2, -2))
    for x in range(1, PACK_W - 1, 4):   # serrilhado de cima e de baixo
        pygame.draw.polygon(s, K, [(x, 6), (x + 2, 1), (x + 4, 6)])
        pygame.draw.polygon(s, dark, [(x + 1, 6), (x + 2, 3), (x + 3, 6)])
        pygame.draw.polygon(s, K, [(x, PACK_H - 6), (x + 2, PACK_H - 1), (x + 4, PACK_H - 6)])
        pygame.draw.polygon(s, dark, [(x + 1, PACK_H - 6), (x + 2, PACK_H - 3), (x + 3, PACK_H - 6)])
    pygame.draw.rect(s, dark, (2, 9, PACK_W - 4, 4))
    pygame.draw.rect(s, dark, (2, PACK_H - 13, PACK_W - 4, 4))
    pygame.draw.line(s, light, (4, 16), (4, PACK_H - 17))
    # carta estampada
    card = pygame.Rect(11, 17, 16, 21)
    pygame.draw.rect(s, K, card, border_radius=2)
    pygame.draw.rect(s, (248, 240, 216), card.inflate(-2, -2), border_radius=2)
    pygame.draw.polygon(s, color, [(19, 21), (23, 27), (19, 33), (15, 27)])
    _pack_cache[color] = s
    return s


# ================================================================ ícones das cartas (12x12)
ICON_PALETTE = {
    "K": K, "R": (224, 64, 48), "O": (248, 144, 48), "Y": (248, 216, 64), "W": (255, 255, 255),
    "B": (72, 136, 232), "b": (40, 88, 176), "G": (104, 200, 96), "g": (56, 136, 64),
    "P": (176, 96, 216), "p": (112, 56, 160), "S": (200, 200, 216), "s": (136, 136, 160),
    "N": (136, 88, 48), "E": (248, 208, 160), "e": (216, 160, 120), "C": (176, 224, 248),
}
ICONS = {
    "sword": [
        "..........KK", ".........KSK", "........KSK.", ".......KSK..", "......KSK...", ".....KSK....",
        "..K.KSK.....", "..KKSK......", "...KNK......", "..KNKKK.....", ".KNK........", ".KK.........",
    ],
    "flame": [
        ".....K......", "....KRK.....", "....KRRK....", "...KRRRK.K..", "..KRRORRKRK.", "..KRROORRRK.",
        ".KRROOYORRK.", ".KRROYYYORK.", ".KROYYYYORK.", ".KROYYWYORK.", "..KROYYORK..", "...KKKKKK...",
    ],
    "bolt": [
        "......KKKK..", ".....KYYK...", "....KYYK....", "...KYYK.....", "..KYYYKKK...", "..KYYYYYK...",
        "...KKKYYK...", ".....KYK....", "....KYK.....", "...KYK......", "..KYK.......", "..KK........",
    ],
    "shield": [
        "..KKKKKKKK..", ".KBBBBBBBBK.", ".KBWWBBbbBK.", ".KBWBBBBbBK.", ".KBBBBBBbBK.", ".KBBBBBBbBK.",
        ".KBBBBBBbBK.", "..KBBBBbBK..", "..KBBBBbBK..", "...KBBbBK...", "....KBBK....", ".....KK.....",
    ],
    "wall": [
        "KKKKKKKKKKKK", "KSSSSKSSSSSK", "KsssSKsssssK", "KKKKKKKKKKKK", "KSSKSSSSSKSK", "KssKsssssKsK",
        "KKKKKKKKKKKK", "KSSSSKSSSSSK", "KsssSKsssssK", "KKKKKKKKKKKK", "KSSKSSSSSKSK", "KKKKKKKKKKKK",
    ],
    "potion": [
        "....KKKK....", "....KWWK....", ".....KK.....", "....KSSK....", "...KWGGGK...", "..KWGGGGGK..",
        "..KGGGGGGK..", "..KGGGGGgK..", "..KGGGGGgK..", "..KgGGGggK..", "...KggggK...", "....KKKK....",
    ],
    "star": [
        ".....KK.....", "....KYYK....", "....KYYK....", "KKKKKYYKKKKK", "KYYYYYYYYYYK", ".KYYYWYYYYK.",
        "..KYYYYYYK..", "..KYYYYYYK..", ".KYYYKKYYYK.", ".KYYK..KYYK.", "KYKK....KKYK", "KK........KK",
    ],
    "poison": [
        ".....KK.....", "....KPPK....", "....KPPK....", "...KPPPPK...", "...KPWPPK...", "..KPWPPPPK..",
        "..KPPPPPPK..", ".KPPPPPPPpK.", ".KPPPPPPPpK.", ".KpPPPPPppK.", "..KppppppK..", "...KKKKKK...",
    ],
    "heart": [
        "............", ".KKK....KKK.", "KRRRK..KRRRK", "KRWRRKKRRRRK", "KRRRRRRRRRRK", "KRRRRRRRRRRK",
        ".KRRRRRRRRK.", "..KRRRRRRK..", "...KRRRRK...", "....KRRK....", ".....KK.....", "............",
    ],
    "slime": [
        "............", "............", "....KKKK....", "...KGGGGK...", "..KGWGGGGK..", "..KGGGGGGK..",
        ".KGGKGGKGGK.", ".KGGKGGKGGK.", ".KGGGGGGGGK.", ".KgGGGGGGgK.", "..KggggggK..", "...KKKKKK...",
    ],
    "dagger": [
        "............", "..........K.", ".........KSK", "........KSK.", ".......KSK..", "......KSK...",
        "...K.KSK....", "...KKSK.....", "....KNK.....", "...KNKK.....", "..KNK.......", "..KK........",
    ],
    "meteor": [
        "K...........", ".KO.........", "..KOO.......", "...KROKKK...", "....KRKNNK..", ".....KNNNNK.",
        "....KNNsNNK.", "....KNNNNsK.", "....KNsNNNK.", ".....KNNNK..", "......KKK...", "............",
    ],
    "fang": [
        "............", "............", "KKKKKKKKKKKK", "KRRRRRRRRRRK", "KRRRRRRRRRRK", "KKWKKKKKKWKK",
        ".KWWK..KWWK.", ".KWWK..KWWK.", "..KWK..KWK..", "..KWK..KWK..", "...K....K...", "............",
    ],
    "spear": [
        ".......KKKKK", ".......KSSSK", "........KWSK", ".......KSKSK", "......KNK.KK", ".....KNK....",
        "....KNK.....", "...KNK......", "..KNK.......", ".KNK........", "KNK.........", "KK..........",
    ],
    "thorn": [
        ".....K......", "....KgK..K..", "..K.KGK.KgK.", ".KgKKGGKKGK.", "..KGGGGGGK..", "KKKGGWGGGKKK",
        "KgGGGGGGGGgK", "..KGGGGGgK..", ".KGKKGGKKgK.", ".KK.KgK.KK..", "....KgK.....", ".....K......",
    ],
    "book": [
        "..KKKKKKKK..", "..KBBBBBBBK.", "..KBYYYYBBK.", "..KBBBBBBBK.", "..KBYYYBBBK.", "..KBBBBBBBK.",
        "..KBBBBBBBK.", "..KBBBBBBBK.", "..KbbbbbbbK.", "..KWWWWWWWK.", "..KKKKKKKKK.", "............",
    ],
    "stun": [
        "...KKKKKK...", "..KPPPPPPK..", ".KP.KYK..PK.", "KP.KYYK...PK", "KP.KYKKK..PK", "KP.KYYYYK.PK",
        "KP..KKKYK.PK", "KP...KYK..PK", "KP..KYK...PK", ".KP.KK...PK.", "..KPPPPPPK..", "...KKKKKK...",
    ],
    "smoke": [
        "............", "....KKK.....", "...KSSSK.KK.", "..KSWWSsKSsK", ".KSWWSSSsSsK", ".KSSSSSSSSsK",
        "KSSSSSSSSSsK", "KsSSSSSSSSK.", ".KssSSSSsK..", "..KKssssK...", "....KKKK....", "............",
    ],
    "ice": [
        ".....K......", "..K.KWK.K...", "..KKKWKKK...", "...KWCWK....", "KKKWKWKWKKK.", "KWCWWCWWCWK.",
        "KKKWKWKWKKK.", "...KWCWK....", "..KKKWKKK...", "..K.KWK.K...", ".....K......", "............",
    ],
    "crystal": [
        ".....KK.....", "....KWCK....", "...KWCCBK...", "..KWCCCBbK..", "..KWCCCBbK..", "..KCCCCBbK..",
        "..KCCCBBbK..", "...KCCBbK...", "...KCBBbK...", "....KBbK....", ".....KK.....", "............",
    ],
    "aura": [
        "....KKKK....", "..KKPPPPKK..", ".KPPWPPPPPK.", ".KPK....KPK.", "KPK......KPK", "KPK..YY..KPK",
        "KPK..YY..KPK", "KPK......KPK", ".KPK....KPK.", ".KPPPPPPppK.", "..KKppppKK..", "....KKKK....",
    ],
    "fist": [
        "............", "...KKKKKK...", "..KEEKEEKK..", "..KEEKEEKEK.", "..KEEKEEKEK.", ".KKKKKKKKEK.",
        ".KEEEEEEEEK.", ".KEEEEEEEEK.", "..KEEEEEEK..", "..KeeeeeK...", "...KKKKK....", "............",
    ],
    "boot": [
        "............", "..KKKK......", "..KNNK......", "..KNNK......", "..KNNK......", "..KNNK......",
        "..KNNNKKKK..", "..KNNNNNNNK.", "..KNNNNNNNNK", "..KKKKKKKKKK", "..KSSSSSSSSK", "...KKKKKKKK.",
    ],
}
_icon_cache = {}


def icon(name):
    if name not in _icon_cache:
        _icon_cache[name] = optimize(from_strings(ICONS[name], ICON_PALETTE))
    return _icon_cache[name]


# ================================================================ cartas
CARD_W, CARD_H = 56, 80
PACK_W, PACK_H = 38, 54   # pacotinho dos packs (desenhado no tamanho antigo)
# (moldura, fundo da arte) de cada arquétipo
ARCHETYPE_COLORS = {
    "fogo": ((216, 80, 48), (248, 200, 168)),
    "gelo": ((64, 152, 216), (208, 236, 248)),
    "raio": ((208, 160, 24), (248, 236, 168)),
    "veneno": ((136, 72, 184), (220, 196, 240)),
    "utilidades": ((112, 104, 96), (224, 216, 200)),
}
STAT_COLORS = {"dano": (200, 48, 40), "defesa": (48, 88, 200), "aura": (136, 64, 184), "cura": (40, 144, 64),
               "energia": (176, 128, 16), "compra": (176, 128, 16)}
RARITY_GEMS = {"rara": (96, 200, 248), "epica": (248, 200, 48)}
RARITY_COLORS = {"comum": (96, 96, 104), "rara": (40, 120, 200), "epica": (200, 136, 16)}
_card_cache = {}


def draw_level_stars(surf, level, x, y):
    """Uma estrelinha por nível de evolução acima do 1."""
    for i in range(level - 1):
        sx = x + i * 7
        pygame.draw.polygon(surf, K, [(sx + 3, y), (sx + 6, y + 3), (sx + 3, y + 6), (sx, y + 3)])
        pygame.draw.polygon(surf, (248, 216, 64), [(sx + 3, y + 1), (sx + 5, y + 3), (sx + 3, y + 5), (sx + 1, y + 3)])


def draw_stats(surf, stats, cx, y, size=12):
    """Números da carta lado a lado, cada um na cor do seu tipo (dano, defesa, aura, cura...)."""
    texts = [(str(value), STAT_COLORS[kind]) for kind, value in stats]
    gap = 3
    total = sum(text_width(t, size) for t, _ in texts) + gap * max(0, len(texts) - 1)
    x = cx - total // 2
    for text, color in texts:
        x += draw_text(surf, text, (x, y), color=color, size=size, shadow=None) + gap


_zoom_cache = {}


def card_zoom(card, factor=2):
    """Carta ampliada, guardada em cache (ampliar a cada quadro é desperdício: a imagem não muda)."""
    key = (card.id, card.level, factor)
    if key not in _zoom_cache:
        _zoom_cache[key] = scale(render_card(card), factor)
    return _zoom_cache[key]


def _tone(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color)


def render_card(card, dim=False):
    """Carta 56x80: moldura do arquétipo em degradê, arte grande, nome e os números coloridos."""
    key = (card.id, card.level, dim)
    if key in _card_cache:
        return _card_cache[key]
    main, light = ARCHETYPE_COLORS[card.archetype]
    s = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    rect = s.get_rect()
    pygame.draw.rect(s, K, rect, border_radius=4)
    pygame.draw.rect(s, main, rect.inflate(-2, -2), border_radius=4)
    for y in range(3, CARD_H - 3):   # moldura em degradê: mais clara em cima, mais escura embaixo
        tone = 32 - y * 64 // CARD_H
        pygame.draw.line(s, _tone(main, tone), (2, y), (CARD_W - 3, y))
    pygame.draw.line(s, _tone(main, 80), (4, 1), (CARD_W - 5, 1))     # brilho na borda de cima
    pygame.draw.line(s, _tone(main, -60), (4, CARD_H - 2), (CARD_W - 5, CARD_H - 2))
    # janela da arte: fundo em degradê pontilhado e ícone 3x
    pygame.draw.rect(s, K, (4, 4, 48, 42))
    s.blit(dither_gradient((46, 40), _tone(light, 28), _tone(light, -28), bands=5), (5, 5))
    s.blit(scale(icon(card.icon), 3), (10, 7))
    pygame.draw.line(s, _tone(light, 60), (5, 5), (50, 5))
    # nome e números
    pygame.draw.rect(s, (248, 240, 216), (4, 48, 48, 13), border_radius=2)
    name_size = next((n for n in (12, 11, 10) if text_width(card.short, n) <= 46), 9)
    draw_text(s, card.short, (28, 49 + (12 - name_size) // 2), size=name_size, shadow=None, align="center")
    pygame.draw.rect(s, (232, 220, 192), (4, 62, 48, 15), border_radius=2)
    draw_stats(s, card.stats, 28, 63, size=16)
    # custo de energia
    pygame.draw.circle(s, K, (9, 9), 8)
    pygame.draw.circle(s, (248, 208, 64), (9, 9), 7)
    pygame.draw.circle(s, (255, 240, 160), (7, 7), 2)
    draw_text(s, str(card.cost), (9, 4), color=K, size=16, shadow=None, align="center")
    draw_level_stars(s, card.level, 7, 38)
    gem = RARITY_GEMS.get(card.rarity)
    if gem:
        pygame.draw.polygon(s, K, [(47, 3), (52, 9), (47, 15), (42, 9)])
        pygame.draw.polygon(s, gem, [(47, 4), (51, 9), (47, 14), (43, 9)])
        pygame.draw.line(s, (255, 255, 255), (46, 6), (45, 8))
    if dim:
        shade = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        pygame.draw.rect(shade, (40, 40, 56, 120), rect, border_radius=4)
        s.blit(shade, (0, 0))
    s = optimize(s)
    _card_cache[key] = s
    return s

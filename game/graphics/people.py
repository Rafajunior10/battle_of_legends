"""Personagens no estilo Habbo (20 x 40): cabeça grande e redonda, corpo reto, braços ao lado, pés em diagonal.

Como funciona (leia na ordem):
1. O CORPO é um "molde" de letras. Cada letra é uma REGIÃO do corpo, não uma cor:
     K contorno     S pele sempre visível (rosto, orelha, nariz, pescoço, mãos)
     W/E branco e pupila do olho     M boca
     U ombro/manga  A antebraço     T peito        Y barriga        B cintura
     L coxa         N canela        F tênis        O sola do tênis
   Letra minúscula (h) = tom mais escuro do cabelo (raspado, laterais do moicano).
2. A ROUPA decide a cor de cada região (veja `palette`): a regata deixa o ombro (U) com cor de pele,
   a bermuda deixa a canela (N) de fora, o top deixa a barriga (Y) de fora, a manga longa pinta o braço (A)...
3. Um SOMBREADO AUTOMÁTICO dá volume: pixel encostado no contorno pela esquerda ganha sombra,
   pela direita ganha luz. Por isso cada região usa uma letra só.
4. O CABELO é outro molde, pintado por cima da cabeça. Quase todos começam pela mesma "touca" (CAP).

Como no Habbo, o rosto fica virado um pouco para a direita (orelha à esquerda, nariz saltando à direita).
De frente e de lado usamos essa pose (a esquerda é o espelho); de costas, a cabeça inteira vira cabelo.
Quadros: 0 = parado, 1 e 2 = passos (uma perna levanta e os braços balançam ao contrário).
"""
from __future__ import annotations

import pygame

from game.data.looks import CLOTH_COLORS, HAIR_COLORS, SHOE_COLORS, SKIN_TONES, Look

W, H = 20, 40
TOP_PAD = 2                     # linhas livres acima da cabeça (para topete, coque, black power...)
OUTLINE = (34, 26, 30)
EYE_WHITE = (252, 252, 252)
PUPIL = (30, 30, 40)
LIPS = (150, 64, 60)
SOLE = (240, 240, 236)

# ------------------------------------------------------------------ corpo (38 linhas)
HEAD = [
    "......KKKKKKK.......",
    "....KKSSSSSSSKK.....",
    "...KSSSSSSSSSSSK....",
    "...KSSSSSSSSSSSK....",
    "...KSSSSSSSSSSSK....",
    "...KSSSKKSSKKSSK....",   # sobrancelhas
    "...KSSSWESSWESSK....",   # olhos
    "..KSSSSWESSWESSSK...",   # orelha (esq.) e nariz saltando (dir.)
    "..KSKSSSSSSSSSSSK...",
    "...KSSSSSSSSSSSK....",
    "...KSSSSSSMMMSSK....",   # boca sorrindo
    "....KSSSSSSSSSK.....",
    ".....KKSSSSSKK......",
]
NECK = [
    "........KSSK........",
]
TORSO = [
    "...KUUUUUSSUUUUUK...",
    "..KUUUUUUTTUUUUUUK..",
    "..KUUKTTTTTTTTKUUK..",
    "..KUUKTTTTTTTTKUUK..",
    "..KAAKTTTTTTTTKAAK..",
    "..KAAKTTTTTTTTKAAK..",
    "..KAAKYYYYYYYYKAAK..",
    "..KAAKYYYYYYYYKAAK..",
    "..KSSKYYYYYYYYKSSK..",
    "..KSSKBBBBBBBBKSSK..",
    "...KKKLLLLLLLLKKK...",
]
LEGS = [
    ".....KLLLLLLLLK.....",
    ".....KLLLKKLLLK.....",
    ".....KLLLKKLLLK.....",
    ".....KLLLKKLLLK.....",
    ".....KLLLKKLLLK.....",
    ".....KNNNKKNNNK.....",
    ".....KNNNKKNNNK.....",
    ".....KNNNKKNNNK.....",
    ".....KNNNKKNNNK.....",
    ".....KFFFKKFFFFK....",   # pés em diagonal, como no Habbo
    "....KFFFFKKFFFFFK...",
    "....KOOOOKKOOOOOK...",
    ".....KKKK..KKKKK....",
]
FRONT = HEAD + NECK + TORSO + LEGS
def _no_face(row: str) -> str:
    """A cabeça vista de trás: só o contorno de fora; olhos, boca, sobrancelhas e orelha viram pele."""
    inside = [x for x, ch in enumerate(row) if ch != "."]
    return "".join("S" if inside[0] < x < inside[-1] and ch != "." else ch for x, ch in enumerate(row))


BACK_HEAD = [_no_face(r) for r in HEAD]
TORSO_TOP = len(HEAD) + len(NECK)
LEG_TOP = TORSO_TOP + len(TORSO)
ARM_LEFT, ARM_RIGHT = range(2, 5), range(15, 18)
LEG_LEFT, LEG_RIGHT = range(4, 10), range(10, 18)

# Saia e vestido por cima das coxas (a partir da linha SKIRT_ROW do corpo)
SKIRT_ROW = LEG_TOP - 1
SKIRT = [
    "....KLLLLLLLLLLK....",
    "....KLLLLLLLLLLK....",
    "...KLLLLLLLLLLLLK...",
    "...KLLLLLLLLLLLLK...",
    "...KKKKKKKKKKKKKK...",
]
DRESS = [*SKIRT[:-1], "..KLLLLLLLLLLLLLLK..", "..KLLLLLLLLLLLLLLK..", "..KLLLLLLLLLLLLLLK..", "..KKKKKKKKKKKKKKKK.."]

# ------------------------------------------------------------------ cabelo
# Cada molde começa 2 linhas ACIMA do topo da cabeça (TOP_PAD). "." não pinta nada; "S" repinta pele.
# `cap` = pintar antes a touca padrão (CAP). As costas são calculadas: a cabeça vira cabelo até a nuca
# (`nape`, linha da cabeça) e, por cima, entra a silhueta do penteado; `long` = o cabelo desce pelas costas.
CAP = [
    "....................",
    "......KKKKKKKK......",
    "....KKHHHHHHHHKK....",
    "...KHHHHHHHHHHHHK...",
    "..KHHHHHHHHHHHHHHK..",
    "..KHHHHHHHHHHHHHHK..",
    "..KHHHHKHHHHKHHHHK..",
    "..KHHK.........KHK..",
    "..KHK...............",
]
HAIR = {
    "curto": {"rows": [], "cap": True, "nape": 9},
    "espetado": {
        "rows": [
            "...K...K...K...K....",
            "..KHK.KHK.KHK.KHK...",
            "..KHHKHHHKHHHKHHHK..",
        ],
        "cap": True, "nape": 9,
    },
    "topete": {
        "rows": [
            ".......KKKKKKKK.....",
            "......KHHHHHHHHKK...",
            ".....KHHHHHHHHHHHK..",
            "...KHHHHHHHHHHHHHHK.",
            "..KHHHHHHHHHHHHHHK..",
            "..KHHHHHHHHHHHHHK...",
            "..KHHHK....KKKKK....",
            "..KHHK..............",
            "..KHK...............",
        ],
        "cap": False, "nape": 9,
    },
    "moicano": {
        "rows": [
            ".........KK.........",
            "........KHHK........",
            "......KKKHHKKK......",
            "....KKhhKHHKhhKK....",
            "...KhhhhKHHKhhhhK...",
            "..KhhhhhKHHKhhhhhK..",
            "..KhhhhhhKKhhhhhhK..",
            "..Khh...........hK..",
        ],
        "cap": False, "nape": -1,
    },
    "black": {
        "rows": [
            "....KKKKKKKKKKKK....",
            "...KHHHHHHHHHHHHK...",
            "..KHHHHHHHHHHHHHHK..",
            ".KHHHHHHHHHHHHHHHHK.",
            ".KHHHHHHHHHHHHHHHHK.",
            ".KHHHHHHHHHHHHHHHHK.",
            ".KHHHHKHHHHHKHHHHHK.",
            ".KHHHK..........KHK.",
            ".KHHK...........KHK.",
            "..KK.............KK.",
        ],
        "cap": False, "nape": 9, "long": True,
    },
    "raspado": {
        "rows": [
            "", "",
            "......KKKKKKK.......",
            "....KKhhhhhhhKK.....",
            "...KhhhhhhhhhhhK....",
            "...KhhhhhhhhhhhK....",
            "...KhSSSSSSSSShK....",
        ],
        "cap": False, "nape": 9, "back_color": "h",
    },
    "chanel": {
        "rows": [
            "", "", "", "", "", "",
            "..KHHHHHHHHHHHHHHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHHK.......KHHK..",
            "...KKK.........KK...",
        ],
        "cap": True, "nape": 11, "long": True,
    },
    "longo": {
        "rows": [
            "", "", "", "", "", "",
            "..KHHHHHHHHHHHHHHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHK..",
            "..KHHK.........KHHK.",
            "..KHHK.........KHHK.",
            "..KHHK.........KHHK.",
            "..KHHK.........KHHK.",
            "..KHHK.........KHHK.",
            "..KHHK.........KHHK.",
            "..KHHK.........KHHK.",
            "...KK...........KK..",
        ],
        "cap": True, "nape": 11, "long": True,
    },
    "rabo": {
        "rows": [
            "", "", "", "", "", "",
            "KKKHHHHKHHHHKHHHHK..",
            "KHHK...........KHK..",
            "KHHK................",
            "KHHK................",
            "KHHK................",
            ".KHHK...............",
            ".KHHK...............",
            "..KK................",
        ],
        "cap": True, "nape": 9,
        "back_extra": [
            "", "", "", "", "", "", "", "", "", "", "", "",
            "........KHHK........",
            "........KHHK........",
            "........KHHK........",
            "........KHHK........",
            ".........KK.........",
        ],
    },
    "chiquinhas": {
        "rows": [
            "", "", "", "",
            ".KK..............KK.",
            "KHHK............KHHK",
            "KHHKHHHKHHHHKHHHKHHK",
            "KHHKHK.........KKHHK",
            "KHHKK...........KHHK",
            "KHHK............KHHK",
            "KHHK............KHHK",
            ".KHHK..........KHHK.",
            ".KHHK..........KHHK.",
            "..KK............KK..",
        ],
        "cap": True, "nape": 9,
    },
    "coque": {
        "rows": [
            "........KKKK........",
            ".......KHHHHK.......",
            "......KHHHHHHK......",
        ],
        "cap": True, "nape": 9,
    },
    "cacheado": {
        "rows": [
            "....KK.KKKKK.KK.....",
            "...KHHKHHHHHKHHK....",
            "..KHHHHHHHHHHHHHK...",
            ".KHHHHHHHHHHHHHHHK..",
            "KHHHHHHHHHHHHHHHHHK.",
            "KHHHHHHHHHHHHHHHHHK.",
            "KHHHHHKHHHHHKHHHHHK.",
            "KHHHHK.........KHHK.",
            "KHHHK...........KHHK",
            "KHHHK...........KHHK",
            "KHHHK...........KHHK",
            "KHHHK...........KHHK",
            "KHHHK...........KHHK",
            "KHHHHK.........KHHHK",
            "KHHHHK.........KHHK.",
            ".KHHK...........KK..",
            "..KK................",
        ],
        "cap": False, "nape": 11, "long": True,
    },
}

_cache: dict = {}
_SHADED = set("SAUTYLNFH")      # regiões que ganham luz/sombra automática


# ------------------------------------------------------------------ cores
def _darker(color, factor=0.66):
    return tuple(int(c * factor) for c in color)


def _lighter(color, amount=36):
    return tuple(min(255, c + amount) for c in color)


def palette(look: Look) -> dict:
    """Cor de cada região do corpo para esta roupa (a roupa decide o que cobre o quê)."""
    skin = SKIN_TONES[look.skin % len(SKIN_TONES)][0]
    dress = look.bottom == "vestido"
    top = CLOTH_COLORS[look.legs if dress else look.shirt][0]
    bottom, belt = CLOTH_COLORS[look.legs]
    hair, hair_dark = HAIR_COLORS[look.hair_color]
    colors = {
        "K": OUTLINE, "W": EYE_WHITE, "E": PUPIL, "M": LIPS, "O": SOLE,
        "S": skin, "H": hair, "h": hair_dark,
        "U": top if look.top in ("camisa", "manga curta", "manga longa") else skin,   # regata e top: ombro de fora
        "A": top if look.top == "manga longa" else skin,
        "T": top,
        "Y": skin if look.top == "top" and not dress else top,                          # top: barriga de fora
        "B": top if dress else belt,
        "L": bottom,
        "N": bottom if look.bottom == "calça" else skin,                               # bermuda/saia: canela de fora
        "F": SHOE_COLORS[look.shoes],
    }
    for letter in "UASLNFO":    # lado de lá do corpo: mais escuro
        colors[letter.lower()] = _darker(colors[letter], 0.8)
    return colors


# ------------------------------------------------------------------ moldes
def _paint(surf, rows, colors, top=0):
    """Pinta um molde com o sombreado automático (sombra atrás, luz na frente e no alto)."""
    for y, row in enumerate(rows):
        if not 0 <= top + y < H:
            continue
        for x, ch in enumerate(row):
            color = colors.get(ch)
            if color is None:
                continue
            if ch in _SHADED:
                left = row[x - 1] if x > 0 else "K"
                right = row[x + 1] if x + 1 < len(row) else "K"
                above = rows[y - 1][x] if y > 0 and x < len(rows[y - 1]) else "K"
                if left == "K":
                    color = _darker(color, 0.78)
                elif right == "K" or (above == "K" and ch == "H"):
                    color = _lighter(color)
            surf.set_at((x, top + y), color)


def _pad(rows):
    """Encosta o molde no chão: completa por cima até a altura H (pés sempre na última linha)."""
    return ["." * W] * (H - len(rows)) + list(rows)


def _walk(rows, step):
    """Passo: uma perna levanta 2 px (a outra fica no chão) e os braços balançam ao contrário."""
    lifted, forward_arm, back_arm = ((LEG_LEFT, ARM_RIGHT, ARM_LEFT) if step == 1
                                     else (LEG_RIGHT, ARM_LEFT, ARM_RIGHT))
    grid = [list(r) for r in rows]
    for y in range(LEG_TOP + 1, len(rows)):
        for x in lifted:
            grid[y][x] = rows[y + 2][x] if y + 2 < len(rows) else "."
    for y in range(TORSO_TOP + 2, LEG_TOP):
        for x in forward_arm:                   # braço que vai para frente desce 1 px
            grid[y][x] = rows[y - 1][x]
        for x in back_arm:                      # braço que vai para trás sobe 1 px
            grid[y][x] = rows[y + 1][x]
    return ["".join(r) for r in grid]


def _span(row: str) -> range:
    """Colunas entre o primeiro e o último pixel de uma linha."""
    inside = [x for x, ch in enumerate(row) if ch != "."]
    return range(inside[0], inside[-1] + 1) if inside else range(0)


def _back_hair(style: dict) -> list[str]:
    """Cabelo visto de costas: a cabeça vira cabelo até a nuca e, por cima, a silhueta do penteado.

    O vão do rosto é preenchido; nos penteados `long`, o vão entre as mechas também (cabelo nas costas).
    """
    letter = style.get("back_color", "H")
    rows = ["." * W] * TOP_PAD
    rows += [r.replace("S", letter) if i <= style["nape"] else "." * W for i, r in enumerate(BACK_HEAD)]
    layers = ([CAP] if style["cap"] else []) + [style["rows"]]
    rows += ["." * W] * (max(len(layer) for layer in layers) - len(rows))
    for layer in layers:
        for i, row in enumerate(layer):
            span = _span(row)
            if not span:
                continue
            head = i - TOP_PAD
            fill = span if style.get("long") else (_span(BACK_HEAD[head]) if 0 <= head <= style["nape"] else range(0))
            inner = range(fill[0] + 1, fill[-1]) if fill else range(0)   # dentro do contorno da cabeça
            filled = list(rows[i])
            for x, ch in enumerate(row):
                if ch == ".":
                    if x in inner:
                        filled[x] = letter
                elif ch == "S":
                    continue
                elif ch == "K" and x in inner:
                    filled[x] = letter      # contorno da franja/nuca que, visto de trás, fica no meio do cabelo
                else:
                    filled[x] = ch
            rows[i] = "".join(filled)
    return rows


FALLBACK_HAIR = {"careca": "raspado"}   # penteados do Mana Seed que aqui têm outro nome


def _hair_layers(look: Look, back: bool) -> list[list[str]]:
    style = HAIR.get(FALLBACK_HAIR.get(look.hair, look.hair), HAIR["curto"])
    if back:
        return [_back_hair(style), style.get("back_extra", [])]
    return ([CAP] if style["cap"] else []) + [style["rows"]]


def _frame(look: Look, direction: str, step: int) -> pygame.Surface:
    colors = palette(look)
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    back = direction == "up"
    body = FRONT
    if back:
        body = BACK_HEAD + body[len(HEAD):]
    if step:
        body = _walk(body, step)
    body = _pad(body)
    head_top = next(i for i, r in enumerate(body) if "K" in r)
    _paint(surf, body, colors)
    if look.bottom in ("saia", "vestido"):
        _paint(surf, SKIRT if look.bottom == "saia" else DRESS, colors, top=head_top + SKIRT_ROW)
    for layer in _hair_layers(look, back):
        _paint(surf, layer, colors, top=head_top - TOP_PAD)
    if direction == "left":
        surf = pygame.transform.flip(surf, True, False)
    return surf


def character_frames(look: Look) -> dict:
    """{(direção, quadro): Surface 20 x 40}."""
    if look not in _cache:
        frames = {(d, i): _frame(look, d, i) for d in ("down", "up", "right", "left") for i in range(3)}
        if pygame.display.get_surface() is not None:
            frames = {k: v.convert_alpha() for k, v in frames.items()}
        _cache[look] = frames
    return _cache[look]


def face(look: Look) -> pygame.Surface:
    """Retrato para a caixa de diálogo: a cabeça, ampliada e recortada em 38 x 38."""
    key = ("face", look)
    if key not in _cache:
        head = character_frames(look)[("down", 0)].subsurface((1, 0, 18, 17))
        big = pygame.transform.scale(head, (45, 42))
        out = pygame.Surface((38, 38))
        out.fill((120, 168, 216))
        out.blit(big, (-4, 0))
        _cache[key] = out
    return _cache[key]

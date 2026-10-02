"""Guarda-roupa: peças novas (camisa, regata, top, manga longa, calça, bermuda, shorts, saia, vestido, tênis)
feitas a partir das roupas desenhadas pelo artista do Mana Seed.

A ideia (leia na ordem):
1. O corpo base do Mana Seed é desenhado SEM roupa. Então, se apagamos um pedaço da roupa, aparece a pele
   que já está desenhada embaixo: regata = camisa sem as mangas, bermuda = calça sem a canela.
2. A roupa do lenhador (`fstr`) serve de MOLDE: cada cor dela marca uma parte do corpo.
       vermelho = mangas | bege acima do cinto = tronco | azul-marinho = cinto | bege abaixo = pernas
   A manga longa vem da túnica do fazendeiro (`pfpn`), tudo o que fica acima do cinto dourado dela.
3. Cada peça é pintada com a cor escolhida no MESMO tom relativo do original (sombra continua sombra).
4. Saia e vestido não existem no pacote: são desenhados por cima das pernas, quadro a quadro, seguindo a
   largura das pernas (por isso abrem quando o boneco anda), com contorno e sombra.
Os moldes são calculados uma vez só (`_molds`); para cada aparência só pintamos os pixels já separados.
"""
from __future__ import annotations

import os

import pygame

from game.data.looks import CLOTH_COLORS, SHOE_COLORS, Look

FRAME = 64
OUTLINE = (24, 24, 24)
# cores da roupa do lenhador (fstr_v01) e da túnica do fazendeiro (pfpn_v01)
NAVY = {(30, 43, 65), (60, 85, 117)}
RED = {(91, 24, 57), (141, 34, 70), (190, 86, 103)}
GOLD = {(129, 92, 33), (178, 145, 73), (224, 210, 142)}
BELT_COLOR = (70, 46, 34)
CELLS = [(row, 0) for row in range(4)] + [(row, col) for row in range(4, 8) for col in range(6)]

_molds: dict = {}
_layers: dict = {}


def _lum(color) -> float:
    r, g, b = color[:3]
    return 0.3 * r + 0.59 * g + 0.11 * b


def _tone(target, ratio) -> tuple:
    """A cor escolhida, clareada ou escurecida na mesma proporção do tom original."""
    if ratio <= 1:
        return tuple(max(0, min(255, round(c * ratio))) for c in target)
    return tuple(min(255, round(c + (255 - c) * min(1.0, ratio - 1) * 0.3)) for c in target)


class Mold:
    """As partes de UM quadro: cada parte é uma lista de (x, y, cor original)."""

    def __init__(self):
        self.parts: dict[str, list] = {}
        self.belt = 0          # linha do cinto
        self.bottom = 0        # linha mais baixa (pés)
        self.chest = 0         # linha do corte do top
        self.knee = 0          # linha do corte da bermuda
        self.thigh = 0         # linha do corte do shorts (mais alto que a bermuda)

    def add(self, part, x, y, color):
        self.parts.setdefault(part, []).append((x, y, color))


def _cell_pixels(sheet, row, col):
    pixels = {}
    for y in range(FRAME):
        for x in range(FRAME):
            color = sheet.get_at((col * FRAME + x, row * FRAME + y))
            if color.a:
                pixels[(x, y)] = tuple(color)[:3]
    return pixels


def _busiest_row(pixels, colors, below: int = 0) -> int | None:
    """Linha com mais pixels dessas cores (só a partir da linha `below`): é onde fica o cinto."""
    rows: dict = {}
    for (_, y), color in pixels.items():
        if color in colors and y >= below:
            rows[y] = rows.get(y, 0) + 1
    return max(rows, key=rows.get) if rows else None


def _region(x, y, color, mold: Mold) -> str:
    if color in RED:
        return "sleeves"
    if color in NAVY and y in (mold.belt, mold.belt + 1):
        return "belt"
    if y < mold.belt:
        return "torso"
    return "legs"


def _classify(pixels, mold: Mold) -> dict:
    """Papel de cada pixel do molde. O contorno fica com a parte vizinha mais comum."""
    roles = {p: _region(*p, c, mold) for p, c in pixels.items() if c != OUTLINE}
    for (x, y), color in pixels.items():
        if color != OUTLINE:
            continue
        near = [roles[(x + dx, y + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (x + dx, y + dy) in roles]
        roles[(x, y)] = max(set(near), key=near.count) if near else ("torso" if y < mold.belt else "legs")
    # tênis: os 2 pixels mais baixos de cada coluna das pernas
    lowest: dict = {}
    for (x, y), role in roles.items():
        if role == "legs":
            lowest.setdefault(x, []).append(y)
    for x, ys in lowest.items():
        for y in sorted(ys)[-3:]:
            roles[(x, y)] = "shoes"
    return roles


def _mold_cell(fstr, pfpn, row, col) -> Mold:
    mold = Mold()
    pixels = _cell_pixels(fstr, row, col)
    if not pixels:
        return mold
    mold.bottom = max(y for _, y in pixels)
    top = min(y for _, y in pixels)
    mold.belt = _busiest_row(pixels, NAVY) or (top + mold.bottom) // 2
    mold.chest = top + round((mold.belt - top) * 0.55)
    mold.knee = mold.belt + round((mold.bottom - mold.belt) * 0.5)
    mold.thigh = mold.belt + round((mold.bottom - mold.belt) * 0.28)
    for (x, y), role in _classify(pixels, mold).items():
        mold.add(role, x, y, pixels[(x, y)])
    long_pixels = _cell_pixels(pfpn, row, col)
    long_belt = _busiest_row(long_pixels, GOLD, below=mold.belt - 2) or mold.belt   # a gola também é dourada
    for (x, y), color in long_pixels.items():
        if y < long_belt:
            mold.add("long", x, y, color)
    return mold


def molds() -> dict:
    """{(linha, coluna): Mold} — calculado uma vez a partir das folhas do pacote."""
    if not _molds:
        from game.graphics.mana_seed import PAGE_DIR
        fstr = pygame.image.load(os.path.join(PAGE_DIR, "1out", "char_a_p1_1out_fstr_v01.png"))
        pfpn = pygame.image.load(os.path.join(PAGE_DIR, "1out", "char_a_p1_1out_pfpn_v01.png"))
        for cell in CELLS:
            _molds[cell] = _mold_cell(fstr, pfpn, *cell)
    return _molds


# ------------------------------------------------------------------ pintura
def _paint(surf, ox, oy, pixels, target, keep=lambda x, y: True, hem=None):
    """Pinta uma parte com a cor `target`. `keep` corta pedaços; na linha `hem` vira contorno (barra)."""
    colored = [c for _, _, c in pixels if c != OUTLINE]
    if not colored:
        return
    main = max(set(colored), key=colored.count)
    for x, y, color in pixels:
        if not keep(x, y):
            continue
        out = OUTLINE if color == OUTLINE or y == hem else _tone(target, _lum(color) / _lum(main))
        surf.set_at((ox + x, oy + y), out)


def _skirt(surf, ox, oy, mold: Mold, target, hem: int):
    """Saia desenhada por cima das pernas: segue a largura das pernas e abre 1 px a cada 4 linhas."""
    legs = mold.parts.get("legs", []) + mold.parts.get("shoes", [])
    span = None
    for y in range(mold.belt + 1, hem + 1):
        xs = [x for x, yy, _ in legs if yy == y]
        if xs:
            span = (min(xs), max(xs))
        if span is None:
            continue
        flare = (y - mold.belt) // 4
        left, right = span[0] - flare, span[1] + flare
        for x in range(left, right + 1):
            if x in (left, right) or y == hem:
                color = OUTLINE
            elif x == left + 1:
                color = _tone(target, 1.15)
            elif x == right - 1 or y == hem - 1:
                color = _tone(target, 0.72)
            else:
                color = target
            surf.set_at((ox + x, oy + y), color)


def _cell(surf, ox, oy, mold: Mold, look: Look):
    top_color = CLOTH_COLORS[look.legs if look.bottom == "vestido" else look.shirt][0]
    bottom_color = CLOTH_COLORS[look.legs][0]
    parts = mold.parts
    # parte de baixo
    if look.bottom in ("calça", "bermuda", "shorts"):
        cut = {"bermuda": mold.knee, "shorts": mold.thigh}.get(look.bottom)
        _paint(surf, ox, oy, parts.get("legs", []), bottom_color,
               keep=(lambda x, y: y <= cut) if cut is not None else (lambda x, y: True), hem=cut)
    _paint(surf, ox, oy, parts.get("shoes", []), SHOE_COLORS[look.shoes])
    if look.bottom in ("saia", "vestido"):
        hem = mold.knee if look.bottom == "saia" else mold.bottom - 3
        _skirt(surf, ox, oy, mold, bottom_color, hem)
    # parte de cima
    if look.top == "manga longa":
        _paint(surf, ox, oy, parts.get("long", []), top_color)
    else:
        cut = mold.chest if look.top == "top" else None
        _paint(surf, ox, oy, parts.get("torso", []), top_color,
               keep=(lambda x, y: y <= cut) if cut is not None else (lambda x, y: True), hem=cut)
        if look.top in ("camisa", "manga curta"):
            _paint(surf, ox, oy, parts.get("sleeves", []), top_color)
    if look.top != "top" or look.bottom == "vestido":
        _paint(surf, ox, oy, parts.get("belt", []), top_color if look.bottom == "vestido" else BELT_COLOR)


def clothes_layer(look: Look) -> pygame.Surface:
    """A folha (512 x 512) só com as roupas desta aparência, para empilhar sobre o corpo."""
    key = (look.top, look.shirt, look.bottom, look.legs, look.shoes)
    if key not in _layers:
        sheet = pygame.Surface((8 * FRAME, 8 * FRAME), pygame.SRCALPHA)
        for (row, col), mold in molds().items():
            _cell(sheet, col * FRAME, row * FRAME, mold, look)
        _layers[key] = sheet
    return _layers[key]


# ------------------------------------------------------------------ cortes de cabelo novos
EYE_WHITE = (248, 240, 224)     # branco do olho no corpo base: marca a altura dos olhos
LONG_EXTRA = 7                  # quantas linhas o cabelo longo desce além do chanel


def _eye_row(body_pixels: dict) -> int:
    eyes = [y for (_, y), c in body_pixels.items() if c == EYE_WHITE]
    top = min((y for _, y in body_pixels), default=0)
    return min(eyes) if eyes else top + 9      # de costas não há olhos: altura média dos olhos


def _shaved(hair: dict, body: dict) -> dict:
    """Raspado: só o cabelo colado no crânio, acima da testa (sem volume e sem franja)."""
    limit = _eye_row(body) - 3
    return {p: c for p, c in hair.items() if p in body and p[1] <= limit}


def _long(hair: dict, body: dict) -> dict:
    """Longo: as mechas que já passam da altura dos olhos (laterais e nuca) descem mais LONG_EXTRA linhas,
    repetindo os 2 últimos tons de cada coluna; a ponta ganha contorno."""
    out = dict(hair)
    eyes = _eye_row(body)
    columns: dict = {}
    for (x, y) in hair:
        columns.setdefault(x, []).append(y)
    for x, ys in columns.items():
        bottom = max(ys)
        if bottom < eyes + 1:
            continue                                     # franja: não desce sobre o rosto
        colors = [hair[(x, y)] for y in sorted(ys) if hair[(x, y)] != OUTLINE][-2:]
        if not colors:
            continue
        for k in range(LONG_EXTRA):
            out[(x, bottom + k)] = colors[k % len(colors)]
        out[(x, bottom + LONG_EXTRA)] = OUTLINE
    return out


CURLY_EXTRA = 4                 # o cacheado desce um pouco abaixo do chanel (até o ombro)


SIDES = ((1, 0), (-1, 0), (0, -1), (0, 1))


def _curly(hair: dict, body: dict) -> dict:
    """Cacheado: o chanel com VOLUME (1 px a mais em volta, menos sobre o rosto), pontas que descem até o
    ombro em ondas, contorno recortado em bolinhas e "cachos" (pontos claros e escuros) por dentro."""
    tones = sorted({c for c in hair.values() if c != OUTLINE}, key=_lum)
    if not tones:
        return dict(hair)
    eyes = _eye_row(body)

    def over_face(p):
        return p in body and p[1] >= eyes - 2 and p not in hair

    shape = _curly_volume(_curly_ends(hair, eyes), eyes, over_face)
    out = _curly_paint(shape, hair, (tones[0], tones[len(tones) // 2], tones[-1]))
    for (x, y), color in list(out.items()):              # fecha o contorno onde o recorte abriu buraco
        if color != OUTLINE:
            for dx, dy in SIDES:
                p = (x + dx, y + dy)
                if p not in out and not over_face(p):
                    out[p] = OUTLINE
    return out


def _curly_ends(hair: dict, eyes: int) -> set:
    """As mechas que já passam dos olhos descem CURLY_EXTRA linhas, uma coluna sim, outra não (ondas)."""
    mask = set(hair)
    columns: dict = {}
    for (x, y) in hair:
        columns.setdefault(x, []).append(y)
    for x, ys in columns.items():
        bottom = max(ys)
        if bottom >= eyes + 1:
            mask |= {(x, bottom + k) for k in range(1, CURLY_EXTRA - (x % 2) + 1)}
    return mask


def _curly_volume(mask: set, eyes: int, over_face) -> set:
    """1 px de volume para fora, sem cobrir o rosto e sem crescer para baixo acima dos olhos."""
    grown = set(mask)
    for (x, y) in mask:
        for dx, dy in SIDES:
            p = (x + dx, y + dy)
            if p not in mask and not over_face(p) and (dy != 1 or y >= eyes):
                grown.add(p)
    return grown


def _curly_paint(shape: set, hair: dict, tones) -> dict:
    """Contorno recortado em bolinhas e, por dentro, pontos claros e escuros que parecem cachos."""
    dark, mid, light = tones
    out = {}
    for (x, y) in shape:
        if any((x + dx, y + dy) not in shape for dx, dy in SIDES):
            if (x * 7 + y * 3) % 4 or (x, y) in hair:
                out[(x, y)] = OUTLINE
            continue
        curl = (x * 3 + y * 5) % 7
        base = hair.get((x, y), mid)
        out[(x, y)] = light if curl == 0 else dark if curl == 4 else (mid if base == OUTLINE else base)
    return out


HAIR_MAKERS = {"raspado": ("dap1", _shaved), "longo": ("bob1", _long), "cacheado": ("bob1", _curly)}


def hair_layer(style: str, hair_path: str, body_path: str) -> pygame.Surface:
    """Folha do cabelo `style` feita a partir do arquivo de cabelo do pacote (`hair_path`)."""
    key = ("hair", style, hair_path, body_path)
    if key not in _layers:
        hair_sheet, body_sheet = pygame.image.load(hair_path), pygame.image.load(body_path)
        maker = HAIR_MAKERS[style][1]
        sheet = pygame.Surface((8 * FRAME, 8 * FRAME), pygame.SRCALPHA)
        for row, col in CELLS:
            new = maker(_cell_pixels(hair_sheet, row, col), _cell_pixels(body_sheet, row, col))
            for (x, y), color in new.items():
                if 0 <= y < FRAME:
                    sheet.set_at((col * FRAME + x, row * FRAME + y), color)
        _layers[key] = sheet
    return _layers[key]

"""Prepara a arte dos LEGENDS a partir das folhas de referência (assets/legends/source/<id>.jpg).

Rode uma vez (ou quando trocar uma folha):  python tools/build_legends.py
Para cada legend ele salva em assets/legends/<id>/:
    front.png     vista de frente (o oponente na batalha)
    back.png      vista de costas (você na batalha)
    portrait.png  retrato do rosto (diálogos, editor de deck, faixa da transformação)
    splash.png    a ilustração grande (cena de transformação)

Como o fundo é tirado: as folhas têm fundo cinza-escuro liso. Pintamos de transparente só o cinza que está
LIGADO à borda do recorte (igual ao "balde de tinta" dos editores de imagem). Assim, partes escuras DENTRO do
personagem (roupa preta, sombra) não somem.
"""
import os
import sys
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "assets", "legends", "source")
OUT = os.path.join(ROOT, "assets", "legends")
TOLERANCE = (11, 11, 11, 255)      # quanto uma cor pode variar e ainda ser "fundo"
HALO_TOLERANCE = 30                # borda acinzentada do JPG em volta da figura
HALO_PASSES = 4
SHADOW_MIN, SHADOW_MAX, SHADOW_SPREAD = 13, 52, 7    # sombra do chão: cinza neutro escuro (o contorno é ~preto)
SHADOW_FROM = 0.6                                     # só da altura 60% para baixo (onde fica o chão)

# Recortes (x, y, largura, altura) medidos nas folhas 1312 x 1199
CROPS = {
    "cold": {"front": (642, 75, 176, 242), "back": (1135, 69, 164, 248),
             "portrait": (650, 374, 156, 170), "splash": (16, 4, 624, 972)},
    "drogoz": {"front": (628, 63, 159, 256), "back": (1098, 61, 201, 253),
               "portrait": (620, 343, 136, 195), "splash": (0, 3, 632, 913)},
    "mimo": {"front": (637, 82, 185, 241), "back": (1122, 85, 177, 239),
             "portrait": (651, 372, 152, 153), "splash": (0, 8, 640, 860)},
    "blitz": {"front": (650, 55, 176, 231), "back": (1130, 51, 174, 237),
              "portrait": (832, 316, 152, 157), "splash": (0, 4, 652, 899)},
}
KEEP_BACKGROUND = {"portrait"}     # o retrato fica com o quadro de fundo dele


def remove_background(img: pygame.Surface, background_color) -> pygame.Surface:
    """Deixa transparente o fundo (cor `background_color`) ligado às bordas da imagem."""
    out = img.convert_alpha().copy()
    w, h = out.get_size()
    near = pygame.mask.from_threshold(out, background_color, TOLERANCE)
    background = pygame.mask.Mask((w, h))
    border = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    for x, y in border:
        if near.get_at((x, y)) and not background.get_at((x, y)):
            background.draw(near.connected_component((x, y)), (0, 0))
    for y in range(h):
        for x in range(w):
            if background.get_at((x, y)):
                out.set_at((x, y), (0, 0, 0, 0))
    _remove_halo(out, background_color)
    _remove_shadows(out)
    return out


def _is_shadow(color) -> bool:
    """Cinza neutro escuro: a sombra que o desenho original projeta no chão (e atrás da capa)."""
    r, g, b = color[:3]
    return min(r, g, b) >= SHADOW_MIN and max(r, g, b) <= SHADOW_MAX and max(r, g, b) - min(r, g, b) <= SHADOW_SPREAD


def _remove_shadows(out: pygame.Surface) -> None:
    """Apaga as sombras ligadas ao que já é transparente ("balde de tinta" só pelo cinza de sombra).
    O contorno do personagem é quase preto, então ele segura o balde e protege o desenho."""
    w, h = out.get_size()
    top = int(h * SHADOW_FROM)
    queue = deque((x, y) for y in range(top, h) for x in range(w) if not out.get_at((x, y)).a)
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and top <= ny < h:
                color = out.get_at((nx, ny))
                if color.a and _is_shadow(color):
                    out.set_at((nx, ny), (0, 0, 0, 0))
                    queue.append((nx, ny))


def _remove_halo(out: pygame.Surface, background_color) -> None:
    """O JPG deixa uma borda cinza "suja" em volta da figura. A cada passada, apagamos os pixels quase da cor
    do fundo que encostam no que já é transparente (o contorno preto do desenho é bem mais escuro e fica)."""
    w, h = out.get_size()
    bg = background_color[:3]
    for _ in range(HALO_PASSES):
        clear = []
        for y in range(h):
            for x in range(w):
                color = out.get_at((x, y))
                if not color.a or max(abs(c - b) for c, b in zip(color[:3], bg, strict=True)) > HALO_TOLERANCE:
                    continue
                if any(0 <= x + dx < w and 0 <= y + dy < h and not out.get_at((x + dx, y + dy)).a
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    clear.append((x, y))
        for x, y in clear:
            out.set_at((x, y), (0, 0, 0, 0))


def build(legend_id: str, crops: dict) -> None:
    sheet = pygame.image.load(os.path.join(SOURCE, f"{legend_id}.jpg"))
    background_color = sheet.get_at((5, 5))         # o canto da folha é sempre fundo
    folder = os.path.join(OUT, legend_id)
    os.makedirs(folder, exist_ok=True)
    for name, rect in crops.items():
        piece = sheet.subsurface(pygame.Rect(rect)).copy()
        if name not in KEEP_BACKGROUND:
            piece = remove_background(piece, background_color)
            piece = piece.subsurface(piece.get_bounding_rect()).copy()    # corta a borda vazia
        pygame.image.save(piece, os.path.join(folder, f"{name}.png"))
    print(f"{legend_id}: ok")


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    for legend_id, crops in CROPS.items():
        if len(sys.argv) > 1 and legend_id not in sys.argv[1:]:
            continue
        build(legend_id, crops)


if __name__ == "__main__":
    main()

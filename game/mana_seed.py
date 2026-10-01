"""Personagens do "Mana Seed Character Base" (demo grátis, by Seliel the Shaper), montados em CAMADAS.

É um "paper doll" (boneca de papel): várias folhas de sprites com o MESMO desenho de quadros, uma por cima
da outra, na ordem do guia do autor:
    corpo (0bas)  ->  roupa  ->  cabelo (4har)  ->  chapéu (5hat)
As roupas (camisa, regata, saia...) e os cortes raspado/longo são montados em game/wardrobe.py a partir
das peças do pacote.
Como todas as folhas têm a mesma animação, trocar uma peça é só trocar o arquivo daquela camada.
As cores vêm prontas do artista: cada arquivo `_vNN` é uma variação de cor (pele, cabelo, roupa...).

Folha (page 1) = 512 x 512, quadros de 64 x 64:
    linhas 0-3: parado (coluna 0), olhando para baixo, cima, direita e esquerda
    linhas 4-7: andando (colunas 0-5), nas mesmas 4 direções
Sem a pasta assets/mana_seed, quem desenha as pessoas é game/people.py (desenho por código).
"""
from __future__ import annotations

import os

import pygame

from . import wardrobe
from .looks import HATS, Look
from .settings import ROOT_DIR

PAGE_DIR = os.path.join(ROOT_DIR, "assets", "mana_seed", "char_a_p1")
FRAME = 64
DIRECTIONS = ("down", "up", "right", "left")     # ordem das linhas na folha
WALK_ROW = 4                                     # primeira linha da caminhada
WALK_FRAMES = 6
CROP = pygame.Rect(16, 1, 32, 44)                # recorte do quadro 64 x 64: os pés ficam na última linha

# Escolhas da aparência (game/looks.py) -> arquivo do pacote: código da peça + variação de cor
SKINS = ["v01", "v02", "v03", "v04", "v05", "v06", "v07"]            # 7 tons humanos (looks.SKIN_TONES)
HAIRS = {"curto": "dap1", "chanel": "bob1", "raspado": "dap1", "longo": "bob1", "careca": None}
HAIR_VARIANTS = {
    "preto": "v13", "castanho": "v11", "loiro": "v03", "ruivo": "v05", "acobreado": "v04", "rosa": "v12",
    "vermelho": "v06", "roxo": "v07", "verde": "v08", "azul": "v09", "grisalho": "v10", "branco": "v01",
}
HAT_CODES = {"nenhum": None, "capuz": "pfht", "mago": "pnty"}


def _variant(options: list[str], name: str) -> str:
    """Cor -> arquivo: a primeira cor da lista é o v01, a segunda é o v02..."""
    return f"v{options.index(name) + 1:02d}" if name in options else "v01"


_cache: dict = {}


def available() -> bool:
    return os.path.isfile(_path("", "0bas", "humn", "v01"))


def _path(folder: str, layer: str, code: str, variant: str) -> str:
    return os.path.join(PAGE_DIR, folder, f"char_a_p1_{layer}_{code}_{variant}.png")


def files(look: Look) -> dict:
    """Arquivos do pacote que esta aparência usa: corpo, cabelo (de onde o corte sai) e chapéu."""
    look = look.fitted()
    used = {"body": _path("", "0bas", "humn", SKINS[look.skin % len(SKINS)])}
    hair = HAIRS[look.hair]
    if hair and look.hat != "capuz":            # o capuz cobre a cabeça toda
        used["hair"] = _path("4har", "4har", hair, HAIR_VARIANTS[look.hair_color])
    hat = HAT_CODES[look.hat]
    if hat:
        used["hat"] = _path("5hat", "5hat", hat, _variant(HATS[look.hat], look.hat_color))
    return used


def layers(look: Look) -> list[pygame.Surface]:
    """As camadas, de baixo para cima: corpo -> roupas (game/wardrobe.py) -> cabelo -> chapéu."""
    look = look.fitted()
    used = files(look)
    stack = [_image(used["body"]), wardrobe.clothes_layer(look)]
    if "hair" in used:
        if look.hair in wardrobe.HAIR_MAKERS:           # corte feito a partir de outro (raspado, longo)
            stack.append(wardrobe.hair_layer(look.hair, used["hair"], used["body"]))
        else:
            stack.append(_image(used["hair"]))
    if "hat" in used:
        stack.append(_image(used["hat"]))
    return stack


def _image(path: str) -> pygame.Surface:
    if path not in _cache:
        _cache[path] = pygame.image.load(path)
    return _cache[path]


def _page(look: Look) -> pygame.Surface:
    page = pygame.Surface((8 * FRAME, 8 * FRAME), pygame.SRCALPHA)
    for layer in layers(look):
        page.blit(layer, (0, 0))
    return page


def _cut(page: pygame.Surface, row: int, col: int) -> pygame.Surface:
    return page.subsurface((col * FRAME + CROP.x, row * FRAME + CROP.y, CROP.w, CROP.h)).copy()


def character_frames(look: Look) -> dict | None:
    """{(direção, 0): parado, (direção, 1|2): passos, (direção, "walk"): os 6 quadros da caminhada}.

    Devolve None sem a pasta do Mana Seed (aí entra o desenho por código)."""
    if not available():
        return None
    if look not in _cache:
        page = _page(look)
        frames: dict = {}
        for row, direction in enumerate(DIRECTIONS):
            walk = [_cut(page, WALK_ROW + row, col) for col in range(WALK_FRAMES)]
            frames[(direction, 0)] = _cut(page, row, 0)
            frames[(direction, 1)], frames[(direction, 2)] = walk[1], walk[4]
            frames[(direction, "walk")] = walk
        if pygame.display.get_surface() is not None:
            frames = {k: [f.convert_alpha() for f in v] if isinstance(v, list) else v.convert_alpha()
                      for k, v in frames.items()}
        _cache[look] = frames
    return _cache[look]


def face(look: Look) -> pygame.Surface | None:
    """Retrato 38 x 38: a cabeça do boneco de frente, ampliada 2x."""
    frames = character_frames(look)
    if frames is None:
        return None
    key = ("face", look)
    if key not in _cache:
        head = frames[("down", 0)].subsurface((7, 8, 19, 19))
        out = pygame.Surface((38, 38))
        out.fill((120, 168, 216))
        out.blit(pygame.transform.scale_by(head, 2), (0, 0))
        _cache[key] = out
    return _cache[key]

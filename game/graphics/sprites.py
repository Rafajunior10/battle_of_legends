"""Ponto único para pegar desenhos de personagens, monstros e rostos.

  * Pessoas (você e os NPCs): bonecos do Mana Seed montados em camadas (corpo, roupa, cabelo, chapéu)
    pela aparência escolhida (game/graphics/mana_seed.py). Sem o pacote, bonecos desenhados por código
    (game/graphics/people.py).
  * Monstros: vêm do pacote Ninja Adventure (game/graphics/assets.py); sem ele, viram a gosma desenhada por
    código (game/graphics/pixelart.py) — o "fallback".
"""
from __future__ import annotations

import os

import pygame

from game.data.looks import Look
from game.engine.settings import ROOT_DIR
from game.graphics import assets, mana_seed, people
from game.graphics import pixelart as art

_cache: dict = {}


def has_pack() -> bool:
    return assets.pack().available


def character_frames(look: Look) -> dict:
    """{(direção, quadro): Surface} de uma pessoa: Mana Seed (32 x 44) ou, sem ele, o boneco por código."""
    return mana_seed.character_frames(look) or people.character_frames(look)


def face(look: Look | None) -> pygame.Surface | None:
    """Retrato 38 x 38 para a caixa de diálogo."""
    if not look:
        return None
    return mana_seed.face(look) or people.face(look)


def fit_scale(img: pygame.Surface, height: int) -> int:
    """Ampliação inteira (pixel art não amplia pela metade) que deixa o desenho perto de `height` px."""
    return max(1, round(height / img.get_height()))


def monster_image(sprite: str | None, fallback_color: str = "green") -> pygame.Surface:
    """Monstro de frente (16 x 16). Sem pacote, vira a gosma desenhada por código."""
    key = ("monster", sprite, fallback_color)
    if key not in _cache:
        frames = assets.monster_frames(sprite) if sprite and has_pack() else None
        _cache[key] = frames[("down", 0)] if frames else art.slime_sprite(fallback_color)
    return _cache[key]


LEGEND_DIR = os.path.join(ROOT_DIR, "assets", "legends")


def legend_image(legend_id: str, view: str, height: int | None = None) -> pygame.Surface:
    """Arte do legend (assets/legends/<id>/<view>.png): "front", "back", "portrait" ou "splash".
    Com `height`, a imagem é reduzida (suavizada) para essa altura. Sem o arquivo, vira uma silhueta."""
    key = ("legend", legend_id, view, height)
    if key not in _cache:
        path = os.path.join(LEGEND_DIR, legend_id, f"{view}.png")
        if os.path.isfile(path):
            img = pygame.image.load(path)
            img = img.convert_alpha() if pygame.display.get_surface() else img
        else:
            img = pygame.Surface((64, 96), pygame.SRCALPHA)
            pygame.draw.ellipse(img, (60, 60, 80), (8, 0, 48, 96))
        if height and img.get_height() != height:
            width = max(1, round(img.get_width() * height / img.get_height()))
            img = pygame.transform.smoothscale(img.convert_alpha() if pygame.display.get_surface() else img,
                                               (width, height))
        _cache[key] = img
    return _cache[key]


def player_frames(ch) -> dict:
    return character_frames(ch.appearance)

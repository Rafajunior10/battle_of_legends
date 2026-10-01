"""Arte em arquivo: o pacote Ninja Adventure (pixel-boy, licença CC0), em `assets/ninja_adventure/`.

Funciona também com o zip original dentro de `assets/`. Se o pacote não estiver lá, quem chama
recebe None e o jogo continua com a arte desenhada por código (pixelart.py).

Formato das folhas de personagens e monstros: cada quadro tem 16x16; as COLUNAS são as direções
(baixo, cima, esquerda, direita) e as LINHAS são os quadros da animação.
"""
from __future__ import annotations

import io
import os
import zipfile

import pygame

from .settings import ROOT_DIR

ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
FRAME = 16                                      # quadros de 16x16
SHEET_DIRECTIONS = ("down", "up", "left", "right")   # colunas das folhas
CHARACTER_DIR = "actor/character"
MONSTER_DIR = "actor/monster"


class _Pack:
    """Índice dos PNGs do pacote, por caminho em minúsculas, vindo de um zip ou de uma pasta."""

    def __init__(self):
        self.zip = None
        self.files: dict[str, str] = {}
        self._images: dict[str, pygame.Surface] = {}
        self._scan()

    def _scan(self):
        if not os.path.isdir(ASSETS_DIR):
            return
        for entry in sorted(os.listdir(ASSETS_DIR)):
            path = os.path.join(ASSETS_DIR, entry)
            if entry.lower().endswith(".zip") and "ninja" in entry.lower():
                self.zip = zipfile.ZipFile(path)
                self.files = {_key(n): n for n in self.zip.namelist() if n.lower().endswith(".png")}
                return
            if os.path.isdir(path) and "ninja" in entry.lower():
                for folder, _, names in os.walk(path):
                    for name in names:
                        if name.lower().endswith(".png"):
                            full = os.path.join(folder, name)
                            self.files[_key(os.path.relpath(full, path))] = full
                return

    @property
    def available(self) -> bool:
        return bool(self.files)

    def find(self, *parts: str) -> str | None:
        """Primeiro arquivo cujo caminho termina com as partes dadas (sem diferenciar maiúsculas)."""
        tail = _key("/".join(parts))
        return next((k for k in self.files if k.endswith(tail)), None)

    def image(self, key: str) -> pygame.Surface:
        if key not in self._images:
            if self.zip:
                data = io.BytesIO(self.zip.read(self.files[key]))
                surf = pygame.image.load(data, key)
            else:
                surf = pygame.image.load(self.files[key])
            if pygame.display.get_surface() is not None:
                surf = surf.convert_alpha()
            self._images[key] = surf
        return self._images[key]

    def names_under(self, folder: str) -> list[str]:
        """Subpastas diretas de `folder` (ex.: os nomes dos personagens em Actor/Characters)."""
        prefix = _key(folder).rstrip("/") + "/"
        names = set()
        for k in self.files:
            i = k.find(prefix)
            if i >= 0:
                rest = k[i + len(prefix):].split("/")
                if len(rest) > 1:
                    names.add(rest[0])
        return sorted(names)


def _key(path: str) -> str:
    return path.replace("\\", "/").lower()


_pack: _Pack | None = None


def pack() -> _Pack:
    global _pack
    if _pack is None:
        _pack = _Pack()
    return _pack


def reset() -> None:
    """Esquece o índice (para testes ou depois de colocar o pacote com o jogo aberto)."""
    global _pack
    _pack = None


def character_names() -> list[str]:
    return pack().names_under(CHARACTER_DIR)


def _walk_frames(sheet: pygame.Surface) -> dict:
    """{(direção, quadro): Surface 16x16}, no mesmo formato de pixelart.character_frames.

    Quadro 0 = parado (linha 0); 1 e 2 = os dois passos (linhas 1 e 3). Algumas folhas têm só
    2 linhas (ex.: OldWoman, Child); aí os passos reaproveitam as linhas que existem.
    """
    rows = max(1, sheet.get_height() // FRAME)
    frames = {}
    for col, direction in enumerate(SHEET_DIRECTIONS):
        for frame, row in enumerate((0, 1 % rows, 3 % rows)):
            frames[(direction, frame)] = sheet.subsurface((col * FRAME, row * FRAME, FRAME, FRAME)).copy()
    return frames


def character_frames(name: str) -> dict | None:
    """Quadros de andar de um personagem do pacote. None se ele não existir."""
    key = pack().find(CHARACTER_DIR, name, "spritesheet.png")
    return _walk_frames(pack().image(key)) if key else None


def monster_frames(name: str) -> dict | None:
    """Quadros de um monstro. A folha se chama SpriteSheet.png na maioria das pastas e <Nome>.png em
    algumas (Slime, Mushroom...); tentamos os dois."""
    key = pack().find(MONSTER_DIR, name, "spritesheet.png") or pack().find(MONSTER_DIR, name, f"{name}.png")
    return _walk_frames(pack().image(key)) if key else None


def faceset(name: str) -> pygame.Surface | None:
    """Rosto 38x38 do personagem ou monstro, para as caixas de diálogo."""
    for folder in (CHARACTER_DIR, MONSTER_DIR):
        key = pack().find(folder, name, "faceset.png")
        if key:
            return pack().image(key)
    return None

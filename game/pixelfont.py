"""Fonte pixel feita à mão: letras nítidas na tela pequena (480 x 270), com os acentos do português.

Cada letra é um molde de "#" (pixel aceso) e "." (vazio), igual aos bonecos de game/people.py.
  * NORMAL: maiúsculas de 7 px, minúsculas de 5 px, com pernas (g, p, q, y) descendo 2 px.
  * SMALL: só maiúsculas de 5 px, para nomes apertados (o nome dentro da carta).
Letra acentuada = letra base + acento desenhado por cima (ACCENTS), então não precisa desenhar "á", "ã"...
Tamanhos grandes (títulos) são a fonte NORMAL ampliada 2x ou 3x: continua pixelada e nítida.
"""
from __future__ import annotations

from dataclasses import dataclass

import pygame


def _parse(data: str) -> dict[str, list[str]]:
    """Lê os blocos "letra + linhas" separados por linha em branco."""
    glyphs = {}
    for block in data.strip("\n").split("\n\n"):
        lines = block.split("\n")
        glyphs[lines[0]] = lines[1:]
    return glyphs


_NORMAL = """A
.###.
#...#
#...#
#####
#...#
#...#
#...#

B
####.
#...#
#...#
####.
#...#
#...#
####.

C
.###.
#...#
#....
#....
#....
#...#
.###.

D
####.
#...#
#...#
#...#
#...#
#...#
####.

E
#####
#....
#....
####.
#....
#....
#####

F
#####
#....
#....
####.
#....
#....
#....

G
.###.
#...#
#....
#.###
#...#
#...#
.####

H
#...#
#...#
#...#
#####
#...#
#...#
#...#

I
###
.#.
.#.
.#.
.#.
.#.
###

J
..###
...#.
...#.
...#.
#..#.
#..#.
.##..

K
#...#
#..#.
#.#..
##...
#.#..
#..#.
#...#

L
#....
#....
#....
#....
#....
#....
#####

M
#...#
##.##
#.#.#
#.#.#
#...#
#...#
#...#

N
#...#
##..#
#.#.#
#..##
#...#
#...#
#...#

O
.###.
#...#
#...#
#...#
#...#
#...#
.###.

P
####.
#...#
#...#
####.
#....
#....
#....

Q
.###.
#...#
#...#
#...#
#.#.#
#..#.
.##.#

R
####.
#...#
#...#
####.
#.#..
#..#.
#...#

S
.###.
#...#
#....
.###.
....#
#...#
.###.

T
#####
..#..
..#..
..#..
..#..
..#..
..#..

U
#...#
#...#
#...#
#...#
#...#
#...#
.###.

V
#...#
#...#
#...#
#...#
#...#
.#.#.
..#..

W
#...#
#...#
#...#
#.#.#
#.#.#
##.##
#...#

X
#...#
#...#
.#.#.
..#..
.#.#.
#...#
#...#

Y
#...#
#...#
.#.#.
..#..
..#..
..#..
..#..

Z
#####
....#
...#.
..#..
.#...
#....
#####

a
.....
.....
.###.
....#
.####
#...#
.####

b
#....
#....
####.
#...#
#...#
#...#
####.

c
....
....
.###
#...
#...
#...
.###

d
....#
....#
.####
#...#
#...#
#...#
.####

e
.....
.....
.###.
#...#
#####
#....
.###.

f
..##
.#..
####
.#..
.#..
.#..
.#..

g
.....
.....
.####
#...#
#...#
#...#
.####
....#
.###.

h
#....
#....
####.
#...#
#...#
#...#
#...#

i
#
.
#
#
#
#
#

ı
.
.
#
#
#
#
#

j
..#
...
..#
..#
..#
..#
..#
#.#
.#.

k
#...
#...
#..#
#.#.
##..
#.#.
#..#

l
#.
#.
#.
#.
#.
#.
.#

m
.....
.....
##.#.
#.#.#
#.#.#
#.#.#
#.#.#

n
.....
.....
####.
#...#
#...#
#...#
#...#

o
.....
.....
.###.
#...#
#...#
#...#
.###.

p
.....
.....
####.
#...#
#...#
#...#
####.
#....
#....

q
.....
.....
.####
#...#
#...#
#...#
.####
....#
....#

r
....
....
#.##
##..
#...
#...
#...

s
.....
.....
.####
#....
.###.
....#
####.

t
.#..
.#..
####
.#..
.#..
.#..
..##

u
.....
.....
#...#
#...#
#...#
#...#
.####

v
.....
.....
#...#
#...#
#...#
.#.#.
..#..

w
.....
.....
#...#
#...#
#.#.#
#.#.#
.#.#.

x
.....
.....
#...#
.#.#.
..#..
.#.#.
#...#

y
.....
.....
#...#
#...#
#...#
#...#
.####
....#
.###.

z
.....
.....
#####
...#.
..#..
.#...
#####

0
.###.
#...#
#..##
#.#.#
##..#
#...#
.###.

1
.#.
##.
.#.
.#.
.#.
.#.
###

2
.###.
#...#
....#
...#.
..#..
.#...
#####

3
####.
....#
....#
.###.
....#
....#
####.

4
...#.
..##.
.#.#.
#..#.
#####
...#.
...#.

5
#####
#....
####.
....#
....#
#...#
.###.

6
.###.
#....
#....
####.
#...#
#...#
.###.

7
#####
....#
...#.
..#..
.#...
.#...
.#...

8
.###.
#...#
#...#
.###.
#...#
#...#
.###.

9
.###.
#...#
#...#
.####
....#
....#
.###.

.
.
.
.
.
.
.
#

,
.
.
.
.
.
.
#
#

:
.
.
#
.
.
.
#

;
.
.
#
.
.
.
#
#

!
#
#
#
#
#
.
#

?
.###.
#...#
....#
...#.
..#..
.....
..#..

-
...
...
...
###

—
.....
.....
.....
#####

º
.#.
#.#
.#.
...
###

ª
##.
.##
###
...
###

+
.....
..#..
..#..
#####
..#..
..#..

=
....
....
####
....
####

/
..#
..#
.#.
.#.
.#.
#..
#..

(
.#
#.
#.
#.
#.
#.
.#

)
#.
.#
.#
.#
.#
.#
#.

[
##
#.
#.
#.
#.
#.
##

]
##
.#
.#
.#
.#
.#
##

'
#
#

"
#.#
#.#

%
##..#
##..#
...#.
..#..
.#...
#..##
#..##

*
.....
#.#.#
.###.
#####
.###.
#.#.#

<
...#
..#.
.#..
#...
.#..
..#.
...#

>
#...
.#..
..#.
...#
..#.
.#..
#...

_
.....
.....
.....
.....
.....
.....
#####

#
.#.#.
.#.#.
#####
.#.#.
#####
.#.#.
.#.#.

▶
#...
##..
###.
####
###.
##..
#...
"""

_SMALL = """A
.#.
#.#
###
#.#
#.#

B
##.
#.#
##.
#.#
##.

C
.##
#..
#..
#..
.##

D
##.
#.#
#.#
#.#
##.

E
###
#..
##.
#..
###

F
###
#..
##.
#..
#..

G
.##
#..
#.#
#.#
.##

H
#.#
#.#
###
#.#
#.#

I
###
.#.
.#.
.#.
###

J
..#
..#
..#
#.#
.#.

K
#.#
#.#
##.
#.#
#.#

L
#..
#..
#..
#..
###

M
#...#
##.##
#.#.#
#...#
#...#

N
#..#
##.#
#.##
#..#
#..#

O
.#.
#.#
#.#
#.#
.#.

P
##.
#.#
##.
#..
#..

Q
.#.
#.#
#.#
#.#
.##

R
##.
#.#
##.
#.#
#.#

S
.##
#..
.#.
..#
##.

T
###
.#.
.#.
.#.
.#.

U
#.#
#.#
#.#
#.#
###

V
#.#
#.#
#.#
#.#
.#.

W
#...#
#...#
#.#.#
##.##
#...#

X
#.#
#.#
.#.
#.#
#.#

Y
#.#
#.#
.#.
.#.
.#.

Z
###
..#
.#.
#..
###

0
###
#.#
#.#
#.#
###

1
.#.
##.
.#.
.#.
###

2
##.
..#
.#.
#..
###

3
##.
..#
.#.
..#
##.

4
#.#
#.#
###
..#
..#

5
###
#..
##.
..#
##.

6
.##
#..
###
#.#
###

7
###
..#
.#.
.#.
.#.

8
###
#.#
###
#.#
###

9
###
#.#
###
..#
##.

.
.
.
.
.
#

,
.
.
.
.
#
#

!
#
#
#
.
#

?
##.
..#
.#.
...
.#.

-
..
..
##

:
.
#
.
#

/
..#
..#
.#.
#..
#..

+
...
.#.
###
.#.
"""

# Acentos: (molde, deslocamento x extra). Ficam 2 linhas acima da letra.
_MARKS = {
    "acute": [".#", "#."],
    "grave": ["#.", ".#"],
    "circ": [".#.", "#.#"],
    "tilde": [".#.#", "#.#."],
    "uml": ["#.#"],
}
ACCENTS = {
    "á": ("a", "acute"), "à": ("a", "grave"), "â": ("a", "circ"), "ã": ("a", "tilde"),
    "é": ("e", "acute"), "ê": ("e", "circ"), "í": ("ı", "acute"), "ó": ("o", "acute"),
    "ô": ("o", "circ"), "õ": ("o", "tilde"), "ú": ("u", "acute"), "ü": ("u", "uml"),
    "Á": ("A", "acute"), "À": ("A", "grave"), "Â": ("A", "circ"), "Ã": ("A", "tilde"),
    "É": ("E", "acute"), "Ê": ("E", "circ"), "Í": ("I", "acute"), "Ó": ("O", "acute"),
    "Ô": ("O", "circ"), "Õ": ("O", "tilde"), "Ú": ("U", "acute"), "Ü": ("U", "uml"),
}
CEDILLA = {"ç": "c", "Ç": "C"}
CEDILLA_MARK = [".#", "#."]


@dataclass(frozen=True)
class PixelFont:
    glyphs: dict
    cap: int            # altura das maiúsculas
    space: int          # largura do espaço
    upper_only: bool    # a fonte pequena só tem maiúsculas

    @property
    def line_height(self) -> int:
        """Acento (2) + letra + perna do g/p (2)."""
        return 2 + self.cap + 2


NORMAL = PixelFont(_parse(_NORMAL), cap=7, space=3, upper_only=False)
SMALL = PixelFont(_parse(_SMALL), cap=5, space=2, upper_only=True)


def _stamp(grid, pattern, top, left):
    """Carimba um molde pequeno (acento, cedilha) na grade da letra, cortando o que sair dela."""
    for y, row in enumerate(pattern):
        for x, c in enumerate(row):
            if c == "#" and 0 <= top + y < len(grid) and 0 <= left + x < len(grid[0]):
                grid[top + y][left + x] = "#"


def _glyph(font: PixelFont, ch: str) -> list[str]:
    """Molde final da letra (com acento/cedilha), já alinhado: linhas 0-1 = espaço do acento."""
    if font.upper_only:
        ch = ch.upper()
    base, mark = ACCENTS.get(ch, (CEDILLA.get(ch, ch), None))
    rows = font.glyphs.get(base) or font.glyphs.get(base.upper()) or font.glyphs["?"]
    width = max(len(r) for r in rows)
    grid = [["."] * width for _ in range(font.line_height)]
    _stamp(grid, rows, 2, 0)
    if mark:
        pattern = _MARKS[mark]
        small_letter = (base.islower() or base == "ı") and not font.upper_only
        # minúscula: acento logo acima da letra baixa, com 1 px de folga; maiúscula: encostado no topo
        top = 2 + (font.cap - 5) - len(pattern) - 1 if small_letter else 2 - len(pattern)
        left = (width - len(pattern[0])) // 2 + (1 if mark == "acute" and width > 2 else 0)
        _stamp(grid, pattern, top, left)
    if ch in CEDILLA:
        _stamp(grid, CEDILLA_MARK, 2 + font.cap, (width - 2) // 2)
    return ["".join(r) for r in grid]


_glyph_cache: dict = {}


def glyph(font: PixelFont, ch: str) -> list[str]:
    key = (id(font), ch)
    if key not in _glyph_cache:
        _glyph_cache[key] = _glyph(font, ch)
    return _glyph_cache[key]


def pick(size: int) -> tuple[PixelFont, int]:
    """Converte o "tamanho" antigo (estilo pygame.font) em fonte + ampliação."""
    if size < 12:
        return SMALL, 1
    if size < 20:
        return NORMAL, 1
    if size < 40:
        return NORMAL, 2
    return NORMAL, 3


def width(text: str, size: int = 16) -> int:
    font, scale = pick(size)
    total = 0
    for ch in text:
        total += (font.space if ch == " " else len(glyph(font, ch)[0])) + 1
    return max(0, total - 1) * scale


def height(size: int = 16) -> int:
    font, scale = pick(size)
    return font.line_height * scale


def render(text: str, size: int, color) -> pygame.Surface:
    """Desenha o texto numa Surface transparente (sem antialias: pixel puro)."""
    font, scale = pick(size)
    surf = pygame.Surface((max(1, width(text, size) // scale), font.line_height), pygame.SRCALPHA)
    x = 0
    for ch in text:
        if ch == " ":
            x += font.space + 1
            continue
        rows = glyph(font, ch)
        for y, row in enumerate(rows):
            for gx, c in enumerate(row):
                if c == "#":
                    surf.set_at((x + gx, y), color)
        x += len(rows[0]) + 1
    if scale > 1:
        surf = pygame.transform.scale_by(surf, scale)
    return surf

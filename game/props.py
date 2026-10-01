"""Catálogo de objetos do mapa (casas, árvores, enfeites): tamanho, parte sólida e porta. Sem Pygame.

Os desenhos ficam em tilemap.py; aqui só os dados que as regras do mapa precisam
(onde dá para andar, onde fica a porta).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectDef:
    """Figura de w x h tiles, recortada de um tileset do pacote na posição (col, row).

    solid: quantas linhas de baixo bloqueiam a passagem (0 = dá para passar por cima/atrás).
    door:  posição da porta dentro da figura (coluna, linha), se houver.
    tileset vazio = desenho feito por código (pixelart.py), como o Coliseu.
    """
    tileset: str
    col: int
    row: int
    w: int
    h: int
    solid: int
    door: tuple[int, int] | None = None

    def footprint(self, x: int, y: int) -> set[tuple[int, int]]:
        """Tiles bloqueados quando a figura é colocada com o canto de cima à esquerda em (x, y)."""
        return {(x + dx, y + dy) for dy in range(self.h - self.solid, self.h) for dx in range(self.w)}


H, N, E = "TilesetHouse.png", "TilesetNature.png", "TilesetElement.png"
OBJECTS = {
    # ---- construções (a porta fica na última linha)
    "house_orange": ObjectDef(H, 0, 0, 4, 3, 2, door=(1, 2)),
    "house_beige": ObjectDef(H, 4, 0, 4, 3, 2, door=(1, 2)),
    "house_red": ObjectDef(H, 12, 0, 4, 3, 2, door=(1, 2)),
    "house_wood": ObjectDef(H, 26, 0, 3, 3, 2, door=(1, 2)),
    "house_round": ObjectDef(H, 23, 0, 3, 3, 2, door=(1, 2)),
    "market": ObjectDef(H, 19, 0, 4, 3, 2, door=(1, 2)),
    "dojo": ObjectDef(H, 25, 7, 4, 7, 4, door=(1, 6)),
    "hall": ObjectDef(H, 25, 14, 4, 5, 3, door=(1, 4)),
    "torii": ObjectDef(H, 0, 5, 4, 2, 0),
    # construções modernas desenhadas por código (buildings.py)
    "coliseum": ObjectDef("", 0, 0, 7, 4, 4, door=(3, 3)),
    "house_modern_red": ObjectDef("", 0, 0, 5, 5, 3, door=(2, 4)),
    "house_modern_blue": ObjectDef("", 0, 0, 5, 5, 3, door=(2, 4)),
    "house_modern_green": ObjectDef("", 0, 0, 5, 5, 3, door=(2, 4)),
    "house_modern_gray": ObjectDef("", 0, 0, 5, 5, 3, door=(2, 4)),
    "card_shop": ObjectDef("", 0, 0, 6, 4, 2, door=(3, 3)),
    "arena": ObjectDef("", 0, 0, 7, 5, 3, door=(3, 4)),
    "construction": ObjectDef("", 0, 0, 6, 5, 3),
    "lamp": ObjectDef("", 0, 0, 1, 2, 1),
    # ---- natureza
    "tree": ObjectDef(N, 0, 0, 2, 2, 1),
    "pine": ObjectDef(N, 2, 0, 2, 2, 1),
    "oak": ObjectDef(N, 6, 0, 2, 2, 1),
    "small_tree": ObjectDef(N, 6, 8, 2, 2, 1),
    "grove": ObjectDef(N, 4, 2, 4, 3, 1),
    "pines": ObjectDef(N, 0, 2, 4, 3, 1),
    "stump": ObjectDef(N, 4, 8, 1, 1, 1),
    "big_rock": ObjectDef(N, 0, 12, 2, 2, 2),
    "bush": ObjectDef(N, 1, 10, 1, 1, 1),
    "fern": ObjectDef(N, 4, 10, 1, 1, 0),
    "sunflower": ObjectDef(N, 0, 11, 1, 1, 0),
    # ---- objetos da vila
    "well": ObjectDef(E, 7, 1, 1, 2, 1),
    "clothesline": ObjectDef(E, 11, 3, 3, 1, 1),
    "laundry": ObjectDef(E, 14, 3, 2, 1, 1),
    "hay": ObjectDef(E, 12, 4, 1, 2, 1),
    "crates": ObjectDef(E, 4, 4, 2, 1, 1),
    "crate": ObjectDef(E, 0, 0, 1, 1, 1),
    "pot": ObjectDef(E, 1, 0, 1, 1, 1),
    "cart": ObjectDef(E, 2, 3, 2, 2, 1),
    "bench": ObjectDef(E, 11, 1, 3, 1, 1),
    "scarecrow": ObjectDef(E, 15, 0, 1, 1, 1),
}

# Tiles de 1x1 do mapa que viram objetos desenhados (só quando o pacote está instalado):
# a árvore "T" vira uma árvore 2x2 com o tronco nesse tile; "R" vira pedra; "S" vira placa.
TREE_KINDS = ("tree", "pine", "oak", "tree", "pine")

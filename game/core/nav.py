"""Caminhos pelos mapas (usados pela Rebeca e pelos NPCs). Regras puras, sem Pygame.

- dentro de um mapa: busca em largura na grade (tiles livres = sem parede, objeto sólido nem NPC que não sai do
  lugar, como a Lu no caixa);
- entre mapas: pelas PASSAGENS (warps: escada, saída da vila, porta da rua da casa) e pelas PORTAS de construção
  (pisar no tile embaixo da porta leva para dentro). Primeiro acha a sequência de mapas, depois o caminho em cada um.
`private=False` (os NPCs): os mapas particulares (a casa de cada jogador) ficam de fora.
"""
from __future__ import annotations

from collections import deque

from game.data.world import DIR_VECTORS, DOOR_TARGETS, MAPS, SOLID_TILES


class Nav:
    """Onde dá para andar em cada mapa e como ir de um mapa a outro (só dados de game/data/world.py)."""

    def __init__(self, maps=None, private=True):
        self.maps = {k: m for k, m in (maps or MAPS).items() if private or not m.private}
        self._blocked: dict[str, set] = {}
        self._size: dict[str, tuple[int, int]] = {}

    def blocked(self, map_id: str) -> set:
        if map_id not in self._blocked:
            m = self.maps[map_id]
            grid = m.build()
            tiles = {(x, y) for y, row in enumerate(grid) for x, t in enumerate(row) if t in SOLID_TILES}
            tiles |= m.solid_objects()
            spots = [*m.trainers.values(), *(h.spot for h in m.helpers.values())]
            tiles |= {(s.x, s.y) for s in spots if not s.roams}          # quem nunca sai do lugar
            self._blocked[map_id] = tiles
            self._size[map_id] = (len(grid[0]), len(grid))
        return self._blocked[map_id]

    def walkable(self, map_id: str, x: int, y: int) -> bool:
        blocked = self.blocked(map_id)
        w, h = self._size[map_id]
        return 0 <= x < w and 0 <= y < h and (x, y) not in blocked

    def portals(self, map_id: str) -> list[tuple[tuple[int, int], str, tuple[int, int]]]:
        """(tile onde pisar, mapa de destino, tile de chegada)."""
        m = self.maps[map_id]
        out = [((w.x, w.y), w.to_map, (w.to_x, w.to_y)) for w in m.warps]
        for (dx, dy), action in m.doors.items():
            if action in DOOR_TARGETS:
                to_map, spot, _ = DOOR_TARGETS[action]
                out.append(((dx, dy + 1), to_map, spot))
        return [p for p in out if p[1] in self.maps]

    def path(self, map_id, start, goal, avoid=frozenset()) -> list[tuple[int, int]] | None:
        """Tiles do caminho de `start` até `goal` (sem o start). None se não houver caminho."""
        if start == goal:
            return []
        prev = {start: None}
        queue = deque([start])
        while queue:
            tile = queue.popleft()
            for dx, dy in DIR_VECTORS.values():
                nxt = (tile[0] + dx, tile[1] + dy)
                if nxt in prev or not self.walkable(map_id, *nxt) or (nxt in avoid and nxt != goal):
                    continue
                prev[nxt] = tile
                if nxt == goal:
                    steps = [nxt]
                    while prev[steps[-1]] != start:
                        steps.append(prev[steps[-1]])
                    return steps[::-1]
                queue.append(nxt)
        return None

    def route(self, map_id, start, to_map, goal, avoid=frozenset()) -> list[tuple[str, int, int]] | None:
        """Caminho completo, talvez passando por outros mapas: lista de (mapa, x, y)."""
        hops = self._map_hops(map_id, to_map)
        if hops is None:
            return None
        out, here, tile = [], map_id, start
        for portal_tile, next_map, arrive in hops:
            steps = self.path(here, tile, portal_tile, avoid if here == map_id else frozenset())
            if steps is None:
                return None
            out += [(here, x, y) for x, y in steps]
            out.append((next_map, *arrive))
            here, tile = next_map, arrive
        steps = self.path(here, tile, goal, avoid if here == map_id else frozenset())
        if steps is None:
            return None
        return out + [(here, x, y) for x, y in steps]

    def _map_hops(self, from_map, to_map):
        """Que portais atravessar para ir de um mapa a outro (busca em largura nos mapas)."""
        prev = {from_map: None}
        queue = deque([from_map])
        while queue:
            here = queue.popleft()
            if here == to_map:
                hops = []
                while prev[here] is not None:
                    before, portal = prev[here]
                    hops.append(portal)
                    here = before
                return hops[::-1]
            for portal in self.portals(here):
                if portal[1] not in prev:
                    prev[portal[1]] = (here, portal)
                    queue.append(portal[1])
        return None

def free_tile_near(nav: Nav, map_id: str, tile, occupied=frozenset(), prefer: str = "down"):
    """Um tile livre ao lado de `tile` (para ela aparecer junto do jogador). Tenta primeiro `prefer`."""
    order = [prefer, *(d for d in DIR_VECTORS if d != prefer)]
    for direction in order:
        dx, dy = DIR_VECTORS[direction]
        spot = (tile[0] + dx, tile[1] + dy)
        if nav.walkable(map_id, *spot) and spot not in occupied:
            return spot
    return None


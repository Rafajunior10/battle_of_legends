"""Companheira com vida própria (a Rebeca): anda pelos mapas, faz as atividades da rotina, segue o jogador,
vai dormir. Regras puras, sem Pygame: a cena só desenha onde ela está (`map_id`, `x`, `y`, `facing`, `pose`).

Os caminhos (dentro de um mapa e entre mapas) vêm de game/core/nav.py.

Modos (`mode`): "routine" (escolhe atividades sozinha), "follow" (vai atrás do jogador), "sleep" (deitada até
acordar). `hold(s)` faz ela parar uns segundos (conversa, abraço). A cada passo o tempo é STEP_TIME.
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from game.core.nav import Nav, free_tile_near
from game.data.companion import Activity, CompanionDef
from game.data.world import DIR_VECTORS, MAPS

STEP_TIME = 0.30           # segundos por tile andando sozinha
FOLLOW_STEP = 0.20         # seguindo o jogador ela anda mais rápido
REST = (2.0, 5.0)          # pausa entre uma atividade e outra
BLOCKED_WAIT = 1.0         # alguém no caminho: espera e depois procura outro caminho


# ============================================================ a companheira
@dataclass
class Companion:
    spec: CompanionDef
    map_id: str
    x: int
    y: int
    facing: str = "down"
    pose: str = "stand"
    mode: str = "routine"
    task: Activity | None = None
    phase: str = "rest"                     # go (andando até a atividade) | do (fazendo) | rest (pausa)
    timer: float = 1.0
    step_t: float = 0.0
    held: float = 0.0
    stand_tile: tuple[int, int] | None = None   # de onde ela saiu para sentar/deitar (volta para lá)
    route: deque = field(default_factory=deque)
    last: str = ""

    @classmethod
    def at_home(cls, spec: CompanionDef) -> Companion:
        map_id, x, y = spec.home
        return cls(spec, map_id, x, y)

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def tile(self) -> tuple[int, int]:
        return self.x, self.y

    # ------------------------------------------------------------ comandos do jogador
    def follow(self) -> None:
        self.get_up()
        self.mode, self.task, self.route = "follow", None, deque()

    def stop_following(self) -> None:
        self.mode, self.phase, self.timer = "routine", "rest", 2.0

    def go_to_sleep(self, nav: Nav) -> bool:
        """Vai deitar na cama (o "vamos dormir"). False se não achar caminho."""
        self.get_up()
        self.mode = "sleep"
        return self._start(self.spec.sleep, nav)

    def wake(self) -> None:
        self.get_up()
        self.mode, self.task, self.phase, self.timer = "routine", None, "rest", 3.0

    def hold(self, seconds: float, face: str | None = None) -> None:
        """Para por uns segundos (conversa, abraço), olhando para `face`."""
        self.held = max(self.held, seconds)
        if face and self.pose == "stand":
            self.facing = face

    def place(self, map_id: str, x: int, y: int, facing: str | None = None) -> None:
        """Aparece direto num lugar (ex.: entrou junto com o jogador por uma porta)."""
        self.get_up()
        self.map_id, self.x, self.y = map_id, x, y
        self.facing = facing or self.facing
        self.route = deque()

    def get_up(self) -> None:
        if self.pose != "stand" and self.stand_tile:
            self.x, self.y = self.stand_tile
        self.pose, self.stand_tile = "stand", None

    # ------------------------------------------------------------ tempo
    def tick(self, dt, nav: Nav, rng: random.Random | None = None, occupied=frozenset(), leader=None) -> list:
        """Avança o tempo. `occupied`: tiles com gente agora (no mapa dela); `leader`: (mapa, tile atrás do
        jogador, tile do jogador) quando ela está seguindo. Devolve eventos: ("say", texto) e
        ("reply", npc, texto) para a cena mostrar os balões."""
        rng = rng or random.Random()
        if self.held > 0:
            self.held = max(0.0, self.held - dt)
            return []
        if self.mode == "follow":
            return self._follow(dt, nav, occupied, leader)
        if self.phase == "go":
            return self._walk(dt, nav, occupied, STEP_TIME)
        if self.phase == "do":
            if self.mode == "sleep":
                return []
            self.timer -= dt
            if self.timer <= 0:
                self.get_up()
                nxt = next((a for a in self.spec.activities if a.id == self.task.then), None) if self.task else None
                if nxt and self._start(nxt, nav):
                    return []
                self.task, self.phase, self.timer = None, "rest", rng.uniform(*REST)
            return []
        self.timer -= dt
        if self.timer <= 0:
            self._choose(nav, rng)
        return []

    def _choose(self, nav, rng):
        options = [a for a in self.spec.activities if a.weight > 0 and a.id != self.last]
        activity = rng.choices(options, weights=[a.weight for a in options])[0]
        if not self._start(activity, nav):
            self.timer = rng.uniform(*REST)

    def _start(self, activity: Activity, nav: Nav) -> bool:
        route = nav.route(self.map_id, self.tile, activity.map_id, activity.spot)
        if route is None:
            return False
        self.task, self.last = activity, activity.id
        self.route, self.phase, self.step_t = deque(route), "go", 0.0
        return True

    def _walk(self, dt, nav, occupied, step_time):
        self.step_t += dt
        if self.step_t < step_time:
            return []
        if not self.route:
            return self._arrive()
        map_id, x, y = self.route[0]
        if map_id == self.map_id and (x, y) in occupied:          # alguém no caminho: espera um pouco
            if self.step_t > step_time + BLOCKED_WAIT and self.task:
                route = nav.route(self.map_id, self.tile, self.task.map_id, self.task.spot, avoid=occupied)
                self.route = deque(route) if route else self.route
                self.step_t = 0.0
            return []
        self.route.popleft()
        if map_id == self.map_id:
            self.facing = next((d for d, v in DIR_VECTORS.items() if v == (x - self.x, y - self.y)), self.facing)
        self.map_id, self.x, self.y = map_id, x, y
        self.step_t = 0.0
        return [] if self.route else self._arrive()

    def _arrive(self):
        task = self.task
        self.facing = task.facing
        self.phase, self.timer = "do", task.duration
        if task.seat:
            self.stand_tile = self.tile
            self.x, self.y = task.seat
            self.pose = task.pose
            self.facing = MAPS[task.map_id].seats.get(task.seat, task.facing)   # sentada: olha para a mesa
        events = [("say", task.bubble)] if task.bubble else []
        if task.talk_to:
            events.append(("reply", task.talk_to, task.reply))
        return events

    def _follow(self, dt, nav, occupied, leader):
        if leader is None:
            return []
        map_id, behind, player = leader
        if map_id != self.map_id:
            return []                                    # a cena a coloca junto quando o jogador troca de mapa
        if abs(self.x - player[0]) + abs(self.y - player[1]) <= 1:
            self.route = deque()
            return []
        if not self.route or self.route[-1][1:] != behind:
            steps = nav.path(self.map_id, self.tile, behind, avoid=occupied)
            self.route = deque((self.map_id, x, y) for x, y in steps or [])
        self.step_t += dt
        if self.step_t < FOLLOW_STEP or not self.route:
            return []
        _, x, y = self.route[0]
        if (x, y) in occupied:
            return []
        self.route.popleft()
        self.facing = next((d for d, v in DIR_VECTORS.items() if v == (x - self.x, y - self.y)), self.facing)
        self.x, self.y, self.step_t = x, y, 0.0
        return []


__all__ = ["Companion", "Nav", "free_tile_near"]

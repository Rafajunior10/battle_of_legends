"""Vida dos NPCs: passeiam pelos mapas, conversam entre si, duelistas treinam uns contra os outros, vão à
lanchonete comer e, de vez em quando, um duelista vai até um jogador e o desafia. Regras puras, sem Pygame.

Funciona em qualquer mapa público (vila, bosque, lanchonete e os mapas novos), sem configurar nada: o passeio é
para tiles livres perto de onde o NPC mora. Quem não sai do lugar tem `Spot.roams = False` (a Lu no caixa).

Quem roda isto:
- jogando sozinho, o próprio lobby (`LobbyScene`);
- no online, o SERVIDOR (game/net/server.py), para os dois jogadores verem o mesmo NPC no mesmo lugar. O servidor
  sabe onde cada jogador está e manda o desafio só para quem foi abordado.

`NpcWorld.tick(dt, players)` devolve eventos para quem desenha:
    ("move", id, estado)   o NPC andou/virou/sentou (estado = {"map", "x", "y", "facing", "pose"})
    ("say", id, texto)     balão de fala
    ("challenge", id, jogador)   o NPC chegou do lado do jogador e quer duelar
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from game.core.nav import Nav, free_tile_near
from game.data.cards import CARDS
from game.data.food import MENU
from game.data.opponents import TRAINERS
from game.data.world import (
    DIR_VECTORS,
    MAPS,
    NPC_CHATS,
    NPC_DUEL,
    NPC_EATING,
    NPC_ORDER,
    NPC_ORDER_REPLY,
    OPPOSITE,
)

STEP_TIME = 0.38                  # segundos por tile (os NPCs andam sem pressa)
IDLE = (3.0, 9.0)                 # parado entre um plano e outro
LOOK_AROUND = (1.5, 4.0)          # parado, de vez em quando vira para outro lado
WANDER_RADIUS = 8                 # passeio: até este tanto de tiles de onde mora
PARTNER_RANGE = 14                # conversa/duelo de treino só com quem está perto
APPROACH_CHECK = 5.0              # a cada 5 s um duelista pode resolver ir até um jogador...
APPROACH_CHANCE = 0.12            # ...com esta chance
APPROACH_COOLDOWN = (150.0, 300.0)   # o mesmo NPC só desafia de novo depois disso
PLAYER_COOLDOWN = 150.0           # cada jogador fica um tempo sem ser abordado (não fica chato)
APPROACH_TIMEOUT = 25.0           # não alcançou o jogador: desiste
MEAL_INTERVAL = (240.0, 480.0)    # cada NPC come de novo só depois disso
CAFE, COUNTER, CASHIER = "lanchonete", (5, 6), "lu"
PLANS = {"wander": 4, "home": 2, "chat": 2, "duel": 1, "eat": 1}


@dataclass
class Townsfolk:
    id: str
    name: str
    map_id: str
    x: int
    y: int
    facing: str
    home: tuple                    # (mapa, x, y, para onde olha)
    duelist: bool = False
    roams: bool = True
    cards: tuple = ()              # nomes das cartas do deck (o que ele grita no duelo de treino)
    pose: str = "stand"
    plan: str = "idle"             # idle | walk | do | wait | approach
    task: str = ""                 # wander | home | chat | duel | order | eat | approach
    timer: float = 0.0
    look_t: float = 0.0
    step_t: float = 0.0
    held: float = 0.0
    route: deque = field(default_factory=deque)
    partner: str | None = None
    target: str | None = None      # jogador que ele foi desafiar
    seat: tuple | None = None
    stand_tile: tuple | None = None
    challenge_cd: float = 0.0
    meal_cd: float = 0.0
    says: list = field(default_factory=list)       # [segundos, texto]: falas marcadas para daqui a pouco

    @property
    def tile(self):
        return self.x, self.y

    def state(self) -> dict:
        return {"map": self.map_id, "x": self.x, "y": self.y, "facing": self.facing, "pose": self.pose}

    def say_later(self, seconds, text):
        self.says.append([seconds, text])


def _deck_names(trainer_id):
    return tuple(CARDS[c].name.upper() for c in dict.fromkeys(TRAINERS[trainer_id]["deck"]) if c in CARDS)


def _facing_to(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


class NpcWorld:
    def __init__(self, rng: random.Random | None = None, maps=None):
        self.rng = rng or random.Random()
        self.nav = Nav(maps, private=False)
        self.folk: dict[str, Townsfolk] = {}
        self.player_cd: dict = {}
        self.check_t = APPROACH_CHECK
        self.reserved: set = set()             # assentos da lanchonete já escolhidos por alguém
        self.events: list = []
        self.night = False
        for m in self.nav.maps.values():
            for tid, spot in m.trainers.items():
                self._add(tid, TRAINERS[tid]["name"], m.id, spot, duelist=True, cards=_deck_names(tid))
            for hid, helper in m.helpers.items():
                self._add(hid, hid.upper(), m.id, helper.spot)

    def _add(self, npc_id, name, map_id, spot, duelist=False, cards=()):
        self.folk[npc_id] = Townsfolk(npc_id, name, map_id, spot.x, spot.y, spot.facing,
                                      (map_id, spot.x, spot.y, spot.facing), duelist, spot.roams, cards,
                                      timer=self.rng.uniform(2.0, 8.0),
                                      challenge_cd=self.rng.uniform(*APPROACH_COOLDOWN) / 3,
                                      meal_cd=self.rng.uniform(*MEAL_INTERVAL) / 4)

    # ------------------------------------------------------------ de fora
    def snapshot(self) -> list[dict]:
        return [dict(f.state(), id=f.id) for f in self.folk.values()]

    def hold(self, npc_id, seconds, face=None):
        """Para o NPC (o jogador está conversando ou duelando com ele)."""
        f = self.folk.get(npc_id)
        if f is None:
            return
        f.held = max(f.held, float(seconds))
        if face in DIR_VECTORS and f.pose == "stand":
            f.facing = face
            self._emit_move(f)

    # ------------------------------------------------------------ tempo
    def tick(self, dt: float, players=(), night=False) -> list:
        """`players`: [{"id", "map", "x", "y", "busy", "target"}] (target=False: só obstáculo, ex.: a Rebeca).
        `night`: de noite os NPCs voltam para casa e ninguém desafia ninguém."""
        self.events = []
        self.night = night
        self.player_cd = {k: v - dt for k, v in self.player_cd.items() if v > dt}
        occupied = self._occupied(players)
        for f in self.folk.values():
            before = f.state()
            self._tick_one(f, dt, players, occupied)
            if f.state() != before:
                self.events.append(("move", f.id, f.state()))
        self.check_t -= dt
        if self.check_t <= 0 and not night:
            self.check_t = APPROACH_CHECK
            self._maybe_approach(players)
        return self.events

    def _occupied(self, players):
        occupied: dict = {}
        for f in self.folk.values():
            occupied.setdefault(f.map_id, set()).add(f.tile)
        for p in players:
            occupied.setdefault(p["map"], set()).add((p["x"], p["y"]))
        return occupied

    def _tick_one(self, f, dt, players, occupied):
        for say in list(f.says):
            say[0] -= dt
            if say[0] <= 0:
                f.says.remove(say)
                self.events.append(("say", f.id, say[1]))
        f.challenge_cd = max(0.0, f.challenge_cd - dt)
        f.meal_cd = max(0.0, f.meal_cd - dt)
        if f.held > 0:
            f.held = max(0.0, f.held - dt)
            return
        if f.plan in ("walk", "approach") and f.route:
            self._step(f, dt, occupied)
            return
        handler = {"idle": self._idle, "walk": self._arrive, "do": self._doing, "wait": self._waiting,
                   "approach": self._approaching}[f.plan]
        handler(f, dt, players, occupied)

    def _step(self, f, dt, occupied):
        f.step_t += dt
        if f.step_t < STEP_TIME:
            return
        map_id, x, y = f.route[0]
        if (x, y) in occupied.get(map_id, ()):           # alguém no caminho: espera
            if f.step_t > STEP_TIME * 4:
                f.route.clear()                          # desiste deste passo (o plano decide o que fazer)
            return
        f.route.popleft()
        occupied.get(f.map_id, set()).discard(f.tile)
        if map_id == f.map_id:
            f.facing = _facing_to(f.tile, (x, y))
        f.map_id, f.x, f.y, f.step_t = map_id, x, y, 0.0
        occupied.setdefault(map_id, set()).add((x, y))

    # ------------------------------------------------------------ planos
    def _idle(self, f, dt, players, occupied):
        f.look_t -= dt
        if f.look_t <= 0:
            f.look_t = self.rng.uniform(*LOOK_AROUND)
            if f.roams or self.rng.random() < 0.3:
                f.facing = self.rng.choice(list(DIR_VECTORS)) if f.roams else f.home[3]
        if not f.roams:
            return
        f.timer -= dt
        if f.timer <= 0:
            self._choose(f, occupied)

    def _choose(self, f, occupied):
        allowed = {"home": 1} if self.night else PLANS              # de noite, cada um para a sua casa
        plans = {name: w for name, w in allowed.items() if self._possible(f, name)}
        plan = self.rng.choices(list(plans), weights=list(plans.values()))[0] if plans else None
        started = plan and getattr(self, f"_start_{plan}")(f, occupied)
        if not started:
            f.timer = self.rng.uniform(*IDLE)

    def _possible(self, f, plan):
        if plan == "home":
            return (f.map_id, f.x, f.y) != f.home[:3]
        if plan in ("chat", "duel"):
            return self._partner(f, duelist=plan == "duel") is not None
        if plan == "eat":
            return f.map_id != CAFE and CAFE in self.nav.maps and f.meal_cd == 0
        return True

    def _partner(self, f, duelist):
        if duelist and not f.duelist:
            return None
        options = [o for o in self.folk.values() if o is not f and o.roams and o.plan == "idle" and o.held == 0
                   and o.map_id == f.map_id and (o.duelist or not duelist)
                   and abs(o.x - f.x) + abs(o.y - f.y) <= PARTNER_RANGE]
        return self.rng.choice(options) if options else None

    def _go(self, f, map_id, goal, task, occupied=None):
        avoid = frozenset(occupied.get(f.map_id, ())) if occupied else frozenset()
        route = self.nav.route(f.map_id, f.tile, map_id, goal, avoid=avoid)
        if route is None:
            return False
        f.route, f.plan, f.task, f.step_t = deque(route), "walk", task, 0.0
        return True

    def _start_wander(self, f, occupied):
        home_map, hx, hy, _ = f.home
        base = (hx, hy) if f.map_id == home_map else f.tile
        for _ in range(12):
            goal = (base[0] + self.rng.randint(-WANDER_RADIUS, WANDER_RADIUS),
                    base[1] + self.rng.randint(-WANDER_RADIUS, WANDER_RADIUS))
            if self.nav.walkable(f.map_id, *goal) and goal not in occupied.get(f.map_id, ()):
                return self._go(f, f.map_id, goal, "wander", occupied)
        return False

    def _start_home(self, f, occupied):
        return self._go(f, f.home[0], f.home[1:3], "home", occupied)

    def _start_chat(self, f, occupied, duel=False):
        partner = self._partner(f, duelist=duel)
        spot = partner and free_tile_near(self.nav, partner.map_id, partner.tile,
                                          frozenset(occupied.get(partner.map_id, ())), prefer=partner.facing)
        if not spot or not self._go(f, f.map_id, spot, "duel" if duel else "chat", occupied):
            return False
        f.partner, partner.partner = partner.id, f.id
        partner.plan, partner.task, partner.timer, partner.route = "wait", f.task, 20.0, deque()
        return True

    def _start_duel(self, f, occupied):
        return self._start_chat(f, occupied, duel=True)

    def _start_eat(self, f, occupied):
        return self._go(f, CAFE, COUNTER, "order", occupied)

    def _arrive(self, f, dt, players, occupied):
        """Terminou de andar: faz o que foi fazer."""
        arrive = {"chat": self._meet, "duel": self._meet, "order": self._order, "eat": self._sit}.get(f.task)
        if arrive is None or not arrive(f, occupied):
            if f.task == "home":
                f.facing = f.home[3]
            self._rest(f)

    def _meet(self, f, occupied):
        partner = self.folk.get(f.partner)
        if partner is None or partner.plan != "wait" or abs(partner.x - f.x) + abs(partner.y - f.y) != 1:
            return False
        f.facing, partner.facing = _facing_to(f.tile, partner.tile), _facing_to(partner.tile, f.tile)
        if f.task == "chat":
            line, reply = self.rng.choice(NPC_CHATS)
            f.say_later(0.0, line)
            partner.say_later(2.8, reply)                # responde quando o primeiro balão já está sumindo
            seconds = 6.0
        else:
            seconds = self._duel_lines(f, partner)
        f.plan, partner.plan = "do", "do"
        f.timer, partner.timer = seconds, seconds
        return True

    def _duel_lines(self, f, partner):
        """Duelo de treino entre dois NPCs: só balões (as cartas que eles gritam vêm do deck de cada um)."""
        (start, accept), (win, lose) = NPC_DUEL
        f.say_later(0.0, start)
        partner.say_later(1.6, accept)
        t = 3.2
        for _ in range(3):
            for who in (f, partner):
                if who.cards:
                    who.say_later(t, self.rng.choice(who.cards) + "!")
                    t += 1.4
        winner, loser = (f, partner) if self.rng.random() < 0.5 else (partner, f)
        winner.say_later(t + 0.4, win)
        loser.say_later(t + 1.8, lose)
        return t + 3.5

    def _order(self, f, occupied):
        f.facing = "up"
        food = self.rng.choice(MENU)
        f.say_later(0.0, NPC_ORDER.format(food=food.name.lower().capitalize()))
        f.meal_cd = self.rng.uniform(*MEAL_INTERVAL)
        cashier = self.folk.get(CASHIER)
        if cashier:
            cashier.say_later(1.8, NPC_ORDER_REPLY)
        f.plan, f.timer = "do", 3.5
        return True

    def _sit(self, f, occupied):
        if f.seat is None:
            return False
        f.stand_tile = f.tile
        f.x, f.y = f.seat
        f.pose = "sit"
        f.facing = MAPS[f.map_id].seats.get(f.seat, f.facing)
        f.say_later(0.5, NPC_EATING)
        f.plan, f.timer = "do", self.rng.uniform(10.0, 16.0)
        return True

    def _doing(self, f, dt, players, occupied):
        f.timer -= dt
        if f.timer > 0:
            return
        if f.task == "order" and self._go_sit(f, occupied):
            return
        if f.pose == "sit":
            f.x, f.y = f.stand_tile or f.tile
            f.pose = "stand"
            self.reserved.discard(f.seat)
            f.seat = None
            if self._start_home(f, occupied):
                return
        if f.partner and self.folk.get(f.partner) and self.folk[f.partner].partner == f.id:
            self._rest(self.folk[f.partner])
        self._rest(f)

    def _go_sit(self, f, occupied):
        """Pediu no balcão: escolhe um assento livre da lanchonete e vai sentar."""
        taken = occupied.get(CAFE, set()) | self.reserved
        for seat in self.rng.sample(list(MAPS[CAFE].seats), len(MAPS[CAFE].seats)):
            if seat in taken:
                continue
            spot = free_tile_near(self.nav, CAFE, seat, frozenset(taken))
            if spot and self._go(f, CAFE, spot, "eat", occupied):
                f.seat = seat
                self.reserved.add(seat)
                return True
        return False

    def _waiting(self, f, dt, players, occupied):
        """Esperando quem vem conversar/duelar (se demorar, desiste)."""
        f.timer -= dt
        if f.timer <= 0:
            self._rest(f)

    def _rest(self, f):
        f.plan, f.task, f.partner, f.target = "idle", "", None, None
        f.route = deque()
        f.timer = self.rng.uniform(*IDLE)

    # ------------------------------------------------------------ desafiar um jogador
    def _maybe_approach(self, players):
        for p in players:
            if not p.get("target", True) or p.get("busy") or self.player_cd.get(p["id"], 0) > 0:
                continue
            near = [f for f in self.folk.values() if f.duelist and f.roams and f.plan == "idle" and f.held == 0
                    and f.challenge_cd == 0 and f.map_id == p["map"]
                    and abs(f.x - p["x"]) + abs(f.y - p["y"]) <= PARTNER_RANGE]
            if near and self.rng.random() < APPROACH_CHANCE:
                f = self.rng.choice(near)
                f.plan, f.task, f.target, f.timer, f.route = "approach", "approach", p["id"], APPROACH_TIMEOUT, deque()
                self.player_cd[p["id"]] = PLAYER_COOLDOWN

    def _approaching(self, f, dt, players, occupied):
        f.timer -= dt
        p = next((p for p in players if p["id"] == f.target), None)
        if p is None or p["map"] != f.map_id or p.get("busy") or f.timer <= 0:
            self._rest(f)
            return
        player = (p["x"], p["y"])
        if abs(f.x - player[0]) + abs(f.y - player[1]) == 1:          # chegou do lado: desafia
            f.facing = _facing_to(f.tile, player)
            self.events.append(("challenge", f.id, f.target))
            f.say_later(0.0, "!")
            f.challenge_cd = self.rng.uniform(*APPROACH_COOLDOWN)
            f.plan, f.task, f.timer = "do", "approach", 6.0
            return
        spot = free_tile_near(self.nav, f.map_id, player, frozenset(occupied.get(f.map_id, ())),
                              prefer=OPPOSITE.get(_facing_to(player, f.tile), "down"))
        steps = spot and self.nav.path(f.map_id, f.tile, spot, avoid=frozenset(occupied.get(f.map_id, ())))
        f.route = deque([(f.map_id, *steps[0])]) if steps else deque()     # um passo por vez: o jogador anda

    def _emit_move(self, f):
        self.events.append(("move", f.id, f.state()))

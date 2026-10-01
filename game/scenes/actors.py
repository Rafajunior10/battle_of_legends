"""Personagens que andam no mapa em grade (estilo Pokémon)."""
import random
from collections import deque

from game.data.world import DIR_VECTORS
from game.engine.settings import TILE

WALK_TIME = 0.24     # segundos para andar 1 tile
RUN_TIME = 0.13
FOOT_Y = 13          # altura do pé dentro do tile: o desenho é alinhado por baixo e centralizado no tile


class Actor:
    def __init__(self, tx, ty, frames, facing="down"):
        self.frames = frames
        self.facing = facing
        self.moving = False
        self.progress = 0.0
        self.step_time = WALK_TIME
        self.parity = 0
        self.place(tx, ty)

    def place(self, tx, ty):
        self.tx, self.ty = tx, ty
        self.px, self.py = float(tx * TILE), float(ty * TILE)
        self.start = (self.px, self.py)
        self.moving = False

    def start_move(self, direction, step_time):
        dx, dy = DIR_VECTORS[direction]
        self.facing = direction
        self.start = (self.tx * TILE, self.ty * TILE)
        self.tx += dx
        self.ty += dy
        self.moving = True
        self.progress = 0.0
        self.step_time = step_time
        self.parity ^= 1

    def update(self, dt):
        """Devolve True no frame em que um passo termina."""
        if not self.moving:
            return False
        self.progress = min(1.0, self.progress + dt / self.step_time)
        sx, sy = self.start
        self.px = sx + (self.tx * TILE - sx) * self.progress
        self.py = sy + (self.ty * TILE - sy) * self.progress
        if self.progress >= 1.0:
            self.moving = False
            return True
        return False

    @property
    def frame_index(self):
        return 1 + self.parity if self.moving and self.progress < 0.5 else 0

    def image(self):
        """Quadro atual. Com uma caminhada completa (Mana Seed tem 6 quadros), cada passo de 1 tile mostra
        metade do ciclo: o passo de um pé usa os quadros 0-2 e o do outro pé, os quadros 3-5."""
        walk = self.frames.get((self.facing, "walk"))
        if walk and self.moving:
            half = len(walk) // 2
            return walk[self.parity * half + min(half - 1, int(self.progress * half))]
        return self.frames[(self.facing, self.frame_index)]

    def draw(self, surf, cam):
        img = self.image()
        x = round(self.px) + (TILE - img.get_width()) // 2
        surf.blit(img, (x - cam[0], round(self.py) + FOOT_Y - img.get_height() - cam[1]))


class NPC(Actor):
    def __init__(self, npc_id, spot, frames, on_talk, look=None):
        """frames: quadros de andar (vêm de sprites.character_frames); look: aparência, para o rosto."""
        super().__init__(spot.x, spot.y, frames, spot.facing)
        self.id = npc_id
        self.look = look
        self.on_talk = on_talk
        self.looks_around = spot.looks_around
        self.timer = random.uniform(1.5, 3.5)

    def idle(self, dt):
        if not self.looks_around:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(1.5, 4.0)
            self.facing = random.choice(list(DIR_VECTORS))


LAG_LIMIT = 4        # passos acumulados (internet lenta): o boneco pula direto para o último


class RemotePlayer(Actor):
    """Outro jogador do mundo compartilhado. Cada passo dele chega pela rede e entra numa fila; aqui ele
    anda os passos um de cada vez, com a mesma animação de quem joga no próprio computador."""

    def __init__(self, player_id, name, frames, map_id, x, y, facing):
        super().__init__(x, y, frames, facing or "down")
        self.id = player_id
        self.name = name
        self.map_id = map_id
        self.pending = deque()       # passos que chegaram e ainda não foram andados
        self.emote = None            # balão de fala atual
        self.emote_t = 0.0
        self.battle = False

    def queue_move(self, map_id, x, y, facing, run):
        self.pending.append((map_id, x, y, facing, run))
        if len(self.pending) > LAG_LIMIT:
            last = self.pending[-1]
            self.pending.clear()
            self.map_id = last[0]
            self.place(last[1], last[2])
            self.facing = last[3]

    def say(self, text, seconds=3.0):
        self.emote, self.emote_t = text, seconds

    def tick(self, dt):
        self.emote_t = max(0.0, self.emote_t - dt)
        if self.emote_t == 0:
            self.emote = None
        self.update(dt)
        if self.moving or not self.pending:
            return
        map_id, x, y, facing, run = self.pending.popleft()
        dx, dy = x - self.tx, y - self.ty
        direction = next((d for d, v in DIR_VECTORS.items() if v == (dx, dy)), None)
        if map_id == self.map_id and direction:
            self.start_move(direction, RUN_TIME if run else WALK_TIME)
        else:                        # virou no lugar, trocou de mapa ou pulou: só reposiciona
            self.map_id = map_id
            self.place(x, y)
        self.facing = facing or self.facing

"""Personagens que andam no mapa em grade (estilo Pokémon)."""
from collections import deque

import pygame

from game.data.world import DIR_VECTORS
from game.engine.settings import TILE

WALK_TIME = 0.24     # segundos para andar 1 tile
RUN_TIME = 0.13
FOOT_Y = 13          # altura do pé dentro do tile: o desenho é alinhado por baixo e centralizado no tile
SIT_DROP, SIT_CROP = 6, 12   # sentado: o corpo desce um pouco e as pernas somem atrás do assento


class Actor:
    def __init__(self, tx, ty, frames, facing="down"):
        self.frames = frames
        self.facing = facing
        self.moving = False
        self.progress = 0.0
        self.step_time = WALK_TIME
        self.parity = 0
        self.pose = "stand"          # stand | sit | lie | shower
        self.anchor = None           # deitado/no banho: (centro x, topo) em pixels, decidido pela cena
        self.flip = False            # deitado de cabeça para baixo (cama virada para a TV)
        self.depth = None            # deitado: a cena manda desenhar depois da cama
        self.nudge = (0, 0)          # empurrãozinho em pixels (abraço, beijo)
        self.emote, self.emote_t = None, 0.0     # balão de fala
        self._upside_down = None
        self.place(tx, ty)

    @property
    def sitting(self):
        return self.pose == "sit"

    @sitting.setter
    def sitting(self, value):
        self.pose = "sit" if value else "stand"

    def say(self, text, seconds=3.0):
        self.emote, self.emote_t = text, seconds

    def tick_emote(self, dt):
        self.emote_t = max(0.0, self.emote_t - dt)
        if self.emote_t == 0:
            self.emote = None

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

    def lying_image(self):
        """De frente, parado; de cabeça para baixo se `flip` (girado uma vez só e guardado)."""
        img = self.frames[("down", 0)]
        if not self.flip:
            return img
        if self._upside_down is None or self._upside_down[0] is not img:
            self._upside_down = (img, pygame.transform.rotate(img, 180))
        return self._upside_down[1]

    def draw(self, surf, cam):
        if self.pose in ("lie", "shower") and self.anchor:    # na cama ou no box: a cena diz onde
            img = self.lying_image()
            surf.blit(img, (self.anchor[0] - img.get_width() // 2 - cam[0], self.anchor[1] - cam[1]))
            return
        img = self.image()
        x = round(self.px) + (TILE - img.get_width()) // 2 - cam[0] + self.nudge[0]
        y = round(self.py) + FOOT_Y - img.get_height() - cam[1] + self.nudge[1]
        if self.sitting:                 # sentado: mostra só até a cintura, um pouco mais baixo
            surf.blit(img, (x, y + SIT_DROP), pygame.Rect(0, 0, img.get_width(), img.get_height() - SIT_CROP))
            return
        surf.blit(img, (x, y))


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
        self.battle = False

    def queue_move(self, map_id, x, y, facing, run, pose="stand"):
        """`pose`: "stand", "sit", "lie" ou "shower" (True/False = sentado ou não, como vem da rede)."""
        pose = {True: "sit", False: "stand"}.get(pose, pose) if isinstance(pose, bool) else pose
        self.pending.append((map_id, x, y, facing, run, pose))
        if len(self.pending) > LAG_LIMIT:
            last = self.pending[-1]
            self.pending.clear()
            self.map_id = last[0]
            self.place(last[1], last[2])
            self.facing = last[3]
            self.pose = last[5]

    def tick(self, dt):
        self.tick_emote(dt)
        self.update(dt)
        if self.moving or not self.pending:
            return
        map_id, x, y, facing, run, pose = self.pending.popleft()
        dx, dy = x - self.tx, y - self.ty
        direction = next((d for d, v in DIR_VECTORS.items() if v == (dx, dy)), None)
        if pose != "stand" or self.pose != "stand":   # sentar, deitar e levantar não têm passo: só reposiciona
            self.pose = pose
            self.map_id = map_id
            self.place(x, y)
        elif map_id == self.map_id and direction:
            self.start_move(direction, RUN_TIME if run else WALK_TIME)
        else:                        # virou no lugar, trocou de mapa ou pulou: só reposiciona
            self.map_id = map_id
            self.place(x, y)
        self.facing = facing or self.facing


class NPC(RemotePlayer):
    """Um NPC (treinador ou ajudante). Anda pela mesma fila de passos dos jogadores online: quem decide para onde
    ele vai é a vida dos NPCs (game/core/townsfolk.py), rodando aqui ou no servidor."""

    def __init__(self, npc_id, name, map_id, spot, frames, on_talk, look=None):
        """frames: quadros de andar (vêm de sprites.character_frames); look: aparência, para o rosto."""
        super().__init__(npc_id, name, frames, map_id, spot.x, spot.y, spot.facing)
        self.look = look
        self.on_talk = on_talk

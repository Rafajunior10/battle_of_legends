"""Dia, tarde e noite na tela. Mixin do LobbyScene.

O relógio (core/clock.py) anda sozinho. Jogando sozinho ele é guardado no save; no online quem manda é o
SERVIDOR (mensagem "clock"), para todos verem a mesma hora.
- A tela ganha uma camada de cor (`clock.tint`): fim de tarde dourado, noite azul. Dentro de casa/lanchonete
  a camada é bem mais fraca (as luzes estão acesas).
- À noite os postes da rua acendem (um brilho amarelo desenhado uma vez e reaproveitado).
- Dormir: deitado à noite você está "dormindo". Sozinho, a noite passa na hora. No online, você avisa o
  servidor ("bed") e ele só pula para a manhã quando TODOS estiverem deitados (aí chega "clock" com slept).
"""
import pygame

from game.core.clock import WorldClock, lights_on, tint
from game.engine.settings import GAME_H, GAME_W, TILE
from game.engine.ui import draw_text, overlay

INDOOR_DIM = 0.3            # dentro de casa a noite escurece só 30% do que escurece na rua
_glow: list = []


def lamp_glow():
    """Brilho amarelo de um poste (círculos transparentes, desenhado uma vez)."""
    if not _glow:
        s = pygame.Surface((56, 56), pygame.SRCALPHA)
        for radius, alpha in ((28, 26), (21, 34), (14, 46), (7, 70)):
            pygame.draw.circle(s, (255, 226, 150, alpha), (28, 28), radius)
        _glow.append(s)
    return _glow[0]


class DayNightMixin:
    def setup_clock(self):
        start = getattr(self.net, "initial_clock", None)
        self.clock = WorldClock.from_dict(start) if start else WorldClock(self.ch.world_minutes, self.ch.world_day)
        self.sleep_skip = False

    def update_clock(self, dt):
        if self.sleep_t is None:
            self.clock.advance(dt)
        if self.net is None:                      # sozinho: o relógio vai junto com o save
            self.ch.world_minutes, self.ch.world_day = self.clock.minutes, self.clock.day

    def on_clock_message(self, message):
        """Online: o servidor acertou o relógio (e talvez todos tenham dormido)."""
        fresh = WorldClock.from_dict(message)
        self.clock.minutes, self.clock.day = fresh.minutes, fresh.day
        if message.get("slept") and self.player.pose == "lie" and self.sleep_t is None:
            self.start_sleep(skip=False, morning=True)    # o servidor já pulou a noite; aqui é só a cena

    def send_bed(self, lying):
        if self.net:
            self.net.send({"t": "bed", "lying": bool(lying)})

    # ------------------------------------------------------------ dormir
    def start_sleep(self, skip, morning=True):
        """A cena de dormir. `skip`: a noite passa aqui (sozinho); `morning`: acorda de manhã (senão é cochilo)."""
        self.sleep_t, self.sleep_skip, self.sleep_morning = 0.0, skip, morning

    def go_to_sleep_now(self):
        """Deitou de noite: sozinho, dorme na hora; online, espera todos deitarem."""
        if self.net is None:
            self.start_sleep(skip=True)
        else:
            self.banner("Dormindo... a noite só passa quando todos estiverem deitados.")

    # ------------------------------------------------------------ desenho
    def draw_daylight(self, surf, cam):
        color, alpha = tint(self.clock.minutes)
        if self.map_def.interior:
            alpha = round(alpha * INDOOR_DIM)
        if alpha:
            surf.blit(overlay(color, alpha), (0, 0))
        if lights_on(self.clock.minutes) and not self.map_def.interior:
            glow = lamp_glow()
            for obj in self.map_def.objects:
                if obj.name == "lamp":
                    x, y = obj.x * TILE + 8 - cam[0], obj.y * TILE + 4 - cam[1]
                    if -40 < x < GAME_W + 40 and -40 < y < GAME_H + 40:
                        surf.blit(glow, (x - 28, y - 28))

    def draw_clock(self, surf):
        """Relógio no canto de baixo, à direita: dia, hora e a fase (sol ou lua)."""
        text = self.clock.label()
        width = 96
        x, y = GAME_W - width - 6, GAME_H - 16
        pygame.draw.rect(surf, (20, 20, 32), (x, y, width, 11), border_radius=3)
        night = self.clock.is_night
        if night:
            pygame.draw.circle(surf, (230, 230, 200), (x + 7, y + 5), 3)
            pygame.draw.circle(surf, (20, 20, 32), (x + 8, y + 4), 3)
        else:
            pygame.draw.circle(surf, (255, 210, 70), (x + 7, y + 5), 3)
        draw_text(surf, text, (x + 14, y + 2), size=8, color=(250, 246, 236), shadow=None)

"""Pescaria. Mixin do LobbyScene. As regras (o que vem no anzol e quanto vale) ficam em core/fishing.py.

A de frente para a água joga a linha. Espere: quando o peixe morder aparece "!" em cima da boia e você tem
menos de 1 segundo para apertar A. Apertou cedo demais ou demorou: o peixe foge. Qualquer direção recolhe a linha.
"""
import math

import pygame

from game.core import fishing
from game.engine import sfx
from game.engine.settings import TILE
from game.engine.ui import draw_outlined
from game.scenes.actors import FOOT_Y


class FishingMixin:
    def setup_fishing(self):
        self.fishing = None             # {"phase": "wait"/"bite", "t": segundos, "spot": tile da boia}

    def start_fishing(self, spot):
        self.fishing = {"phase": "wait", "t": fishing.bite_delay(), "spot": spot}
        sfx.play("cursor")
        self.banner("Pescando... quando o peixe morder (!), aperte A rápido!")

    def update_fishing(self, dt):
        f = self.fishing
        if not f:
            return
        f["t"] -= dt
        if f["t"] > 0:
            return
        if f["phase"] == "wait":
            f["phase"], f["t"] = "bite", fishing.BITE_WINDOW
            sfx.play("encounter")
        else:
            self.end_fishing("O peixe escapou! Tente de novo.")

    def pull_line(self):
        """A pescando: pega o peixe se ele estiver mordendo."""
        if self.fishing["phase"] != "bite":
            self.end_fishing("Puxou cedo demais! O peixe fugiu.")
            return
        item = fishing.catch(night=self.clock.is_night)
        bets = fishing.reward(self.ch, item)
        self.fishing = None
        self.ch.save()
        if bets:
            sfx.play("coin")
            self.say([f"Você pescou um {item.name}!", f"Vendido na hora: +{bets} BETS. ({self.ch.fish_caught} peixes)"])
        else:
            sfx.play("error")
            self.say(f"Você pescou... uma {item.name}. Que azar!")

    def end_fishing(self, text=None):
        self.fishing = None
        if text:
            sfx.play("cancel")
            self.say(text)

    def draw_fishing(self, surf, cam):
        """Linha da vara até a boia, a boia balançando e o "!" quando morde."""
        f = self.fishing
        if not f:
            return
        hand = (round(self.player.px) + TILE // 2 - cam[0], round(self.player.py) + FOOT_Y - 22 - cam[1])
        bob = math.sin(self.time * 6) * (2 if f["phase"] == "bite" else 1)
        float_x = f["spot"][0] * TILE + TILE // 2 - cam[0]
        float_y = f["spot"][1] * TILE + TILE // 2 - cam[1] + round(bob)
        pygame.draw.line(surf, (240, 240, 240), hand, (float_x, float_y))
        pygame.draw.circle(surf, (20, 20, 32), (float_x, float_y), 3)
        pygame.draw.circle(surf, (230, 60, 50), (float_x, float_y), 2)
        if f["phase"] == "bite":
            draw_outlined(surf, "!", (float_x, float_y - 18), (255, 230, 80), (20, 20, 32), size=16, align="center")

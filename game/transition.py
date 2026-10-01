"""Transições de tela: fade simples e a clássica entrada de batalha (piscar + barras)."""
import pygame

from .settings import GAME_H, GAME_W


class Transition:
    def __init__(self, style, on_middle):
        self.style = style
        self.on_middle = on_middle   # chamado com a tela toda preta (troca de cena)
        self.phase = "out"
        self.t = 0.0
        self.done = False
        self.out_time = 1.3 if style == "battle" else 0.35
        self.in_time = 0.45 if style == "battle" else 0.35
        self.overlay = pygame.Surface((GAME_W, GAME_H))

    def update(self, dt):
        self.t += dt
        if self.phase == "out" and self.t >= self.out_time:
            self.on_middle()
            self.phase, self.t = "in", 0.0
        elif self.phase == "in" and self.t >= self.in_time:
            self.done = True

    def draw(self, surf):
        if self.phase == "in":
            self._fade(surf, 1 - min(1.0, self.t / self.in_time))
            return
        p = min(1.0, self.t / self.out_time)
        if self.style == "battle":
            self._battle(surf, p)
        else:
            self._fade(surf, p)

    def _fade(self, surf, amount):
        self.overlay.fill((0, 0, 0))
        self.overlay.set_alpha(int(255 * amount))
        surf.blit(self.overlay, (0, 0))

    def _battle(self, surf, p):
        if p < 0.35:   # tela piscando
            if int(p * 24) % 2 == 0:
                self.overlay.fill((248, 248, 248))
                self.overlay.set_alpha(190)
                surf.blit(self.overlay, (0, 0))
            return
        q = min(1.0, (p - 0.35) / 0.65 * 1.15)
        bars = 8
        h = GAME_H // bars
        w = int(GAME_W * q)
        for i in range(bars):   # barras fechando de lados alternados
            x = 0 if i % 2 == 0 else GAME_W - w
            pygame.draw.rect(surf, (16, 16, 24), (x, i * h, w, h))

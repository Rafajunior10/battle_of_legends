"""Tela de título."""
import math

import pygame

from game.data.cards import CARDS
from game.engine import sfx
from game.engine.settings import GAME_H, GAME_W
from game.engine.ui import Menu, draw_outlined, draw_text, vertical_gradient
from game.graphics import pixelart as art
from game.graphics import tilemap
from game.scenes.base import Scene

GRASS_GREEN = (88, 168, 72)   # faixa de grama se o pacote de arte faltar

class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        options = ["JOGAR", "OPÇÕES", "SAIR"]
        self.menu = Menu(options, (GAME_W - 96) // 2, GAME_H - 18 - 14 * len(options), width=96, line_h=14)
        self.time = 0.0
        self.bg = vertical_gradient((GAME_W, GAME_H), (40, 56, 120), (136, 184, 240))
        if tilemap.available():
            grass = tilemap.tile(*tilemap.GRASS_TILES[0])
            for x in range(0, GAME_W, 16):
                for y in (GAME_H - 32, GAME_H - 16):
                    self.bg.blit(grass, (x, y))
        else:
            self.bg.fill(GRASS_GREEN, (0, GAME_H - 32, GAME_W, 32))
        self.cards = [
            (art.scale(art.render_card(CARDS[cid]), 2), angle)
            for cid, angle in (("bola_de_fogo", 12), ("choque_do_trovao", 0), ("fica_frio_ai", -12))
        ]

    def on_enter(self):
        sfx.music("lobby")

    def handle(self, event):
        choice = self.menu.handle(event)
        if choice is None or choice == -1:
            return
        option = self.menu.options[choice]
        if option == "JOGAR":                     # hospedar ou entrar no mundo, e fazer login
            from game.scenes.online import OnlineScene
            self.game.transition_to(lambda: OnlineScene(self.game))
        elif option == "OPÇÕES":
            from game.scenes.options import OptionsScene
            self.game.transition_to(lambda: OptionsScene(self.game, lambda: TitleScene(self.game)))
        else:
            self.game.quit()

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        # estrelinhas piscando
        for i in range(36):
            x = (i * 53) % GAME_W
            y = (i * 29) % 110
            if int(self.time * 2 + i) % 3:
                surf.set_at((x, y), (248, 248, 232))
        # cartas em leque flutuando
        for i, (img, angle) in enumerate(self.cards):
            bob = math.sin(self.time * 2 + i) * 3
            rotated = pygame.transform.rotate(img, angle)
            x = GAME_W // 2 + (i - 1) * 140 - rotated.get_width() // 2
            y = GAME_H // 2 + 6 + bob - rotated.get_height() // 2 + (abs(i - 1) * 10)
            surf.blit(rotated, (x, y))
        draw_outlined(surf, "CARD QUEST", (GAME_W // 2 + 2, 16), (248, 208, 64), (40, 40, 48), size=48, align="center")
        draw_text(surf, "um RPG de cartas", (GAME_W // 2, 50), color=(248, 248, 248), shadow=(40, 56, 120),
                  align="center")
        self.menu.draw(surf)

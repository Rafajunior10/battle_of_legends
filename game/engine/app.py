"""Classe principal: janela, loop do jogo e troca de cenas."""
import os

import pygame

from game.engine import config, sfx
from game.engine.display import Display
from game.engine.settings import TITLE
from game.engine.transition import Transition
from game.engine.ui import draw_outlined

MAX_DT = 1 / 20      # um travamento longo não faz tudo "pular" de uma vez


class Game:
    def __init__(self):
        sfx.pre_init()
        pygame.init()
        pygame.display.set_caption(TITLE)
        config.load()
        self.display = Display()
        self.clock = pygame.time.Clock()
        sfx.init()
        self.character = None
        self.lobby = None
        self.net = None          # conexão com o mundo compartilhado (game.net.client.WorldClient) ou None
        self.transition = None
        self.running = True
        self.scene = None
        if not (os.environ.get("CARD_QUEST_AUTOLOAD") and self.autoload()):
            from game.scenes.title import TitleScene
            self.change_scene(TitleScene(self))

    def autoload(self):
        """Modo dev: carrega o save e vai direto para o lobby."""
        from game.data.character import Character
        from game.scenes.lobby import LobbyScene
        character = Character.load() if Character.exists() else None
        if character is None:
            return False
        self.character = character
        self.lobby = LobbyScene(self)
        self.change_scene(self.lobby)
        return True

    @property
    def screen(self):
        """Superfície 320x240 onde tudo é desenhado."""
        return self.display.screen

    def apply_display(self):
        """Reabre a janela depois de mudar tela cheia ou tamanho nas OPÇÕES."""
        self.display.open()

    def set_fullscreen(self, on):
        config.display["fullscreen"] = on
        config.save()
        self.apply_display()

    def present(self):
        self.display.present()

    @property
    def busy(self):
        return self.transition is not None

    def change_scene(self, scene):
        self.scene = scene
        scene.on_enter()

    def transition_to(self, make_scene, style="fade"):
        """make_scene é chamada no meio da transição e deve devolver a nova cena."""
        if self.transition is None:
            self.transition = Transition(style, lambda: self.change_scene(make_scene()))

    def start_battle(self, spec, on_end):
        from game.scenes.battle import BattleScene
        if self.net:
            self.net.send({"t": "status", "battle": True})   # os outros veem a espada em cima de você
        sfx.music(None)
        sfx.play("encounter")
        self.transition_to(lambda: BattleScene(self, spec, on_end), style="battle")

    def draw_fps(self):
        label = f"{self.clock.get_fps():.0f} FPS" + (" vsync" if self.display.vsync else "")
        draw_outlined(self.screen, label, (self.screen.get_width() - 3, 2), (248, 248, 120), size=12, align="right")

    def quit(self):
        self.running = False

    def leave_online(self):
        """Sai do mundo compartilhado (e fecha o servidor, se este computador estava hospedando)."""
        from game.data import character
        character.remote_save = None          # sem conexão, o save volta para o arquivo
        if self.net is not None:
            self.net.close()
            self.net = None

    def run(self):
        """Laço principal. Ctrl+C no terminal fecha o jogo normalmente, sem mostrar erro."""
        try:
            while self.running:
                self.frame()
        except KeyboardInterrupt:
            print("Card Quest fechado pelo terminal (Ctrl+C).")
        finally:
            self.leave_online()
            pygame.quit()

    def frame(self):
        """Um quadro do jogo: eventos -> atualizar -> desenhar."""
        dt = min(self.clock.tick(config.display["fps"]) / 1000.0, MAX_DT)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.set_fullscreen(not config.display["fullscreen"])
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                config.display["show_fps"] = not config.display["show_fps"]
                config.save()
            elif not self.busy:
                self.scene.handle(event)
        self.scene.update(dt)
        if self.transition:
            self.transition.update(dt)
            if self.transition.done:
                self.transition = None
        sfx.update()
        self.scene.draw(self.screen)
        if self.transition:
            self.transition.draw(self.screen)
        if config.display["show_fps"]:
            self.draw_fps()
        self.present()


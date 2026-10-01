"""Janela do jogo: a tela interna de 320x240 ampliada para o monitor.

Caminho preferido: a placa de vídeo amplia (pygame.SCALED) e o vsync sincroniza com o monitor,
o que deixa o movimento liso e sem "rasgos". Se o computador não aceitar, o processador amplia
(o jeito antigo), mantendo a proporção com bordas pretas.
"""
import warnings

import pygame

from game.engine import config
from game.engine.settings import GAME_H, GAME_W


class Display:
    def __init__(self):
        self.gpu = False       # a placa de vídeo está ampliando a imagem
        self.vsync = False
        self.window = None
        self.screen = None     # superfície 320x240 onde as cenas desenham
        self.open()

    def open(self):
        """(Re)abre a janela no modo configurado."""
        full = config.display["fullscreen"]
        flags = pygame.SCALED | (pygame.FULLSCREEN if full else 0)
        for vsync in (1, 0):
            try:
                surface = pygame.display.set_mode((GAME_W, GAME_H), flags, vsync=vsync)
            except pygame.error:
                continue
            self.gpu, self.vsync = True, bool(vsync)
            self.window = self.screen = surface
            if not full:
                self._resize_window(config.display["scale"])
            break
        else:
            self._open_software(full)
        pygame.mouse.set_visible(not full)

    @staticmethod
    def fitting_scale(scale):
        """Maior escala até `scale` que cabe no monitor (com folga para a barra de tarefas)."""
        try:
            desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError):
            return scale
        while scale > 1 and (GAME_W * scale > desk_w or GAME_H * scale > desk_h - 60):
            scale -= 1
        return scale

    def _resize_window(self, scale):
        """No modo SCALED o tamanho da janela é escolhido pelo SDL; aqui aplicamos o tamanho das OPÇÕES."""
        scale = self.fitting_scale(scale)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            try:
                window = pygame.Window.from_display_module()
            except (AttributeError, pygame.error):
                return
        window.size = (GAME_W * scale, GAME_H * scale)

    def _open_software(self, full):
        self.gpu = self.vsync = False
        if full:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            scale = self.fitting_scale(config.display["scale"])
            self.window = pygame.display.set_mode((GAME_W * scale, GAME_H * scale))
        if self.screen is None or self.screen is self.window or self.screen.get_size() != (GAME_W, GAME_H):
            self.screen = pygame.Surface((GAME_W, GAME_H)).convert()

    def present(self):
        """Leva o quadro para o monitor."""
        if not self.gpu:
            self._scale_to_window()
        pygame.display.flip()

    def _scale_to_window(self):
        ww, wh = self.window.get_size()
        k = min(ww / GAME_W, wh / GAME_H)
        size = (int(GAME_W * k), int(GAME_H * k))
        if size == (ww, wh):
            pygame.transform.scale(self.screen, size, self.window)
            return
        self.window.fill((0, 0, 0))
        self.window.blit(pygame.transform.scale(self.screen, size), ((ww - size[0]) // 2, (wh - size[1]) // 2))

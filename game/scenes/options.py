"""Opções: modo de tela (janela / tela cheia), tamanho da janela, FPS e teclas."""
import pygame

from game.engine import config, sfx
from game.engine.config import ACTIONS, FPS_OPTIONS, SCALES, action_label, key_label
from game.engine.settings import (
    CANCEL_KEYS,
    CONFIRM_KEYS,
    DOWN_KEYS,
    GAME_H,
    GAME_W,
    HIGHLIGHT,
    LEFT_KEYS,
    RIGHT_KEYS,
    UP_KEYS,
)
from game.engine.ui import draw_box, draw_cursor, draw_text, vertical_gradient
from game.scenes.base import Scene

ROW_SCREEN, ROW_SCALE, ROW_FPS, ROW_SHOW_FPS = 0, 1, 2, 3
FIRST_ACTION = 4
ROW_RESET = FIRST_ACTION + len(ACTIONS)
ROW_BACK = ROW_RESET + 1
ROWS = ROW_BACK + 1
COL_X = (GAME_W - 190, GAME_W - 84)   # centro das colunas TECLA 1 e TECLA 2


RESET_Y = 99 + len(ACTIONS) * 12 + 4      # logo abaixo da última ação (cresce sozinho com ações novas)


def row_y(row):
    if row < FIRST_ACTION:
        return 36 + row * 12
    if row < ROW_RESET:
        return 99 + (row - FIRST_ACTION) * 12
    return RESET_Y + (row - ROW_RESET) * 12


def fps_label(fps):
    return "SEM LIMITE" if fps == 0 else f"{fps} FPS"


class OptionsScene(Scene):
    def __init__(self, game, back):
        """back: função que devolve a cena para onde voltar."""
        super().__init__(game)
        self.back = back
        self.row = 0
        self.col = 0
        self.waiting = False   # esperando a nova tecla
        self.toast = None
        self.toast_t = 0.0
        self.time = 0.0
        self.bg = vertical_gradient((GAME_W, GAME_H), (48, 56, 96), (112, 136, 184))

    def say(self, text, ok=True):
        self.toast = text
        self.toast_t = 2.2
        sfx.play("confirm" if ok else "error")

    # ------------------------------------------------------------ input
    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if self.waiting:
            self.waiting = False
            if key == pygame.K_ESCAPE:
                sfx.play("cancel")
                return
            action = ACTIONS[self.row - FIRST_ACTION][0]
            error = config.bind(action, self.col, key)
            if error:
                self.say(error, ok=False)
            else:
                config.save()
                self.say(f"{config.ACTION_NAMES[action]} agora usa {key_label(key)}.")
            return
        if key in UP_KEYS or key in DOWN_KEYS:
            self.row = (self.row + (-1 if key in UP_KEYS else 1)) % ROWS
            sfx.play("cursor")
        elif key in LEFT_KEYS or key in RIGHT_KEYS:
            self.side(1 if key in RIGHT_KEYS else -1)
        elif key in CONFIRM_KEYS:
            self.confirm()
        elif key in CANCEL_KEYS:
            self.leave()

    def side(self, step):
        if self.row == ROW_SCREEN:
            self.game.set_fullscreen(not config.display["fullscreen"])
            sfx.play("cursor")
        elif self.row == ROW_SCALE:
            self.change_scale(step)
        elif self.row == ROW_FPS:
            i = FPS_OPTIONS.index(config.display["fps"])
            config.display["fps"] = FPS_OPTIONS[(i + step) % len(FPS_OPTIONS)]
            config.save()
            sfx.play("cursor")
        elif self.row == ROW_SHOW_FPS:
            config.display["show_fps"] = not config.display["show_fps"]
            config.save()
            sfx.play("cursor")
        elif FIRST_ACTION <= self.row < ROW_RESET:
            self.col = 1 - self.col
            sfx.play("cursor")

    def change_scale(self, step):
        if config.display["fullscreen"]:
            self.say("O tamanho só vale no modo janela.", ok=False)
            return
        i = SCALES.index(config.display["scale"])
        config.display["scale"] = SCALES[(i + step) % len(SCALES)]
        config.save()
        self.game.apply_display()
        sfx.play("cursor")

    def confirm(self):
        if self.row < FIRST_ACTION:
            self.side(1)
        elif self.row == ROW_RESET:
            config.reset_bindings()
            config.save()
            self.say("Teclas voltaram ao padrão.")
        elif self.row == ROW_BACK:
            self.leave()
        else:
            self.waiting = True
            sfx.play("confirm")

    def leave(self):
        sfx.play("cancel")
        config.save()
        self.game.transition_to(self.back)

    def update(self, dt):
        self.time += dt
        self.toast_t = max(0.0, self.toast_t - dt)

    # ------------------------------------------------------------ desenho
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_box(surf, (4, 4, GAME_W - 8, 24))
        draw_text(surf, "OPÇÕES", (14, 9))
        draw_text(surf, "F11: tela cheia   F3: FPS", (GAME_W - 14, 11), size=12, align="right")
        draw_box(surf, (4, 30, GAME_W - 8, GAME_H - 46))

        full = config.display["fullscreen"]
        scale = config.display["scale"]
        vsync = " (vsync)" if self.game.display.vsync else ""
        rows = [
            (ROW_SCREEN, "TELA", "TELA CHEIA" if full else "JANELA", False),
            (ROW_SCALE, "TAMANHO DA JANELA", f"{GAME_W * scale}x{GAME_H * scale}", full),
            (ROW_FPS, "LIMITE DE FPS", fps_label(config.display["fps"]) + vsync, False),
            (ROW_SHOW_FPS, "MOSTRAR FPS", "SIM" if config.display["show_fps"] else "NÃO", False),
        ]
        for row, label, value, dim in rows:
            self.draw_label(surf, row, label, dim=dim, size=12)
            self.draw_choice(surf, row, value, dim=dim)

        pygame.draw.line(surf, (184, 200, 216), (14, 84), (GAME_W - 14, 84))
        draw_text(surf, "CONTROLES", (16, 87), color=(208, 64, 56), size=12)
        for x, title in zip(COL_X, ("TECLA 1", "TECLA 2"), strict=True):
            draw_text(surf, title, (x, 87), color=(136, 136, 144), size=12, align="center")
        for i, (action, name) in enumerate(ACTIONS):
            row = FIRST_ACTION + i
            self.draw_label(surf, row, name, size=12)
            for col, x in enumerate(COL_X):
                cell = pygame.Rect(x - 36, row_y(row) - 1, 72, 12)
                selected = row == self.row and col == self.col
                if selected:
                    blink = self.waiting and int(self.time * 4) % 2
                    pygame.draw.rect(surf, (248, 200, 48) if not blink else (248, 240, 200), cell, border_radius=2)
                key = config.bindings[action][col]
                text = "???" if selected and self.waiting else key_label(key)
                draw_text(surf, text, (x, row_y(row)), size=12, shadow=None, align="center",
                          color=(72, 72, 80) if key else (176, 176, 176))
        pygame.draw.line(surf, (184, 200, 216), (14, RESET_Y - 3), (GAME_W - 14, RESET_Y - 3))
        self.draw_label(surf, ROW_RESET, "RESTAURAR TECLAS PADRÃO", size=12)
        self.draw_label(surf, ROW_BACK, "VOLTAR", size=12)

        if self.waiting:
            name = config.ACTION_NAMES[ACTIONS[self.row - FIRST_ACTION][0]]
            hint = f"Aperte a nova tecla para {name} (ESC cancela)"
        elif self.toast_t > 0:
            hint = self.toast
        else:
            hint = f"{action_label('a')}: mudar   < >: escolher   {action_label('b')}: voltar"
        draw_text(surf, hint, (GAME_W // 2, GAME_H - 13), color=(248, 248, 248), shadow=(40, 48, 88), size=12,
                  align="center")

    def draw_label(self, surf, row, text, dim=False, size=16):
        y = row_y(row)
        if row == self.row and not (self.waiting and row >= FIRST_ACTION):
            draw_cursor(surf, 12, y + (1 if size == 16 else 0))
        color = (176, 176, 176) if dim else (72, 72, 80)
        draw_text(surf, text, (22, y - (1 if size == 16 else 0)), size=size, color=color)

    def draw_choice(self, surf, row, text, dim=False):
        y = row_y(row)
        color = (176, 176, 176) if dim else (40, 88, 176)
        draw_text(surf, f"<  {text}  >", (GAME_W - 137, y), color=color, size=12, align="center")
        if row == self.row and not dim:
            pygame.draw.line(surf, HIGHLIGHT, (GAME_W - 245, y + 10), (GAME_W - 30, y + 10))

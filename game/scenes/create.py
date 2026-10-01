"""Criação de personagem: aparência (boneco de papel) + nome."""
from dataclasses import asdict

import pygame

from .. import pixelart as art
from .. import sfx, sprites
from ..character import Character
from ..config import action_label
from ..looks import (
    BOTTOMS,
    CLOTH_COLORS,
    DEFAULT_HAIR,
    GENDERS,
    HAIR_COLORS,
    HAIR_STYLES,
    HATS,
    SHOE_COLORS,
    SKIN_TONES,
    TOPS,
    Look,
)
from ..settings import CANCEL_KEYS, CONFIRM_KEYS, DOWN_KEYS, GAME_H, GAME_W, LEFT_KEYS, RIGHT_KEYS, UP_KEYS
from ..ui import draw_box, draw_cursor, draw_outlined, draw_text, vertical_gradient, wrap
from .base import Scene

COLORS = list(CLOTH_COLORS)
# Cada opção: (rótulo, campo do Look, escolhas). As escolhas podem depender da aparência atual (uma função):
# homem escolhe camisa/regata/manga longa e calça/bermuda; mulher, camisa/top/manga longa e saia/calça/vestido.
OPTIONS = [
    ("GÊNERO", "gender", GENDERS),
    ("CABELO", "hair", HAIR_STYLES),
    ("COR DO CABELO", "hair_color", list(HAIR_COLORS)),
    ("PELE", "skin", list(range(len(SKIN_TONES)))),
    ("PARTE DE CIMA", "top", lambda look: TOPS[look.gender]),
    ("COR DE CIMA", "shirt", COLORS),
    ("PARTE DE BAIXO", "bottom", lambda look: BOTTOMS[look.gender]),
    ("COR DE BAIXO", "legs", COLORS),
    ("TÊNIS", "shoes", list(SHOE_COLORS)),
    ("CHAPÉU", "hat", list(HATS)),
    ("COR DO CHAPÉU", "hat_color", lambda look: HATS[look.hat]),
]
MAX_NAME = 10
PREVIEW_DIRS = ["down", "left", "up", "right"]
PREVIEW_HEIGHT = 132      # altura do boneco na prévia
ROW_H = 15


def choices_of(option, look: Look) -> list:
    choices = option[2]
    return choices(look) if callable(choices) else choices


class CreateScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.values = asdict(Look())      # valor escolhido em cada campo
        self.name = ""
        self.row = 0
        self.time = 0.0
        self.warning = None
        self.bg = vertical_gradient((GAME_W, GAME_H), (32, 40, 88), (88, 128, 200))

    @property
    def look(self) -> Look:
        """A aparência montada com as escolhas atuais."""
        return Look(**self.values).fitted()

    @property
    def options(self) -> list:
        """As opções que aparecem agora: sem chapéu não tem cor de chapéu; careca ou de capuz, não tem
        cor de cabelo; com vestido, não tem cor de cima (o vestido é uma peça só)."""
        look = self.look
        hidden = {"shirt"} if look.bottom == "vestido" else set()
        if look.hat == "nenhum":
            hidden.add("hat_color")
        if look.hair == "careca" or look.hat == "capuz":
            hidden.add("hair_color")
        return [o for o in OPTIONS if o[1] not in hidden]

    @property
    def name_row(self):
        return len(self.options)

    @property
    def done_row(self):
        return len(self.options) + 1

    @property
    def row_count(self):
        return len(self.options) + 2

    def on_enter(self):
        pygame.key.start_text_input()
        sfx.music("lobby")

    # ------------------------------------------------------------ input
    def handle(self, event):
        if event.type == pygame.TEXTINPUT and self.row == self.name_row:
            for ch in event.text:
                if (ch.isalnum() or ch in " -_") and len(self.name) < MAX_NAME:
                    self.name += ch
                    sfx.play("cursor")
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        typing = self.row == self.name_row   # no nome, letras são texto: só as setas navegam
        if key == pygame.K_UP or (not typing and key in UP_KEYS):
            self.row = (self.row - 1) % self.row_count
            sfx.play("cursor")
        elif key == pygame.K_DOWN or (not typing and key in DOWN_KEYS):
            self.row = (self.row + 1) % self.row_count
            sfx.play("cursor")
        elif typing:
            self.handle_name_key(key)
        elif key in LEFT_KEYS or key in RIGHT_KEYS:
            self.change(1 if key in RIGHT_KEYS else -1)
        elif key in CONFIRM_KEYS:
            if self.row == self.done_row:
                self.finish()
            else:
                self.row += 1
                sfx.play("cursor")
        elif key in CANCEL_KEYS:
            self.back()

    def handle_name_key(self, key):
        """Teclas especiais na linha do nome (as letras chegam pelo TEXTINPUT)."""
        if key == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.row = self.done_row
            sfx.play("cursor")
        elif key == pygame.K_ESCAPE:
            self.back()

    def change(self, step):
        if self.row >= len(self.options):
            return
        option = self.options[self.row]
        choices = choices_of(option, self.look)
        current = getattr(self.look, option[1])
        index = choices.index(current) if current in choices else 0
        self.values[option[1]] = choices[(index + step) % len(choices)]
        if option[1] == "gender":                     # trocou de gênero: sugere o cabelo combinando
            self.values["hair"] = DEFAULT_HAIR[self.values["gender"]]
        self.values = asdict(self.look)   # trocou de gênero? as peças que não existem para ele são trocadas
        sfx.play("cursor")

    def back(self):
        from .title import TitleScene
        pygame.key.stop_text_input()
        sfx.play("cancel")
        self.game.transition_to(lambda: TitleScene(self.game))

    def finish(self):
        name = self.name.strip()
        if not name:
            sfx.play("error")
            self.warning = "Escolha um nome antes de começar!"
            self.row = self.name_row
            return
        from .lobby import LobbyScene
        pygame.key.stop_text_input()
        sfx.play("save")
        character = Character(name=name)
        character.wear(self.look)
        character.save()
        self.game.character = character
        self.game.lobby = LobbyScene(self.game, first_time=True)
        self.game.transition_to(lambda: self.game.lobby)

    def update(self, dt):
        self.time += dt

    # ------------------------------------------------------------ desenho
    def label_of(self, row):
        """Rótulo da linha (as opções, o NOME e o PRONTO!)."""
        if row == self.name_row:
            return "NOME"
        if row == self.done_row:
            return "PRONTO!"
        label, field, _ = self.options[row]
        if field == "legs" and self.look.bottom == "vestido":
            return "COR DO VESTIDO"
        return label

    def value_of(self, row):
        if row < len(self.options):
            field = self.options[row][1]
            value = getattr(self.look, field)
            return f"Tom {value + 1}" if field == "skin" else str(value).capitalize()
        if row == self.name_row:
            cursor = "_" if self.row == self.name_row and int(self.time * 3) % 2 == 0 else ""
            return self.name + cursor
        return ""

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_outlined(surf, "CRIE SEU PERSONAGEM", (GAME_W // 2, 10), (248, 248, 248), (32, 40, 88), size=24,
                      align="center")
        self.draw_preview(surf)
        box = pygame.Rect(GAME_W - 262, 32, 250, 16 + ROW_H * self.row_count)
        draw_box(surf, box)
        for i in range(self.row_count):
            y = box.y + 8 + i * ROW_H
            color = (208, 64, 56) if i == self.done_row else (72, 72, 80)
            draw_text(surf, self.label_of(i), (box.x + 20, y), color=color)
            value = self.value_of(i)
            if value:
                if i == self.name_row:
                    draw_text(surf, value, (box.x + 140, y))
                else:
                    draw_text(surf, value, (box.x + 190, y), align="center")
            if i == self.row:
                draw_cursor(surf, box.x + 10, y + 1)
                if i < len(self.options):
                    draw_text(surf, "<", (box.x + 134, y), color=(208, 64, 56))
                    draw_text(surf, ">", (box.right - 12, y), color=(208, 64, 56), align="right")
        self.draw_hint(surf)

    def draw_preview(self, surf):
        """O personagem girando e andando no lugar, com as escolhas atuais."""
        frames = sprites.character_frames(self.look)
        direction = PREVIEW_DIRS[int(self.time / 0.9) % 4]
        frame = (0, 1, 0, 2)[int(self.time / 0.15) % 4]
        img = frames[(direction, frame)]
        figure = art.scale(img, sprites.fit_scale(img, PREVIEW_HEIGHT))
        feet = (110, 196)
        pygame.draw.ellipse(surf, (40, 56, 96), (feet[0] - 56, feet[1] - 14, 112, 26))
        pygame.draw.ellipse(surf, (120, 168, 224), (feet[0] - 52, feet[1] - 14, 104, 20))
        surf.blit(figure, (feet[0] - figure.get_width() // 2, feet[1] - figure.get_height()))

    def draw_hint(self, surf):
        if self.warning and self.row == self.name_row:
            hint = self.warning
        elif self.row < self.name_row:
            hint = "ESQ/DIR mudam a opção. CIMA/BAIXO trocam de linha."
        elif self.row == self.name_row:
            hint = "Digite seu nome no teclado. ENTER para confirmar."
        else:
            hint = f"Aperte {action_label('a')} para começar a sua aventura!"
        draw_box(surf, (4, GAME_H - 36, GAME_W - 8, 32))
        draw_text(surf, wrap(hint, GAME_W - 36)[0], (18, GAME_H - 26))

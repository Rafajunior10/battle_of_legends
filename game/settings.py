"""Configurações globais do jogo."""
import os

TITLE = "Card Quest"
GAME_W, GAME_H = 480, 270   # resolução interna 16:9 (x2 = 960x540, x4 = 1920x1080)
TILE = 16

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_PATH = os.path.join(ROOT_DIR, "save.json")

# Controles (estilo GBA: Z = A, X = B, ENTER = START). Configuráveis no menu OPÇÕES.
from .config import (  # noqa: E402,F401
                     CANCEL_KEYS,
                     CONFIRM_KEYS,
                     DOWN_KEYS,
                     INTERACT_KEYS,
                     KEY_DIRS,
                     LEFT_KEYS,
                     MENU_KEYS,
                     PROFILE_KEYS,
                     RIGHT_KEYS,
                     RUN_KEYS,
                     UP_KEYS,
)

# Paleta de interface estilo GBA
TEXT = (72, 72, 80)
TEXT_SHADOW = (208, 208, 200)
BOX_BORDER = (56, 88, 120)
BOX_INNER = (120, 184, 216)
BOX_FILL = (248, 248, 248)
HIGHLIGHT = (248, 200, 48)

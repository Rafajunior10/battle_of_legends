"""Opções do jogo (tela e controles), salvas em config.json.

As teclas ficam em `bindings`: cada ação tem 2 teclas. Os conjuntos como
CONFIRM_KEYS são dinâmicos, então mudar uma tecla vale na hora para o jogo todo.
ENTER e ESC são fixos (sempre confirmam/voltam e abrem o menu), para ninguém ficar preso.
"""
import json
import os

import pygame

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # card-quest/
CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")

ACTIONS = [
    ("up", "CIMA"), ("down", "BAIXO"), ("left", "ESQUERDA"), ("right", "DIREITA"),
    ("a", "A (CONFIRMAR)"), ("b", "B (VOLTAR)"), ("start", "START (MENU)"), ("run", "CORRER"),
    ("profile", "FICHA"),
]
ACTION_NAMES = dict(ACTIONS)
DEFAULT_BINDINGS = {
    "up": [pygame.K_UP, pygame.K_w],
    "down": [pygame.K_DOWN, pygame.K_s],
    "left": [pygame.K_LEFT, pygame.K_a],
    "right": [pygame.K_RIGHT, pygame.K_d],
    "a": [pygame.K_z, pygame.K_SPACE],
    "b": [pygame.K_x, pygame.K_BACKSPACE],
    "start": [pygame.K_m, pygame.K_TAB],
    "run": [pygame.K_LSHIFT, pygame.K_RSHIFT],
    "profile": [pygame.K_i, pygame.K_e],
}
RESERVED = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_F11, pygame.K_F3}
SCALES = [2, 3, 4]
FPS_OPTIONS = [60, 120, 144, 0]     # 0 = sem limite (o vsync ainda segura no ritmo do monitor)

bindings = {k: list(v) for k, v in DEFAULT_BINDINGS.items()}
display = {"fullscreen": False, "scale": 3, "fps": 60, "show_fps": False}
online = {"address": ""}       # último endereço digitado em ONLINE > ENTRAR


class KeySet:
    """Conjunto de teclas calculado na hora a partir das ações configuradas."""

    def __init__(self, *actions, extra=()):
        self.actions = actions
        self.extra = extra

    def keys(self):
        keys = set(self.extra)
        for action in self.actions:
            keys.update(k for k in bindings[action] if k)
        return keys

    def __contains__(self, key):
        return key in self.keys()

    def __iter__(self):
        return iter(self.keys())


class DirKeys:
    """Pares (tecla, direção) para o movimento no mapa."""

    def __iter__(self):
        for action in ("up", "down", "left", "right"):
            for k in bindings[action]:
                if k:
                    yield k, action


CONFIRM_KEYS = KeySet("a", extra=(pygame.K_RETURN, pygame.K_KP_ENTER))
CANCEL_KEYS = KeySet("b", extra=(pygame.K_ESCAPE,))
INTERACT_KEYS = KeySet("a")
MENU_KEYS = KeySet("start", extra=(pygame.K_RETURN, pygame.K_ESCAPE))
RUN_KEYS = KeySet("run", "b")
PROFILE_KEYS = KeySet("profile")
UP_KEYS = KeySet("up")
DOWN_KEYS = KeySet("down")
LEFT_KEYS = KeySet("left")
RIGHT_KEYS = KeySet("right")
KEY_DIRS = DirKeys()


def key_label(key):
    if not key:
        return "---"
    names = {pygame.K_SPACE: "ESPAÇO", pygame.K_BACKSPACE: "APAGAR", pygame.K_LSHIFT: "SHIFT E",
             pygame.K_RSHIFT: "SHIFT D", pygame.K_UP: "SETA CIMA", pygame.K_DOWN: "SETA BAIXO",
             pygame.K_LEFT: "SETA ESQ", pygame.K_RIGHT: "SETA DIR", pygame.K_LCTRL: "CTRL E",
             pygame.K_RCTRL: "CTRL D", pygame.K_LALT: "ALT E", pygame.K_RALT: "ALT D"}
    return names.get(key) or pygame.key.name(key).upper() or f"#{key}"


def action_label(action):
    """Nome da tecla principal de uma ação, para as dicas na tela (ex.: 'Z')."""
    return key_label(next((k for k in bindings[action] if k), 0))


def bind(action, slot, key):
    """Liga `key` à ação. Se a tecla já era de outra ação, sai de lá.
    Devolve None se deu certo, ou o motivo do erro."""
    if key in RESERVED:
        return "ENTER, ESC, F3 e F11 são fixos."
    for other, keys in bindings.items():
        if other != action and key in keys:
            if sum(1 for k in keys if k) == 1:
                return f"Essa é a única tecla de {ACTION_NAMES[other]}."
            keys[keys.index(key)] = 0
    keys = bindings[action]
    if key in keys:
        keys[keys.index(key)] = 0
    keys[slot] = key
    return None


def reset_bindings():
    for action, keys in DEFAULT_BINDINGS.items():
        bindings[action] = list(keys)


def load():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    address = data.get("online", {}).get("address", "")
    online["address"] = address if isinstance(address, str) else ""
    disp = data.get("display", {})
    display["fullscreen"] = bool(disp.get("fullscreen", False))
    if disp.get("scale") in SCALES:
        display["scale"] = disp["scale"]
    if disp.get("fps") in FPS_OPTIONS:
        display["fps"] = disp["fps"]
    display["show_fps"] = bool(disp.get("show_fps", False))
    for action, keys in data.get("bindings", {}).items():
        if action in bindings and isinstance(keys, list) and len(keys) == 2 and any(keys):
            bindings[action] = [int(k) for k in keys]
    _drop_duplicates()


def _drop_duplicates():
    """Ação nova (ex.: FICHA) num config antigo: se a tecla padrão já era de outra ação, ela sai da nova."""
    taken = {}
    for action, keys in bindings.items():
        for i, key in enumerate(keys):
            if key and key in taken and taken[key] != action:
                keys[i] = 0
            elif key:
                taken[key] = action


def save():
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"display": display, "bindings": bindings, "online": online}, f, indent=2)
    except OSError:
        pass

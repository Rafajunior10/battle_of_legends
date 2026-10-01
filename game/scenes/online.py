"""Tela JOGAR: hospedar o mundo (o seu PC é o servidor) ou entrar no mundo de quem hospeda, e fazer login.

Hospedar: este computador abre o servidor (game/net/server.py), com as contas e personagens em world.db.
Entrar: digita o endereço de quem hospeda (na mesma casa, o que começa com 192.168.).
Depois, os dois fazem login. Conta nova cria o personagem (ou importa o que já estava salvo neste PC).
O personagem fica no servidor: cada vez que o jogo salva, ele vai para lá.
"""
import os
from dataclasses import asdict

import pygame

from game.data import character as character_module
from game.data.character import Character
from game.engine import config, sfx
from game.engine.settings import CANCEL_KEYS, CONFIRM_KEYS, DOWN_KEYS, GAME_H, GAME_W, ROOT_DIR, UP_KEYS
from game.engine.ui import Menu, Prompt, draw_box, draw_cursor, draw_outlined, draw_text, vertical_gradient, wrap
from game.net.client import JoinError, WorldClient
from game.net.protocol import PORT, local_addresses, parse_address
from game.scenes.base import Scene

WORLD_DB = os.path.join(ROOT_DIR, "world.db")      # contas e personagens (só no PC de quem hospeda)
OPTIONS = ["HOSPEDAR", "ENTRAR", "VOLTAR"]
LOGIN_ROWS = ["USUÁRIO", "SENHA", "ENTRAR", "CRIAR CONTA"]
USER_ROW, PASSWORD_ROW, LOGIN_ROW, REGISTER_ROW = range(4)
MAX_ADDRESS, MAX_USER, MAX_PASSWORD = 21, 16, 24
ADDRESS_CHARS = set("0123456789.:abcdefghijklmnopqrstuvwxyz-")
USER_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-.")
HELP = {
    "HOSPEDAR": "Abre o mundo neste computador (ele vira o servidor). Os outros entram pelo seu endereço.",
    "ENTRAR": "Entra no mundo de quem está hospedando. Digite o endereço que aparece na tela dele.",
    "VOLTAR": "Volta para a tela de título.",
}
TIP = "Na mesma casa, use o endereço que começa com 192.168. Pela internet: Radmin VPN ou ZeroTier."


class OnlineScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = Menu(OPTIONS, GAME_W // 2 - 50, 92, width=100, line_h=16)
        self.mode = "menu"                     # menu | address | login
        self.address = config.online["address"]
        self.user = config.online.get("user", "")
        self.password = ""
        self.row = USER_ROW
        self.error = None
        self.client = None
        self.prompt = Prompt()
        self.time = 0.0
        self.bg = vertical_gradient((GAME_W, GAME_H), (24, 32, 72), (72, 104, 168))

    def on_enter(self):
        sfx.music("lobby")

    # ------------------------------------------------------------ conexão
    def host(self):
        self.connect(lambda client: client.host(PORT, WORLD_DB))

    def join(self):
        config.online["address"] = self.address
        config.save()
        try:
            host, port = parse_address(self.address)
        except ValueError as err:
            self.fail(str(err))
            return
        self.connect(lambda client: client.open(host, port))

    def connect(self, opener):
        client = WorldClient()
        try:
            opener(client)
        except JoinError as err:
            client.close()
            self.fail(str(err))
            return
        self.client = client
        self.mode, self.row, self.error = "login", USER_ROW, None
        pygame.key.start_text_input()
        sfx.play("confirm")

    def login(self, register):
        try:
            data = self.client.authenticate(self.user, self.password, register=register)
        except JoinError as err:
            if not self.client.connected:          # a conexão caiu: volta para o começo
                self.client = None
                self.mode = "menu"
            self.fail(str(err))
            return
        config.online["user"] = self.user
        config.save()
        pygame.key.stop_text_input()
        self.game.net = self.client
        character_module.remote_save = self.client.save_character
        character = Character.from_dict(data) if data else None
        if character is not None:
            self.enter_world(character)
        else:
            self.new_character()

    def new_character(self):
        """Conta nova: importa o personagem salvo neste PC (se houver) ou cria um."""
        local = Character.load() if Character.exists() else None
        if local is None:
            self.create_character()
            return
        question = f"Importar o personagem salvo neste PC ({local.name}, Nv {local.level}, {local.bets} BETS)?"
        self.prompt.ask(question, lambda yes: self.enter_world(local) if yes else self.create_character())

    def create_character(self):
        from game.scenes.create import CreateScene
        self.game.transition_to(lambda: CreateScene(self.game, on_created=self.enter_world))

    def enter_world(self, character):
        """Salva no servidor, entra no mundo e vai para a vila."""
        from game.data.world import HOME_SPOT, START_MAP
        from game.scenes.lobby import LobbyScene
        client = self.game.net
        self.game.character = character
        character.save()
        try:
            client.enter({"name": character.name.upper(), "look": asdict(character.appearance), "map": START_MAP,
                          "x": HOME_SPOT[0], "y": HOME_SPOT[1], "facing": "down"})
        except JoinError as err:
            self.game.leave_online()
            self.mode, self.client = "menu", None
            self.fail(str(err))
            return
        sfx.play("save")
        self.game.lobby = LobbyScene(self.game)
        self.game.transition_to(lambda: self.game.lobby)

    def fail(self, text):
        sfx.play("error")
        self.error = text

    def back_to_menu(self):
        pygame.key.stop_text_input()
        if self.client is not None:
            self.client.close()
            self.client = None
        self.mode, self.error = "menu", None

    # ------------------------------------------------------------ entrada
    def handle(self, event):
        if self.prompt.handle(event):
            return
        if self.mode == "address":
            self.handle_address(event)
        elif self.mode == "login":
            self.handle_login(event)
        elif event.type == pygame.KEYDOWN:
            self.handle_menu(event)

    def handle_menu(self, event):
        choice = self.menu.handle(event)
        if choice is None:
            return
        self.error = None
        option = OPTIONS[choice] if choice >= 0 else "VOLTAR"
        if option == "HOSPEDAR":
            self.host()
        elif option == "ENTRAR":
            self.mode = "address"
            pygame.key.start_text_input()
        else:
            from game.scenes.title import TitleScene
            self.game.transition_to(lambda: TitleScene(self.game))

    def handle_address(self, event):
        """Digitação do endereço (as letras chegam pelo TEXTINPUT, como o nome na criação)."""
        if event.type == pygame.TEXTINPUT:
            self.address = type_into(self.address, event.text.lower(), ADDRESS_CHARS, MAX_ADDRESS)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.address = self.address[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.error = None
                self.join()
            elif event.key == pygame.K_ESCAPE:
                self.back_to_menu()

    def handle_login(self, event):
        """Usuário e senha: setas cima/baixo trocam de linha; ENTER confirma; ESC volta."""
        if event.type == pygame.TEXTINPUT:
            self.type_login(event.text)
            return
        if event.type != pygame.KEYDOWN:
            return
        typing = self.row in (USER_ROW, PASSWORD_ROW)
        if event.key == pygame.K_ESCAPE:
            self.back_to_menu()
        elif event.key == pygame.K_BACKSPACE and typing:
            self.type_login(None)
        elif event.key == pygame.K_UP or (not typing and event.key in UP_KEYS):
            self.row = (self.row - 1) % len(LOGIN_ROWS)
            sfx.play("cursor")
        elif event.key == pygame.K_DOWN or (not typing and event.key in DOWN_KEYS):
            self.row = (self.row + 1) % len(LOGIN_ROWS)
            sfx.play("cursor")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) or (not typing and event.key in CONFIRM_KEYS):
            if typing:
                self.row += 1
            else:
                self.error = None
                self.login(register=self.row == REGISTER_ROW)
        elif not typing and event.key in CANCEL_KEYS:
            self.back_to_menu()

    def type_login(self, typed):
        """Escreve no campo atual (typed=None apaga o último caractere)."""
        if self.row == USER_ROW:
            self.user = self.user[:-1] if typed is None else type_into(self.user, typed.lower(), USER_CHARS, MAX_USER)
        elif self.row == PASSWORD_ROW:
            self.password = (self.password[:-1] if typed is None
                             else type_into(self.password, typed, None, MAX_PASSWORD))

    def update(self, dt):
        self.time += dt
        self.prompt.update(dt)

    # ------------------------------------------------------------ desenho
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_outlined(surf, "JOGAR", (GAME_W // 2, 14), (248, 248, 248), (24, 32, 72), size=24, align="center")
        if self.mode == "login":
            self.draw_login(surf)
        elif self.mode == "address":
            self.draw_address(surf)
        else:
            draw_text(surf, "vocês se veem andando na vila e no bosque, e cada um tem a sua conta",
                      (GAME_W // 2, 48), size=12, color=(220, 228, 248), shadow=None, align="center")
            draw_box(surf, (GAME_W // 2 - 60, 82, 120, 62))
            self.menu.draw(surf)
            self.draw_message(surf, HELP[OPTIONS[self.menu.index]])
        self.prompt.draw(surf)

    def draw_address(self, surf):
        box = pygame.Rect(GAME_W // 2 - 140, 70, 280, 70)
        draw_box(surf, box)
        draw_text(surf, "Endereço de quem hospeda:", (box.x + 14, box.y + 10))
        self.draw_field(surf, pygame.Rect(box.x + 14, box.y + 30, box.w - 28, 20), self.address, True)
        draw_text(surf, "ENTER conecta   ESC volta", (box.centerx, box.bottom + 6), size=12,
                  color=(220, 228, 248), shadow=None, align="center")
        self.draw_message(surf, f"Ex.: 192.168.0.5 (porta padrão {PORT}).")

    def draw_login(self, surf):
        if self.client and self.client.hosting:               # quem hospeda vê o endereço para passar
            addresses = "   ".join(local_addresses()[:3])
            draw_text(surf, f"Mundo aberto! Endereço: {addresses}", (GAME_W // 2, 46), size=12,
                      color=(255, 240, 160), shadow=(16, 16, 32), align="center")
        box = pygame.Rect(GAME_W // 2 - 130, 62, 260, 112)
        draw_box(surf, box)
        values = [self.user, "*" * len(self.password)]
        for i, label in enumerate(LOGIN_ROWS):
            y = box.y + 10 + i * 24
            if i == self.row:
                draw_cursor(surf, box.x + 10, y + 4)
            if i < 2:
                draw_text(surf, label, (box.x + 20, y + 2))
                self.draw_field(surf, pygame.Rect(box.x + 96, y, box.w - 110, 18), values[i], i == self.row)
            else:
                draw_text(surf, label, (box.x + 20, y + 2), color=(208, 64, 56) if i == self.row else (72, 72, 80))
        self.draw_message(surf, "Conta nova? Escolha usuário e senha e vá em CRIAR CONTA. ESC volta.")

    def draw_field(self, surf, rect, text, active):
        pygame.draw.rect(surf, (232, 236, 248) if active else (214, 218, 228), rect, border_radius=3)
        cursor = "_" if active and int(self.time * 3) % 2 == 0 else ""
        draw_text(surf, text + cursor, (rect.x + 6, rect.y + 3), shadow=None)

    def draw_message(self, surf, text):
        """Rodapé: o erro (em vermelho) ou a dica da tela."""
        rect = pygame.Rect(8, GAME_H - 58, GAME_W - 16, 50)
        draw_box(surf, rect)
        lines = wrap(self.error if self.error else f"{text} {TIP}", rect.w - 24, 12)
        for i, line in enumerate(lines[:3]):
            draw_text(surf, line, (rect.x + 12, rect.y + 8 + i * 12), size=12, shadow=None,
                      color=(208, 64, 56) if self.error else (72, 72, 80))


def type_into(text, typed, allowed, limit):
    """Acrescenta o que foi digitado, só com os caracteres permitidos (None = qualquer um) e até o limite."""
    for ch in typed:
        if (allowed is None or ch in allowed) and len(text) < limit:
            text += ch
    return text

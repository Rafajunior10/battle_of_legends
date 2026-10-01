"""Tela ONLINE: hospedar um mundo compartilhado ou entrar no mundo de um amigo.

Hospedar: este computador abre o servidor (game/net/server.py) e mostra os endereços para o amigo digitar.
Entrar: digita o endereço de quem hospeda. Pela internet, os dois precisam estar numa rede virtual
(Radmin VPN ou ZeroTier); na mesma casa, basta o endereço da rede local.
Cada jogador usa o próprio save: BETS, cartas e decks continuam sendo de cada um.
"""
from dataclasses import asdict

import pygame

from game.data.character import Character
from game.engine import config, sfx
from game.engine.settings import CANCEL_KEYS, CONFIRM_KEYS, GAME_H, GAME_W
from game.engine.ui import Menu, draw_box, draw_outlined, draw_text, vertical_gradient, wrap
from game.net.client import JoinError, WorldClient
from game.net.protocol import PORT, local_addresses, parse_address
from game.scenes.base import Scene

OPTIONS = ["HOSPEDAR", "ENTRAR", "VOLTAR"]
MAX_ADDRESS = 21
ADDRESS_CHARS = set("0123456789.:abcdefghijklmnopqrstuvwxyz-")
HELP = {
    "HOSPEDAR": "Abre o mundo neste computador. Seu amigo entra digitando um dos seus endereços.",
    "ENTRAR": "Entra no mundo de um amigo. Digite o endereço que aparece na tela dele.",
    "VOLTAR": "Volta para a tela de título.",
}
TIP = "Pela internet, os dois precisam estar na mesma rede virtual (Radmin VPN ou ZeroTier)."


class OnlineScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = Menu(OPTIONS, GAME_W // 2 - 50, 92, width=100, line_h=16)
        self.mode = "menu"                     # menu | address | hosted
        self.address = config.online["address"]
        self.error = None
        self.client = None
        self.players = []
        self.time = 0.0
        self.bg = vertical_gradient((GAME_W, GAME_H), (24, 32, 72), (72, 104, 168))

    def on_enter(self):
        sfx.music("lobby")

    # ------------------------------------------------------------ conexão
    def hello(self, character) -> dict:
        """Quem eu sou e onde vou aparecer (na porta de casa, como ao continuar o jogo)."""
        from game.data.world import HOME_SPOT, START_MAP
        return {"name": character.name.upper(), "look": asdict(character.appearance), "map": START_MAP,
                "x": HOME_SPOT[0], "y": HOME_SPOT[1], "facing": "down"}

    def start(self, join):
        """Carrega o save e tenta conectar; se der errado, mostra o motivo."""
        character = Character.load()
        if character is None:
            self.fail("Não achei o seu save. Crie um personagem em NOVO JOGO primeiro.")
            return
        client = WorldClient()
        try:
            self.players = join(client, self.hello(character))
        except (JoinError, ValueError) as err:
            client.close()
            self.fail(str(err))
            return
        self.game.character = character
        self.client = client
        sfx.play("save")

    def host(self):
        self.start(lambda client, hello: client.host(hello, PORT))
        if self.client:
            self.mode = "hosted"

    def join(self):
        config.online["address"] = self.address
        config.save()
        try:
            host, port = parse_address(self.address)
        except ValueError as err:
            self.fail(str(err))
            return
        self.start(lambda client, hello: client.connect(host, port, hello))
        if self.client:
            self.enter_world()

    def enter_world(self):
        from game.scenes.lobby import LobbyScene
        pygame.key.stop_text_input()
        self.game.net = self.client
        self.client.initial_players = self.players
        self.game.lobby = LobbyScene(self.game)
        self.game.transition_to(lambda: self.game.lobby)

    def fail(self, text):
        sfx.play("error")
        self.error = text

    # ------------------------------------------------------------ entrada
    def handle(self, event):
        if self.mode == "address":
            self.handle_address(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if self.mode == "hosted":
            if event.key in CONFIRM_KEYS:
                self.enter_world()
            elif event.key in CANCEL_KEYS:          # desistiu de hospedar: fecha o servidor
                self.client.close()
                self.client = None
                self.mode = "menu"
            return
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
            for ch in event.text.lower():
                if ch in ADDRESS_CHARS and len(self.address) < MAX_ADDRESS:
                    self.address += ch
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_BACKSPACE:
            self.address = self.address[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.error = None
            self.join()
        elif event.key == pygame.K_ESCAPE:
            pygame.key.stop_text_input()
            self.mode = "menu"

    def update(self, dt):
        self.time += dt

    # ------------------------------------------------------------ desenho
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_outlined(surf, "JOGAR ONLINE", (GAME_W // 2, 14), (248, 248, 248), (24, 32, 72), size=24,
                      align="center")
        draw_text(surf, "mundo compartilhado: vocês se veem andando na vila e no bosque", (GAME_W // 2, 48),
                  size=12, color=(220, 228, 248), shadow=None, align="center")
        if self.mode == "hosted":
            self.draw_hosted(surf)
        elif self.mode == "address":
            self.draw_address(surf)
        else:
            draw_box(surf, (GAME_W // 2 - 60, 82, 120, 62))
            self.menu.draw(surf)
            self.draw_message(surf, HELP[OPTIONS[self.menu.index]])

    def draw_address(self, surf):
        box = pygame.Rect(GAME_W // 2 - 140, 82, 280, 70)
        draw_box(surf, box)
        draw_text(surf, "Endereço de quem hospeda:", (box.x + 14, box.y + 10))
        cursor = "_" if int(self.time * 3) % 2 == 0 else " "
        field = pygame.Rect(box.x + 14, box.y + 30, box.w - 28, 20)
        pygame.draw.rect(surf, (232, 236, 248), field, border_radius=3)
        draw_text(surf, self.address + cursor, (field.x + 6, field.y + 4), shadow=None)
        draw_text(surf, "ENTER conecta   ESC volta", (box.centerx, box.bottom + 6), size=12,
                  color=(220, 228, 248), shadow=None, align="center")
        self.draw_message(surf, f"Ex.: 26.10.20.30 ou 192.168.0.5 (porta padrão {PORT}).")

    def draw_hosted(self, surf):
        box = pygame.Rect(GAME_W // 2 - 150, 74, 300, 106)
        draw_box(surf, box)
        draw_text(surf, "Mundo aberto! Passe um destes endereços:", (box.x + 14, box.y + 10))
        for i, address in enumerate(local_addresses()[:4]):
            draw_text(surf, address, (box.x + 24, box.y + 30 + i * 14), color=(40, 120, 200))
        draw_text(surf, "A: entrar no mundo   B: fechar o mundo", (box.centerx, box.bottom - 16), size=12,
                  align="center")
        self.draw_message(surf, "Radmin VPN começa com 26. e ZeroTier costuma começar com 10. ou 172.")

    def draw_message(self, surf, text):
        """Rodapé: o erro (em vermelho) ou a dica da opção atual."""
        rect = pygame.Rect(8, GAME_H - 58, GAME_W - 16, 50)
        draw_box(surf, rect)
        lines = wrap(self.error, rect.w - 24, 12) if self.error else [*wrap(text, rect.w - 24, 12), TIP]
        for i, line in enumerate(lines[:3]):
            draw_text(surf, line, (rect.x + 12, rect.y + 8 + i * 12), size=12, shadow=None,
                      color=(208, 64, 56) if self.error else (72, 72, 80))

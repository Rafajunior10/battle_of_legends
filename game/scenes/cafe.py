"""Lanchonete da Vila Carta: o que acontece lá dentro. Mixin do LobbyScene (como o BattleHUD da batalha).

- Atendente LU: vende lanches (regras em core/food.py). O lanche dá PV a mais na próxima batalha.
- Assentos (cadeiras e puffs): A de frente para um assento senta; qualquer direção levanta.
- TV: 3 canais que trocam sozinhos; A de frente para ela (ou sentado num puff olhando para ela) mostra o programa.
- MESA DE TROCA: troca uma carta sobrando com outro jogador online. Pela rede (o servidor só repassa):
      swap_ask   A chama B para a mesa             swap_cards  B responde com as cartas sobrando dele (ou null)
      swap_offer A escolhe: dou X e quero Y        swap_answer B aceita (os dois trocam) ou recusa
"""
from game.core import economy, food
from game.core.economy import ShopError
from game.data.cards import CARDS
from game.data.food import MENU
from game.data.props import OBJECTS
from game.data.world import CAFE, CAFE_SPOT, DIR_VECTORS, GABI_TIPS, TV_SHOWS
from game.engine import sfx
from game.engine.settings import TILE
from game.graphics import interiors

TV_SWITCH = 6.0                     # segundos em cada canal
SEAT_FRONT = {"puff": 7, "chair": 10}   # linhas de baixo do assento desenhadas na frente de quem senta
LOOK_AHEAD = 6                      # sentado, A "enxerga" até este tanto de tiles à frente (a TV do puff)
MAX_SWAP_CARDS = 200


class CafeMixin:
    def setup_cafe(self):
        """Chamado por load_map: prepara balcões, assentos e a TV do mapa atual."""
        self.player.sitting = False
        self.seated_from = None
        self.counters = self.map_def.counter_tiles()
        self.seat_fronts = {}
        self.tv_spot = None
        for obj in self.map_def.objects:
            kind = obj.name.split("_")[0]
            if obj.action and obj.action.startswith("seat:") and kind in SEAT_FRONT:
                img = self.object_image(obj.name)
                rows = SEAT_FRONT[kind]
                front = img.subsurface((0, img.get_height() - rows, img.get_width(), rows))
                tile = (obj.x, obj.y + img.get_height() // TILE - 1)
                self.seat_fronts[tile] = (front, obj.x * TILE, (tile[1] + 1) * TILE - rows)
            elif obj.name == "tv":
                self.tv_spot = (obj.x * TILE + interiors.TV_SCREEN.x, obj.y * TILE + interiors.TV_SCREEN.y)
                self.tv_foot = (obj.y + OBJECTS[obj.name].h) * TILE       # mesma profundidade da TV
        if self.tv_spot and not hasattr(self, "tv_frames"):
            self.tv_frames = interiors.tv_channels()
            self.tv_channel = 0

    def enter_cafe(self):
        sfx.play("confirm")
        self.chain = False

        def arrive():
            self.load_map(CAFE.id, CAFE_SPOT, "up")
            self.steps_since_battle = 0
            return self
        self.game.transition_to(arrive)

    # ------------------------------------------------------------ interação
    def cafe_interact(self, target):
        """A de frente para algo da lanchonete. Devolve True se tratou."""
        dx, dy = DIR_VECTORS[self.player.facing]
        probe = target
        while probe in self.counters:                         # fala com quem está do outro lado do balcão
            probe = (probe[0] + dx, probe[1] + dy)
        npc = next((n for n in self.npcs if (n.tx, n.ty) == probe), None) if probe != target else None
        if npc:
            npc.on_talk()
            return True
        uses = self.map_def.uses
        if self.player.sitting:                               # sentado: olha mais longe (a TV vista do puff)
            ahead = [(self.player.tx + dx * i + dy * side, self.player.ty + dy * i + dx * side)
                     for i in range(1, LOOK_AHEAD + 1) for side in (0, -1, 1)]
            target = next((tile for tile in ahead if tile in uses), target)
        if target in uses:
            {"tv": self.watch_tv, "swap": self.open_swap}[uses[target]]()
            return True
        if target in self.map_def.seats and not self.player.sitting:
            self.sit(target)
            return True
        return False

    def sit(self, tile):
        taken = any((a.tx, a.ty) == tile for a in (*self.npcs, *self.remotes_here()))
        if taken:
            self.say("Esse lugar já está ocupado.")
            return
        self.seated_from = (self.player.tx, self.player.ty)
        self.player.place(*tile)
        self.player.sitting = True
        self.player.facing = self.map_def.seats[tile]
        sfx.play("cursor")
        self.send_position()

    def stand_up(self, direction):
        self.player.place(*self.seated_from)
        self.player.sitting = False
        self.seated_from = None
        self.player.facing = direction
        self.send_position()

    # ------------------------------------------------------------ atendente, cliente e TV
    def talk_lu(self):
        face = self.face_of("lu")
        options = [f"{item.name}  {item.price} BETS" for item in MENU]

        def chosen(index):
            if 0 <= index < len(MENU):
                self.buy_food(MENU[index].id)
            else:
                self.say("LU: Tudo bem! Se der fome, é só chamar.", face=face)
        self.prompt.choose("LU: Oi! Bem-vindo à Lanchonete! O que vai querer hoje?", [*options, "NADA"], chosen,
                           face=face)

    def buy_food(self, food_id):
        face = self.face_of("lu")
        try:
            item = food.buy(self.ch, food_id)
        except ShopError as err:
            sfx.play("error")
            self.say(f"LU: {err}", face=face)
            return
        self.ch.save()
        sfx.play("coin")
        self.my_emote, self.my_emote_t = item.bite, 3.0
        if self.net:
            self.net.send({"t": "emote", "text": item.bite})
        self.say([f"LU: Aqui está: {item.name}. Bom apetite!",
                  f"Delícia! Na próxima batalha você começa com +{item.hp} PV."], face=face)

    def talk_gabi(self):
        self.say(GABI_TIPS[self.gabi_tip % len(GABI_TIPS)], face=self.face_of("gabi"))
        self.gabi_tip += 1

    def watch_tv(self):
        sfx.play("cursor")
        self.tv_channel = (self.tv_channel + 1) % len(self.tv_frames)
        self.tv_time = 0.0
        self.say(TV_SHOWS[self.tv_channel])

    def update_tv(self, dt):
        if not self.tv_spot:
            return
        self.tv_time = getattr(self, "tv_time", 0.0) + dt
        if self.tv_time >= TV_SWITCH:
            self.tv_time = 0.0
            self.tv_channel = (self.tv_channel + 1) % len(self.tv_frames)

    def draw_tv(self, surf, cam):
        """Tela da TV: o canal atual, uma linha de varredura descendo e a bolinha do AO VIVO piscando."""
        x, y = self.tv_spot[0] - cam[0], self.tv_spot[1] - cam[1]
        frame = self.tv_frames[self.tv_channel]
        surf.blit(frame, (x, y))
        line = y + int(self.time * 18) % frame.get_height()
        surf.fill((150, 170, 200), (x, line, frame.get_width(), 1))
        if self.tv_channel == 0 and int(self.time * 2) % 2:
            surf.fill((250, 60, 60), (x + 33, y + 2, 3, 3))

    def draw_seat_front(self, surf, actor, cam):
        """Quem está sentado fica "dentro" do assento: a frente dele é desenhada por cima."""
        front = self.seat_fronts.get((actor.tx, actor.ty))
        if front:
            img, x, y = front
            surf.blit(img, (x - cam[0], y - cam[1]))

    # ------------------------------------------------------------ mesa de troca (online)
    def open_swap(self):
        others = [r for r in self.remotes_here() if not r.battle] if self.net else []
        if not others:
            self.say(["MESA DE TROCA: aqui dois duelistas trocam cartas que estão sobrando.",
                      "Chame um amigo online para a lanchonete!"])
            return
        if not self.ch.spare_cards():
            self.say("Você não tem cartas sobrando para trocar (todas estão nos seus decks).")
            return
        if len(others) == 1:
            self.prompt.ask(f"Chamar {others[0].name} para trocar cartas?",
                            lambda yes: self.ask_swap(others[0]) if yes else None)
            return
        self.prompt.choose("Trocar cartas com quem?", [r.name for r in others] + ["NINGUÉM"],
                           lambda i: self.ask_swap(others[i]) if 0 <= i < len(others) else None)

    def ask_swap(self, remote):
        self.net.send({"t": "swap_ask", "to": remote.id})
        self.banner(f"Chamando {remote.name} para a mesa de troca...")

    def on_swap_message(self, message):
        kind = message["t"]
        if kind == "swap_ask":
            self.swap_invite = message                        # pergunta quando a tela estiver livre
        elif kind == "swap_cards":
            self.swap_cards_arrived(message)
        elif kind == "swap_offer":
            self.swap_offer_arrived(message)
        elif kind == "swap_answer":
            self.swap_answer_arrived(message)

    def ask_swap_invite(self, message):
        self.swap_invite = None
        sender, name = message.get("from"), message.get("name", "???")

        def answer(yes):
            cards = self.ch.spare_cards() if yes else None
            self.net.send({"t": "swap_cards", "to": sender, "cards": cards})
            if yes:
                self.banner(f"Esperando {name} escolher a troca...")
        sfx.play("cursor")
        self.prompt.ask(f"{name} quer trocar cartas com você na mesa de troca. Aceitar?", answer)

    def swap_cards_arrived(self, message):
        name, cards = message.get("name", "???"), message.get("cards")
        if cards is None:
            self.say(f"{name} não quis trocar agora.")
            return
        theirs = [c for c in cards if c in CARDS][:MAX_SWAP_CARDS] if isinstance(cards, list) else []
        if not theirs:
            self.say(f"{name} não tem cartas sobrando para trocar.")
            return
        from game.scenes.trade_table import TradeTableScene
        self.game.transition_to(lambda: TradeTableScene(self.game, self, message.get("from"), name, theirs))

    def swap_offer_arrived(self, message):
        sender, name = message.get("from"), message.get("name", "???")
        give, want = message.get("give"), message.get("want")
        if give not in CARDS or want not in CARDS:
            self.say(f"{name} desistiu da troca.")
            return

        def answer(yes):
            reply = {"t": "swap_answer", "to": sender, "give": give, "want": want, "yes": False}
            if not yes:
                self.net.send(dict(reply, text=f"{self.ch.name.upper()} recusou a troca."))
                return
            try:
                economy.swap_card(self.ch, want, give)       # eu dou o que ele quer e recebo o que ele dá
            except ShopError as err:
                sfx.play("error")
                self.net.send(dict(reply, text=f"{self.ch.name.upper()} não pôde trocar: {err}"))
                self.say(str(err))
                return
            self.ch.save()
            sfx.play("coin")
            self.net.send(dict(reply, yes=True))
            self.say(f"Troca feita! Você deu {CARDS[want].name.upper()} e recebeu {CARDS[give].name.upper()}.")
        self.prompt.ask(f"{name} oferece {CARDS[give].name.upper()} pela sua {CARDS[want].name.upper()}. "
                        "Aceitar?", answer)

    def swap_answer_arrived(self, message):
        give, want = message.get("give"), message.get("want")
        if not message.get("yes") or give not in CARDS or want not in CARDS:
            self.say(message.get("text") or "A troca não rolou.")
            return
        try:
            economy.swap_card(self.ch, give, want)
        except ShopError as err:
            self.say(f"A troca deu errado do seu lado: {err}")
            return
        self.ch.save()
        sfx.play("coin")
        self.say(f"Troca feita! Você deu {CARDS[give].name.upper()} e recebeu {CARDS[want].name.upper()}.")

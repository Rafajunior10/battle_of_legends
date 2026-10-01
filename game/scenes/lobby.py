"""Mundo andável: Vila Carta, Bosque Sussurro e o que vier. Você anda, conversa, desafia treinadores,
entra na loja e no coliseu e passa de um mapa a outro pelas passagens.

Os dados dos mapas e das falas ficam em game/data/world.py; aqui só o comportamento.
"""
import random

import pygame

from game.core import economy
from game.core.duel import duel_spec, fighter, look_from
from game.core.economy import ShopError
from game.core.tournament import ROUND_TITLES, ROUNDS, TOURNAMENT_PRIZE, XP_MULTIPLIER, Tournament
from game.data.cards import CARDS
from game.data.opponents import TRAINERS, random_wild, trainer_spec
from game.data.props import OBJECTS
from game.data.world import (
    BETO_TIPS,
    COLISEUM_DOOR,
    DIR_VECTORS,
    HOME_SPOT,
    MAPS,
    OPPOSITE,
    ROSA_TIPS,
    SOLID_TILES,
    START_MAP,
    TALL_GRASS,
    TRAINER_TALK,
    WATER,
)
from game.engine import sfx
from game.engine.config import action_label
from game.engine.settings import (
    CANCEL_KEYS,
    CONFIRM_KEYS,
    GAME_H,
    GAME_W,
    INTERACT_KEYS,
    KEY_DIRS,
    MENU_KEYS,
    PROFILE_KEYS,
    RUN_KEYS,
    TILE,
)
from game.engine.ui import Menu, Prompt, draw_box, draw_outlined, draw_text, text_width
from game.graphics import buildings, sprites, tilemap
from game.graphics import pixelart as art
from game.net.protocol import EMOTES
from game.scenes.actors import FOOT_Y, NPC, RUN_TIME, WALK_TIME, Actor, RemotePlayer
from game.scenes.base import Scene
from game.scenes.common import draw_bets
from game.scenes.profile import draw_profile

ENCOUNTER_RATE = 0.12
SAFE_STEPS = 3             # passos sem encontro depois de uma batalha
TURN_DELAY = 0.09          # toque rápido numa direção só vira o personagem
BUMP_COOLDOWN = 0.35
BANNER_TIME = 3.0
MENU_OPTIONS = ["DECK", "FICHA", "SALVAR", "OPÇÕES", "FECHAR", "SAIR"]
CREAM, WHITE_WALL, SAND = (244, 236, 220), (248, 244, 236), (232, 220, 196)
NOTICE_TIME = 3.0                              # segundos do aviso "FULANO entrou no mundo!"
# Construções desenhadas por código (buildings.py): recebem o texto da placa

BUILDERS = {
    "house_modern_red": lambda label: buildings.modern_house((196, 72, 60), CREAM, label),
    "house_modern_blue": lambda label: buildings.modern_house((70, 110, 170), CREAM, label),
    "house_modern_green": lambda label: buildings.modern_house((76, 140, 96), WHITE_WALL, label),
    "house_modern_gray": lambda label: buildings.modern_house((90, 90, 104), SAND, label),
    "card_shop": lambda label: buildings.card_shop(label or "LOJA DE CARTAS"),
    "arena": lambda label: buildings.arena(label or "ARENA"),
    "construction": lambda label: buildings.construction(label or "NOVA CONSTRUÇÃO"),
    "lamp": lambda label: buildings.street_lamp(),
    "coliseum": lambda label: art.coliseum(),
}
MISSING_PACK = ("O pacote de arte Ninja Adventure não foi encontrado em assets/ninja_adventure/. "
                "Ele vem junto com o projeto: baixe o repositório de novo ou veja assets/README.txt.")


class LobbyScene(Scene):
    def __init__(self, game, first_time=False, map_id=START_MAP, spot=HOME_SPOT, facing="down"):
        super().__init__(game)
        self.ch = game.character
        self.player = Actor(*spot, sprites.player_frames(self.ch), facing)
        self.prompt = Prompt()
        self.menu = None
        self.showing_profile = False
        self.chain = False         # continuando a andar sem parar
        self.turn_delay = 0.0
        self.bump_cd = 0.0
        self.steps_since_battle = 0
        self.time = 0.0
        self.banner_t = 0.0
        self.tip = 0
        self.rosa_tip = 0
        self.trade = None          # oferta atual da Nina (economy.TradeOffer)
        self.tournament = None     # torneio do coliseu em andamento
        self.first_time = first_time
        self.net = game.net                # conexão com o mundo compartilhado (None = jogando sozinho)
        self.remotes = {}                  # id -> RemotePlayer (os outros jogadores)
        self.my_emote, self.my_emote_t = None, 0.0
        self.notice, self.notice_t = "", 0.0      # aviso no topo: "FULANO entrou no mundo!"
        self.duel_invite = None            # desafio de duelo recebido, esperando a tela ficar livre
        self.load_map(map_id, spot, facing)
        for player in getattr(self.net, "initial_players", []):
            self.add_remote(player)

    # ------------------------------------------------------------ troca de mapa
    def load_map(self, map_id, spot, facing):
        """Monta tudo do mapa: tiles, prédios, NPCs, portas. O chão é pré-desenhado uma vez só."""
        if not tilemap.available():
            raise FileNotFoundError(MISSING_PACK)
        self.map_def = MAPS[map_id]
        self.map = self.map_def.build()
        self.map_h, self.map_w = len(self.map), len(self.map[0])
        self.solid = self.map_def.solid_objects()
        self.figures = self.build_figures()
        self.npcs = []
        for tid, sp in self.map_def.trainers.items():
            t = TRAINERS[tid]
            self.npcs.append(NPC(tid, sp, sprites.character_frames(t["look"]), lambda tid=tid: self.talk_trainer(tid),
                                 t["look"]))
        helper_talk = {"beto": self.talk_beto, "nina": self.talk_nina, "rosa": self.talk_rosa}
        for hid, helper in self.map_def.helpers.items():
            self.npcs.append(NPC(hid, helper.spot, sprites.character_frames(helper.look), helper_talk[hid],
                                 helper.look))
        self.doors = {pos: self.door_action(kind) for pos, kind in self.map_def.doors.items()}
        self.ground = tilemap.render_ground(self.map)
        self.player.place(*spot)
        self.player.facing = facing
        self.trade = None
        self.send_position()

    def door_action(self, kind):
        if kind.startswith("locked:"):
            text = kind.split(":", 1)[1]
            return lambda: self.say(text)
        return {"home": self.enter_home, "shop": self.enter_shop, "coliseum": self.enter_coliseum}[kind]

    def travel(self, warp):
        """Passagem para outro mapa, com transição de tela."""
        self.chain = False
        sfx.play("confirm")

        def arrive():
            self.load_map(warp.to_map, (warp.to_x, warp.to_y), warp.facing)
            self.steps_since_battle = 0
            return self
        self.game.transition_to(arrive)

    def go_home(self):
        if self.map_def.id != START_MAP:
            self.load_map(START_MAP, HOME_SPOT, "down")
        else:
            self.player.place(*HOME_SPOT)
            self.player.facing = "down"

    def on_enter(self):
        sfx.music("lobby")
        if self.net:
            self.net.send({"t": "status", "battle": False})
        self.banner_t = 0.0
        self.chain = False
        if self.first_time:
            self.first_time = False
            self.say([
                f"Bem-vindo à VILA CARTA, {self.ch.name}!",
                "Aqui todo mundo resolve as coisas com duelos de cartas.",
                "Fale com o TICO, aqui perto, ou com o RAFA, na frente da Arena, para duelar!",
                "Vencer duelos dá BETS. Gaste na LOJA, a casa verde no alto da vila.",
                f"Dica: {action_label('a')} interage, ENTER abre o menu e {action_label('run')} faz correr.",
                f"A tecla {action_label('profile')} abre a sua ficha de jogador.",
            ])

    def say(self, text, then=None, face=None):
        self.prompt.say(text, then, face)

    def face_of(self, npc_id):
        """Rosto (do pacote de arte) de um treinador ou ajudante, ou None."""
        if npc_id in TRAINERS:
            return sprites.face(TRAINERS[npc_id]["look"])
        helper = next((m.helpers[npc_id] for m in MAPS.values() if npc_id in m.helpers), None)
        return sprites.face(helper.look) if helper else None

    # ------------------------------------------------------------ mapa
    def tile_at(self, x, y):
        if 0 <= x < self.map_w and 0 <= y < self.map_h:
            return self.map[y][x]
        return "T"

    def walkable(self, x, y):
        if self.tile_at(x, y) in SOLID_TILES or (x, y) in self.solid:
            return False
        return all((n.tx, n.ty) != (x, y) for n in self.npcs)

    def camera(self):
        cx = int(self.player.px + TILE // 2 - GAME_W // 2)
        cy = int(self.player.py + TILE // 2 - GAME_H // 2)
        return max(0, min(cx, self.map_w * TILE - GAME_W)), max(0, min(cy, self.map_h * TILE - GAME_H))

    # ------------------------------------------------------------ input
    def handle(self, event):
        if self.prompt.handle(event):
            return
        if self.menu:
            self.handle_menu(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if self.showing_profile:
            if event.key in CANCEL_KEYS or event.key in CONFIRM_KEYS or event.key in PROFILE_KEYS:
                sfx.play("cancel")
                self.showing_profile = False
        elif not self.player.moving:
            if event.key in MENU_KEYS:
                sfx.play("confirm")
                self.menu = Menu(MENU_OPTIONS, GAME_W - 88, 6, width=82)
            elif event.key in PROFILE_KEYS:      # atalho da ficha (I ou E, mudável em OPÇÕES)
                sfx.play("confirm")
                self.showing_profile = True
            elif event.key in INTERACT_KEYS:
                self.interact()

    def handle_menu(self, event):
        result = self.menu.handle(event)
        if result is None:
            return
        option = self.menu.options[result] if result >= 0 else "FECHAR"
        self.menu = None
        if option == "DECK":
            from game.scenes.deckedit import DeckEditScene
            self.game.transition_to(lambda: DeckEditScene(self.game, lambda: self))
        elif option == "FICHA":
            self.showing_profile = True
        elif option == "SALVAR":
            self.ch.save()
            sfx.play("save")
            self.say("Jogo salvo com sucesso!")
        elif option == "OPÇÕES":
            from game.scenes.options import OptionsScene
            self.game.transition_to(lambda: OptionsScene(self.game, lambda: self))
        elif option == "SAIR":                   # salva, sai do mundo online e volta para o título
            from game.scenes.title import TitleScene
            self.ch.save()
            self.game.leave_online()
            self.game.transition_to(lambda: TitleScene(self.game))

    def interact(self):
        dx, dy = DIR_VECTORS[self.player.facing]
        target = (self.player.tx + dx, self.player.ty + dy)
        remote = next((r for r in self.remotes_here() if (r.tx, r.ty) == target), None)
        if remote and self.net:
            self.talk_to_player(remote)
            return
        npc = next((n for n in self.npcs if (n.tx, n.ty) == target), None)
        if npc:
            npc.facing = OPPOSITE[self.player.facing]
            npc.timer = 4.0
            npc.on_talk()
        elif target in self.map_def.signs:
            self.say(self.map_def.signs[target].format(name=self.ch.name.upper()))
        elif target in self.doors:
            self.doors[target]()
        elif self.tile_at(*target) == WATER:
            self.say("A água do lago está calma e cristalina.")

    # ------------------------------------------------------------ conversas
    def talk_trainer(self, tid):
        trainer = TRAINERS[tid]
        talk = TRAINER_TALK[tid]
        face = self.face_of(tid)
        required = trainer.get("requires")
        if required and required not in self.ch.beaten:
            self.say(list(talk.locked), face=face)
            return
        name, level = trainer["name"], trainer["level"]
        gap = level - self.ch.level
        if gap >= 2:
            warning = f"{name} é nível {level}. Cuidado, é bem mais forte que você!"
        elif gap <= -2:
            warning = f"{name} é nível {level}. Vencer rende poucas BETS agora."
        else:
            warning = f"{name} é nível {level}."
        line = talk.rematch if tid in self.ch.beaten else talk.greet
        self.prompt.ask([warning, line], lambda yes: self.challenge(tid) if yes else self.say(talk.decline, face=face),
                        face=face)

    def talk_nina(self):
        face = self.face_of("nina")
        offer = self.trade
        if offer is None or self.ch.spare(offer.want) <= 0:
            offer = self.trade = economy.make_trade_offer(self.ch)
        if offer is None:
            self.say(["NINA: Eu troco cartas raras! Mas só aceito cartas que não estão em nenhum deck.",
                      "NINA: Você não tem nenhuma sobrando para trocar. Compre cartas na loja e volte!"],
                     face=face)
            return
        give, want = CARDS[offer.give].name.upper(), CARDS[offer.want].name.upper()
        if offer.bets > 0:
            deal = f"NINA: Troco minha {give} pela sua {want} + {offer.bets} BETS. Fechado?"
        elif offer.bets < 0:
            deal = f"NINA: Troco minha {give} pela sua {want}, e ainda te dou {-offer.bets} BETS. Fechado?"
        else:
            deal = f"NINA: Troco minha {give} pela sua {want}. Fechado?"
        self.prompt.ask(deal, self.answer_nina, face=face)

    def answer_nina(self, yes):
        face = self.face_of("nina")
        offer, self.trade = self.trade, None
        if not yes:
            self.say("NINA: Tudo bem! Da próxima vez eu trago outra oferta.", face=face)
            return
        try:
            economy.accept_trade(self.ch, offer)
        except ShopError as err:
            sfx.play("error")
            self.say(f"NINA: {err} Fica para a próxima!", face=face)
            return
        self.ch.save()
        sfx.play("coin")
        self.say([f"Você recebeu {CARDS[offer.give].name.upper()}!", "NINA: Negócio fechado! Use bem essa carta."],
                 face=face)

    def talk_beto(self):
        tip = BETO_TIPS[self.tip % len(BETO_TIPS)]
        self.tip += 1
        keys = {a: action_label(a) for a in ("a", "b", "start", "run")}
        self.say(f"BETO: {tip.format(**keys)}", face=self.face_of("beto"))

    def talk_rosa(self):
        self.say(ROSA_TIPS[self.rosa_tip % len(ROSA_TIPS)], face=self.face_of("rosa"))
        self.rosa_tip += 1

    # ------------------------------------------------------------ portas
    def enter_home(self):
        self.ch.save()
        sfx.play("save")
        self.say(["Você entrou em casa e descansou um pouco.", "Jogo salvo!"])

    def enter_shop(self):
        from game.scenes.shop import ShopScene
        sfx.play("confirm")
        self.game.transition_to(lambda: ShopScene(self.game, lambda: self))

    # ------------------------------------------------------------ coliseu
    def enter_coliseum(self):
        question = [f"COLISEU: {ROUNDS} rodadas eliminatórias contra duelistas do seu nível e acima.",
                    f"Todo duelo aqui vale XP x{XP_MULTIPLIER}, e o campeão leva {TOURNAMENT_PRIZE} BETS!",
                    "Entrar no torneio agora?"]
        self.prompt.ask(question, lambda yes: self.start_tournament() if yes
                        else self.say("Volte quando estiver pronto. O Coliseu estará aqui!"))

    def start_tournament(self):
        self.tournament = Tournament(self.ch.level)
        self.next_round()

    def next_round(self):
        self.game.start_battle(self.tournament.current(), self.after_tournament_battle)

    def after_tournament_battle(self, won, spec):
        """Chamada pela batalha no meio da transição. Devolve esta cena."""
        t = self.tournament
        t.record(won)
        self.steps_since_battle = 0
        self.player.place(COLISEUM_DOOR[0], COLISEUM_DOOR[1] + 1)
        self.player.facing = "down"
        if not won:
            self.tournament = None
            self.say([f"Você foi eliminado na {ROUND_TITLES[t.round].lower()}...",
                      "Tudo bem! O XP que você ganhou fica com você. Tente de novo!"])
        elif t.champion:
            self.tournament = None
            self.ch.bets += TOURNAMENT_PRIZE
            self.ch.coliseum_wins += 1
            self.ch.save()
            sfx.play("levelup")
            self.say(["O público vai à loucura! Você é o CAMPEÃO do Coliseu!",
                      f"Você ganhou o prêmio de {TOURNAMENT_PRIZE} BETS!"])
        else:
            self.prompt.ask([f"Você venceu! Próxima: {ROUND_TITLES[t.round]} (XP x{XP_MULTIPLIER}).",
                             "Seguir para a próxima rodada?"], self.continue_tournament)
        return self

    def continue_tournament(self, yes):
        if yes:
            self.next_round()
        else:
            self.tournament = None
            self.say("Você desistiu do torneio. O XP ganho fica com você!")

    # ------------------------------------------------------------ batalhas
    def challenge(self, trainer_id):
        self.game.start_battle(trainer_spec(trainer_id), self.after_battle)

    def after_battle(self, won, spec):
        """Chamada pela batalha no meio da transição. Devolve esta cena."""
        self.steps_since_battle = 0
        self.showing_profile = False
        self.trade = None
        if not won:
            self.go_home()
            self.say(["Você voltou correndo para casa...",
                      "Depois de descansar, você está pronto para outra!"])
        elif spec.get("first") and spec["id"] in TRAINER_TALK and TRAINER_TALK[spec["id"]].first_win:
            self.say(list(TRAINER_TALK[spec["id"]].first_win), face=self.face_of(spec["id"]))
        return self

    def on_step_done(self):
        warp = self.map_def.warp_at(self.player.tx, self.player.ty)
        if warp:
            self.travel(warp)
            return
        self.steps_since_battle += 1
        in_grass = self.tile_at(self.player.tx, self.player.ty) == TALL_GRASS
        if in_grass and self.steps_since_battle > SAFE_STEPS and random.random() < ENCOUNTER_RATE:
            self.chain = False
            level = self.ch.level + self.map_def.wild_bonus
            self.game.start_battle(random_wild(level, types=self.map_def.wild_types), self.after_battle)

    # ------------------------------------------------------------ update
    @property
    def paused(self):
        """Algo na tela está esperando o jogador: o mundo não se mexe."""
        return self.prompt.visible or self.menu or self.showing_profile or self.game.busy

    def update(self, dt):
        self.time += dt
        self.update_online(dt)
        self.banner_t += dt
        self.bump_cd = max(0.0, self.bump_cd - dt)
        self.prompt.update(dt)
        paused = self.paused
        if not paused:
            for npc in self.npcs:
                npc.idle(dt)
        if self.player.update(dt):
            self.on_step_done()
        if not paused and not self.player.moving:
            self.update_movement(dt)

    # ------------------------------------------------------------ mundo compartilhado (online)
    def send_position(self, running=False):
        """Avisa a rede: comecei um passo para (tx, ty), virei, ou cheguei num mapa."""
        if self.net:
            self.net.send({"t": "move", "map": self.map_def.id, "x": self.player.tx, "y": self.player.ty,
                           "facing": self.player.facing, "run": running})

    def add_remote(self, info):
        frames = sprites.character_frames(look_from(info.get("look")))
        remote = RemotePlayer(info["id"], info.get("name", "???"), frames,
                              info.get("map"), info.get("x", 0), info.get("y", 0), info.get("facing"))
        remote.battle = bool(info.get("battle"))
        self.remotes[remote.id] = remote

    def update_online(self, dt):
        """Lê o que chegou da rede e anima os outros jogadores (mesmo com um menu aberto)."""
        self.my_emote_t = max(0.0, self.my_emote_t - dt)
        self.notice_t = max(0.0, self.notice_t - dt)
        if self.net is None:
            return
        for message in self.net.poll():
            self.on_net_message(message)
            if self.net is None:
                return
        for remote in self.remotes.values():
            remote.tick(dt)
        if self.duel_invite and not self.paused:
            self.ask_challenge(self.duel_invite)

    def on_net_message(self, message):
        kind = message["t"]
        remote = self.remotes.get(message.get("id"))
        if kind == "join":
            self.add_remote(message["player"])
            self.banner(f"{message['player'].get('name', '???')} entrou no mundo!")
        elif kind == "leave" and remote:
            del self.remotes[remote.id]
            self.banner(f"{remote.name} saiu do mundo.")
        elif kind == "move" and remote:
            remote.queue_move(message.get("map"), message.get("x"), message.get("y"), message.get("facing"),
                              message.get("run"))
        elif kind == "emote" and remote:
            remote.say(message.get("text", ""))
        elif kind == "status" and remote:
            remote.battle = bool(message.get("battle"))
        elif kind in ("challenge", "challenge_denied", "duel_start"):
            self.on_duel_message(message)
        elif kind == "disconnected":
            self.remotes.clear()
            self.game.leave_online()
            self.net = None
            self.say("A conexão com o mundo online caiu. Você continua jogando sozinho.")

    def banner(self, text):
        """Aviso curto no topo da tela (quem entrou/saiu)."""
        self.notice, self.notice_t = text, NOTICE_TIME

    def talk_to_player(self, remote):
        """Interagir com outro jogador: desafiar para um duelo ou mandar uma fala rápida."""
        def chosen(index):
            if index == 0:
                self.send_challenge(remote)
            elif index == 1:
                self.prompt.choose(f"Dizer o que para {remote.name}?", [*EMOTES, "NADA"], self.send_emote)
        self.prompt.choose(f"O que fazer com {remote.name}?", ["DUELAR", "FALAR", "NADA"], chosen)

    def send_emote(self, index):
        """Fala rápida: aparece num balão em cima de você, para os dois."""
        if 0 <= index < len(EMOTES):
            self.my_emote, self.my_emote_t = EMOTES[index], 3.0
            self.net.send({"t": "emote", "text": EMOTES[index]})

    # ------------------------------------------------------------ duelo online (PvP)
    def send_challenge(self, remote):
        if remote.battle:
            self.say(f"{remote.name} está numa batalha agora. Tente daqui a pouco.")
            return
        self.net.send({"t": "challenge", "to": remote.id, "fighter": fighter(self.ch)})
        self.banner(f"Desafio enviado para {remote.name}! Esperando a resposta...")

    def on_duel_message(self, message):
        kind = message["t"]
        if kind == "challenge":
            self.duel_invite = message                   # pergunta quando a tela estiver livre
        elif kind == "challenge_denied":
            self.say(message.get("text", "O duelo não aconteceu."))
        elif kind == "duel_start":
            self.duel_invite = None
            self.prompt = Prompt()                       # fecha qualquer conversa aberta
            try:
                spec = duel_spec(message.get("foe") or {}, message.get("side", 0))
            except (ValueError, TypeError, AttributeError):
                self.net.send({"t": "duel", "action": {"forfeit": True}})   # ficha estragada: desiste
                self.net.send({"t": "duel_over"})
                self.say("Não deu para começar o duelo (o deck do outro jogador veio com problema).")
                return
            self.game.start_duel(spec, message.get("seed", 0), message.get("side", 0), self.after_duel)

    def ask_challenge(self, message):
        self.duel_invite = None
        challenger = message.get("from")

        def answer(yes):
            self.net.send({"t": "answer", "to": challenger, "yes": yes, "fighter": fighter(self.ch) if yes else None})
            if yes:
                self.banner("Duelo aceito! Preparando...")
        sfx.play("encounter")
        self.prompt.ask(f"{message.get('name', '???')} te desafiou para um DUELO! Aceitar?", answer)

    def after_duel(self, won, spec):
        """Chamada pelo duelo no meio da transição. Devolve esta cena (perder um duelo não manda para casa)."""
        self.steps_since_battle = 0
        self.showing_profile = False
        return self

    def remotes_here(self):
        """Os outros jogadores que estão neste mesmo mapa."""
        return [r for r in self.remotes.values() if r.map_id == self.map_def.id]

    def update_movement(self, dt):
        keys = pygame.key.get_pressed()
        direction = next((d for k, d in KEY_DIRS if keys[k]), None)
        if direction is None:
            self.chain = False
            self.turn_delay = 0.0
            return
        if self.player.facing != direction and not self.chain:
            self.player.facing = direction
            self.turn_delay = TURN_DELAY
            self.send_position()
            return
        if self.turn_delay > 0:
            self.turn_delay -= dt
            return
        dx, dy = DIR_VECTORS[direction]
        if self.walkable(self.player.tx + dx, self.player.ty + dy):
            running = any(keys[k] for k in RUN_KEYS)
            self.player.start_move(direction, RUN_TIME if running else WALK_TIME)
            self.send_position(running)
            self.chain = True
        else:
            self.player.facing = direction
            self.chain = False
            if self.bump_cd <= 0:
                sfx.play("bump")
                self.bump_cd = BUMP_COOLDOWN

    # ------------------------------------------------------------ desenho
    def object_image(self, name, label=None):
        """Desenho de um objeto do catálogo: construção por código ou recorte do pacote.
        Se tiver `label`, a construção ganha a placa com o nome."""
        d = OBJECTS[name]
        if label:
            label = label.format(name=self.ch.name.upper())
        if name in BUILDERS:
            return art.optimize(BUILDERS[name](label))
        if not d.tileset:
            return None                     # objeto sem desenho: fica invisível (mas sólido)
        img = tilemap.object_image(name)
        return buildings.add_plaque(img, label, d.door[0] if d.door else None) if label else img

    def build_figures(self):
        """Tudo que fica "em pé" no mapa: (imagem, x, y em pixels, chave de profundidade).

        A chave é a altura do pé da figura na tela. Desenhando em ordem crescente, o que está mais
        embaixo na tela cobre o que está mais em cima — por isso dá para passar atrás de uma árvore.
        """
        figures = []
        for obj in self.map_def.objects:
            img = self.object_image(obj.name, obj.label)
            if img is not None:
                figures.append((img, obj.x * TILE, obj.y * TILE, (obj.y + OBJECTS[obj.name].h) * TILE))
        for y, row in enumerate(self.map):
            for x, ch in enumerate(row):
                foot = (y + 1) * TILE
                if ch == "T":                   # árvore 2x2 com o tronco neste tile
                    figures.append((tilemap.tree_image(x, y), x * TILE - TILE // 2, y * TILE - TILE, foot))
                elif ch == "R":
                    figures.append((tilemap.tile(*tilemap.ROCK_TILE), x * TILE, y * TILE, foot))
                elif ch == "S":                 # placa: a tábua fica um tile acima do poste
                    figures.append((tilemap.tile(*tilemap.SIGN_TILE), x * TILE, y * TILE - TILE, foot))
        return figures

    def draw(self, surf):
        cam = self.camera()
        surf.blit(self.ground, (0, 0), pygame.Rect(cam, (GAME_W, GAME_H)))
        self.draw_standing(surf, cam)
        self.draw_online_labels(surf, cam)
        self.draw_notice(surf)

        self.draw_banner(surf)
        if self.showing_profile:
            draw_profile(surf, self.ch, self.player.frames[("down", 0)], self.time)
        if self.menu:
            self.menu.draw(surf)
            draw_box(surf, (4, 6, 110, 26))
            draw_bets(surf, self.ch.bets, 104, 12)
        self.prompt.draw(surf)

    def draw_standing(self, surf, cam):
        """Objetos e personagens juntos, em ordem de profundidade (quem está mais embaixo fica na frente)."""
        view = pygame.Rect(cam[0] - 64, cam[1] - 64, GAME_W + 128, GAME_H + 128)
        layer = [(foot, 0, img, x, y) for img, x, y, foot in self.figures if view.collidepoint(x, y)]
        # 1: no mesmo pé, o personagem fica na frente do objeto
        layer.extend((actor.py + TILE, 1, actor, 0, 0) for actor in (*self.npcs, *self.remotes_here(), self.player))
        shadow = tilemap.actor_shadow()
        for _, kind, thing, x, y in sorted(layer, key=lambda item: (item[0], item[1])):
            if kind == 0:
                surf.blit(thing, (x - cam[0], y - cam[1]))
                continue
            surf.blit(shadow, (round(thing.px) + 1 - cam[0], round(thing.py) + 12 - cam[1]))
            thing.draw(surf, cam)
            if self.tile_at(thing.tx, thing.ty) == TALL_GRASS and not thing.moving:
                self.draw_grass_front(surf, thing, cam)

    def draw_online_labels(self, surf, cam):
        """Nome em cima de cada jogador online, a espada de quem está em batalha e os balões de fala."""
        for remote in self.remotes_here():
            x = round(remote.px) + TILE // 2 - cam[0]
            top = round(remote.py) + FOOT_Y - remote.image().get_height() - cam[1]
            draw_outlined(surf, remote.name, (x, top - 11), (255, 255, 160) if remote.battle else (255, 255, 255),
                          (20, 20, 32), size=12, align="center")
            if remote.battle:                       # espada ao lado do nome: está numa batalha
                surf.blit(art.icon("sword"), (x + text_width(remote.name, 12) // 2 + 3, top - 12))
            if remote.emote:
                self.draw_bubble(surf, remote.emote, x, top - 14)
        if self.my_emote and self.my_emote_t > 0:
            x = round(self.player.px) + TILE // 2 - cam[0]
            top = round(self.player.py) + FOOT_Y - self.player.image().get_height() - cam[1]
            self.draw_bubble(surf, self.my_emote, x, top - 2)

    @staticmethod
    def draw_bubble(surf, text, x, bottom):
        width = text_width(text, 12) + 10
        rect = pygame.Rect(x - width // 2, bottom - 15, width, 13)
        pygame.draw.rect(surf, (20, 20, 32), rect.inflate(2, 2), border_radius=4)
        pygame.draw.rect(surf, (255, 255, 255), rect, border_radius=4)
        pygame.draw.polygon(surf, (255, 255, 255), [(x - 3, rect.bottom), (x + 3, rect.bottom), (x, rect.bottom + 4)])
        draw_text(surf, text, (x, rect.y + 1), size=12, shadow=None, align="center")

    def draw_notice(self, surf):
        if self.notice_t <= 0:
            return
        width = text_width(self.notice, 12) + 20
        rect = pygame.Rect(GAME_W - width - 6, 6, width, 18)
        draw_box(surf, rect)
        draw_text(surf, self.notice, (rect.centerx, rect.y + 3), size=12, align="center")

    def draw_grass_front(self, surf, actor, cam):
        """Metade de baixo do mato alto por cima do personagem: parece que ele está dentro do mato."""
        pos = (actor.tx * TILE - cam[0], actor.ty * TILE - cam[1])
        grass = tilemap.tile(*tilemap.TALL_GRASS_TILE)
        surf.blit(grass, (pos[0], pos[1] + TILE // 2), pygame.Rect(0, TILE // 2, TILE, TILE // 2))

    def draw_banner(self, surf):
        t = self.banner_t
        if t > BANNER_TIME:
            return
        slide = 0.3
        if t < slide:
            y = -26 + t / slide * 30
        elif t > BANNER_TIME - slide:
            y = 4 - (t - (BANNER_TIME - slide)) / slide * 30
        else:
            y = 4
        name = self.map_def.name.upper()
        width = text_width(name) + 28
        draw_box(surf, (4, int(y), width, 26))
        draw_text(surf, name, (4 + width // 2, int(y) + 7), align="center")

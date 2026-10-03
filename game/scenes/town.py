"""NPCs com vida própria na tela. Mixin do LobbyScene (como o CafeMixin e o HomeMixin).

Quem decide para onde cada NPC vai é game/core/townsfolk.py (`NpcWorld`):
- jogando sozinho, o mundo dos NPCs roda AQUI (`self.npc_world`);
- no online, roda no SERVIDOR, e aqui só chegam as mensagens: npc (andou), npc_say (balão) e npc_challenge
  (um duelista veio até você). Assim os dois jogadores veem o mesmo NPC no mesmo lugar.
Os NPCs de TODOS os mapas existem o tempo todo (`self.npc_actors`); a tela mostra os do mapa atual.
Falar com um NPC o segura parado (`hold_npc`), no online avisando o servidor.
"""
from game.core.townsfolk import NpcWorld
from game.data.opponents import TRAINERS
from game.data.world import DIR_VECTORS, MAPS, OPPOSITE, TRAINER_TALK
from game.engine import sfx
from game.graphics import sprites
from game.scenes.actors import NPC

TALK_HOLD = 8.0              # segundos que o NPC fica parado conversando
BATTLE_HOLD = 90.0           # e duelando
INVITE_TIME = 10.0           # o desafio de um NPC espera a tela ficar livre por até 10 s


class TownMixin:
    def setup_town(self):
        """Chamado uma vez, no começo do lobby: cria os NPCs de todos os mapas públicos."""
        helper_talk = {"beto": self.talk_beto, "nina": self.talk_nina, "rosa": self.talk_rosa,
                       "lu": self.talk_lu, "gabi": self.talk_gabi}
        self.npc_actors = {}
        for m in MAPS.values():
            if m.private:
                continue
            for tid, spot in m.trainers.items():
                look = TRAINERS[tid]["look"]
                self.npc_actors[tid] = NPC(tid, TRAINERS[tid]["name"], m.id, spot, sprites.character_frames(look),
                                           lambda tid=tid: self.talk_trainer(tid), look)
            for hid, helper in m.helpers.items():
                npc = NPC(hid, hid.upper(), m.id, helper.spot, sprites.character_frames(helper.look),
                          helper_talk[hid], helper.look)
                npc.sitting = helper.sitting
                self.npc_actors[hid] = npc
        self.npc_world = NpcWorld()
        self.npc_invite = None          # [npc, segundos]: desafio esperando a tela ficar livre
        for state in getattr(self.net, "initial_npcs", []):
            self.apply_npc_state(state.get("id"), state)

    @property
    def npcs(self):
        """Os NPCs que estão no mapa atual."""
        return [n for n in self.npc_actors.values() if n.map_id == self.map_def.id]

    # ------------------------------------------------------------ tempo
    def update_town(self, dt):
        if self.net is None:                                     # sozinho: a vida dos NPCs roda aqui
            for event in self.npc_world.tick(dt, self.town_players(), night=self.clock.is_night):
                self.npc_event(event)
        for npc in self.npc_actors.values():
            npc.tick(dt)
        if self.npc_invite:
            self.npc_invite[1] -= dt
            if self.npc_invite[1] <= 0:
                self.npc_invite = None
            elif not self.paused:
                npc_id, self.npc_invite = self.npc_invite[0], None
                self.npc_challenges_me(npc_id)

    def town_players(self):
        """Quem está no mundo para os NPCs desviarem (e o jogador, para ser desafiado)."""
        busy = bool(self.paused or self.player.pose != "stand" or self.tournament or self.fishing)
        players = [{"id": "me", "map": self.map_key, "x": self.player.tx, "y": self.player.ty, "busy": busy}]
        if self.spouse_here:                                     # a Rebeca: só um obstáculo
            players.append({"id": "spouse", "map": self.map_def.id, "x": self.spouse_actor.tx,
                            "y": self.spouse_actor.ty, "target": False})
        return players

    def npc_event(self, event):
        kind, npc_id = event[0], event[1]
        if kind == "move":
            self.apply_npc_state(npc_id, event[2])
        elif kind == "say":
            npc = self.npc_actors.get(npc_id)
            if npc:
                npc.say(event[2], 3.0)
        elif kind == "challenge" and npc_id in self.npc_actors:
            self.npc_invite = [npc_id, INVITE_TIME]

    def apply_npc_state(self, npc_id, state):
        npc = self.npc_actors.get(npc_id)
        if npc is None or not state.get("map"):
            return
        npc.queue_move(state["map"], state.get("x", npc.tx), state.get("y", npc.ty), state.get("facing"), False,
                       state.get("pose") or "stand")

    def on_npc_message(self, message):
        """Online: o servidor contou algo dos NPCs."""
        kind = message["t"]
        if kind == "npc":
            self.apply_npc_state(message.get("id"), message)
        elif kind == "npc_say":
            self.npc_event(("say", message.get("id"), str(message.get("text", ""))[:60]))
        elif kind == "npc_challenge":
            self.npc_event(("challenge", message.get("id")))

    # ------------------------------------------------------------ conversar e ser desafiado
    def hold_npc(self, npc, seconds=TALK_HOLD):
        """Segura o NPC parado (de frente para o jogador) enquanto vocês conversam ou duelam."""
        face = OPPOSITE[self.player.facing]
        if not npc.sitting:
            npc.facing = face
        if self.net:
            self.net.send({"t": "npc_hold", "id": npc.id, "seconds": seconds, "face": face})
        else:
            self.npc_world.hold(npc.id, seconds, face)

    def talk_npc(self, npc):
        self.hold_npc(npc)
        npc.on_talk()

    def npc_challenges_me(self, npc_id):
        """Um duelista veio até você: "Ei! Vamos duelar?" (aceitar = duelo normal contra ele)."""
        npc = self.npc_actors[npc_id]
        if npc.map_id != self.map_def.id or abs(npc.tx - self.player.tx) + abs(npc.ty - self.player.ty) > 2:
            return
        offset = (npc.tx - self.player.tx, npc.ty - self.player.ty)
        self.player.facing = next((d for d, v in DIR_VECTORS.items() if v == offset), self.player.facing)
        self.hold_npc(npc, TALK_HOLD)
        sfx.play("encounter")
        talk, face = TRAINER_TALK[npc_id], self.face_of(npc_id)
        required = TRAINERS[npc_id].get("requires")
        if required and required not in self.ch.beaten:          # ainda não pode desafiá-lo: só conversa
            self.say(list(talk.locked) or [f"{npc.name}: Oi!"], face=face)
            return
        line = talk.rematch if npc_id in self.ch.beaten else talk.greet
        name = self.ch.name.upper()

        def answer(yes):
            if yes:
                self.hold_npc(npc, BATTLE_HOLD)
                self.challenge(npc_id)
            else:
                self.say(f"{npc.name}: Tudo bem, {name}! Fica pra próxima.", face=face)
        self.prompt.ask([f"{npc.name}: Ei, {name}!", line], answer, face=face)


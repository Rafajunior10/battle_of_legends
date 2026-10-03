"""Casa e vida a dois. Mixin do LobbyScene (como o CafeMixin da lanchonete).

- Cama: A deita (qualquer direção levanta). Deitado, A pergunta se quer dormir (salva o jogo). Se a REBECA
  estiver deitada na mesma cama, vocês dormem juntos: a tela escurece, Zzz, e amanhece.
- Box: A entra no banho por uns segundos (água caindo atrás do vidro).
- REBECA (só para quem tem `Character.spouse`): tem rotina própria (core/companion.py) pela casa, pela vila e
  pela lanchonete. Falar com ela abre: CONVERSAR, ME SEGUE / PODE IR, ABRAÇAR, BEIJAR, VAMOS DORMIR.
  Ela é desenhada por um RemotePlayer (a mesma animação dos jogadores online), alimentado pelo estado dela.
  No online, quando ela está num mapa público, os outros jogadores também a veem (mensagem "companion").
- Estante de troféus e closet (scenes/closet.py).
"""
import math
import random
from dataclasses import asdict

import pygame

from game.core.companion import Companion
from game.core.nav import Nav, free_tile_near
from game.data.companion import COMPANIONS
from game.data.props import OBJECTS
from game.data.world import DIR_VECTORS, MAPS, OPPOSITE
from game.engine import sfx
from game.engine.settings import GAME_H, GAME_W, TILE
from game.engine.ui import draw_outlined, overlay
from game.graphics import house, sprites
from game.scenes.actors import RemotePlayer

SHOWER_TIME = 4.0
SLEEP_TIME = 4.0
AFFECTION_TIME = 1.8
REPLY_DELAY = 1.8             # o NPC responde depois que ela fala (os balões não se cobrem)
NAV = Nav()                   # caminhos dos mapas (calculados uma vez por mapa e reaproveitados)
_heart: list = []
_heart_cache: dict = {}         # imagens pequenas desenhadas uma vez (o vidro do box)


def heart_image():
    """Coraçãozinho 7 x 6 (desenhado uma vez)."""
    if not _heart:
        s = pygame.Surface((7, 6), pygame.SRCALPHA)
        for x, y in ((1, 0), (2, 0), (4, 0), (5, 0), *((x, 1) for x in range(7)), *((x, 2) for x in range(7)),
                     *((x, 3) for x in range(1, 6)), (2, 4), (3, 4), (4, 4), (3, 5)):
            s.set_at((x, y), (236, 60, 90))
        s.set_at((1, 1), (255, 170, 190))
        _heart.append(s)
    return _heart[0]


class HomeMixin:
    def setup_home_state(self):
        """Chamado uma vez, no começo do lobby."""
        spec = COMPANIONS.get(self.ch.spouse)
        self.companion = Companion.at_home(spec) if spec else None
        self.spouse_actor = None
        self.spouse_state = None
        if spec:
            self.spouse_actor = RemotePlayer("spouse", spec.name, sprites.character_frames(spec.look),
                                             self.companion.map_id, self.companion.x, self.companion.y, "down")
        self.spouse_line = 0
        self.rng = random.Random()
        self.trail = None               # o tile de onde o jogador acabou de sair (ela vem atrás)
        self.last_tile = None
        self.shower_t = None            # tomando banho (segundos que faltam)
        self.sleep_t = None             # dormindo (cena da tela escurecendo)
        self.sleep_morning = False      # este sono acaba de manhã (a noite passou)
        self.affection = None           # [tipo, tempo] do abraço/beijo
        self.companion_sent = None
        self.replies = []               # [segundos, npc, texto]: respostas dos NPCs esperando a vez

    def setup_home(self):
        """Chamado por load_map: camas, box e a Rebeca chegando junto se estiver seguindo."""
        self.beds, self.bed_covers, self.showers = {}, {}, {}
        for obj in self.map_def.objects:
            d = OBJECTS[obj.name]
            if obj.name in house.BEDS:
                spec = house.BEDS[obj.name]
                img = self.object_image(obj.name)
                for dy in range(d.h):
                    for dx in range(d.w):
                        self.beds[(obj.x + dx, obj.y + dy)] = obj
                top, bottom = spec.cover
                self.bed_covers[(obj.x, obj.y)] = (img.subsurface((0, top, img.get_width(), bottom - top)),
                                                   obj.x * TILE, obj.y * TILE + top)
            elif obj.name == "shower":
                for dy in range(d.h):
                    for dx in range(d.w):
                        self.showers[(obj.x + dx, obj.y + dy)] = obj
                if "glass" not in _heart_cache:
                    _heart_cache["glass"] = house.shower_glass()
                self.bed_covers[(obj.x, obj.y)] = (_heart_cache["glass"], obj.x * TILE,
                                                   obj.y * TILE + house.SHOWER["glass"][0])
        self.shower_t = None
        self.trail = self.last_tile = None

    def companion_arrives(self):
        """Chamado por load_map depois de o jogador chegar: se ela está seguindo, entra junto."""
        if self.companion and self.companion.mode == "follow" and self.companion.map_id != self.map_def.id:
            self.bring_companion()

    def bring_companion(self):
        """Seguindo o jogador: ela aparece do lado dele no mapa novo."""
        here = (self.player.tx, self.player.ty)
        spot = free_tile_near(NAV, self.map_def.id, here, prefer=OPPOSITE[self.player.facing])
        if spot:
            self.companion.place(self.map_def.id, *spot, facing=self.player.facing)
            self.spouse_actor.map_id = self.map_def.id
            self.spouse_actor.pending.clear()
            self.spouse_actor.place(*spot)
            self.spouse_state = None

    # ------------------------------------------------------------ a Rebeca no tempo
    @property
    def spouse_here(self):
        return self.spouse_actor is not None and self.spouse_actor.map_id == self.map_def.id

    def update_home(self, dt):
        if self.sleep_t is not None:
            self.sleep_t += dt
            if self.sleep_t >= SLEEP_TIME:
                self.wake_up()
            return
        if self.affection:
            self.update_affection(dt)
        if self.shower_t is not None:
            self.shower_t -= dt
            if self.shower_t <= 0:
                self.leave_shower()
        self.update_companion(dt)
        self.update_replies(dt)

    def update_companion(self, dt):
        if not self.companion:
            return
        here = (self.player.tx, self.player.ty)
        if here != self.last_tile:
            self.trail, self.last_tile = self.last_tile, here
        c = self.companion
        occupied = set()
        if c.map_id == self.map_def.id:
            occupied = {here} | {(n.tx, n.ty) for n in self.npcs}
        leader = (self.map_def.id, self.trail or here, here)
        for event in c.tick(dt, NAV, self.rng, occupied=frozenset(occupied), leader=leader):
            self.companion_event(event)
        state = (c.map_id, c.x, c.y, c.facing, c.pose)
        actor = self.spouse_actor
        if state != self.spouse_state:
            self.spouse_state = state
            actor.queue_move(c.map_id, c.x, c.y, c.facing, c.mode == "follow", c.pose)
            self.send_companion()
        actor.tick(dt)
        self.place_pose(actor)
        if c.pose == "stand" and not actor.moving and not actor.pending:
            actor.facing = c.facing

    def companion_event(self, event):
        if self.companion.map_id != self.map_def.id:
            return                                         # longe do jogador: ninguém vê o balão
        if event[0] == "say":
            self.spouse_actor.say(event[1], 3.5)
        elif event[0] == "reply":
            self.spouse_actor.emote_t = min(self.spouse_actor.emote_t, REPLY_DELAY)
            self.replies.append([REPLY_DELAY, event[1], event[2]])

    def update_replies(self, dt):
        for reply in list(self.replies):
            reply[0] -= dt
            if reply[0] <= 0:
                self.replies.remove(reply)
                npc = next((n for n in self.npcs if n.id == reply[1]), None)
                if npc:
                    npc.say(reply[2], 3.0)

    def send_companion(self):
        """Online: os outros veem a Rebeca quando ela está num mapa público (na casa, ninguém vê)."""
        if not self.net or not self.companion:
            return
        c = self.companion
        public = not MAPS[c.map_id].private
        message = {"t": "companion", "map": c.map_id if public else None, "x": c.x, "y": c.y, "facing": c.facing,
                   "pose": c.pose if c.pose == "sit" else "stand", "name": c.name, "look": asdict(c.spec.look)}
        if message != self.companion_sent:
            self.companion_sent = message
            self.net.send(message)

    # ------------------------------------------------------------ conversa e carinho
    def talk_spouse(self):
        c = self.companion
        c.hold(6.0, face=OPPOSITE[self.player.facing])
        face = sprites.face(c.spec.look)
        follow = "PODE IR" if c.mode == "follow" else "ME SEGUE"
        options = ["CONVERSAR", follow, "ABRAÇAR", "BEIJAR", "VAMOS DORMIR", "NADA"]

        def chosen(index):
            c.held = 0.0
            option = options[index] if 0 <= index < len(options) else "NADA"
            if option == "CONVERSAR":
                line = c.spec.lines[self.spouse_line % len(c.spec.lines)]
                self.spouse_line += 1
                c.hold(3.0)
                self.say(line.format(name=self.ch.name.upper()), face=face)
            elif option == "ME SEGUE":
                c.follow()
                self.spouse_actor.say("Vamos juntos!", 2.5)
            elif option == "PODE IR":
                c.stop_following()
                self.spouse_actor.say("Vou cuidar das minhas coisas!", 2.5)
            elif option in ("ABRAÇAR", "BEIJAR"):
                self.start_affection("hug" if option == "ABRAÇAR" else "kiss")
            elif option == "VAMOS DORMIR":
                if c.go_to_sleep(NAV):
                    self.say(f"{c.name}: Bora! Te espero na cama, amor.", face=face)
                else:
                    self.say(f"{c.name}: Hmm, daqui eu não sei chegar em casa...", face=face)
        self.prompt.choose(f"{c.name}: Oi, amor! O que foi?", options, chosen, face=face)

    def start_affection(self, kind):
        self.affection = [kind, 0.0]
        self.companion.hold(AFFECTION_TIME + 0.5, face=OPPOSITE[self.player.facing])
        sfx.play("confirm")

    def update_affection(self, dt):
        kind, t = self.affection
        t += dt
        dx, dy = DIR_VECTORS[self.player.facing]
        push = (2 if kind == "hug" else 3) if 0.15 < t < AFFECTION_TIME - 0.2 else 0
        self.player.nudge = (dx * push, dy * push)
        self.spouse_actor.nudge = (-dx * push, -dy * push)
        if t >= AFFECTION_TIME:
            self.player.nudge = self.spouse_actor.nudge = (0, 0)
            self.affection = None
            self.spouse_actor.say("Que abraço gostoso!" if kind == "hug" else "Te amo!", 2.5)
            return
        self.affection[1] = t

    def draw_affection(self, surf, cam):
        """Coraçõezinhos subindo entre os dois."""
        if not self.affection:
            return
        kind, t = self.affection
        x = (self.player.px + self.spouse_actor.px) / 2 + TILE // 2 - cam[0]
        y = (self.player.py + self.spouse_actor.py) / 2 - 18 - cam[1]
        for i in range(5 if kind == "kiss" else 3):
            phase = (t * 0.9 + i * 0.27) % 1.0
            hx = x + math.sin(t * 5 + i * 2) * 6 - 3
            surf.blit(heart_image(), (round(hx), round(y - phase * 22)))

    # ------------------------------------------------------------ cama, banho e sono
    def slot_tile(self, bed, slot):
        d = OBJECTS[bed.name]
        return (bed.x if slot == 0 else bed.x + d.w - 1), bed.y + 1

    def place_pose(self, actor):
        """Onde desenhar quem está deitado ou no banho (o boneco não fica no meio do tile)."""
        tile = (actor.tx, actor.ty)
        actor.anchor = actor.depth = None
        actor.flip = False
        if actor.pose == "lie" and tile in self.beds:
            bed = self.beds[tile]
            spec, d = house.BEDS[bed.name], OBJECTS[bed.name]
            slot = min(len(spec.slots) - 1, 0 if tile[0] - bed.x < d.w / 2 else 1)
            actor.anchor = (bed.x * TILE + spec.slots[slot], bed.y * TILE + spec.top)
            actor.flip = spec.flip
            actor.depth = (bed.y + d.h) * TILE + 1
        elif actor.pose == "shower" and tile in self.showers:
            box = self.showers[tile]
            actor.anchor = (box.x * TILE + house.SHOWER["center"], box.y * TILE + house.SHOWER["top"])
            actor.depth = (box.y + OBJECTS[box.name].h) * TILE + 1

    def lie_down(self, target):
        bed = self.beds[target]
        taken = {(self.spouse_actor.tx, self.spouse_actor.ty)} if self.spouse_here else set()
        slots = [self.slot_tile(bed, i) for i in range(len(house.BEDS[bed.name].slots))]
        tile = next((t for t in slots if t not in taken), None)
        if tile is None:
            self.say("Não tem espaço nessa cama.")
            return
        self.seated_from = (self.player.tx, self.player.ty)
        self.player.place(*tile)
        self.player.pose = "lie"
        self.place_pose(self.player)
        sfx.play("cursor")
        self.send_bed(True)
        if self.clock.is_night:                                  # de noite, deitar é ir dormir
            self.go_to_sleep_now()
        elif self.spouse_in_bed(bed):
            self.start_sleep(skip=False, morning=False)          # de dia, um cochilo juntinhos
        else:
            self.banner("Deitado. A: cochilar (salva)   direção: levantar")

    def spouse_in_bed(self, bed):
        return self.spouse_here and self.spouse_actor.pose == "lie" and self.beds.get(
            (self.spouse_actor.tx, self.spouse_actor.ty)) is bed

    def posed_interact(self):
        """A deitado: de dia, pergunta se quer cochilar; de noite, avisa que está esperando os outros."""
        if self.player.pose != "lie":
            return
        if self.clock.is_night:
            self.say("Você está dormindo... a noite passa quando todos os jogadores estiverem deitados.")
            return
        self.prompt.ask("Cochilar um pouco? (o jogo é salvo)",
                        lambda yes: self.start_sleep(skip=False, morning=False) if yes else None)

    def wake_up(self):
        together = self.companion is not None and self.spouse_here and self.spouse_actor.pose == "lie"
        morning = self.sleep_morning
        if self.sleep_skip:                                      # sozinho: a noite passa aqui mesmo
            self.clock.sleep_until_morning()
        self.sleep_t, self.sleep_skip, self.sleep_morning = None, False, False
        self.update_clock(0.0)
        self.ch.save()
        sfx.play("save")
        if self.player.pose == "lie":
            self.stand_up("down")
        if together:
            self.companion.wake()
            self.spouse_actor.say("Bom dia, amor!" if morning else "Que soninho bom!", 3.0)
        if morning:
            first = "Vocês dormiram juntinhos a noite toda... Zzz" if together else "Você dormiu a noite toda."
            self.say([first, f"Bom dia! {self.clock.label()}. Jogo salvo."])
        elif together:
            self.say(["Vocês tiraram um cochilo juntinhos.", "Jogo salvo!"])
        else:
            self.say(["Você tirou um cochilo gostoso.", "Jogo salvo!"])

    def take_shower(self, target):
        box = self.showers[target]
        tile = (box.x, box.y + OBJECTS[box.name].h - 1)
        if self.spouse_here and (self.spouse_actor.tx, self.spouse_actor.ty) == tile:
            self.say("A REBECA está no banho! Espera ela sair.")
            return
        self.seated_from = (self.player.tx, self.player.ty)
        self.player.place(*tile)
        self.player.pose = "shower"
        self.place_pose(self.player)
        self.shower_t = SHOWER_TIME
        sfx.play("cursor")

    def leave_shower(self):
        self.shower_t = None
        if self.player.pose == "shower":
            self.stand_up("down")
            self.say("Banho tomado! Cheirosinho.")

    def draw_pose_front(self, surf, actor, cam):
        """O que fica NA FRENTE de quem está sentado (assento), deitado (edredom) ou no banho (vidro e água)."""
        if actor.pose == "sit":
            self.draw_seat_front(surf, actor, cam)
            return
        holder = self.beds.get((actor.tx, actor.ty)) or self.showers.get((actor.tx, actor.ty))
        if holder is None:
            return
        cover, x, y = self.bed_covers[(holder.x, holder.y)]
        surf.blit(cover, (x - cam[0], y - cam[1]))
        if actor.pose == "shower":                               # água caindo
            base_x, top = holder.x * TILE + 7 - cam[0], holder.y * TILE + 15 - cam[1]
            for i in range(5):
                drop = (self.time * 70 + i * 13) % 28
                pygame.draw.line(surf, (170, 220, 250), (base_x + i * 2, top + drop), (base_x + i * 2, top + drop + 3))

    def draw_sleep(self, surf):
        if self.sleep_t is None:
            return
        t = self.sleep_t
        dark = min(1.0, t / 1.2, (SLEEP_TIME - t) / 0.8)
        surf.blit(overlay((8, 8, 24), 230 * max(0.0, dark)), (0, 0))
        if 0.8 < t < SLEEP_TIME - 0.6:
            for i, size in enumerate((12, 16, 20)):
                y = GAME_H // 2 + 10 - i * 18 - (t * 8) % 6
                draw_outlined(surf, "Z", (GAME_W // 2 - 10 + i * 12, round(y)), (230, 230, 255), (20, 20, 50),
                              size=size)

    # ------------------------------------------------------------ estante, closet, cama do quarto de hóspedes
    def show_trophies(self):
        wins = self.ch.coliseum_wins
        lines = [f"ESTANTE: {wins} troféu{'s' if wins != 1 else ''} de campeão do Coliseu." if wins
                 else "ESTANTE: ainda vazia. Vença o torneio do Coliseu para ganhar o primeiro troféu!"]
        medals = [name for who, name in (("rafa", "RAFA"), ("lia", "Mestra LIA"), ("zeca", "Grão-Mestre ZECA"))
                  if who in self.ch.beaten]
        if medals:
            lines.append("Medalhas penduradas: " + ", ".join(medals) + ".")
        self.say(lines)

    def open_closet(self):
        from game.scenes.closet import ClosetScene
        sfx.play("confirm")
        self.game.transition_to(lambda: ClosetScene(self.game, self))

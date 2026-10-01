"""Batalha de cartas por turnos, com animações no estilo das batalhas de GBA.

Tudo que acontece na batalha passa por uma fila de "passos" (mensagens,
animações, chamadas de função). Assim as coisas acontecem uma de cada vez,
na ordem certa, igual nos jogos clássicos. As regras ficam em game/core;
esta cena só pede às regras o que fazer e narra os eventos que voltam.
"""
import random
from collections import deque
from typing import ClassVar

import pygame

from game.core import abilities
from game.core import events as ev
from game.core.ai import choose_card, drogoz_discards, mimo_pick
from game.core.combat import Combatant, end_turn, loser, pay_card, start_turn
from game.core.effects import (
    AuraEffect,
    BurnEffect,
    DamageEffect,
    DefenseEffect,
    DrawEffect,
    EnergyEffect,
    HealEffect,
    IceEffect,
    PoisonEffect,
    StunEffect,
)
from game.core.rules import HAND_SIZE, ICE_LIMIT
from game.data.cards import ARCHETYPE_NAMES, Deck
from game.data.legends import LEGENDS
from game.data.opponents import rewards
from game.engine import sfx
from game.engine.settings import (
    CANCEL_KEYS,
    CONFIRM_KEYS,
    DOWN_KEYS,
    GAME_W,
    LEFT_KEYS,
    RIGHT_KEYS,
    UP_KEYS,
)
from game.engine.ui import DialogBox
from game.graphics import backgrounds, sprites
from game.graphics import pixelart as art
from game.scenes.base import Scene
from game.scenes.battle_fx import FX, Call, CutIn, Faint, Fly, Hit, Lunge, Msg, SlideIn, Transform, Wait, WaitBars
from game.scenes.battle_hud import (
    ENEMY_FEET,
    ENEMY_HEIGHT,
    ENEMY_LEGEND_H,
    GREEN,
    HUD_ICON,
    MESSAGE_BOX,
    MONSTER_SCALE,
    PLAYER_FEET,
    PLAYER_HEIGHT,
    PLAYER_LEGEND_H,
    PORTRAIT_H,
    BattleHUD,
    hud_icon,
)

HIT_STOP = 0.06                               # pausa no impacto (segundos)
MARKER_EFFECT_FX = {BurnEffect: "flame", IceEffect: "ice", PoisonEffect: "poison", StunEffect: "stun"}


def _say(text, auto=0.55):
    """Narrador simples para a tabela NARRATORS: só uma mensagem ({f.name} e {e.campo} são preenchidos)."""
    return lambda scene, e, f: [Msg(text.format(f=f, e=e), auto=auto)]


def white_silhouette(sprite):
    white = sprite.copy()
    white.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
    return white


class Fighter:
    """Visual de quem está duelando. As regras (PV, defesa, mão...) ficam em `state` (core.combat)."""

    def __init__(self, state, sprite, feet):
        self.state = state
        self.disp_hp = float(state.max_hp)   # valor animado da barra de PV
        self.feet = feet
        self.owner = None       # nome de quem se transformou no legend
        self.icon = None        # retratinho no painel de vida
        self.flash = False
        self.offset = pygame.Vector2()
        self.visible = True
        self.set_sprite(sprite)

    def set_sprite(self, sprite):
        """Troca o desenho mantendo os pés no mesmo lugar (usado na transformação em legend)."""
        self.sprite = sprite
        self.white = white_silhouette(sprite)   # pisca em branco ao levar dano
        self.base = pygame.Vector2(self.feet[0] - sprite.get_width() // 2, self.feet[1] - sprite.get_height())

    def __getattr__(self, name):
        # leitura do estado de regras direto pelo visual: f.hp, f.defense, f.hand...
        if name == "state":
            raise AttributeError(name)
        return getattr(self.state, name)

    @property
    def center(self):
        w, h = self.sprite.get_size()
        return (self.base.x + w // 2, self.base.y + h * 11 // 20)

    @property
    def feet_y(self):
        return self.base.y + self.sprite.get_height()


# ============================================================ cena
class BattleScene(BattleHUD, Scene):
    def __init__(self, game, spec, on_end):
        super().__init__(game)
        self.spec = spec
        self.on_end = on_end
        ch = game.character
        back_img = sprites.player_frames(ch)[("up", 0)]                                 # você, de costas
        back = art.scale(back_img, sprites.fit_scale(back_img, PLAYER_HEIGHT))
        if "monster" in spec or "slime" in spec:
            monster = sprites.monster_image(spec.get("monster"), spec.get("slime", "green"))
            front = art.scale(monster, MONSTER_SCALE)
        else:
            front_img = sprites.character_frames(spec["look"])[("down", 0)]
            front = art.scale(front_img, sprites.fit_scale(front_img, ENEMY_HEIGHT))
        self.rng = random.Random()
        my_rng, foe_rng = self.deck_rngs()
        me = Combatant(ch.name.upper(), ch.level, ch.max_hp, Deck(ch.deck, my_rng, ch.card_levels),
                       is_player=True)
        foe = Combatant(spec["name"], spec.get("level", 1), spec["hp"],
                        Deck(spec["deck"], foe_rng, spec.get("card_levels")))
        self.player = Fighter(me, back, PLAYER_FEET)
        self.enemy = Fighter(foe, front, ENEMY_FEET)
        self.player.icon = hud_icon(sprites.face(ch.appearance))
        self.enemy.icon = hud_icon(sprites.face(spec["look"]) if "look" in spec else front)
        self.fighters = (self.player, self.enemy)
        self.legend_ids = {self.player: ch.legend, self.enemy: spec.get("legend")}
        self.picked = []        # Drogoz: POSIÇÕES na mão das cartas marcadas (cartas iguais são ==)
        self.revealed = []      # Mimo: as 2 cartas reveladas do topo
        self.option = 0         # Mimo: cursor nas reveladas (o último é "não jogar")
        self.player.offset.x = 300
        self.enemy.offset.x = -300

        self.bg = backgrounds.battle_background()
        self.dialog = DialogBox(MESSAGE_BOX, speed=70)
        self.steps = deque()
        self.current = None
        self.state = "intro"    # intro | choose | busy | enemy | done
        self.cursor = 0
        self.over = False
        self.time = 0.0
        self.floats = []
        self.prize = None       # (bets, xp, níveis) ganhos ao vencer
        self.shake_t = 0.0      # tremor de tela restante
        self.shake_power = 0
        self.hitstop = 0.0      # pausa curtinha no impacto
        self.run(SlideIn(), Msg(spec["intro"], auto=None),
                 *self.transformation(self.player), *self.transformation(self.enemy),
                 Msg(f"Os dois embaralham e compram {HAND_SIZE} cartas...", auto=0.6), Call(self.deal))

    def on_enter(self):
        sfx.music("battle")

    # ------------------------------------------------------------ ganchos (o duelo online troca estes)
    def deck_rngs(self):
        """Sorteio do (meu baralho, baralho do oponente)."""
        return self.rng, self.rng

    def first(self):
        """Quem joga primeiro."""
        return self.player

    def sent(self, action):
        """Você fez uma jogada (no duelo online ela vai para o outro computador)."""

    # ------------------------------------------------------------ transformação em legend
    def transformation(self, f):
        """Passos da transformação de `f` no legend do deck dele (monstro selvagem não tem legend)."""
        legend = LEGENDS.get(self.legend_ids.get(f) or "")
        if legend is None:
            return []
        color = art.ARCHETYPE_COLORS[legend.archetype][0]
        who = "Você" if f.is_player else f.name
        portrait = sprites.legend_image(legend.id, "portrait", PORTRAIT_H)
        subtitle = (f"{legend.cls} de {ARCHETYPE_NAMES[legend.archetype].upper()}   "
                    f"FOR {legend.strength}  PROT {legend.protection}  EN {legend.energy}")
        return [Msg(f"{who} se transforma no legend do deck!", auto=0.5), Transform(f, color),
                CutIn(portrait, legend.name.upper(), subtitle, color, from_left=f.is_player),
                Msg(f"{legend.full_name.upper()}! {legend.short}", auto=None)]

    def become(self, f):
        """No auge do clarão: as regras viram as do legend e o desenho troca."""
        legend_id = self.legend_ids.get(f)
        legend = abilities.become(f.state, legend_id)
        if legend is None:
            return
        view, height = ("back", PLAYER_LEGEND_H) if f.is_player else ("front", ENEMY_LEGEND_H)
        f.set_sprite(sprites.legend_image(legend_id, view, height))
        f.owner = f.state.name                      # quem se transformou (aparece pequeno no painel)
        f.icon = sprites.legend_image(legend_id, "portrait", HUD_ICON)
        f.state.name = legend.name.upper()
        f.disp_hp = float(f.state.hp)

    # ------------------------------------------------------------ fila
    @property
    def busy(self):
        return self.current is not None or bool(self.steps)

    def run(self, *steps):
        self.steps.extend(steps)

    def run_now(self, steps):
        for step in reversed(steps):
            self.steps.appendleft(step)

    def add_float(self, text, pos, color):
        self.floats.append([text, pos[0], pos[1] - 24, 0.0, color])

    def impact(self, amount):
        """Tremor de tela e pausa proporcionais ao tamanho do golpe."""
        self.shake_power = min(6, 2 + amount // 3)
        self.shake_t = 0.22 + min(0.2, amount * 0.015)
        self.hitstop = HIT_STOP

    # ------------------------------------------------------------ turnos (regras em core/combat.py)
    def view(self, combatant):
        return self.player if combatant is self.player.state else self.enemy

    def other(self, f):
        return self.enemy if f is self.player else self.player

    def deal(self):
        self.player.state.refill_hand()
        self.enemy.state.refill_hand()
        return self.begin_turn(self.first())

    def begin_turn(self, f):
        events = start_turn(f.state)
        steps = []
        for event in events:
            steps += self.narrate(event)
        steps.append(Call(self.check_end))
        if any(isinstance(e, ev.TurnSkipped) for e in events):
            return [*steps, Call(lambda: self.finish_turn(f))]
        if f.is_player:
            return [*steps, Msg("Sua vez!", auto=0.4), Call(self.to_choose)]
        return [*steps, Call(self.enemy_act)]

    def finish_turn(self, f):
        """Fim do turno de `f`: veneno, completar a mão e passar a vez."""
        if self.over:
            return None
        steps = []
        for event in end_turn(f.state, self.other(f).state):
            steps += self.narrate(event)
        nxt = self.other(f)
        steps += [Call(self.check_end), Msg(f"Vez de {nxt.name}!", auto=0.45), Call(lambda: self.begin_turn(nxt))]
        return steps

    def to_choose(self):
        if self.over:
            return
        self.state = "choose"
        self.cursor = min(self.cursor, len(self.player.hand) + 1)

    def play_card(self, user, target, card, start, free=False):
        """Paga a carta agora; cada efeito é aplicado quando a animação dele chega.
        `free`: jogada de graça pela habilidade do Mimo (a carta não estava na mão)."""
        pay_card(user.state, card, free)
        steps = [Fly(card, start), Msg(f"{user.name} usou {card.name.upper()}!", auto=0.6)]
        if abilities.clone_blocks(target.state, card):     # Cold: o clone anula o golpe inteiro
            steps.append(Lunge(user))
            for event in abilities.block_with_clone(user.state, target.state):
                steps += self.narrate(event)
            return [*steps, Call(self.check_end)]
        for effect in card.effects:
            steps += self.effect_intro(effect, card, user, target)
            steps.append(Call(lambda effect=effect: self.resolve(effect, user, target)))
        steps.append(Call(self.check_end))
        return steps

    def effect_intro(self, effect, card, user, target):
        """Animação que antecede cada tipo de efeito."""
        if isinstance(effect, DamageEffect):
            return [Lunge(user), FX(card.fx, target.center)]
        if type(effect) in MARKER_EFFECT_FX and not card.damage:
            return [FX(MARKER_EFFECT_FX[type(effect)], target.center)]
        if isinstance(effect, DefenseEffect):
            return [FX("shield", user.center)]
        if isinstance(effect, AuraEffect):
            return [FX("aura", user.center)]
        if isinstance(effect, HealEffect):
            return [FX("heal", user.center)]
        if isinstance(effect, EnergyEffect) or (isinstance(effect, DrawEffect) and not card.energy):
            return [FX("energy", user.center)]
        return []

    def resolve(self, effect, user, target):
        steps = []
        for event in effect.apply(user.state, target.state):
            steps += self.narrate(event)
        return steps

    # ------------------------------------------------------------ narração dos eventos
    def narrate(self, event):
        """Transforma um evento das regras em animações e mensagens."""
        narrator = self.NARRATORS.get(type(event))
        if narrator is None:
            raise TypeError(f"evento sem narração: {event!r}")
        return narrator(self, event, self.view(event.who))

    def _on_damaged(self, event, f):
        steps = [Hit(f, f"-{event.amount}")] if event.amount else []
        if not event.amount:
            sfx.play("shield")
        steps.append(WaitBars())
        if event.blocked:
            steps.append(Msg(f"A proteção de {f.name} segurou {event.blocked} de dano!", auto=0.55))
        if event.strength and event.amount:
            steps.insert(0, FX("energy", f.center))
        if event.amount:
            burn = f" (+{event.burn_bonus} da queimadura)" if event.burn_bonus else ""
            steps.append(Msg(f"{f.name} sofreu {event.amount} de dano{burn}!", auto=0.55))
        return steps

    def _on_healed(self, event, f):
        if not event.amount:
            return [Msg(f"Os PV de {f.name} já estavam cheios!", auto=0.55)]
        self.add_float(f"+{event.amount}", f.center, GREEN)
        return [WaitBars(), Msg(f"{f.name} recuperou {event.amount} PV!", auto=0.55)]

    def _on_cards_drawn(self, event, f):
        if not event.amount:
            return []
        plural = "carta" if event.amount == 1 else "cartas"
        return [Msg(f"{f.name} comprou {event.amount} {plural}.", auto=0.45)]

    def _on_poison_tick(self, event, f):
        return [FX("poison", f.center), Hit(f, f"-{event.amount}"), WaitBars(),
                Msg(f"O veneno tirou {event.amount} PV de {f.name}!", auto=0.55)]

    def _on_frozen(self, event, f):
        sfx.play("freeze")
        return [FX("ice", f.center), Msg(f"{f.name} congelou! Vai perder o próximo turno.", auto=0.7)]

    def _on_ability_used(self, event, f):
        sfx.play("transform")
        return [FX("aura", f.center), Msg(f"{f.name} usou a habilidade!", auto=0.5)]

    def _on_ice_shattered(self, event, f):
        sfx.play("break")
        return [FX("break", f.center),
                Msg(f"O gelo de {f.name} quebrou! O golpe causou +{event.bonus} de dano e ele descongelou.",
                    auto=0.8)]

    NARRATORS: ClassVar[dict] = {
        ev.Damaged: _on_damaged,
        ev.AbilityUsed: _on_ability_used,
        ev.CardsDiscarded: _say("{f.name} descartou {e.amount} cartas.", 0.5),
        ev.CardsToBottom: _say("{f.name} colocou {e.amount} carta(s) no fundo do baralho.", 0.5),
        ev.IceShattered: _on_ice_shattered,
        ev.CloneBlocked: lambda self, e, f: [FX("ice", f.center),
                                             Msg(f"O clone de gelo de {f.name} anulou o ataque!", auto=0.7)],
        ev.Healed: _on_healed,
        ev.CardsDrawn: _on_cards_drawn,
        ev.PoisonTick: _on_poison_tick,
        ev.Frozen: _on_frozen,
        ev.ProtectionBroken: lambda self, e, f: [FX("break", f.center),
                                                 Msg(f"A {e.layer} de {f.name} foi anulada!", auto=0.55)],
        ev.DefenseGained: _say("{f.name} ganhou {e.amount} de defesa!"),
        ev.AuraGained: _say("{f.name} ganhou {e.amount} de aura!"),
        ev.Burned: _say("{f.name} está queimando! ({e.total} marcadores)"),
        ev.Chilled: _say("{f.name} ficou com {e.total}/" + str(ICE_LIMIT) + " marcadores de gelo."),
        ev.Poisoned: _say("{f.name} foi envenenado! ({e.total} marcadores)"),
        ev.Stunned: _say("{f.name} foi paralisado! Vai perder {e.total} de energia.", 0.6),
        ev.EnergyGained: _say("{f.name} ganhou {e.amount} de energia!"),
        ev.IceCloneReady: _say("Um clone de gelo protege {f.name} até o próximo turno!"),
        ev.IceCloneTriggered: lambda self, e, f: [FX("ice", f.center),
                                                  Msg(f"O clone de gelo congelou a energia de {f.name}!", auto=0.7)],
        ev.NextUtilityFree: _say("O próximo ataque de utilidade de {f.name} não tem custo!"),
        ev.StunTick: lambda self, e, f: [FX("stun", f.center),
                                         Msg(f"{f.name} está paralisado e perdeu {e.amount} de energia!", auto=0.6)],
        ev.TurnSkipped: lambda self, e, f: [FX("ice", f.center),
                                            Msg(f"{f.name} está congelado e perdeu o turno!", auto=0.7)],
    }

    # ------------------------------------------------------------ fim do duelo
    def check_end(self):
        if self.over:
            return None
        dead = loser(self.player.state, self.enemy.state)
        if dead is None:
            return None
        down = self.view(dead)
        won = down is self.enemy
        self.over = True
        self.state = "done"
        self.steps.clear()
        steps = [Faint(down), Call(lambda: self.finish(won)), Msg(f"{down.name} foi derrotado!", auto=None)]
        if "lose" in self.spec:
            line = self.spec["lose"] if won else self.spec["win"]
            steps.append(Msg(f"{self.spec['name']}: {line}", auto=None))
        steps.append(Msg("Você venceu o duelo!" if won else "Você perdeu o duelo...", auto=None))
        steps.append(Call(self.prize_messages))
        steps.append(Call(lambda: self.leave(won)))
        return steps

    def finish(self, won):
        ch = self.game.character
        sfx.music(None)
        sfx.play("win" if won else "lose")
        if won:
            ch.wins += 1
            first = self.spec["kind"] == "trainer" and self.spec["id"] not in ch.beaten
            if first:
                self.spec["first"] = True
                ch.beaten.append(self.spec["id"])
            bets, xp = rewards(self.spec, ch.level, first, self.rng)
            ch.bets += bets
            self.prize = (bets, xp, ch.gain_xp(xp))
        else:
            ch.losses += 1
        ch.save()

    def prize_messages(self):
        if not self.prize:
            return None
        bets, xp, ups = self.prize
        bonus = " (XP em dobro!)" if self.spec.get("xp_mult", 1) > 1 else ""
        steps = [Msg(f"Você ganhou {bets} BETS e {xp} de XP{bonus}!", auto=None)]
        if ups:
            ch = self.game.character
            steps.append(Call(lambda: sfx.play("levelup")))
            steps.append(Msg(f"Você subiu para o nível {ch.level}!", auto=None))
        return steps

    def leave(self, won):
        self.game.transition_to(lambda: self.on_end(won, self.spec))

    # ------------------------------------------------------------ turno do jogador
    def end_player_turn(self):
        self.sent({"end": True})
        self.state = "enemy"
        self.run(Call(lambda: self.finish_turn(self.player)))

    @property
    def ability_slot(self):
        """Posição do botão HABILIDADE no cursor (depois das cartas); FIM DO TURNO vem logo depois."""
        return len(self.player.hand)

    @property
    def end_slot(self):
        return len(self.player.hand) + 1

    def handle(self, event):
        if self.dialog.active:
            self.dialog.handle(event)
            return
        if event.type != pygame.KEYDOWN or self.busy:
            return
        handler = {"choose": self.handle_choose, "discard": self.handle_discard, "mimo": self.handle_mimo}
        if self.state in handler:
            handler[self.state](event.key)

    def handle_choose(self, key):
        n = len(self.player.hand)
        if key in LEFT_KEYS or key in RIGHT_KEYS:
            self.cursor = (self.cursor + (1 if key in RIGHT_KEYS else -1)) % (n + 2)
            sfx.play("cursor")
        elif key in DOWN_KEYS or key in CANCEL_KEYS:
            if self.cursor < n:
                self.cursor = self.end_slot
                sfx.play("cursor")
        elif key in UP_KEYS:
            if self.cursor >= n and n:
                self.cursor = n - 1
                sfx.play("cursor")
        elif key in CONFIRM_KEYS:
            self.confirm_choice()

    def confirm_choice(self):
        hand = self.player.hand
        if self.cursor == self.end_slot:
            sfx.play("confirm")
            self.end_player_turn()
            return
        if self.cursor == self.ability_slot:
            self.use_ability()
            return
        card = hand[self.cursor]
        if not self.player.state.can_play(card):
            sfx.play("error")
            self.run(Msg("Energia insuficiente para essa carta!", auto=0.8))
            return
        self.sent({"card": self.cursor})
        self.state = "busy"
        self.run(*self.play_card(self.player, self.enemy, card, self.card_pos(self.cursor)), Call(self.to_choose))

    # ------------------------------------------------------------ habilidade do seu legend
    def use_ability(self):
        me = self.player.state
        legend = me.legend
        if legend is None:
            return
        if not legend.active:
            sfx.play("error")
            self.run(Msg(f"A habilidade de {legend.name} é passiva: ela funciona sozinha.", auto=0.9))
        elif not abilities.can_use(me):
            sfx.play("error")
            reason = ("Você já usou a habilidade neste turno." if me.ability_used
                      else f"Você precisa de {abilities.DROGOZ_DISCARD} cartas na mão.")
            self.run(Msg(reason, auto=0.9))
        elif legend.id == "drogoz":
            sfx.play("confirm")
            self.state, self.picked, self.cursor = "discard", [], 0
        elif legend.id == "mimo":
            sfx.play("reveal")
            self.revealed = abilities.mimo_reveal(me)
            playable = [c for c in self.revealed if abilities.mimo_can_play(c)]
            self.option = self.revealed.index(playable[0]) if playable else len(self.revealed)
            self.state = "mimo"

    def handle_discard(self, key):
        """Drogoz: marque 3 cartas da mão (A marca/desmarca); com 3 marcadas, elas são descartadas."""
        hand = self.player.hand
        if key in LEFT_KEYS or key in RIGHT_KEYS:
            self.cursor = (self.cursor + (1 if key in RIGHT_KEYS else -1)) % len(hand)
            sfx.play("cursor")
        elif key in CANCEL_KEYS:
            sfx.play("cancel")
            self.state, self.cursor = "choose", self.ability_slot
        elif key in CONFIRM_KEYS:
            if self.cursor in self.picked:
                self.picked.remove(self.cursor)
            else:
                self.picked.append(self.cursor)
            sfx.play("card")
            if len(self.picked) == abilities.DROGOZ_DISCARD:
                self.sent({"drogoz": list(self.picked)})
                events = abilities.drogoz(self.player.state, [hand[i] for i in self.picked])
                self.state, self.picked = "busy", []
                steps = [FX("flame", self.player.center)]
                for event in events:
                    steps += self.narrate(event)
                self.run(*steps, Call(self.to_choose))

    def handle_mimo(self, key):
        """Mimo: escolha uma das cartas reveladas (só VENENO/NINJA) ou "não jogar"."""
        count = len(self.revealed) + 1
        if key in LEFT_KEYS or key in RIGHT_KEYS:
            self.option = (self.option + (1 if key in RIGHT_KEYS else -1)) % count
            sfx.play("cursor")
        elif key in CONFIRM_KEYS:
            chosen = self.revealed[self.option] if self.option < len(self.revealed) else None
            if chosen is not None and not abilities.mimo_can_play(chosen):
                sfx.play("error")
                self.run(Msg("O Mimo só joga de graça cartas de VENENO ou NINJA.", auto=0.8))
                return
            self.sent({"mimo": None if chosen is None else self.option})
            self.state = "busy"
            self.run(*self.mimo_steps(self.player, self.enemy, chosen), Call(self.to_choose))

    def mimo_steps(self, user, target, chosen):
        """Resolve a escolha do Mimo: as outras cartas vão para o fundo; a escolhida é jogada de graça."""
        steps = [Msg(f"{user.name} revelou {' e '.join(c.name.upper() for c in self.revealed)}!", auto=0.7)]
        for event in abilities.mimo_finish(user.state, self.revealed, chosen):
            steps += self.narrate(event)
        if chosen is not None:
            steps += self.play_card(user, target, chosen, (GAME_W // 2, 80), free=True)
        self.revealed = []
        return steps

    # ------------------------------------------------------------ IA do oponente
    def enemy_act(self):
        if self.over:
            return None
        e = self.enemy
        me, foe = e.state, self.player.state
        legend_id = abilities.legend_id(me)
        if legend_id == "mimo" and abilities.can_use(me):          # o Mimo usa a habilidade no começo
            self.revealed = abilities.mimo_reveal(me)
            chosen = mimo_pick(self.revealed, me, foe)
            return [Wait(0.3), Call(lambda: self.narrate(ev.AbilityUsed(me))),
                    *self.mimo_steps(e, self.player, chosen), Call(self.enemy_act)]
        card = choose_card(me, foe, self.spec.get("ai", "normal"), self.rng)
        if card is None:
            discards = drogoz_discards(me) if legend_id == "drogoz" else None
            if discards:                                           # o Drogoz cura no fim do turno
                steps = [FX("flame", e.center)]
                for event in abilities.drogoz(me, discards):
                    steps += self.narrate(event)
                return [*steps, Call(self.enemy_act)]
            return [Msg(f"{e.name} encerrou o turno.", auto=0.5), Call(lambda: self.finish_turn(e))]
        start = e.center
        return [Wait(0.3), *self.play_card(e, self.player, card, start), Call(self.enemy_act)]

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        self.shake_t = max(0.0, self.shake_t - dt)
        if self.hitstop > 0:          # tudo congela por um instante no acerto
            self.hitstop -= dt
            return
        self.dialog.update(dt)
        for f in self.fighters:
            if f.disp_hp > f.hp:
                f.disp_hp = max(float(f.hp), f.disp_hp - dt * 18)
            elif f.disp_hp < f.hp:
                f.disp_hp = min(float(f.hp), f.disp_hp + dt * 18)
        for fl in self.floats:
            fl[3] += dt
        self.floats = [fl for fl in self.floats if fl[3] < 0.9]
        while True:
            if self.current is None:
                if not self.steps:
                    break
                self.current = self.steps.popleft()
                self.current.start(self)
            if self.current.update(dt):
                self.current = None
                dt = 0.0
                continue
            break

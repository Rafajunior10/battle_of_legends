"""Duelo online contra outro jogador (PvP). É a batalha normal (battle.py) com duas diferenças:

- No lugar da IA, o oponente é o outro computador: cada jogada dele chega pela rede ("duel") e entra numa
  fila; quando a tela está livre, a jogada é aplicada nas mesmas regras (game/core).
- Cada jogada sua é enviada para ele (gancho `sent`). Os baralhos usam a mesma semente nos dois PCs
  (core/duel.py), então os dois veem as mesmas cartas saindo.
Duelo não dá BETS nem XP (só conta vitória/derrota): assim ninguém "farma" jogando contra um amigo.
"""
from collections import deque

import pygame

from game.core import abilities, hunger
from game.core import duel as duel_rules
from game.core import events as ev
from game.engine import sfx
from game.engine.ui import draw_text
from game.scenes.battle import BattleScene
from game.scenes.battle_fx import Call, Msg, Wait
from game.scenes.battle_hud import INFO_PANEL


class DuelScene(BattleScene):
    def __init__(self, game, spec, on_end, seed, side):
        self.seed, self.side = seed, side
        self.actions = deque()          # jogadas do oponente esperando a vez delas
        super().__init__(game, spec, on_end)

    # ------------------------------------------------------------ ganchos da batalha
    def deck_rngs(self):
        return duel_rules.deck_rngs(self.seed, self.side)

    def first(self):
        return self.player if self.side == duel_rules.CHALLENGER else self.enemy

    def take_snacks(self):
        """No duelo online o lanche não vale (e não é gasto): os dois PCs precisam começar iguaizinhos."""
        return {}

    def sent(self, action):
        if self.game.net:
            self.game.net.send({"t": "duel", "action": action})

    def enemy_act(self):
        """Vez do oponente: espera a próxima jogada dele chegar pela rede."""
        if not self.over:
            self.state = "remote"

    # ------------------------------------------------------------ rede
    def read_net(self):
        net = self.game.net
        if net is None:
            return
        for message in net.poll():
            kind = message["t"]
            if kind == "duel":
                self.actions.append(message.get("action") or {})
            elif kind == "duel_end":
                self.walkover(f"{self.enemy.name} saiu do duelo. Vitória por W.O.!")
            else:
                if kind == "disconnected":
                    self.walkover("A conexão caiu. O duelo foi cancelado.", won=None)
                lobby = self.game.lobby
                if lobby is not None:
                    lobby.on_net_message(message)        # quem entrou/saiu/andou continua valendo

    def walkover(self, text, won=True):
        """O duelo acaba sem terminar: o oponente saiu (você vence) ou a conexão caiu (won=None)."""
        if self.over:
            return
        self.over, self.state = True, "done"
        self.steps.clear()
        self.current = None
        steps = [Msg(text, auto=None)]
        if won:
            steps.insert(0, Call(lambda: self.finish(True)))
        self.run(*steps, Call(lambda: self.leave(bool(won))))

    def apply_remote(self, action):
        """Aplica uma jogada do oponente. Jogada inválida (não deveria acontecer) é ignorada."""
        try:
            steps = self.remote_steps(action)
        except (ValueError, IndexError, TypeError, KeyError):
            steps = None
        if steps is None:
            self.state = "remote"
            return
        self.state = "busy"
        self.run(*steps)

    def remote_steps(self, action):
        e = self.enemy
        me = e.state
        if action.get("forfeit"):
            self.walkover(f"{e.name} desistiu do duelo. Vitória por W.O.!")
            return []
        if action.get("end"):
            return [Msg(f"{e.name} encerrou o turno.", auto=0.5), Call(lambda: self.finish_turn(e))]
        if "card" in action:
            card = me.hand[int(action["card"])]
            if not me.can_play(card):
                return None
            return [Wait(0.2), *self.play_card(e, self.player, card, e.center), Call(self.enemy_act)]
        if "drogoz" in action:
            picked = [int(i) for i in action["drogoz"]]
            if len(set(picked)) != len(picked):
                return None
            steps = []
            for event in abilities.drogoz(me, [me.hand[i] for i in picked]):
                steps += self.narrate(event)
            return [*steps, Call(self.enemy_act)]
        if "mimo" in action:
            self.revealed = abilities.mimo_reveal(me)
            index = action["mimo"]
            chosen = None if index is None else self.revealed[int(index)]
            return [Call(lambda: self.narrate(ev.AbilityUsed(me))), *self.mimo_steps(e, self.player, chosen),
                    Call(self.enemy_act)]
        return None

    # ------------------------------------------------------------ fim
    def finish(self, won):
        ch = self.game.character
        sfx.music(None)
        sfx.play("win" if won else "lose")
        if won:
            ch.wins += 1
        else:
            ch.losses += 1
        hunger.after_battle(ch)
        ch.save()
        if self.game.net:
            self.game.net.send({"t": "duel_over"})

    def update(self, dt):
        self.read_net()
        if self.state == "remote" and self.actions and not self.busy and not self.dialog.active:
            self.apply_remote(self.actions.popleft())
        super().update(dt)

    def draw_info_panel(self, surf, choosing):
        """Na vez do oponente, o painel da direita mostra que o jogo está esperando a jogada dele."""
        if self.state != "remote" or choosing:
            super().draw_info_panel(surf, choosing)
            return
        info = INFO_PANEL
        pygame.draw.rect(surf, (232, 232, 224), info, border_radius=3)
        dots = "." * (1 + int(self.time * 2) % 3)
        draw_text(surf, f"Vez de {self.enemy.name}", (info.centerx, info.y + 14), size=12, align="center")
        draw_text(surf, f"esperando a jogada{dots}", (info.centerx, info.y + 30), size=12, align="center",
                  color=(72, 72, 80))

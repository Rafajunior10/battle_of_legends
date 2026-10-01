"""Duelo online (PvP): os dois computadores precisam ver exatamente o mesmo duelo.

Aqui os dois "PCs" rodam no mesmo processo: duas cenas de duelo ligadas por um cabo de mentira (FakeLink),
que entrega as jogadas de uma para a outra como o servidor faria.
"""
import random

import pygame
import pytest

from game.core import abilities
from game.core.duel import CHALLENGED, CHALLENGER, deck_rngs, duel_spec, fighter
from game.data.cards import make_deck
from game.data.character import Character
from game.engine.app import Game
from game.scenes.base import Scene
from game.scenes.duel import DuelScene

POISON_DECK = make_deck(choque_do_trovao=3, zeus_luz=3, chicote_de_raios=3, tela_de_luz=2, amansa_loko=3,
                        murrao=3, golpe_perfurante=3)


class FakeLink:
    """Uma ponta do cabo: o que uma cena manda chega na outra (só as mensagens do duelo, como no servidor)."""

    def __init__(self):
        self.inbox, self.other, self.over = [], None, False

    def send(self, message):
        if message["t"] == "duel":
            self.other.inbox.append(message)
        elif message["t"] == "duel_over":
            self.over = True

    def poll(self):
        messages, self.inbox = self.inbox, []
        return messages


def make_side(name, legend, side, foe, seed, link):
    game = Game()
    game.net = link
    ch = Character(name=name)
    ch.decks[0] = list(POISON_DECK)
    ch.deck_legends[0] = legend
    game.character = ch
    results = []

    def on_end(won, spec):                          # o lobby faria isto: anota o resultado e volta
        results.append(won)
        return Scene(game)
    scene = DuelScene(game, duel_spec(fighter(foe), side), on_end, seed, side)
    game.change_scene(scene)
    return game, scene, results


def autoplay(scene, rng):
    """Joga sozinho: às vezes usa a habilidade do legend, senão a primeira carta que der, senão passa a vez."""
    def press(key):
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=key))
    if scene.dialog.active:
        press(pygame.K_z)
    elif scene.busy:
        return
    elif scene.state == "choose":
        me = scene.player.state
        playable = [i for i, c in enumerate(me.hand) if me.can_play(c)]
        if abilities.can_use(me) and rng.random() < 0.5:
            scene.cursor = scene.ability_slot
        else:
            scene.cursor = playable[0] if playable else scene.end_slot
        press(pygame.K_z)
    elif scene.state == "discard":                  # Drogoz: marca 3 cartas seguidas
        scene.cursor = len(scene.picked)
        press(pygame.K_z)
    elif scene.state == "mimo":
        press(pygame.K_z)


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_os_dois_pcs_veem_o_mesmo_duelo(save_path, seed):
    ana_ch, beto_ch = Character(name="Ana"), Character(name="Beto")
    for ch, legend in ((ana_ch, "drogoz"), (beto_ch, "mimo")):
        ch.decks[0] = list(POISON_DECK)
        ch.deck_legends[0] = legend
    link_a, link_b = FakeLink(), FakeLink()
    link_a.other, link_b.other = link_b, link_a
    game_a, ana, won_a = make_side("Ana", "drogoz", CHALLENGER, beto_ch, seed, link_a)
    game_b, beto, won_b = make_side("Beto", "mimo", CHALLENGED, ana_ch, seed, link_b)
    rng = random.Random(seed)
    for frame in range(60_000):
        for game, scene in ((game_a, ana), (game_b, beto)):
            autoplay(scene, rng)
            scene.update(1 / 30)
            if frame % 500 == 0:
                scene.draw(game.screen)
            if game.transition:                           # a troca de tela chama o fim do duelo
                game.transition.update(1 / 30)
        if won_a and won_b:
            break
    assert ana.over and beto.over, "o duelo não terminou"
    # o que um vê de si mesmo é o que o outro vê dele
    assert (ana.player.hp, ana.enemy.hp) == (beto.enemy.hp, beto.player.hp)
    assert [c.id for c in ana.player.hand] == [c.id for c in beto.enemy.hand]
    assert [c.id for c in ana.enemy.deck.draw_pile] == [c.id for c in beto.player.deck.draw_pile]
    assert won_a and won_b and won_a[0] != won_b[0]          # um venceu, o outro perdeu
    assert link_a.over and link_b.over                        # os dois avisaram o servidor
    assert game_a.character.wins + game_b.character.wins == 1


def test_baralhos_embaralham_igual_nos_dois_pcs():
    mine_0, theirs_0 = deck_rngs(99, CHALLENGER)
    mine_1, theirs_1 = deck_rngs(99, CHALLENGED)
    assert mine_0.random() == theirs_1.random()             # o meu baralho no meu PC = o meu no PC dele
    assert theirs_0.random() == mine_1.random()


def test_ficha_do_oponente_que_veio_pela_rede_e_conferida():
    spec = duel_spec({"name": "x" * 40, "deck": ["murrao", "carta_que_nao_existe"], "legend": "hacker",
                      "level": -3, "hp": 0, "look": {"hair": "inexistente", "lixo": 1}})
    assert spec["deck"] == ["murrao"] and spec["legend"] is None
    assert len(spec["name"]) == 12 and spec["level"] == 1 and spec["hp"] == 1
    with pytest.raises(ValueError):
        duel_spec({"deck": []})


def test_oponente_que_desiste_da_vitoria_por_wo(save_path):
    link = FakeLink()
    link.other = FakeLink()
    game, scene, _ = make_side("Ana", "drogoz", CHALLENGED, Character(name="Beto"), 5, link)
    link.inbox.append({"t": "duel", "action": {"forfeit": True}})
    link.inbox.append({"t": "duel", "action": {"card": 999}})   # jogada inválida é ignorada
    for _ in range(3000):
        if scene.dialog.active:
            scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
        scene.update(1 / 30)
        if game.transition:
            break
    assert scene.over and game.character.wins == 1

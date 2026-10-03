"""Fome: cai com o tempo e com as batalhas, comer recupera, e com fome demais não dá para duelar."""
import pygame
import pytest

from game.core import hunger
from game.data.character import Character
from game.data.opponents import random_wild
from game.engine.app import Game
from game.scenes.battle import BattleScene
from game.scenes.lobby import LobbyScene


@pytest.fixture
def game(save_path):
    g = Game()
    g.character = Character(name="Ana")
    g.character.save()
    return g


@pytest.fixture
def lobby(game):
    scene = LobbyScene(game)
    game.lobby = scene
    game.change_scene(scene)
    return scene


def test_fome_cai_com_o_tempo(hero):
    clock = hunger.tick(hero, 0.0, hunger.DECAY_SECONDS * 3 + 5)
    assert hero.hunger == 97 and clock == pytest.approx(5)
    hero.hunger = 0
    hunger.tick(hero, 0.0, 999)
    assert hero.hunger == 0                                   # não fica negativa


def test_limites_para_comer_e_duelar(hero):
    hero.hunger = hunger.FULL
    assert not hunger.can_eat(hero) and hunger.can_duel(hero)
    hero.hunger = hunger.WEAK - 1
    assert hunger.can_eat(hero) and not hunger.can_duel(hero)
    assert hunger.eat(hero, 500) == 100 - (hunger.WEAK - 1) and hero.hunger == 100
    assert hunger.label(hero) == "Satisfeito"


def test_fome_antiga_ou_estragada_no_save():
    assert Character.from_dict({"name": "Velho"}).hunger == 100       # save de antes da fome: de barriga cheia
    assert Character.from_dict({"name": "X", "hunger": -30}).hunger == 0


def test_batalha_gasta_fome(game):
    scene = BattleScene(game, random_wild(1), lambda won, spec: None)
    scene.finish(True)
    assert game.character.hunger == 100 - hunger.BATTLE_COST


def test_com_fome_demais_nao_desafia_ninguem(game, lobby):
    game.character.hunger = hunger.WEAK - 1
    started = []
    game.start_battle = lambda spec, on_end: started.append(spec)
    lobby.challenge("tico")
    lobby.start_tournament()
    assert started == [] and lobby.prompt.visible and lobby.tournament is None
    game.character.hunger = 80
    lobby.challenge("tico")
    assert len(started) == 1


def test_fraco_de_fome_as_gosmas_nao_aparecem(game, lobby, monkeypatch):
    game.character.hunger = 0
    monkeypatch.setattr("game.scenes.lobby.random.random", lambda: 0.0)   # toda chance viraria batalha
    started = []
    game.start_battle = lambda spec, on_end: started.append(spec)
    grass = next((x, y) for y, row in enumerate(lobby.map) for x, t in enumerate(row) if t == ",")
    lobby.player.place(*grass)
    lobby.steps_since_battle = 99
    lobby.on_step_done()
    assert started == []


def test_barra_de_fome_e_ficha(game, lobby):
    for value in (100, 50, 5):
        game.character.hunger = value
        lobby.draw(game.screen)
    lobby.showing_profile = True
    lobby.draw(game.screen)                                   # ficha com a linha FOME
    run_time = hunger.DECAY_SECONDS + 1
    lobby.showing_profile = False
    game.character.hunger = 60
    for _ in range(int(run_time * 10)):
        lobby.update(0.1)
    assert game.character.hunger == 59                        # andando pelo mundo a fome cai
    pygame.event.clear()

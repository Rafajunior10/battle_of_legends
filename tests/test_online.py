"""Mundo compartilhado de ponta a ponta: a tela ONLINE abre o mundo, um amigo (cliente de verdade) entra, e os
dois se veem andar, falar e entrar em batalha."""
import time

import pygame
import pytest

from game.data.character import Character
from game.engine.app import Game
from game.net.client import WorldClient
from game.net.server import WorldServer
from game.scenes.lobby import LobbyScene
from game.scenes.online import OnlineScene


@pytest.fixture
def game(save_path):
    g = Game()
    Character(name="Ana").save()
    yield g
    g.leave_online()


def friend_hello(x, y):
    return {"name": "BETO", "look": {"hair": "chanel", "gender": "Feminino"}, "map": "vila", "x": x, "y": y,
            "facing": "down"}


def run_lobby(lobby, seconds=0.5):
    for _ in range(int(seconds * 60)):
        lobby.update(1 / 60)
        time.sleep(0.002)               # dá tempo para a thread da rede entregar as mensagens


def wait_for(client, kind, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        for message in client.poll():
            if message["t"] == kind:
                return message
        time.sleep(0.01)
    raise AssertionError(f"não chegou '{kind}'")


def host_world(game, monkeypatch):
    """Hospeda pela tela ONLINE (numa porta livre) e entra no mundo."""
    monkeypatch.setattr("game.scenes.online.PORT", 0)
    scene = OnlineScene(game)
    game.change_scene(scene)
    scene.host()
    assert scene.mode == "hosted", scene.error
    scene.draw(game.screen)                                   # a tela com os endereços desenha
    scene.enter_world()
    lobby = game.lobby
    assert isinstance(lobby, LobbyScene) and lobby.net is game.net
    return lobby


def test_hospedar_e_o_amigo_aparece_andando(game, monkeypatch):
    lobby = host_world(game, monkeypatch)
    me = lobby.player
    friend = WorldClient()
    others = friend.connect("127.0.0.1", game.net.server.port, friend_hello(me.tx + 2, me.ty))
    assert [p["name"] for p in others] == ["ANA"]             # o amigo já me vê ao entrar
    run_lobby(lobby)
    remote = next(iter(lobby.remotes.values()))
    assert remote.name == "BETO" and "BETO" in lobby.notice
    friend.send({"t": "move", "map": "vila", "x": me.tx + 3, "y": me.ty, "facing": "right", "run": False})
    run_lobby(lobby)
    assert (remote.tx, remote.ty, remote.facing) == (me.tx + 3, me.ty, "right")
    friend.send({"t": "emote", "text": "Oi!"})
    friend.send({"t": "status", "battle": True})
    run_lobby(lobby, 0.2)
    assert remote.emote == "Oi!" and remote.battle
    lobby.draw(game.screen)                                   # nome, espada e balão desenham sem quebrar
    friend.close()
    run_lobby(lobby)
    assert not lobby.remotes                                   # saiu do mundo


def test_meus_passos_chegam_no_amigo(game, monkeypatch):
    lobby = host_world(game, monkeypatch)
    friend = WorldClient()
    friend.connect("127.0.0.1", game.net.server.port, friend_hello(1, 1))
    lobby.player.facing = "up"
    lobby.send_position()
    move = wait_for(friend, "move")
    assert (move["map"], move["x"], move["y"], move["facing"]) == ("vila", lobby.player.tx, lobby.player.ty, "up")
    lobby.talk_to_player(type("R", (), {"name": "BETO"})())    # fala rápida: escolhe a primeira
    lobby.prompt.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    for _ in range(300):                                       # avança o texto até a escolha aparecer
        if lobby.prompt.choosing:
            break
        lobby.prompt.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
        lobby.update(1 / 30)
    lobby.prompt.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    assert wait_for(friend, "emote")["text"] == "Oi!"
    game.start_battle({"name": "X"}, lambda won, spec: lobby)  # entrar em batalha avisa os outros
    assert wait_for(friend, "status")["battle"] is True
    friend.close()


def test_se_o_mundo_fechar_o_jogo_continua_sozinho(game, save_path):
    server = WorldServer(host="127.0.0.1", port=0)
    server.start()
    game.net = WorldClient()
    game.net.initial_players = game.net.connect("127.0.0.1", server.port, friend_hello(3, 3))
    game.character = Character.load()
    lobby = LobbyScene(game)
    server.stop()
    run_lobby(lobby)
    assert lobby.net is None and game.net is None
    assert lobby.prompt.visible                                # avisou que a conexão caiu


def test_entrar_sem_ninguem_hospedando_mostra_o_motivo(game, monkeypatch):
    scene = OnlineScene(game)
    scene.address = "127.0.0.1:1"
    scene.join()
    assert scene.client is None and "Não achei ninguém" in scene.error
    scene.draw(game.screen)

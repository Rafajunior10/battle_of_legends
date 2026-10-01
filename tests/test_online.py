"""Mundo compartilhado de ponta a ponta: a tela JOGAR abre o mundo, faz login, um amigo (cliente de verdade)
entra, e os dois se veem andar, falar e entrar em batalha."""
import time

import pygame
import pytest

from game.data import character as character_module
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


def friend_joins(port, x=1, y=1):
    """O amigo conecta, cria a conta dele e entra no mundo. Devolve o cliente e quem já estava lá."""
    friend = WorldClient()
    friend.open("127.0.0.1", port)
    friend.authenticate("beto", "1234", register=True)
    return friend, friend.enter(friend_hello(x, y))


def press(scene, key):
    scene.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def answer_prompt(scene, yes=True):
    """Avança o texto do Prompt até a pergunta SIM/NÃO e responde."""
    for _ in range(300):
        if scene.prompt.choosing:
            break
        press(scene, pygame.K_z)
        scene.update(1 / 30)
    if not yes:
        press(scene, pygame.K_DOWN)
    press(scene, pygame.K_z)


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


def open_world(game, monkeypatch, tmp_path):
    """Hospeda pela tela JOGAR (numa porta livre, com o banco numa pasta temporária)."""
    monkeypatch.setattr("game.scenes.online.PORT", 0)
    monkeypatch.setattr("game.scenes.online.WORLD_DB", str(tmp_path / "world.db"))
    scene = OnlineScene(game)
    game.change_scene(scene)
    scene.host()
    assert scene.mode == "login", scene.error
    scene.draw(game.screen)                                   # a tela de login com os endereços desenha
    return scene


def host_world(game, monkeypatch, tmp_path):
    """Hospeda, cria a conta, importa o save deste PC e entra no mundo."""
    scene = open_world(game, monkeypatch, tmp_path)
    scene.user, scene.password = "ana", "1234"
    scene.login(register=True)
    answer_prompt(scene, yes=True)                            # importar o personagem salvo neste PC
    lobby = game.lobby
    assert isinstance(lobby, LobbyScene) and lobby.net is game.net
    return lobby


def test_hospedar_e_o_amigo_aparece_andando(game, monkeypatch, tmp_path):
    lobby = host_world(game, monkeypatch, tmp_path)
    me = lobby.player
    friend, others = friend_joins(game.net.server.port, me.tx + 2, me.ty)
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


def test_meus_passos_chegam_no_amigo(game, monkeypatch, tmp_path):
    lobby = host_world(game, monkeypatch, tmp_path)
    friend, _ = friend_joins(game.net.server.port)
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
    game.net.open("127.0.0.1", server.port)
    game.net.authenticate("ana", "1234", register=True)
    game.net.enter(friend_hello(3, 3))
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


def test_o_personagem_fica_salvo_no_servidor(game, monkeypatch, tmp_path):
    lobby = host_world(game, monkeypatch, tmp_path)
    assert character_module.remote_save is not None           # online, salvar vai para o servidor
    game.character.bets += 50
    game.character.coliseum_wins = 2
    game.character.save()
    time.sleep(0.2)
    server = game.net.server
    account = server.db.login("ana", "1234")
    saved = server.db.load_character(account)
    assert saved["name"] == "Ana" and saved["coliseum_wins"] == 2
    assert saved["bets"] == game.character.bets
    lobby.draw(game.screen)


def test_login_errado_mostra_o_motivo_e_deixa_tentar(game, monkeypatch, tmp_path):
    scene = open_world(game, monkeypatch, tmp_path)
    scene.user, scene.password = "ana", "1234"
    scene.login(register=False)                                # conta ainda não existe
    assert scene.mode == "login" and "incorretos" in scene.error
    scene.draw(game.screen)
    scene.login(register=True)
    answer_prompt(scene, yes=False)                            # não importa: vai criar um personagem novo
    assert game.net is scene.client


def test_digitar_usuario_e_senha(game, monkeypatch, tmp_path):
    scene = open_world(game, monkeypatch, tmp_path)
    scene.user = ""
    scene.handle(pygame.event.Event(pygame.TEXTINPUT, text="Ana Z!"))
    assert scene.user == "anaz"                                 # só minúsculas, números e . - _
    press(scene, pygame.K_RETURN)                               # ENTER passa para a senha
    scene.handle(pygame.event.Event(pygame.TEXTINPUT, text="S3nha!"))
    press(scene, pygame.K_BACKSPACE)
    assert scene.password == "S3nha"
    scene.draw(game.screen)                                     # a senha aparece como *****
    press(scene, pygame.K_ESCAPE)
    assert scene.mode == "menu" and scene.client is None

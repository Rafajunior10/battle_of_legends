"""Dia e noite, dormir para a noite passar (sozinho ou com todos online), pescaria, a vila maior e os balões
dos NPCs que só aparecem de perto."""
import random
import time

import pygame
import pytest

from game.core import clock as clock_rules
from game.core import fishing
from game.core.clock import WorldClock
from game.core.townsfolk import NpcWorld
from game.data.character import Character
from game.data.world import MAPS, PIER_X, VILA
from game.engine.app import Game
from game.net.client import WorldClient
from game.net.database import Database
from game.net.server import WorldServer
from game.scenes.home import SLEEP_TIME
from game.scenes.lobby import LobbyScene


@pytest.fixture
def game(save_path):
    g = Game()
    g.character = Character(name="Juninho", spouse="rebeca")
    g.character.save()
    return g


@pytest.fixture
def lobby(game):
    scene = LobbyScene(game)
    game.lobby = scene
    game.change_scene(scene)
    return scene


def run(lobby, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        lobby.update(dt)


def dialog(lobby):
    return " ".join(" ".join(page) for page in lobby.prompt.dialog.pages)


def lie_in_suite(lobby):
    lobby.load_map("casa_superior", (13, 13), "up")
    lobby.player.place(6, 5)
    lobby.player.facing = "right"
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))


# ------------------------------------------------------------ relógio
def test_manha_tarde_noite_e_os_dias_passando():
    c = WorldClock(11 * 60 + 59, 1)
    assert c.phase == "MANHÃ"
    c.advance(1)
    assert c.phase == "TARDE" and c.label() == "DIA 1  12:00"
    c.advance(6 * 60)
    assert c.is_night
    c.advance(6 * 60)                                         # passou da meia-noite
    assert c.day == 2 and c.is_night
    c.advance(5 * 60)
    assert c.phase == "MANHÃ"


def test_dormir_pula_para_as_6_da_manha():
    c = WorldClock(22 * 60, 3)
    c.sleep_until_morning()
    assert (c.day, c.minutes) == (4, 360)
    c = WorldClock(3 * 60, 4)                                 # de madrugada: acorda no mesmo dia
    c.sleep_until_morning()
    assert (c.day, c.minutes) == (4, 360)


def test_cor_da_tela_e_postes():
    assert clock_rules.tint(12 * 60)[1] == 0                 # meio-dia: sem camada
    color, alpha = clock_rules.tint(23 * 60)
    assert alpha >= 140 and color == clock_rules.NIGHT_BLUE
    assert 0 < clock_rules.tint(17 * 60)[1] < 140            # fim de tarde dourado
    assert clock_rules.lights_on(20 * 60) and not clock_rules.lights_on(12 * 60)


def test_hora_vai_no_save_e_save_antigo_comeca_de_manha():
    ch = Character.from_dict({"name": "Velho"})
    assert (ch.world_day, ch.world_minutes) == (1, clock_rules.START)
    assert WorldClock.from_dict({"minutes": "lixo"}).minutes == clock_rules.START


# ------------------------------------------------------------ dormir (sozinho)
def test_de_noite_deitar_e_dormir_e_a_noite_passa(game, lobby):
    lobby.clock = WorldClock(22 * 60, 5)
    lie_in_suite(lobby)
    assert lobby.sleep_t is not None and lobby.sleep_skip     # sozinho: dorme na hora
    lobby.draw(game.screen)
    run(lobby, SLEEP_TIME + 0.3)
    assert (lobby.clock.day, int(lobby.clock.minutes)) == (6, 360)
    assert "Bom dia! DIA 6  06:00" in dialog(lobby)
    saved = Character.load()
    assert (saved.world_day, int(saved.world_minutes)) == (6, 360)


def test_de_dia_deitar_nao_pula_a_noite(game, lobby):
    lobby.clock = WorldClock(10 * 60, 2)
    lie_in_suite(lobby)
    assert lobby.sleep_t is None and lobby.player.pose == "lie"
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))     # A: "Cochilar?"
    for _ in range(300):
        if lobby.prompt.choosing:
            break
        lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
        lobby.update(1 / 30)
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    run(lobby, SLEEP_TIME + 0.3)
    assert lobby.clock.day == 2 and "cochilo" in dialog(lobby)


# ------------------------------------------------------------ dormir (online: todos precisam deitar)
def wait_for(client, kind, timeout=3.0, check=lambda m: True):
    end = time.time() + timeout
    while time.time() < end:
        for message in client.poll():
            if message["t"] == kind and check(message):
                return message
        time.sleep(0.01)
    raise AssertionError(f"não chegou '{kind}'")


def join(port, name):
    client = WorldClient()
    client.open("127.0.0.1", port)
    client.authenticate(name.lower(), "1234", register=True)
    client.enter({"name": name, "look": {}, "map": "vila", "x": 31, "y": 21, "facing": "down"})
    return client


def test_online_a_noite_so_passa_com_todos_deitados(tmp_path):
    server = WorldServer(host="127.0.0.1", port=0, db_path=str(tmp_path / "world.db"))
    server.clock = WorldClock(23 * 60, 2)
    server.start()
    try:
        ana, beto = join(server.port, "ANA"), join(server.port, "BETO")
        assert ana.initial_clock["day"] == 2
        ana.send({"t": "bed", "lying": True})                 # só a Ana deitou: a noite continua
        time.sleep(0.5)
        assert server.clock.is_night and server.clock.day == 2
        beto.send({"t": "bed", "lying": True})                # os dois deitados: amanhece
        slept = wait_for(ana, "clock", check=lambda m: m.get("slept"))
        assert (slept["day"], int(slept["minutes"])) == (3, 360)
        ana.close()
        beto.close()
    finally:
        server.stop()
    saved = Database(str(tmp_path / "world.db"))
    assert saved.get_meta("clock")["day"] == 3               # a hora fica guardada no banco
    saved.close()


def test_online_deitado_esperando_os_outros(game, lobby):
    sent = []
    lobby.net = type("Net", (), {"send": lambda self, m: sent.append(m), "poll": lambda self: []})()
    lobby.clock = WorldClock(22 * 60, 2)
    lie_in_suite(lobby)
    assert lobby.sleep_t is None and {"t": "bed", "lying": True} in sent    # não dorme sozinho: espera
    lobby.on_clock_message({"minutes": 360, "day": 3, "slept": True})       # todos deitaram
    assert lobby.sleep_t is not None and lobby.clock.day == 3
    lobby.net = None


# ------------------------------------------------------------ NPCs de noite
def test_de_noite_os_npcs_vao_para_casa_e_nao_desafiam():
    world = NpcWorld(random.Random(5))
    for f in world.folk.values():
        f.challenge_cd = 0.0
    me = {"id": "me", "map": "vila", "x": 31, "y": 21}
    events = []
    for _ in range(3000):
        events += world.tick(0.1, [me], night=True)
    assert not [e for e in events if e[0] == "challenge"]
    away = [f.id for f in world.folk.values() if (f.map_id, f.x, f.y) != f.home[:3] and f.plan == "idle"]
    assert len(away) <= 2


# ------------------------------------------------------------ pescaria e a vila nova
def test_vila_nova_lago_pier_estabulo_shopping():
    names = {o.name for o in VILA.objects}
    assert {"stable_site", "mall_site"} <= names and "house_modern_blue" not in names   # sem a casa do Rafa
    grid = VILA.build()
    assert len(grid[0]) == 88
    assert grid[25][PIER_X] == "B" and grid[25][PIER_X - 1] == "W"                       # píer dentro do lago


def test_pescar_do_pier(game, lobby, monkeypatch):
    monkeypatch.setattr(fishing, "catch", lambda rng=None, night=False: fishing.CATCHES[3])  # um tucunaré
    lobby.player.place(PIER_X, 25)
    lobby.player.facing = "left"
    bets = game.character.bets
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))         # joga a linha
    assert lobby.fishing and lobby.fishing["phase"] == "wait"
    lobby.draw(game.screen)
    lobby.fishing["t"] = 0.01
    run(lobby, 0.1)
    assert lobby.fishing["phase"] == "bite"                    # mordeu: "!"
    lobby.draw(game.screen)
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))         # puxa a tempo
    assert game.character.bets == bets + 18 and game.character.fish_caught == 1
    assert Character.load().fish_caught == 1


def test_pescar_cedo_ou_tarde_demais_o_peixe_foge(game, lobby):
    lobby.player.place(PIER_X, 25)
    lobby.player.facing = "left"
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))         # puxou antes de morder
    assert lobby.fishing is None and "cedo" in dialog(lobby)
    lobby.prompt = type(lobby.prompt)()
    lobby.start_fishing((PIER_X - 1, 25))
    lobby.fishing.update(phase="bite", t=0.05)
    run(lobby, 0.2)
    assert lobby.fishing is None and "escapou" in dialog(lobby)


def test_peixe_da_noite_so_aparece_de_noite():
    rng = random.Random(0)
    assert all(not fishing.catch(rng).night for _ in range(300))
    assert any(fishing.catch(rng, night=True).night for _ in range(300))


# ------------------------------------------------------------ balões dos NPCs só de perto
def test_conversa_dos_npcs_so_aparece_de_perto(game, lobby, monkeypatch):
    texts = []
    monkeypatch.setattr(LobbyScene, "draw_bubble", staticmethod(lambda surf, text, x, bottom: texts.append(text)))
    near, far = lobby.npcs[0], lobby.npcs[1]
    near.say("Bom dia!", 5)
    far.say("Vi! Que final!", 5)
    far.place(lobby.player.tx + 20, lobby.player.ty)
    near.place(lobby.player.tx + 2, lobby.player.ty)
    lobby.draw(game.screen)
    assert "Bom dia!" in texts and "..." in texts and "Vi! Que final!" not in texts
    assert MAPS["vila"].name == "Vila Carta"


def test_trocar_de_mapa_recolhe_a_linha(lobby):
    """Regressão: a linha de pesca continuava desenhada depois de entrar em outro mapa."""
    lobby.player.place(PIER_X, 25)
    lobby.start_fishing((PIER_X - 1, 25))
    lobby.load_map("lanchonete", (14, 15), "up")
    assert lobby.fishing is None

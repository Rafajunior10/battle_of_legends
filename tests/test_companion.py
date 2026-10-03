"""A Rebeca: só existe para quem tem `spouse`, tem rotina própria (casa, vila, lanchonete), segue o jogador,
abraça, beija e vai dormir junto. Regras em game/core/companion.py; cena em game/scenes/home.py."""
import random

import pygame
import pytest

from game.core.companion import Companion
from game.core.nav import Nav
from game.data.character import Character
from game.data.companion import REBECA
from game.data.world import HOME_SPOT, HOUSE_SPOT
from game.engine.app import Game
from game.scenes.home import AFFECTION_TIME, SLEEP_TIME
from game.scenes.lobby import LobbyScene

NAV = Nav()


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


def press(scene, key):
    scene.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def pick(lobby, index):
    for _ in range(300):
        if lobby.prompt.choosing:
            break
        press(lobby, pygame.K_z)
        lobby.update(1 / 30)
    assert lobby.prompt.choosing
    for _ in range(index):
        press(lobby, pygame.K_DOWN)
    press(lobby, pygame.K_z)


def run(lobby, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        lobby.update(dt)


def meet_rebeca(lobby):
    """Entra em casa e fica de frente para a Rebeca (ela é segurada parada)."""
    lobby.load_map("casa_terreo", HOUSE_SPOT, "up")
    c = lobby.companion
    c.place("casa_terreo", 10, 7, facing="left")
    c.hold(99)
    run(lobby, 0.2)
    lobby.player.place(9, 7)
    lobby.player.facing = "right"
    return c


# ------------------------------------------------------------ regras
def test_caminho_atravessa_mapas():
    route = NAV.route("casa_superior", (13, 13), "lanchonete", (5, 6))
    maps = []
    for map_id, _, _ in route:
        if not maps or maps[-1] != map_id:
            maps.append(map_id)
    assert maps == ["casa_superior", "casa_terreo", "vila", "lanchonete"]
    assert route[-1] == ("lanchonete", 5, 6)


def test_rotina_faz_varias_atividades_e_sai_de_casa():
    c = Companion.at_home(REBECA)
    rng = random.Random(3)
    done, maps, poses = set(), set(), set()
    for _ in range(12_000):                               # 20 minutos de jogo, de 0,1 em 0,1 s
        c.tick(0.1, NAV, rng)
        maps.add(c.map_id)
        poses.add(c.pose)
        if c.phase == "do":
            done.add(c.task.id)
    assert len(done) >= 6
    assert "vila" in maps and {"sit", "stand"} <= poses


def test_segue_o_jogador():
    c = Companion.at_home(REBECA)
    c.follow()
    for _ in range(200):
        c.tick(0.05, NAV, leader=("casa_terreo", (20, 10), (20, 11)), occupied=frozenset({(20, 11)}))
    assert (c.x, c.y) == (20, 10)                          # chegou atrás do jogador


def test_vai_dormir_e_acorda():
    c = Companion.at_home(REBECA)
    assert c.go_to_sleep(NAV)
    for _ in range(2000):
        c.tick(0.05, NAV)
    assert (c.map_id, c.tile, c.pose) == ("casa_superior", REBECA.sleep.seat, "lie")
    c.wake()
    assert c.pose == "stand" and c.tile == REBECA.sleep.spot and c.mode == "routine"


def test_espera_quem_esta_no_caminho():
    c = Companion.at_home(REBECA)
    c._start(next(a for a in REBECA.activities if a.id == "geladeira"), NAV)
    blocker = c.route[0][1:]
    for _ in range(5):
        c.tick(0.1, NAV, occupied=frozenset({blocker}))
    assert c.tile == REBECA.home[1:]                       # não atravessou ninguém


# ------------------------------------------------------------ só para quem é casado
def test_so_quem_tem_esposa_tem_a_rebeca(save_path):
    g = Game()
    g.character = Character(name="Bilu")
    assert LobbyScene(g).companion is None
    assert Character.from_dict({"name": "X", "spouse": "fulana"}).spouse == ""   # save estragado


def test_rebeca_aparece_em_casa_e_anda(game, lobby):
    lobby.load_map("casa_terreo", HOUSE_SPOT, "up")
    assert lobby.spouse_here
    start = (lobby.spouse_actor.tx, lobby.spouse_actor.ty)
    run(lobby, 8)
    lobby.draw(game.screen)
    assert lobby.companion.last                             # já escolheu uma atividade
    assert (lobby.spouse_actor.tx, lobby.spouse_actor.ty) != start or lobby.companion.phase == "do"


# ------------------------------------------------------------ interações
def test_abraco_e_beijo(game, lobby):
    c = meet_rebeca(lobby)
    press(lobby, pygame.K_z)
    pick(lobby, 2)                                          # ABRAÇAR
    assert lobby.affection
    run(lobby, AFFECTION_TIME / 2)
    assert lobby.player.nudge != (0, 0)                     # os dois se aproximam
    lobby.draw(game.screen)                                 # com coraçõezinhos
    run(lobby, AFFECTION_TIME)
    assert lobby.affection is None and lobby.spouse_actor.emote == "Que abraço gostoso!"
    c.hold(99)
    press(lobby, pygame.K_z)
    pick(lobby, 3)                                          # BEIJAR
    run(lobby, AFFECTION_TIME + 0.5)
    assert lobby.spouse_actor.emote == "Te amo!"


def test_conversar_e_me_segue_pela_porta(game, lobby):
    c = meet_rebeca(lobby)
    press(lobby, pygame.K_z)
    pick(lobby, 0)                                          # CONVERSAR
    assert "REBECA" in " ".join(" ".join(p) for p in lobby.prompt.dialog.pages)
    lobby.prompt = type(lobby.prompt)()
    press(lobby, pygame.K_z)
    pick(lobby, 1)                                          # ME SEGUE
    assert c.mode == "follow"
    lobby.load_map("vila", HOME_SPOT, "down")               # saiu de casa: ela vem junto
    assert c.map_id == "vila" and abs(c.x - HOME_SPOT[0]) + abs(c.y - HOME_SPOT[1]) == 1
    assert lobby.spouse_here


def test_dormir_juntos(game, lobby):
    c = meet_rebeca(lobby)
    game.character.bets = 321
    press(lobby, pygame.K_z)
    pick(lobby, 4)                                          # VAMOS DORMIR
    assert c.mode == "sleep"
    lobby.prompt = type(lobby.prompt)()                     # fecha o "te espero na cama"
    lobby.load_map("casa_superior", (13, 13), "up")
    run(lobby, 30)
    assert c.pose == "lie" and lobby.spouse_actor.pose == "lie"
    lobby.player.place(6, 5)
    lobby.player.facing = "right"
    press(lobby, pygame.K_z)                                # deita do lado dela
    assert lobby.sleep_t is not None                        # os dois deitados: dormem
    lobby.draw(game.screen)
    run(lobby, SLEEP_TIME + 0.2)
    assert lobby.sleep_t is None and c.mode == "routine" and lobby.player.pose == "stand"
    assert Character.load().bets == 321


def test_rebeca_conversa_com_os_npcs(game, lobby):
    beto = next(a for a in REBECA.activities if a.id == "beto")
    c = lobby.companion
    c.place("vila", beto.spot[0] + 1, beto.spot[1])
    c._start(beto, NAV)
    run(lobby, 1)
    npc = next(n for n in lobby.npcs if n.id == "beto")
    assert lobby.spouse_actor.emote == beto.bubble and npc.emote is None     # ela fala primeiro...
    run(lobby, 2.5)
    assert npc.emote == beto.reply                          # ...e o Beto responde depois


def test_sentada_olha_para_a_mesa():
    """Regressão: na lanchonete ela sentava de costas para a mesa."""
    c = Companion.at_home(REBECA)
    lanchar = next(a for a in REBECA.activities if a.id == "lanchar")
    c.place("lanchonete", *lanchar.spot)
    c._start(lanchar, NAV)
    c.tick(1.0, NAV)
    assert (c.pose, c.facing) == ("sit", "right")

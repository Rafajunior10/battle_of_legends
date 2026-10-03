"""Vida dos NPCs (game/core/townsfolk.py + game/scenes/town.py): passeiam por todos os mapas públicos sem
trombar, conversam, treinam duelos, comem na lanchonete e às vezes desafiam o jogador."""
import random
import time

import pygame
import pytest

from game.core import hunger, townsfolk
from game.core.townsfolk import NpcWorld
from game.data.character import Character
from game.data.world import MAPS, SOLID_TILES
from game.engine.app import Game
from game.net.server import WorldServer
from game.scenes.lobby import LobbyScene


def simulate(world, seconds, players=(), dt=0.1, check=None):
    events = []
    for _ in range(int(seconds / dt)):
        events += world.tick(dt, list(players))
        if check:
            check(world)
    return events


def no_overlaps(world):
    seen = set()
    for f in world.folk.values():
        key = (f.map_id, f.x, f.y)
        assert key not in seen, f"dois NPCs em {key}"
        seen.add(key)
        assert MAPS[f.map_id].build()[f.y][f.x] not in SOLID_TILES or f.pose == "sit"


# ------------------------------------------------------------ regras
def test_npcs_passeiam_sem_trombar_e_sem_entrar_em_casa():
    world = NpcWorld(random.Random(7))
    assert "lu" in world.folk and "tico" in world.folk and "kaio" in world.folk
    start = {f.id: (f.map_id, f.x, f.y) for f in world.folk.values()}
    maps, moved = {}, set()

    def check(w):
        no_overlaps(w)
        for f in w.folk.values():
            maps.setdefault(f.id, set()).add(f.map_id)
            if (f.map_id, f.x, f.y) != start[f.id]:
                moved.add(f.id)
    simulate(world, 600, check=check)
    assert {"lu", "gabi"}.isdisjoint(moved)                   # a Lu não sai do caixa; a Gabi fica sentada
    assert len(moved) >= 10                                   # o resto passeia
    assert all(not MAPS[m].private for ms in maps.values() for m in ms)
    assert any("lanchonete" in ms for npc, ms in maps.items() if npc != "lu")
    assert "vila" in maps["kaio"] or "vila" in maps["mila"] or "vila" in maps["rosa"]   # o bosque sai para a vila


def test_npcs_conversam_treinam_e_pedem_comida():
    world = NpcWorld(random.Random(2))
    said = {e[2] for e in simulate(world, 900) if e[0] == "say"}
    assert said & {line for pair in townsfolk.NPC_CHATS for line in pair}       # conversa
    assert said & set(townsfolk.NPC_DUEL[1])                                    # duelo de treino
    assert any(t.endswith("por favor, Lu!") for t in said) and townsfolk.NPC_ORDER_REPLY in said


def test_duelista_desafia_o_jogador_de_vez_em_quando(monkeypatch):
    monkeypatch.setattr(townsfolk, "APPROACH_CHANCE", 1.0)
    world = NpcWorld(random.Random(1))
    for f in world.folk.values():
        f.challenge_cd = 0.0
    me = {"id": "me", "map": "vila", "x": 31, "y": 21, "busy": False}
    challenges = []
    for _ in range(600):                                             # 1 minuto
        for event in world.tick(0.1, [me]):
            if event[0] == "challenge":
                npc = world.folk[event[1]]
                challenges.append((event[2], npc.duelist, abs(npc.x - 31) + abs(npc.y - 21)))
    assert challenges == [("me", True, 1)]       # um duelista veio até o lado; só um (depois o jogador descansa)


def test_quem_esta_ocupado_nao_e_desafiado(monkeypatch):
    monkeypatch.setattr(townsfolk, "APPROACH_CHANCE", 1.0)
    world = NpcWorld(random.Random(1))
    busy = {"id": "me", "map": "vila", "x": 31, "y": 21, "busy": True}
    rebeca = {"id": "spouse", "map": "vila", "x": 32, "y": 21, "target": False}
    assert not [e for e in simulate(world, 60, [busy, rebeca]) if e[0] == "challenge"]


def test_npc_segurado_fica_parado():
    world = NpcWorld(random.Random(3))
    tico = world.folk["tico"]
    world.hold("tico", 30, face="left")
    before = tico.tile
    simulate(world, 20)
    assert tico.tile == before and tico.facing == "left"


# ------------------------------------------------------------ na tela (jogando sozinho)
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


def bring(lobby, npc_id, dx, dy):
    """Coloca o NPC do lado do jogador (no desenho e no mundo dos NPCs)."""
    x, y = lobby.player.tx + dx, lobby.player.ty + dy
    folk = lobby.npc_world.folk[npc_id]
    folk.map_id, folk.x, folk.y, folk.held = "vila", x, y, 5.0
    actor = lobby.npc_actors[npc_id]
    actor.map_id = "vila"
    actor.pending.clear()
    actor.place(x, y)


def answer(lobby, yes=True):
    for _ in range(300):
        if lobby.prompt.choosing:
            break
        lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
        lobby.update(1 / 30)
    if not yes:
        lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    lobby.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))


def test_npcs_andam_na_tela(game, lobby):
    start = {n.id: (n.tx, n.ty) for n in lobby.npcs}
    for _ in range(30 * 40):
        lobby.update(1 / 30)
    lobby.draw(game.screen)
    moved = [n.id for n in lobby.npc_actors.values() if (n.tx, n.ty) != start.get(n.id, (n.tx, n.ty))]
    assert moved
    assert all(n.map_id == "vila" for n in lobby.npcs)


def test_npc_vem_desafiar_e_eu_aceito(game, lobby):
    bring(lobby, "tico", 1, 0)
    started = []
    game.start_battle = lambda spec, on_end: started.append(spec["id"])
    lobby.npc_event(("challenge", "tico"))
    lobby.update(1 / 30)
    assert lobby.player.facing == "right"                     # virou para o Tico
    answer(lobby, yes=True)
    assert started == ["tico"] and lobby.npc_world.folk["tico"].held > 60


def test_npc_que_ainda_nao_pode_ser_desafiado_so_conversa(game, lobby):
    bring(lobby, "lia", 0, 1)
    lobby.npc_event(("challenge", "lia"))
    lobby.update(1 / 30)
    assert lobby.prompt.visible and not lobby.prompt.choosing     # "Vença o Rafa primeiro"


def test_com_fome_nao_da_para_aceitar(game, lobby):
    game.character.hunger = hunger.WEAK - 1
    bring(lobby, "tico", -1, 0)
    started = []
    game.start_battle = lambda spec, on_end: started.append(spec)
    lobby.npc_event(("challenge", "tico"))
    lobby.update(1 / 30)
    answer(lobby, yes=True)
    assert started == []


# ------------------------------------------------------------ online: o servidor manda nos NPCs
def wait_for(client, kind, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        for message in client.poll():
            if message["t"] == kind:
                return message
        time.sleep(0.01)
    raise AssertionError(f"não chegou '{kind}'")


def test_servidor_move_os_npcs_para_todos():
    from game.net.client import WorldClient
    server = WorldServer(host="127.0.0.1", port=0)
    server.start()
    try:
        client = WorldClient()
        client.open("127.0.0.1", server.port)
        client.authenticate("ana", "1234", register=True)
        client.enter({"name": "ANA", "look": {}, "map": "vila", "x": 31, "y": 21, "facing": "down"})
        assert {n["id"] for n in client.initial_npcs} >= {"tico", "lu", "kaio"}
        with server.npc_lock:
            server.npc_world.folk["tico"].timer = 0.0             # o Tico resolve sair andando agora
        assert wait_for(client, "npc")["id"]
        client.send({"t": "npc_hold", "id": "beto", "seconds": 30, "face": "up"})
        time.sleep(0.3)
        assert server.npc_world.folk["beto"].held > 20
        server._npc_event(("challenge", "tico", client.id))
        assert wait_for(client, "npc_challenge")["id"] == "tico"
        client.close()
    finally:
        server.stop()

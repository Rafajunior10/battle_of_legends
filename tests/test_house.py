"""Casa do jogador: entrar e sair, escada entre os andares, Rebeca, estante de troféus, cama, sofá, closet
(trocar de roupa) e a casa ser particular no online. Também as peças novas: cabelo cacheado e shorts."""
import pygame
import pytest

from game.data.character import Character
from game.data.world import HOME_SPOT, HOUSE_GROUND, HOUSE_SPOT, REBECA_LINES
from game.engine.app import Game
from game.graphics import house, sprites
from game.scenes.actors import RemotePlayer
from game.scenes.closet import ClosetScene
from game.scenes.lobby import LobbyScene


@pytest.fixture
def game(save_path):
    g = Game()
    g.character = Character(name="Juninho")
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


def step(game, frames=1, dt=1 / 30):
    for _ in range(frames):
        game.scene.update(dt)
        if game.transition:
            game.transition.update(dt)
            if game.transition.done:
                game.transition = None
        game.scene.draw(game.screen)


def face(lobby, x, y, facing):
    lobby.player.place(x, y)
    lobby.player.facing = facing


def walk(game, lobby, direction):
    lobby.player.start_move(direction, 0.05)
    step(game, 40)


def dialog_text(lobby):
    return " ".join(" ".join(page) for page in lobby.prompt.dialog.pages)


def test_entrar_subir_descer_e_sair_de_casa(game, lobby):
    face(lobby, HOME_SPOT[0], HOME_SPOT[1], "up")
    press(lobby, pygame.K_z)                                  # A na porta de casa
    step(game, 40)
    assert lobby.map_def.id == "casa_terreo" and (lobby.player.tx, lobby.player.ty) == HOUSE_SPOT
    face(lobby, 13, 4, "up")                                  # no meio da escada
    walk(game, lobby, "up")
    assert lobby.map_def.id == "casa_superior" and (lobby.player.tx, lobby.player.ty) == (13, 13)
    face(lobby, 13, 15, "down")
    walk(game, lobby, "down")
    assert lobby.map_def.id == "casa_terreo" and (lobby.player.tx, lobby.player.ty) == (13, 6)
    face(lobby, *HOUSE_SPOT, "down")
    walk(game, lobby, "down")                                 # capacho da porta da rua
    assert lobby.map_def.id == "vila" and (lobby.player.tx, lobby.player.ty) == HOME_SPOT


def test_rebeca_conversa(lobby):
    lobby.load_map("casa_terreo", HOUSE_SPOT, "up")
    rebeca = next(n for n in lobby.npcs if n.id == "rebeca")
    look = rebeca.look
    assert (look.hair, look.top, look.shirt, look.bottom, look.legs) == ("cacheado", "top", "preto", "shorts", "preto")
    face(lobby, rebeca.tx, rebeca.ty + 1, "up")
    press(lobby, pygame.K_z)
    assert REBECA_LINES[0].format(name="JUNINHO") in dialog_text(lobby)
    assert lobby.rebeca_line == 1


def test_estante_mostra_os_trofeus(game, lobby):
    game.character.coliseum_wins = 2
    game.character.beaten = ["lia"]
    lobby.load_map("casa_terreo", HOUSE_SPOT, "up")
    face(lobby, 26, 3, "up")
    press(lobby, pygame.K_z)
    text = dialog_text(lobby)
    assert "2 troféus" in text and "Mestra LIA" in text
    empty = house.trophy_shelf(Character(name="X"))
    full = house.trophy_shelf(game.character)
    assert pygame.image.tobytes(empty, "RGBA") != pygame.image.tobytes(full, "RGBA")   # os troféus aparecem


def test_deitar_na_cama_salva(game, lobby):
    lobby.load_map("casa_superior", (13, 13), "up")
    game.character.bets = 777
    face(lobby, 6, 5, "up")                                   # pé da cama de casal
    press(lobby, pygame.K_z)
    assert "salvo" in dialog_text(lobby) and Character.load().bets == 777


def test_sentar_no_sofa_ver_tv(game, lobby):
    lobby.load_map("casa_terreo", HOUSE_SPOT, "up")
    face(lobby, 20, 7, "down")
    press(lobby, pygame.K_z)                                  # senta no sofá (olhando para a TV)
    assert lobby.player.sitting and lobby.player.facing == "up" and (lobby.player.tx, lobby.player.ty) == (20, 8)
    lobby.draw(game.screen)
    press(lobby, pygame.K_z)                                  # sentado, A mostra o programa da TV
    assert dialog_text(lobby).startswith("TV:")


def test_as_duas_tvs_do_andar_de_cima_ficam_ligadas(lobby):
    lobby.load_map("casa_superior", (13, 13), "up")
    assert len(lobby.tvs) == 2


def test_closet_troca_a_roupa(game, lobby):
    lobby.load_map("casa_superior", (13, 13), "up")
    face(lobby, 2, 4, "up")
    press(lobby, pygame.K_z)                                  # A no closet
    step(game, 40)
    closet = game.scene
    assert isinstance(closet, ClosetScene)
    assert [o[1] for o in closet.options] == ["top", "shirt", "bottom", "legs", "shoes", "hat"]   # só roupa
    press(closet, pygame.K_RIGHT)                             # camisa -> regata
    closet.row = closet.done_row
    press(closet, pygame.K_z)                                 # PRONTO
    step(game, 40)
    assert game.scene is lobby
    assert game.character.top == "regata" and Character.load().top == "regata"
    assert lobby.player.frames is sprites.player_frames(game.character)


def test_closet_voltar_nao_troca(game, lobby):
    closet = ClosetScene(game, lobby)
    game.change_scene(closet)
    press(closet, pygame.K_RIGHT)
    press(closet, pygame.K_x)                                 # B: volta sem vestir
    assert game.character.appearance.top == "camisa"


def test_casa_e_particular_no_online(lobby):
    lobby.load_map("casa_terreo", HOUSE_SPOT, "up")
    assert HOUSE_GROUND.private and lobby.map_key == "casa_terreo@JUNINHO"
    other = RemotePlayer(9, "BILU", lobby.player.frames, "casa_terreo@BILU", 5, 5, "down")
    lobby.remotes[9] = other
    assert other not in lobby.remotes_here()                  # cada um na sua casa
    other.map_id = "casa_terreo@JUNINHO"
    assert other in lobby.remotes_here()


def test_rebeca_tem_cabelo_cacheado_e_shorts_desenhados(lobby):
    from game.data.looks import Look
    curly = Look("Feminino", "cacheado", "castanho", 3, top="top", shirt="preto", bottom="shorts", legs="preto")
    straight = Look("Feminino", "chanel", "castanho", 3, top="top", shirt="preto", bottom="shorts", legs="preto")
    pants = Look("Feminino", "cacheado", "castanho", 3, top="top", shirt="preto", bottom="calça", legs="preto")
    frames = {look: sprites.character_frames(look)[("down", 0)] for look in (curly, straight, pants)}
    as_bytes = {look: pygame.image.tobytes(img, "RGBA") for look, img in frames.items()}
    assert as_bytes[curly] != as_bytes[straight]              # o cacheado é outro corte
    assert as_bytes[curly] != as_bytes[pants]                 # shorts deixa a perna de fora

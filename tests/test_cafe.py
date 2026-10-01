"""Lanchonete: cardápio e bônus do lanche, troca de cartas entre jogadores, entrar/sair, sentar e a TV."""
import pygame
import pytest

from game.core import economy, food
from game.core.economy import ShopError
from game.data.character import Character
from game.data.food import FOOD
from game.data.legends import LEGENDS
from game.data.opponents import random_wild
from game.data.world import CAFE_DOOR, CAFE_SPOT, TV_SHOWS
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


def pick(scene, index):
    """Avança o texto até as opções aparecerem e escolhe a de número `index`."""
    for _ in range(300):
        if scene.prompt.choosing:
            break
        press(scene, pygame.K_z)
        scene.update(1 / 30)
    assert scene.prompt.choosing, "as opções não apareceram"
    for _ in range(index):
        press(scene, pygame.K_DOWN)
    press(scene, pygame.K_z)


def face(lobby, x, y, facing):
    lobby.player.place(x, y)
    lobby.player.facing = facing


def in_cafe(lobby):
    lobby.load_map("lanchonete", CAFE_SPOT, "up")
    return lobby


# ------------------------------------------------------------ regras
def test_comprar_lanche_cobra_e_guarda_para_a_proxima_batalha(hero):
    hero.bets = 30
    item = food.buy(hero, "xburguer")
    assert (hero.bets, hero.snack, item.hp) == (5, "xburguer", 12)
    with pytest.raises(ShopError, match="barriga cheia"):
        food.buy(hero, "maca")                                 # um lanche por vez
    hero.snack = ""
    with pytest.raises(ShopError, match="BETS"):
        food.buy(hero, "sorvete")
    hero.save()
    assert Character.load().snack == ""


def test_lanche_salvo_volta_e_lanche_invalido_some(hero):
    hero.snack = "cafe"
    hero.save()
    assert Character.load().snack == "cafe"
    assert Character.from_dict({"name": "X", "snack": "pizza"}).snack == ""   # save antigo/estragado


def test_lanche_da_pv_a_mais_na_batalha_e_e_gasto(game):
    game.character.snack = "xburguer"
    scene = BattleScene(game, random_wild(1), lambda won, spec: None)
    assert game.character.snack == ""                         # gasto ao começar a batalha
    scene.become(scene.player)                                # a transformação zera os PV...
    steps = scene.eat_snacks()                                # ...e o lanche soma depois
    legend = LEGENDS[game.character.legend]
    assert (scene.player.state.hp, scene.player.state.max_hp) == (legend.hp + 12, legend.hp + 12)
    assert steps                                              # narra: "+12 PV"


def test_troca_entre_jogadores_so_com_carta_sobrando(hero):
    with pytest.raises(ShopError, match="sobrando"):
        economy.swap_card(hero, "murrao", "zeus_luz")         # todas as cópias estão no deck
    hero.collection.append("murrao")
    economy.swap_card(hero, "murrao", "zeus_luz")
    assert hero.owned("zeus_luz") == 1 and hero.spare("murrao") == 0
    hero.collection += ["bola_de_gelo", "zeus_luz", "zeus_luz"]
    with pytest.raises(ShopError, match="3 cópias"):
        economy.swap_card(hero, "bola_de_gelo", "zeus_luz")
    with pytest.raises(ShopError, match="não existe"):
        economy.swap_card(hero, "bola_de_gelo", "carta_falsa")


# ------------------------------------------------------------ mapa
def test_entrar_e_sair_da_lanchonete(game, lobby):
    face(lobby, CAFE_DOOR[0], CAFE_DOOR[1] + 1, "up")
    press(lobby, pygame.K_z)                                  # A na porta
    step(game, 40)
    assert lobby.map_def.id == "lanchonete" and (lobby.player.tx, lobby.player.ty) == CAFE_SPOT
    lobby.player.start_move("down", 0.05)                     # pisa no capacho da porta
    step(game, 40)
    assert lobby.map_def.id == "vila" and (lobby.player.tx, lobby.player.ty) == (CAFE_DOOR[0], CAFE_DOOR[1] + 1)


def test_pedir_lanche_para_a_lu_por_cima_do_balcao(game, lobby):
    in_cafe(lobby)
    face(lobby, 5, 6, "up")                                   # o balcão fica entre você e a LU
    press(lobby, pygame.K_z)
    pick(lobby, 5)                                            # X-BURGUER
    assert game.character.snack == "xburguer" and game.character.bets == 100 - FOOD["xburguer"].price
    assert lobby.my_emote == FOOD["xburguer"].bite
    assert Character.load().snack == "xburguer"               # salvou


def test_balcao_longe_do_caixa_explica_onde_pedir(lobby):
    in_cafe(lobby)
    face(lobby, 2, 6, "up")
    press(lobby, pygame.K_z)
    assert lobby.prompt.visible and not lobby.prompt.choosing


def test_sentar_no_puff_ver_tv_e_levantar(game, lobby):
    in_cafe(lobby)
    face(lobby, 17, 7, "up")
    press(lobby, pygame.K_z)                                  # A de frente para o puff: senta
    assert lobby.player.sitting and (lobby.player.tx, lobby.player.ty) == (17, 6)
    lobby.draw(game.screen)                                   # sentado desenha (com a frente do puff)
    channel = lobby.tv_channel
    press(lobby, pygame.K_z)                                  # sentado olhando a TV: troca de canal
    assert lobby.tv_channel == (channel + 1) % len(TV_SHOWS)
    assert lobby.prompt.visible
    lobby.prompt = type(lobby.prompt)()
    lobby.stand_up("down")
    assert not lobby.player.sitting and (lobby.player.tx, lobby.player.ty) == (17, 7)


def test_lugar_ocupado_e_conversa_com_a_cliente(lobby):
    in_cafe(lobby)
    face(lobby, 16, 11, "up")                                 # a GABI está sentada nessa cadeira
    press(lobby, pygame.K_z)
    assert lobby.prompt.visible and not lobby.player.sitting
    assert lobby.gabi_tip == 1


def test_mesa_de_troca_sem_ninguem_online_explica(lobby):
    in_cafe(lobby)
    face(lobby, 5, 12, "up")
    press(lobby, pygame.K_z)
    text = " ".join(" ".join(page) for page in lobby.prompt.dialog.pages)
    assert lobby.prompt.visible and "MESA DE TROCA" in text


def test_tv_troca_de_canal_sozinha(game, lobby):
    in_cafe(lobby)
    channel = lobby.tv_channel
    for _ in range(7 * 30):
        lobby.update(1 / 30)
    assert lobby.tv_channel != channel
    lobby.draw(game.screen)

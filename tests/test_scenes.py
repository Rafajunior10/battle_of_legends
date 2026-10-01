"""Testes de fumaça das telas: rodam as cenas de verdade sem janela (driver de vídeo "dummy").

Não conferem pixels, só garantem que cada tela abre, desenha e reage às teclas sem quebrar.
"""
from collections import deque

import pygame
import pytest

from game.data.cards import PACKS, make_deck
from game.data.character import Character
from game.data.opponents import trainer_spec
from game.data.world import MAPS, TRAINER_TALK
from game.engine.app import Game
from game.scenes.battle import BattleScene
from game.scenes.deckedit import DeckEditScene
from game.scenes.lobby import LobbyScene
from game.scenes.options import OptionsScene
from game.scenes.shop import TABS, TYPES, ShopScene
from game.scenes.title import TitleScene

STRONG_DECK = make_deck(choque_do_trovao=3, zeus_luz=3, chicote_de_raios=3, tela_de_luz=2, amansa_loko=3,
                        murrao=3, golpe_perfurante=3)


class Driver:
    """Aperta teclas e avança frames como o loop principal faria."""

    def __init__(self, game):
        self.game = game

    def press(self, key):
        self.game.scene.handle(pygame.event.Event(pygame.KEYDOWN, key=key))

    def step(self, frames=1, dt=1 / 30):
        g = self.game
        for _ in range(frames):
            g.scene.update(dt)
            if g.transition:
                g.transition.update(dt)
                if g.transition.done:
                    g.transition = None
            g.scene.draw(g.screen)

    def answer(self, scene, yes=True):
        """Avança o texto até a pergunta aparecer e responde SIM ou NÃO."""
        for _ in range(300):
            if scene.prompt.choosing:
                break
            self.press(pygame.K_z)
            self.step()
        assert scene.prompt.choosing, "a pergunta não apareceu"
        if not yes:
            self.press(pygame.K_DOWN)
        self.press(pygame.K_z)
        self.step()

    def play_battle(self, max_frames=30_000):
        scene = self.game.scene
        assert isinstance(scene, BattleScene)
        for _ in range(max_frames):
            if scene.dialog.active:
                self.press(pygame.K_z)
            elif scene.state == "choose" and not scene.busy:
                hand = scene.player.hand
                playable = [i for i, c in enumerate(hand) if c.cost <= scene.player.energy]
                scene.cursor = playable[0] if playable else scene.end_slot
                self.press(pygame.K_z)
            self.step()
            if self.game.scene is not scene:
                return scene
        raise AssertionError("a batalha não terminou")


@pytest.fixture
def game(save_path):
    g = Game()
    g.character = Character(name="Teste")
    g.character.save()
    return g   # sem pygame.quit(): como no jogo real, o pygame é iniciado uma vez só


@pytest.fixture
def drive(game):
    return Driver(game)


@pytest.fixture
def lobby(game):
    scene = LobbyScene(game)
    game.lobby = scene
    game.change_scene(scene)
    return scene


def test_titulo_e_opcoes(game, drive):
    game.change_scene(TitleScene(game))
    drive.step(3)
    game.change_scene(OptionsScene(game, lambda: TitleScene(game)))
    for key in (pygame.K_DOWN, pygame.K_DOWN, pygame.K_z, pygame.K_j, pygame.K_UP, pygame.K_RIGHT):
        drive.press(key)
        drive.step()


NEIGHBORS = ((0, 1), (0, -1), (1, 0), (-1, 0))


def reachable(scene, start):
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in NEIGHBORS:
            nxt = (x + dx, y + dy)
            if nxt not in seen and scene.walkable(*nxt):
                seen.add(nxt)
                queue.append(nxt)
    return seen


@pytest.mark.parametrize("map_id", list(MAPS))
def test_mapa_tudo_alcancavel(lobby, map_id):
    first_warp = next(w for m in MAPS.values() for w in m.warps if w.to_map == map_id) if map_id != "vila" else None
    start = (first_warp.to_x, first_warp.to_y) if first_warp else (lobby.player.tx, lobby.player.ty)
    lobby.load_map(map_id, start, "down")
    seen = reachable(lobby, start)
    for door in lobby.map_def.doors:
        assert (door[0], door[1] + 1) in seen, f"porta {door} inalcançável"
    for npc in lobby.npcs:
        assert any((npc.tx + dx, npc.ty + dy) in seen for dx, dy in NEIGHBORS), npc.id
    for warp in lobby.map_def.warps:
        assert (warp.x, warp.y) in seen, f"passagem {warp} inalcançável"


@pytest.mark.parametrize("map_id", list(MAPS))
def test_passagens_e_treinadores_validos(lobby, map_id):
    lobby.load_map(map_id, (0, 0), "down")
    for warp in MAPS[map_id].warps:
        dest = MAPS[warp.to_map]
        grid = dest.build()
        assert grid[warp.to_y][warp.to_x] not in "TWFSR", f"{warp} chega num tile sólido"
        assert dest.warp_at(warp.to_x, warp.to_y) is None, f"{warp} chega em cima de outra passagem"
    for tid in MAPS[map_id].trainers:
        assert tid in TRAINER_TALK


def test_viajar_da_vila_ao_bosque_e_voltar(lobby, drive):
    vila_exit = MAPS["vila"].warps[0]
    lobby.player.place(vila_exit.x, vila_exit.y - 1)
    lobby.player.start_move("down", 0.05)
    drive.step(30)
    assert lobby.map_def.id == "bosque"
    back = MAPS["bosque"].warps[0]
    lobby.player.place(back.x, back.y + 1)
    lobby.player.start_move("up", 0.05)
    drive.step(30)
    assert lobby.map_def.id == "vila"


def test_derrota_no_bosque_volta_para_casa(lobby):
    lobby.load_map("bosque", (21, 2), "down")
    lobby.after_battle(False, {"id": "wild", "kind": "wild"})
    assert lobby.map_def.id == "vila"


def test_conversas_do_lobby(lobby, drive):
    for npc in lobby.npcs:
        npc.on_talk()
        for _ in range(40):
            drive.press(pygame.K_x)
            drive.step()


@pytest.mark.parametrize("tab", TABS)
def test_abas_da_loja(game, drive, tab):
    game.change_scene(ShopScene(game, lambda: game.scene))
    game.scene.tab = TABS.index(tab)
    drive.step(2)


def test_abrir_pack(game, drive):
    """Regressão: abrir pack quebrava com NameError."""
    ch = game.character
    ch.bets = PACKS[2].price
    shop = ShopScene(game, lambda: shop)
    game.change_scene(shop)
    shop.buy_pack(PACKS[2])          # a aba está desligada, mas a compra continua funcionando
    drive.answer(shop, yes=True)
    assert shop.opening is not None
    drive.step(120)
    assert shop.opening.done
    converted = len(shop.opening.converted)   # cópias além do limite de 3 viram BETS
    drive.press(pygame.K_z)
    assert shop.opening is None
    assert len(ch.collection) == 20 + 3 - converted


def test_aba_de_packs_desligada():
    assert "PACKS" not in TABS


def test_evoluir_carta_pela_loja(game, drive):
    ch = game.character
    ch.battle_xp = 100
    shop = ShopScene(game, lambda: shop)
    game.change_scene(shop)
    shop.tab = TABS.index("EVOLUIR")
    shop.kind = TYPES.index("utilidades")   # Murrão fica na sub-aba Utilidades
    shop.focus = "list"
    shop.lst.index = shop.items().index("murrao")
    drive.press(pygame.K_z)
    drive.answer(shop, yes=True)           # primeira opção = pagar com XP
    assert ch.card_level("murrao") == 2
    assert ch.battle_xp == 60


def test_editor_de_deck(game, drive):
    ch = game.character
    editor = DeckEditScene(game, lambda: editor, slot=1)
    game.change_scene(editor)
    drive.press(pygame.K_RIGHT)
    drive.step()
    assert ch.decks[1] == ["queimar"]
    drive.press(pygame.K_LEFT)
    assert ch.decks[1] == []


def test_batalha_completa(game, drive, lobby):
    ch = game.character
    ch.collection = list(STRONG_DECK)
    ch.decks[0] = list(STRONG_DECK)
    lobby.challenge("tico")
    drive.step(60)
    battle = drive.play_battle()
    assert battle.over
    assert ch.wins + ch.losses == 1


def test_torneio_pelo_coliseu(game, drive, lobby):
    ch = game.character
    ch.collection = list(STRONG_DECK)
    ch.decks[0] = list(STRONG_DECK)
    ch.card_levels = {"choque_do_trovao": 3, "zeus_luz": 3, "amansa_loko": 3, "murrao": 3}
    lobby.enter_coliseum()
    drive.answer(lobby, yes=True)
    drive.step(60)
    for _ in range(3):
        drive.play_battle()
        drive.step(40)
        if lobby.tournament is None:
            break
        drive.answer(lobby, yes=True)
        drive.step(60)
    assert lobby.tournament is None          # terminou: campeão, eliminado ou desistiu
    assert ch.wins + ch.losses >= 1
    assert (ch.battle_xp > 0) == (ch.wins > 0)   # XP de batalha só vem de vitória


def test_todo_evento_tem_narracao():
    from game.core import events
    kinds = {cls for cls in vars(events).values()
             if isinstance(cls, type) and issubclass(cls, events.Event) and cls is not events.Event}
    assert kinds == set(BattleScene.NARRATORS)


def test_criacao_mostra_o_valor_certo_em_cada_linha(game):
    """Regressão: com o pacote de arte, a linha NOME mostrava 'Castanho' (valor do cabelo)."""
    from game.scenes.create import CreateScene
    scene = CreateScene(game)
    scene.name = "Ana"
    scene.row = 0
    assert scene.value_of(scene.name_row).startswith("Ana")
    assert scene.value_of(scene.done_row) == ""


def test_sem_o_pacote_de_arte_o_mapa_avisa_o_que_falta(game, tmp_path, monkeypatch):
    """O pacote Ninja Adventure vem com o projeto; se sumir, o lobby explica o problema (o título ainda abre)."""
    from game.graphics import assets
    monkeypatch.setattr(assets, "ASSETS_DIR", str(tmp_path))
    assets.reset()
    try:
        with pytest.raises(FileNotFoundError, match="ninja_adventure"):
            LobbyScene(game)
        TitleScene(game).draw(game.screen)
    finally:
        assets.reset()


def test_menu_sair_volta_para_o_titulo(game, lobby, drive):
    drive.press(pygame.K_ESCAPE)
    assert lobby.menu is not None
    for _ in range(lobby.menu.options.index("SAIR")):
        drive.press(pygame.K_DOWN)
    drive.press(pygame.K_z)
    drive.step(60)
    assert isinstance(game.scene, TitleScene)


def test_atalho_abre_e_fecha_a_ficha(lobby, drive):
    drive.press(pygame.K_i)
    assert lobby.showing_profile
    drive.step(2)                       # desenha a ficha com o tema do deck
    drive.press(pygame.K_e)
    assert not lobby.showing_profile


def test_ficha_usa_o_tema_do_deck(game):
    from game.data.cards import CARDS
    from game.scenes.profile import NEUTRAL, THEMES, theme_of
    ch = game.character
    for element in THEMES:
        ch.decks[ch.active_deck] = [c.id for c in CARDS.values() if c.archetype == element][:3]
        assert theme_of(ch) is THEMES[element]
    ch.decks[ch.active_deck] = []
    assert theme_of(ch) is NEUTRAL


def test_ctrl_c_no_terminal_fecha_sem_erro(game, monkeypatch):
    """Regressão: Ctrl+C no meio do desenho mostrava um KeyboardInterrupt enorme no terminal."""
    def interrompe():
        raise KeyboardInterrupt
    monkeypatch.setattr(game, "frame", interrompe)
    monkeypatch.setattr(pygame, "quit", lambda: None)   # os outros testes ainda usam o pygame
    game.run()                                           # não pode levantar exceção


def test_loja_separa_as_cartas_por_tipo(game):
    from game.data.cards import CARDS
    shop = ShopScene(game, lambda: shop)
    shop.tab = TABS.index("COMPRAR")
    for i, kind in enumerate(TYPES):
        shop.kind = i
        items = shop.items()
        assert items, kind
        assert all(CARDS[c].archetype == kind for c in items)


def test_loja_navega_abas_sub_abas_e_lista(game, drive):
    shop = ShopScene(game, lambda: shop)
    game.change_scene(shop)
    assert shop.focus == "tabs"
    drive.press(pygame.K_DOWN)                 # abas -> sub-abas de tipo
    assert shop.focus == "types"
    drive.press(pygame.K_RIGHT)                # troca o tipo
    assert shop.kind == 1
    drive.press(pygame.K_DOWN)                 # sub-abas -> lista
    assert shop.focus == "list"
    drive.press(pygame.K_UP)                   # do topo da lista volta para as sub-abas
    assert shop.focus == "types"
    drive.step(2)


def test_editor_so_mostra_cartas_do_tipo_do_deck(game):
    from game.data.cards import CARDS
    ch = game.character
    ch.collection += ["garras_de_veneno", "bola_de_fogo"]
    ch.set_deck_element(1, "veneno")
    editor = DeckEditScene(game, lambda: editor, slot=1)
    tipos = {CARDS[c].archetype for c in editor.rows if isinstance(c, str)}
    assert tipos <= {"veneno", "utilidades"}
    assert "garras_de_veneno" in editor.rows and "bola_de_fogo" not in editor.rows


def _battle_ready(game, drive, trainer):
    scene = BattleScene(game, trainer_spec(trainer), lambda won, spec: game.lobby or scene)
    game.change_scene(scene)
    for _ in range(3000):
        if scene.state == "choose" and not scene.busy:
            return scene
        if scene.dialog.active:
            drive.press(pygame.K_z)
        drive.step()
    raise AssertionError("a batalha não chegou na sua vez")


def test_transformacao_no_comeco_da_batalha(game, drive):
    scene = _battle_ready(game, drive, "bruno")
    assert scene.player.state.legend.id == "drogoz"           # deck inicial de Fogo
    assert scene.enemy.state.legend.id == "mimo"              # Bruno tem deck de Veneno
    assert scene.player.state.max_hp == 70 and scene.player.owner == "TESTE"


def test_habilidade_do_drogoz_pelas_teclas(game, drive):
    scene = _battle_ready(game, drive, "tico")
    me = scene.player.state
    me.hp = 30
    scene.cursor = scene.ability_slot
    drive.press(pygame.K_z)                                     # HABILIDADE
    assert scene.state == "discard"
    for _ in range(3):                                          # marca as 3 primeiras cartas
        drive.press(pygame.K_z)
        scene.cursor = min(scene.cursor + 1, len(me.hand) - 1) if scene.state == "discard" else scene.cursor
    for _ in range(200):
        drive.step()
    assert me.hp == 45 and me.ability_used


def test_habilidade_do_mimo_pelas_teclas(game, drive):
    ch = game.character
    ch.collection += ["garras_de_veneno"] * 3 + ["cortina_de_veneno"] * 2 + ["picadura_de_mosquito"] * 2
    ch.set_deck_element(1, "veneno")
    for cid in ["garras_de_veneno"] * 3 + ["cortina_de_veneno"] * 2 + ["picadura_de_mosquito"] * 2 + \
            ["defender"] * 3 + ["foco"] * 2 + ["murrao"] * 3 + ["amansa_loko"] * 2 + ["farma_aura"] * 2 + \
            ["chute_violento"]:
        ch.add_to_deck(1, cid)
    ch.set_active_deck(1)
    scene = _battle_ready(game, drive, "tico")
    scene.cursor = scene.ability_slot
    drive.press(pygame.K_z)
    assert scene.state == "mimo" and len(scene.revealed) == 3
    drive.press(pygame.K_z)                                     # confirma a opção do cursor
    for _ in range(400):
        if scene.state == "choose" and not scene.busy:
            break
        drive.step()
    assert scene.player.state.ability_used and not scene.revealed


@pytest.mark.parametrize("trainer", ["bruno", "rafa"])        # oponentes Mimo e Drogoz usam a habilidade
def test_batalha_completa_contra_legends_com_habilidade(game, drive, lobby, trainer):
    game.character.decks[0] = list(STRONG_DECK)
    game.character.collection += list(STRONG_DECK)
    game.character.sanitize()
    scene = BattleScene(game, trainer_spec(trainer), lambda won, spec: lobby)
    game.change_scene(scene)
    drive.play_battle(max_frames=60_000)


def test_campeao_do_coliseu_conta_vitoria_na_ficha(game, lobby):
    from game.core.tournament import ROUNDS, Tournament
    ch = game.character
    lobby.tournament = Tournament(ch.level)
    lobby.tournament.round = ROUNDS - 1                       # chegou na final
    bets = ch.bets
    lobby.after_tournament_battle(True, {})
    assert ch.coliseum_wins == 1 and ch.bets > bets
    assert Character.load().coliseum_wins == 1                # ficou salvo
    lobby.showing_profile = True
    lobby.draw(game.screen)                                   # a ficha mostra a linha COLISEU


def test_save_antigo_sem_coliseu_carrega_com_zero(save_path):
    import json
    save_path.write_text(json.dumps({"name": "Velho", "level": 3}), encoding="utf-8")
    assert Character.load().coliseum_wins == 0
    assert Character.from_dict({"name": "X", "coliseum_wins": -4}).coliseum_wins == 0


def test_criacao_online_entrega_o_personagem(game):
    """Online, a criação não salva no PC: entrega o personagem novo para a tela de login."""
    from game.scenes.create import CreateScene
    created = []
    scene = CreateScene(game, on_created=created.append)
    scene.name = "Nova"
    scene.finish()
    assert [c.name for c in created] == ["Nova"]

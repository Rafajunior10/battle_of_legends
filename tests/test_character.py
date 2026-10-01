import json

import pytest

from game.data.cards import CARDS, DECK_MAX, DECK_MIN, MAX_COPIES, PLAYER_DECK, START_BETS, UTILITY
from game.data.character import LEGACY_REFUND, Character, DeckError, archetypes_ok, xp_to_next


def test_novo_personagem(hero):
    assert hero.deck == PLAYER_DECK
    assert hero.collection == PLAYER_DECK
    assert hero.level == 1
    assert hero.max_hp == 40


def test_xp_sobe_nivel_e_enche_carteira(hero):
    ups = hero.gain_xp(xp_to_next(1) + 5)
    assert ups == 1
    assert hero.level == 2
    assert hero.xp == 5
    assert hero.battle_xp == xp_to_next(1) + 5
    assert hero.max_hp == 43


def test_cartas_sobrando(hero):
    assert hero.spare_cards() == []
    hero.collection.append("zeus_luz")
    assert hero.spare("zeus_luz") == 1
    assert hero.spare_cards() == ["zeus_luz"]


def test_regras_do_deck(hero):
    slot = 1
    assert len(hero.decks[slot]) < DECK_MIN
    with pytest.raises(DeckError):
        hero.set_active_deck(slot)            # deck vazio não pode batalhar
    hero.add_to_deck(slot, "amansa_loko")
    hero.add_to_deck(slot, "amansa_loko")
    with pytest.raises(DeckError):
        hero.add_to_deck(slot, "amansa_loko")       # só tem 2 cópias
    with pytest.raises(DeckError):
        hero.remove_from_deck(slot, "zeus_luz")


def test_deck_so_aceita_um_arquetipo_mais_utilidades(hero):
    hero.collection += ["bola_de_gelo"]
    hero.decks[1] = []
    hero.add_to_deck(1, "queimar")
    hero.add_to_deck(1, "murrao")               # utilidade combina com tudo
    with pytest.raises(DeckError):
        hero.add_to_deck(1, "bola_de_gelo")      # gelo não entra num deck de fogo
    assert not archetypes_ok(["queimar", "bola_de_gelo"])
    assert archetypes_ok(["murrao", "defender"])


def test_deck_tem_tamanho_maximo(hero):
    utilities = [c for c in CARDS if CARDS[c].archetype == UTILITY]
    hero.collection = [c for c in utilities for _ in range(MAX_COPIES)]
    hero.decks[0] = []
    for c in hero.collection[:DECK_MAX]:
        hero.add_to_deck(0, c)
    with pytest.raises(DeckError):
        hero.add_to_deck(0, hero.collection[-1])


def test_save_e_load(hero, save_path):
    hero.bets, hero.battle_xp, hero.card_levels = 777, 12, {"murrao": 2}
    hero.save()
    loaded = Character.load()
    assert loaded == hero


def test_migra_save_antigo(save_path):
    old = {"name": "Velho", "max_hp": 30, "wins": 2, "beaten": ["rafa"], "deck": PLAYER_DECK}
    save_path.write_text(json.dumps(old), encoding="utf-8")
    ch = Character.load()
    assert ch.collection == PLAYER_DECK
    assert ch.decks[0] == PLAYER_DECK
    assert ch.decks[1] == []
    assert ch.wins == 2
    assert ch.bets > 0


def test_save_com_copias_demais_vira_bets(hero, save_path):
    hero.collection = PLAYER_DECK + ["zeus_luz"] * 5
    hero.bets = 0
    hero.save()
    ch = Character.load()
    assert ch.owned("zeus_luz") == MAX_COPIES
    assert ch.bets == 2 * CARDS["zeus_luz"].sell_price


def test_cartas_antigas_viram_bets_e_ganha_deck_inicial(save_path):
    old = {"name": "Velho", "bets": 100, "collection": ["golpe", "chama", "raio"],
           "decks": [["golpe", "chama", "raio"], [], []], "card_levels": {"golpe": 3}}
    save_path.write_text(json.dumps(old), encoding="utf-8")
    ch = Character.load()
    assert ch.bets == 100 + 3 * LEGACY_REFUND
    assert ch.deck == PLAYER_DECK
    assert ch.deck_valid(ch.active_deck)
    assert ch.card_levels == {}


def test_save_bem_antigo_tambem_reembolsa(save_path):
    save_path.write_text(json.dumps({"name": "Muito Velho", "deck": ["golpe"] * 10}), encoding="utf-8")
    ch = Character.load()
    assert ch.bets == START_BETS + 10 * LEGACY_REFUND
    assert ch.deck == PLAYER_DECK


def test_save_corrompido_devolve_none(save_path):
    save_path.write_text("{isso não é json", encoding="utf-8")
    assert Character.load() is None


def test_deck_aceita_so_o_seu_tipo_e_utilidades(hero):
    hero.collection += ["garras_de_veneno", "foco"]
    hero.set_deck_element(1, "veneno")
    hero.add_to_deck(1, "garras_de_veneno")
    hero.add_to_deck(1, "foco")
    with pytest.raises(DeckError, match="Veneno"):
        hero.add_to_deck(1, "queimar")


def test_trocar_o_tipo_tira_as_cartas_do_tipo_antigo(hero):
    hero.collection += ["foco"]
    hero.decks[1] = ["queimar", "foco"]
    hero.set_deck_element(1, "fogo")
    removed = hero.set_deck_element(1, "gelo")
    assert removed == ["queimar"]
    assert hero.decks[1] == ["foco"]                    # Utilidades ficam
    assert hero.deck_element(1) == "gelo"


def test_save_antigo_ganha_o_tipo_pelas_cartas_do_deck(hero):
    hero.deck_elements = []                             # save de antes desta versão
    hero.sanitize()
    assert hero.deck_elements[hero.active_deck] == "fogo"   # o deck inicial é de Fogo
    assert len(hero.deck_elements) == 3

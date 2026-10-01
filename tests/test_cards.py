import random

import pytest

from game.cards import (
    ARCHETYPE_NAMES,
    CARD_LIST,
    CARDS,
    MAX_CARD_LEVEL,
    PACK_SIZE,
    PACKS,
    PLAYER_DECK,
    RARITY_NAMES,
    UTILITY,
    Deck,
    make_deck,
    open_pack,
)
from game.character import archetypes_ok
from game.core.effects import DamageEffect, IceCloneEffect, PoisonEffect, StunEffect

# (id, arquétipo, custo, dano, defesa, aura, raridade) — conferido com a planilha de regras
SPREADSHEET = [
    ("bola_de_fogo", "fogo", 3, 8, 0, 0, "epica"),
    ("queimar", "fogo", 2, 4, 0, 4, "comum"),
    ("fenix", "fogo", 1, 0, 6, 0, "rara"),
    ("fumaca", "fogo", 1, 1, 0, 10, "comum"),
    ("pocao_da_vida", UTILITY, 1, 0, 0, 0, "rara"),
    ("defender", UTILITY, 1, 0, 10, 0, "comum"),
    ("farma_aura", UTILITY, 1, 0, 0, 10, "comum"),
    ("foco", UTILITY, 0, 0, 0, 0, "comum"),
    ("murrao", UTILITY, 1, 4, 0, 0, "comum"),
    ("amansa_loko", UTILITY, 2, 6, 0, 0, "comum"),
    ("chute_violento", UTILITY, 1, 4, 0, 0, "comum"),
    ("golpe_perfurante", UTILITY, 1, 4, 0, 0, "comum"),
    ("contra_golpe", UTILITY, 2, 6, 4, 4, "rara"),
    ("golpe_duplo", UTILITY, 2, 4, 0, 0, "rara"),
    ("golpes_rapidos", UTILITY, 2, 4, 0, 0, "rara"),
    ("fica_frio_ai", "gelo", 3, 6, 0, 0, "epica"),
    ("clone_de_gelo", "gelo", 2, 0, 5, 8, "rara"),
    ("bola_de_gelo", "gelo", 2, 4, 0, 0, "comum"),
    ("gelo_fino", "gelo", 1, 2, 4, 0, "comum"),
    ("choque_do_trovao", "raio", 3, 7, 0, 0, "rara"),
    ("zeus_luz", "raio", 1, 4, 0, 0, "comum"),
    ("tela_de_luz", "raio", 2, 0, 5, 5, "rara"),
    ("chicote_de_raios", "raio", 1, 1, 0, 0, "comum"),
    ("agulha_escarlate", "veneno", 3, 2, 0, 0, "epica"),
    ("garras_de_veneno", "veneno", 1, 0, 0, 0, "rara"),
    ("cortina_de_veneno", "veneno", 2, 0, 0, 8, "rara"),
    ("picadura_de_mosquito", "veneno", 1, 1, 0, 0, "comum"),
]


def test_catalogo_e_exatamente_a_planilha():
    assert {row[0] for row in SPREADSHEET} == set(CARDS)
    assert len(CARD_LIST) == len(SPREADSHEET)


@pytest.mark.parametrize("row", SPREADSHEET, ids=lambda r: r[0])
def test_numeros_da_planilha(row):
    card_id, archetype, cost, damage, defense, aura, rarity = row
    card = CARDS[card_id]
    assert (card.archetype, card.cost, card.damage, card.defense, card.aura, card.rarity) == \
        (archetype, cost, damage, defense, aura, rarity)


def test_efeitos_da_planilha():
    c = CARDS
    assert c["bola_de_fogo"].burn == 2
    assert c["queimar"].burn == 1
    assert c["fenix"].heal == 6
    assert c["fumaca"].stun == 1
    assert c["pocao_da_vida"].heal == 15
    assert (c["foco"].energy, c["foco"].draw) == (2, 1)
    assert c["chute_violento"].pierce_aura
    assert c["golpe_perfurante"].pierce_defense
    assert c["golpe_duplo"].free_next_utility
    assert c["golpes_rapidos"].repeat == 2
    assert c["fica_frio_ai"].ice == 4
    assert c["clone_de_gelo"].ice_clone
    assert c["bola_de_gelo"].ice == 2
    assert c["gelo_fino"].ice == 1
    assert c["choque_do_trovao"].stun == 2
    assert c["zeus_luz"].stun == 1
    assert (c["chicote_de_raios"].energy, c["chicote_de_raios"].draw) == (2, 2)
    assert c["agulha_escarlate"].poison == 4
    assert c["garras_de_veneno"].poison == 2
    assert c["cortina_de_veneno"].poison == 1
    assert c["picadura_de_mosquito"].poison == 1


@pytest.mark.parametrize("card", CARD_LIST, ids=lambda c: c.id)
def test_toda_carta_tem_efeito_e_texto(card):
    assert card.effects
    assert card.text
    assert card.rarity in RARITY_NAMES
    assert card.archetype in ARCHETYPE_NAMES


def test_golpes_rapidos_repete_tudo():
    assert CARDS["golpes_rapidos"].effects == [DamageEffect(4), DamageEffect(4)]


def test_efeitos_compostos():
    assert CARDS["agulha_escarlate"].effects == [DamageEffect(2), PoisonEffect(4)]
    assert CARDS["choque_do_trovao"].effects == [DamageEffect(7), StunEffect(2)]
    assert IceCloneEffect() in CARDS["clone_de_gelo"].effects


def test_deck_inicial_e_valido():
    assert len(PLAYER_DECK) == 20
    assert archetypes_ok(PLAYER_DECK)


def test_make_deck_recusa_carta_inexistente():
    with pytest.raises(KeyError):
        make_deck(carta_que_nao_existe=1)


def test_evolucao_de_cartas():
    queimar = CARDS["queimar"]
    assert [queimar.at_level(n).damage for n in (1, 2, 3)] == [4, 5, 6]
    assert queimar.at_level(3).aura == 6
    assert queimar.at_level(3).burn == 1                 # marcadores não sobem
    assert queimar.at_level(99).level == MAX_CARD_LEVEL
    assert queimar.at_level(2).at_level(3) == queimar.at_level(3)
    assert CARDS["foco"].at_level(3).draw == 3           # só recurso: +1 de compra por nível
    assert "6 de dano" in queimar.at_level(3).text


def test_packs_tem_10_cartas_diferentes():
    for pack in PACKS:
        assert len(pack.cards) == 10 == len(set(pack.cards))
        assert all(c in CARDS for c in pack.cards)


def test_open_pack():
    rng = random.Random(7)
    for pack in PACKS:
        for _ in range(30):
            got = open_pack(pack, rng)
            assert len(got) == PACK_SIZE == len(set(got))
            assert set(got) <= set(pack.cards)
    assert open_pack(PACKS[0], random.Random(3)) == open_pack(PACKS[0], random.Random(3))


def test_deck_compra_e_reembaralha_descarte():
    deck = Deck(["murrao", "queimar"], random.Random(1))
    first, second = deck.draw(), deck.draw()
    assert {first.id, second.id} == {"murrao", "queimar"}
    assert deck.draw() is None
    deck.discard += [first, second]
    assert deck.draw() is not None


def test_deck_aplica_nivel_e_clone_e_independente():
    deck = Deck(["murrao", "queimar", "defender"], random.Random(5), {"murrao": 3})
    assert any(c.id == "murrao" and c.damage == 6 for c in deck.draw_pile)
    copy = deck.clone()
    assert copy.draw() == deck.draw()
    copy.draw()
    assert len(copy.draw_pile) != len(deck.draw_pile)

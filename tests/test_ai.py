import random
import time

import pytest

from game.core.ai import DIFFICULTIES, choose_card, expected_damage
from game.data.cards import CARDS


def snapshot(c):
    return (c.hp, c.defense, c.aura, c.energy, c.stun, c.burn, c.ice, c.poison, c.frozen, c.ice_clone,
            [x.id for x in c.hand], [x.id for x in c.deck.draw_pile], len(c.deck.discard))


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_ia_nao_altera_o_estado(make_fighter, difficulty):
    me = make_fighter(hand=["murrao", "defender", "foco", "bola_de_gelo", "golpe_duplo"], deck=["queimar"] * 6)
    foe = make_fighter(aura=4, burn=1)
    before = snapshot(me), snapshot(foe)
    card = choose_card(me, foe, difficulty, random.Random(1))
    assert card in me.hand
    assert (snapshot(me), snapshot(foe)) == before


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_sem_carta_jogavel_encerra_turno(make_fighter, difficulty):
    me = make_fighter(hand=["bola_de_fogo"], energy=1)
    assert choose_card(me, make_fighter(), difficulty, random.Random(1)) is None


def test_dano_esperado_considera_protecao_e_queimadura(make_fighter):
    foe = make_fighter(aura=3, defense=2, burn=1)
    assert expected_damage(CARDS["murrao"], foe) == 0
    assert expected_damage(CARDS["chute_violento"], foe) == 3
    assert expected_damage(CARDS["golpes_rapidos"], foe) == 5


@pytest.mark.parametrize("difficulty", ["normal", "hard"])
def test_ia_mata_quando_pode(make_fighter, difficulty):
    me = make_fighter(hand=["defender", "murrao", "pocao_da_vida"])
    foe = make_fighter(hp=4)
    assert choose_card(me, foe, difficulty, random.Random(1)).id == "murrao"


@pytest.mark.parametrize("difficulty", ["normal", "hard"])
def test_ia_fura_protecao_grande(make_fighter, difficulty):
    me = make_fighter(hand=["murrao", "chute_violento"], energy=1)
    foe = make_fighter(aura=10)
    assert choose_card(me, foe, difficulty, random.Random(1)).id == "chute_violento"


def test_ia_dificil_pensa_na_sequencia(make_fighter):
    # Foco (0) dá +2 energia: com ele dá para jogar Amansa + Amansa (12); sem ele, só uma.
    me = make_fighter(hand=["amansa_loko", "amansa_loko", "foco"], energy=3, deck=["murrao"] * 5)
    foe = make_fighter(hp=12)
    assert choose_card(me, foe, "hard", random.Random(1)).id == "foco"


def test_ia_dificil_e_rapida(make_fighter):
    me = make_fighter(hand=["foco", "chicote_de_raios", "farma_aura", "golpe_duplo", "murrao", "zeus_luz",
                            "defender"], energy=3, deck=["murrao", "foco", "zeus_luz", "chicote_de_raios"] * 3)
    start = time.perf_counter()
    choose_card(me, make_fighter(), "hard", random.Random(1))
    assert time.perf_counter() - start < 1.0

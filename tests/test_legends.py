"""Legends: os números da tabela do usuário, a transformação e as 4 habilidades."""
import os
import random

import pytest

from game.cards import CARDS, ELEMENTS, Deck
from game.character import DeckError
from game.core import abilities
from game.core import events as ev
from game.core.combat import Combatant, start_turn
from game.core.effects import DamageEffect, IceEffect
from game.legends import LEGENDS, legends_for
from game.sprites import LEGEND_DIR

# (nome, classe, arquétipo, vida, força, proteção, energia) — a tabela que o usuário mandou
TABLE = {
    "mimo": ("Mimo", "NINJA", "veneno", 80, 7, 4, 4),
    "drogoz": ("Drogoz", "MAGO", "fogo", 70, 8, 5, 5),
    "blitz": ("Blitz", "FERA", "raio", 95, 5, 9, 4),
    "cold": ("Cold", "LUTADOR", "gelo", 70, 7, 7, 5),     # o usuário mudou a vida do Cold de 90 para 70
}


def fighter(legend_id=None, deck=("murrao",) * 10, hand=()):
    c = Combatant("A", 1, 30, Deck(list(deck), random.Random(1)))
    abilities.become(c, legend_id)
    c.hand = [CARDS[h] for h in hand]
    return c


@pytest.mark.parametrize("legend_id", list(TABLE))
def test_numeros_da_tabela(legend_id):
    lg = LEGENDS[legend_id]
    assert (lg.name, lg.cls, lg.archetype, lg.hp, lg.strength, lg.protection, lg.energy) == TABLE[legend_id]


def test_todo_tipo_de_deck_tem_legend_e_arte():
    for element in ELEMENTS:
        assert legends_for(element)
    for legend_id in LEGENDS:
        for view in ("front", "back", "portrait", "splash"):
            assert os.path.isfile(os.path.join(LEGEND_DIR, legend_id, f"{view}.png")), (legend_id, view)


def test_transformar_usa_vida_forca_protecao_e_energia_do_legend():
    c = fighter("cold")
    assert (c.max_hp, c.hp, c.strength, c.protection, c.max_energy) == (70, 70, 7, 7, 5)
    start_turn(c)
    assert c.energy == 5


def test_forca_soma_no_golpe_e_protecao_segura():
    atacante, alvo = fighter("drogoz"), fighter("mimo")        # força 8 contra proteção 4
    events = DamageEffect(4).apply(atacante, alvo)
    hit = next(e for e in events if isinstance(e, ev.Damaged))
    assert hit.amount == 4 + 8 - 4
    assert alvo.hp == 80 - 8


def test_monstro_sem_legend_nao_tem_forca_nem_protecao():
    monstro, alvo = fighter(None), fighter(None)
    DamageEffect(4).apply(monstro, alvo)
    assert alvo.hp == 26


def test_drogoz_descarta_3_e_cura_15_uma_vez_por_turno():
    c = fighter("drogoz", hand=("murrao", "foco", "defender", "queimar"))
    c.hp = 40
    events = abilities.drogoz(c, c.hand[:3])
    assert c.hp == 55 and len(c.hand) == 1 and len(c.deck.discard) == 3
    assert any(isinstance(e, ev.CardsDiscarded) for e in events)
    assert not abilities.can_use(c)                            # só 1 vez por turno
    start_turn(c)
    assert not abilities.can_use(c)                            # agora falta carta na mão (só tem 1)


def test_mimo_joga_de_graca_a_de_veneno_e_a_outra_vai_pro_fundo():
    c = fighter("mimo", deck=("defender", "garras_de_veneno", "foco", "murrao"))
    revealed = abilities.mimo_reveal(c)
    assert len(revealed) == 3 and len(c.deck.draw_pile) == 1   # revela as 3 do topo
    if not any(card.archetype == "veneno" for card in revealed):
        c.deck.draw_pile, revealed[0] = [revealed[0]], CARDS["garras_de_veneno"]
    poison = next(card for card in revealed if card.archetype == "veneno")
    others = [card for card in revealed if card is not poison]
    abilities.mimo_finish(c, revealed, poison)
    assert c.deck.draw_pile[:2] == list(reversed(others))     # as outras vão para o fundo
    assert poison in c.deck.discard
    with pytest.raises(ValueError):                             # utilidade não pode
        abilities.mimo_finish(fighter("mimo"), others[:1], others[0])


def test_blitz_ganha_9_de_forca_com_9_de_defesa_e_aura_no_turno():
    c = fighter("blitz")
    assert abilities.attack_bonus(c) == 5                      # a proteção fixa (9) não conta
    c.defense, c.aura = 5, 3
    assert abilities.attack_bonus(c) == 5
    c.aura = 4                                                 # 5 + 4 = 9
    assert abilities.attack_bonus(c) == 5 + 9
    start_turn(c)                                              # defesa e aura zeram no começo do turno
    assert abilities.attack_bonus(c) == 5


def test_cold_quebra_o_gelo_do_congelado_com_mais_5():
    cold, alvo = fighter("cold"), fighter("blitz")
    IceEffect(10).apply(cold, alvo)
    assert alvo.frozen
    events = DamageEffect(4).apply(cold, alvo)
    assert any(isinstance(e, ev.IceShattered) for e in events)
    assert not alvo.frozen and alvo.ice == 0                   # descongelou: não perde mais o turno
    assert alvo.hp == 95 - (4 + 7 + 5 - 9)
    DamageEffect(4).apply(cold, alvo)                           # já descongelado: sem o +5
    assert alvo.hp == 95 - (4 + 7 + 5 - 9) - (4 + 7 - 9)


def test_clone_de_gelo_do_cold_anula_o_primeiro_ataque_e_da_gelo():
    from game.core.combat import play_card
    cold = fighter("cold")
    atacante = fighter("drogoz", hand=("murrao", "murrao"))
    atacante.energy = 5
    cold.ice_clone = True
    events = play_card(atacante, cold, atacante.hand[0])
    assert cold.hp == 70 and atacante.ice == 1                 # sem dano, e o atacante ganhou 1 de gelo
    assert any(isinstance(e, ev.CloneBlocked) for e in events) and not cold.ice_clone
    play_card(atacante, cold, atacante.hand[0])                # o segundo ataque já passa
    assert cold.hp < 70


def test_veneno_pega_nas_duas_passagens_de_turno():
    from game.core.combat import end_turn
    a, b = fighter("drogoz"), fighter("mimo")
    b.poison = 3
    end_turn(a, b)                                             # fim do turno do ADVERSÁRIO: o veneno pega
    assert b.hp == 80 - 3
    end_turn(b, a)                                             # fim do turno dele: pega de novo
    assert b.hp == 80 - 6


def test_deck_escolhe_legend_do_mesmo_tipo(hero):
    hero.set_deck_element(1, "veneno")
    assert hero.deck_legend(1) == "mimo"
    with pytest.raises(DeckError, match="Veneno"):
        hero.set_deck_legend(1, "drogoz")
    hero.set_deck_element(1, "gelo")
    assert hero.deck_legend(1) == "cold"                       # trocou o tipo, trocou o legend


def test_save_antigo_ganha_legend(hero):
    hero.deck_legends = []
    hero.sanitize()
    assert hero.legend == "drogoz"                             # o deck inicial é de Fogo

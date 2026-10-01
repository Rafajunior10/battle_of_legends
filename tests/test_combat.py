import pytest

from game.cards import CARDS
from game.core import events as ev
from game.core.combat import end_turn, loser, pay_card, play_card, start_turn
from game.core.rules import HAND_SIZE, ICE_LIMIT, MAX_ENERGY


def test_dano_bate_na_aura_depois_defesa_depois_pv(make_fighter):
    a, b = make_fighter(hand=["amansa_loko"]), make_fighter(aura=2, defense=3)
    events = play_card(a, b, CARDS["amansa_loko"])
    assert (b.aura, b.defense, b.hp) == (0, 0, 29)
    assert events == [ev.Damaged(b, 1, 5, 0)]


def test_chute_violento_anula_aura(make_fighter):
    a, b = make_fighter(hand=["chute_violento"]), make_fighter(aura=10, defense=2)
    events = play_card(a, b, CARDS["chute_violento"])
    assert b.aura == 0
    assert (b.defense, b.hp) == (0, 28)
    assert ev.ProtectionBroken(b, "aura") in events


def test_golpe_perfurante_anula_defesa(make_fighter):
    a, b = make_fighter(hand=["golpe_perfurante"]), make_fighter(defense=10, aura=1)
    play_card(a, b, CARDS["golpe_perfurante"])
    assert (b.defense, b.aura, b.hp) == (0, 0, 27)


def test_queimadura_soma_dano_em_todo_golpe(make_fighter):
    a, b = make_fighter(hand=["bola_de_fogo", "murrao"], energy=4), make_fighter(hp=50)
    play_card(a, b, CARDS["bola_de_fogo"])
    assert b.hp == 42                  # 8 (a queimadura vem depois do golpe)
    assert b.burn == 2
    events = play_card(a, b, CARDS["murrao"])
    assert b.hp == 42 - (4 + 2)
    assert events[0].burn_bonus == 2


def test_gelo_congela_ao_chegar_em_4_e_zera_contagem(make_fighter):
    a, b = make_fighter(hand=["bola_de_gelo", "bola_de_gelo"], energy=4), make_fighter()
    play_card(a, b, CARDS["bola_de_gelo"])
    assert (b.ice, b.frozen) == (2, False)
    events = play_card(a, b, CARDS["bola_de_gelo"])
    assert (b.ice, b.frozen) == (0, True)
    assert ev.Frozen(b) in events
    turn = start_turn(b)
    assert ev.TurnSkipped(b) in turn
    assert b.energy == 0
    assert not b.frozen
    assert start_turn(b) == []           # o turno seguinte é normal
    assert b.energy == MAX_ENERGY


def test_fica_frio_ai_congela_de_uma_vez(make_fighter):
    a, b = make_fighter(hand=["fica_frio_ai"]), make_fighter()
    play_card(a, b, CARDS["fica_frio_ai"])
    assert b.frozen
    assert ICE_LIMIT == 4


def test_veneno_acumula_e_age_no_fim_do_turno(make_fighter):
    a, b = make_fighter(hand=["agulha_escarlate", "picadura_de_mosquito"], energy=4), make_fighter(hp=40)
    play_card(a, b, CARDS["agulha_escarlate"])
    play_card(a, b, CARDS["picadura_de_mosquito"])
    assert b.poison == 5
    hp = b.hp
    events = end_turn(b)
    assert b.hp == hp - 5
    assert ev.PoisonTick(b, 5) in events
    end_turn(b)
    assert b.hp == hp - 10               # os marcadores não somem


def test_paralisia_acumula(make_fighter):
    a, b = make_fighter(hand=["zeus_luz", "zeus_luz"]), make_fighter()
    play_card(a, b, CARDS["zeus_luz"])
    play_card(a, b, CARDS["zeus_luz"])
    assert b.stun == 2
    start_turn(b)
    assert b.energy == MAX_ENERGY - 2
    assert b.stun == 0


def test_defesa_e_aura_somem_no_comeco_do_turno(make_fighter):
    a = make_fighter(hand=["contra_golpe"])
    play_card(a, make_fighter(), CARDS["contra_golpe"])
    assert (a.defense, a.aura) == (4, 4)
    start_turn(a)
    assert (a.defense, a.aura) == (0, 0)


def test_fim_do_turno_compra_ate_5(make_fighter):
    a = make_fighter(deck=["murrao"] * 20, hand=["murrao"])
    events = end_turn(a)
    assert len(a.hand) == HAND_SIZE
    assert ev.CardsDrawn(a, HAND_SIZE - 1) in events


def test_chicote_passa_de_5_cartas(make_fighter):
    a = make_fighter(deck=["murrao"] * 20, hand=["chicote_de_raios", "murrao", "murrao", "murrao", "murrao"])
    play_card(a, make_fighter(), CARDS["chicote_de_raios"])
    assert len(a.hand) == 6
    assert a.energy == MAX_ENERGY - 1 + 2


def test_clone_de_gelo_zera_energia_de_quem_ataca(make_fighter):
    a, b = make_fighter(hand=["clone_de_gelo"]), make_fighter(hand=["murrao", "murrao"])
    play_card(a, b, CARDS["clone_de_gelo"])
    assert a.ice_clone
    events = play_card(b, a, CARDS["murrao"])
    assert b.energy == 0
    assert not a.ice_clone
    assert ev.IceCloneTriggered(b) in events
    start_turn(a)
    assert not a.ice_clone


def test_clone_de_gelo_some_no_proprio_turno(make_fighter):
    a = make_fighter(hand=["clone_de_gelo"])
    play_card(a, make_fighter(), CARDS["clone_de_gelo"])
    start_turn(a)
    assert not a.ice_clone


def test_golpe_duplo_deixa_proximo_ataque_de_utilidade_gratis(make_fighter):
    a, b = make_fighter(hand=["golpe_duplo", "amansa_loko", "queimar"], energy=3), make_fighter(hp=60)
    play_card(a, b, CARDS["golpe_duplo"])
    assert a.energy == 1
    assert a.cost_of(CARDS["queimar"]) == 2          # fogo não é utilidade: custo normal
    assert a.cost_of(CARDS["amansa_loko"]) == 0
    play_card(a, b, CARDS["amansa_loko"])
    assert a.energy == 1
    assert not a.free_utility


def test_golpes_rapidos_acerta_duas_vezes(make_fighter):
    a, b = make_fighter(hand=["golpes_rapidos"]), make_fighter(burn=1)
    events = play_card(a, b, CARDS["golpes_rapidos"])
    assert b.hp == 30 - 2 * (4 + 1)
    assert sum(isinstance(e, ev.Damaged) for e in events) == 2


def test_cura_nao_passa_do_maximo(make_fighter):
    a = make_fighter(hand=["pocao_da_vida"], hp=30)
    a.hp = 20
    events = play_card(a, make_fighter(), CARDS["pocao_da_vida"])
    assert a.hp == 30
    assert events == [ev.Healed(a, 10)]


def test_nao_joga_sem_energia(make_fighter):
    a = make_fighter(hand=["bola_de_fogo"], energy=2)
    with pytest.raises(ValueError):
        pay_card(a, CARDS["bola_de_fogo"])


def test_marcador_em_alvo_morto_nao_aplica(make_fighter):
    a, b = make_fighter(hand=["agulha_escarlate"]), make_fighter(hp=1)
    events = play_card(a, b, CARDS["agulha_escarlate"])
    assert b.poison == 0
    assert not any(isinstance(e, ev.Poisoned) for e in events)
    assert loser(a, b) is b

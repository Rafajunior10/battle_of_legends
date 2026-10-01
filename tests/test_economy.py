import random

import pytest

from game.core import economy
from game.core.economy import ShopError, TradeOffer
from game.data.cards import CARDS, MAX_COPIES, PACKS


def test_comprar_carta(hero):
    hero.bets = 100
    economy.buy_card(hero, "golpe_perfurante")
    assert hero.bets == 100 - CARDS["golpe_perfurante"].price
    assert hero.owned("golpe_perfurante") == 1


def test_comprar_sem_bets(hero):
    hero.bets = 10
    with pytest.raises(ShopError):
        economy.buy_card(hero, "golpe_perfurante")
    assert hero.bets == 10
    assert hero.owned("golpe_perfurante") == 0


def test_limite_de_3_copias(hero):
    hero.bets = 10_000
    hero.collection = ["queimar"] * MAX_COPIES
    with pytest.raises(ShopError):
        economy.buy_card(hero, "queimar")
    assert hero.bets == 10_000
    with pytest.raises(ValueError):
        hero.add_card("queimar")


def test_pack_com_carta_no_limite_vira_bets(hero):
    pack = PACKS[0]
    hero.collection = [c for c in pack.cards for _ in range(MAX_COPIES)]
    hero.bets = pack.price
    result = economy.buy_pack(hero, pack, random.Random(2))
    assert len(result.cards) == 3
    assert set(result.converted) == set(result.cards)
    assert hero.bets == sum(CARDS[c].sell_price for c in result.cards)
    assert all(hero.owned(c) == MAX_COPIES for c in pack.cards)


def test_pack_normal(hero):
    hero.bets = 1000
    result = economy.buy_pack(hero, PACKS[1], random.Random(4))
    assert hero.bets == 1000 - PACKS[1].price
    assert all(hero.owned(c) >= 1 for c in result.cards)
    assert not result.converted


def test_vender_so_carta_sobrando(hero):
    hero.bets = 0
    with pytest.raises(ShopError):   # o deck inicial usa as 2 cópias de Amansa Loko
        economy.sell_card(hero, "amansa_loko")
    hero.collection.append("amansa_loko")
    assert economy.sell_card(hero, "amansa_loko") == CARDS["amansa_loko"].sell_price
    assert hero.owned("amansa_loko") == 2


def test_evoluir_com_xp_e_bets(hero):
    hero.battle_xp, hero.bets = 40, 1000
    assert economy.upgrade_cost(hero, "murrao") == (40, 120)
    assert economy.upgrade_card(hero, "murrao", "xp") == 2
    assert hero.battle_xp == 0
    assert economy.upgrade_cost(hero, "murrao") == (80, 240)
    with pytest.raises(ShopError):
        economy.upgrade_card(hero, "murrao", "xp")
    assert economy.upgrade_card(hero, "murrao", "bets") == 3
    assert hero.bets == 1000 - 240
    assert economy.upgrade_cost(hero, "murrao") is None
    with pytest.raises(ShopError):
        economy.upgrade_card(hero, "murrao", "bets")
    assert hero.card("murrao").damage == 6


def test_nao_evolui_carta_que_nao_tem(hero):
    hero.battle_xp = 999
    with pytest.raises(ShopError):
        economy.upgrade_card(hero, "bola_de_fogo", "xp")


def test_troca_da_nina(hero):
    hero.collection.append("golpe_perfurante")          # carta sobrando
    offer = economy.make_trade_offer(hero, random.Random(1))
    assert offer.want == "golpe_perfurante"
    assert offer.give != "golpe_perfurante"
    hero.bets = max(0, offer.bets) + 5
    economy.accept_trade(hero, offer)
    assert hero.owned(offer.give) == 1
    assert hero.owned("golpe_perfurante") == 0   # a única cópia foi para a Nina
    assert hero.bets == 5 - min(0, offer.bets)


def test_nina_sem_cartas_sobrando(hero):
    assert economy.make_trade_offer(hero, random.Random(1)) is None


def test_troca_recusada_sem_bets(hero):
    hero.collection.append("amansa_loko")
    hero.bets = 0
    with pytest.raises(ShopError):
        economy.accept_trade(hero, TradeOffer("bola_de_fogo", "amansa_loko", 140))
    assert hero.owned("amansa_loko") == 3
    assert hero.owned("bola_de_fogo") == 0

"""Regras de dinheiro e coleção: loja, packs, evolução de cartas e trocas com a Nina.

As funções mudam o personagem ou levantam ShopError com a mensagem para o jogador.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from ..cards import CARD_LIST, CARDS, MAX_CARD_LEVEL, MAX_COPIES, RARITY_PRICES, Pack, open_pack
from ..character import Character

# custo em XP de batalha para ir ao nível 2 e ao nível 3
UPGRADE_XP = {"comum": (40, 80), "rara": (80, 160), "epica": (120, 240)}
UPGRADE_BETS_FACTOR = 3     # evoluir com BETS custa o triplo
NINA_POOL = [c.id for c in CARD_LIST if c.rarity != "comum"]   # a Nina só oferece raras e épicas


class ShopError(Exception):
    """Operação recusada; a mensagem é mostrada ao jogador."""


def _name(card_id: str) -> str:
    return CARDS[card_id].name.upper()


def _pay(ch: Character, price: int) -> None:
    if ch.bets < price:
        raise ShopError(f"Você precisa de {price} BETS.")
    ch.bets -= price


# ------------------------------------------------------------ cartas avulsas
def buy_card(ch: Character, card_id: str) -> None:
    if not ch.can_add(card_id):
        raise ShopError(f"Você já tem {MAX_COPIES} cópias de {_name(card_id)}.")
    _pay(ch, CARDS[card_id].price)
    ch.add_card(card_id)


def sell_card(ch: Character, card_id: str) -> int:
    """Vende uma cópia que não está em nenhum deck. Devolve os BETS recebidos."""
    if not ch.remove_card(card_id):
        raise ShopError("Só dá para vender cópias que não estão em nenhum deck.")
    price = CARDS[card_id].sell_price
    ch.bets += price
    return price


# ------------------------------------------------------------ packs
@dataclass
class PackResult:
    cards: list[str]            # as 3 cartas sorteadas
    new: set[str]               # as que o jogador ainda não tinha
    converted: dict[str, int]   # cartas que passariam do limite de cópias -> BETS recebidos


def buy_pack(ch: Character, pack: Pack, rng: random.Random | None = None) -> PackResult:
    _pay(ch, pack.price)
    got = open_pack(pack, rng)
    result = PackResult(got, {c for c in got if c not in ch.collection}, {})
    for c in got:
        if ch.can_add(c):
            ch.add_card(c)
        else:
            refund = CARDS[c].sell_price
            ch.bets += refund
            result.converted[c] = result.converted.get(c, 0) + refund
    return result


# ------------------------------------------------------------ evolução
def upgrade_cost(ch: Character, card_id: str) -> tuple[int, int] | None:
    """(XP de batalha, BETS) para o próximo nível, ou None se já está no máximo."""
    level = ch.card_level(card_id)
    if level >= MAX_CARD_LEVEL:
        return None
    xp = UPGRADE_XP[CARDS[card_id].rarity][level - 1]
    return xp, xp * UPGRADE_BETS_FACTOR


def upgrade_card(ch: Character, card_id: str, currency: str) -> int:
    """Evolui a carta pagando com "xp" ou "bets". Devolve o novo nível."""
    if card_id not in ch.collection:
        raise ShopError("Você não tem essa carta.")
    cost = upgrade_cost(ch, card_id)
    if cost is None:
        raise ShopError(f"{_name(card_id)} já está no nível máximo.")
    xp, bets = cost
    if currency == "xp":
        if ch.battle_xp < xp:
            raise ShopError(f"Você precisa de {xp} de XP de batalha.")
        ch.battle_xp -= xp
    elif currency == "bets":
        _pay(ch, bets)
    else:
        raise ValueError(f"moeda desconhecida: {currency}")
    ch.card_levels[card_id] = ch.card_level(card_id) + 1
    return ch.card_levels[card_id]


# ------------------------------------------------------------ trocas com a Nina
@dataclass(frozen=True)
class TradeOffer:
    give: str      # carta da Nina
    want: str      # carta do jogador
    bets: int      # > 0: o jogador paga; < 0: a Nina paga


def trade_value(card_id: str) -> int:
    return RARITY_PRICES[CARDS[card_id].rarity]


def make_trade_offer(ch: Character, rng: random.Random | None = None) -> TradeOffer | None:
    """Oferta da Nina: uma carta dela por uma carta sobrando do jogador. None se não houver troca possível."""
    rng = rng or random.Random()
    spare = ch.spare_cards()
    if not spare:
        return None
    want = rng.choice(spare)
    pool = [c for c in NINA_POOL if c != want and ch.can_add(c)]
    if not pool:
        return None
    give = rng.choice(pool)
    diff = trade_value(give) - trade_value(want)
    return TradeOffer(give, want, diff if diff > 0 else diff // 2)


def accept_trade(ch: Character, offer: TradeOffer) -> None:
    if ch.spare(offer.want) <= 0:
        raise ShopError("Essa carta não está mais sobrando.")
    if not ch.can_add(offer.give):
        raise ShopError(f"Você já tem {MAX_COPIES} cópias de {_name(offer.give)}.")
    if offer.bets > 0:
        _pay(ch, offer.bets)
    else:
        ch.bets -= offer.bets
    ch.remove_card(offer.want)
    ch.add_card(offer.give)

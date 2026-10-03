"""Regras da lanchonete: comprar um lanche e o bônus que ele dá na próxima batalha. Sem Pygame."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import hunger
from game.core.economy import ShopError
from game.data.food import FOOD, FoodItem

if TYPE_CHECKING:
    from game.core.combat import Combatant
    from game.data.character import Character


def buy(ch: Character, food_id: str) -> FoodItem:
    """Compra e come o lanche: mata a fome e o bônus de PV fica em `ch.snack` até a próxima batalha
    (comendo mais de um, fica o bônus maior)."""
    item = FOOD[food_id]
    if not hunger.can_eat(ch):
        raise ShopError(f"Você está de barriga cheia (fome {ch.hunger}/{hunger.MAX_HUNGER})! "
                        "Volte quando der fome.")
    if ch.bets < item.price:
        raise ShopError(f"Você precisa de {item.price} BETS.")
    ch.bets -= item.price
    hunger.eat(ch, item.fill)
    if not ch.snack or FOOD[ch.snack].hp < item.hp:
        ch.snack = item.id
    return item


def boost(c: Combatant, food_id: str | None) -> int:
    """Começo da batalha (depois da transformação): o lanche soma PV ao máximo e ao atual. Devolve quanto."""
    item = FOOD.get(food_id or "")
    if item is None:
        return 0
    c.max_hp += item.hp
    c.hp += item.hp
    return item.hp

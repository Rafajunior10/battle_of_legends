"""Regras da lanchonete: comprar um lanche e o bônus que ele dá na próxima batalha. Sem Pygame."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.core.economy import ShopError
from game.data.food import FOOD, FoodItem

if TYPE_CHECKING:
    from game.core.combat import Combatant
    from game.data.character import Character


def buy(ch: Character, food_id: str) -> FoodItem:
    """Compra e come o lanche: ele fica guardado em `ch.snack` até a próxima batalha."""
    item = FOOD[food_id]
    if ch.snack:
        raise ShopError(f"Você ainda está de barriga cheia ({FOOD[ch.snack].name})! "
                        "O lanche vale até a próxima batalha.")
    if ch.bets < item.price:
        raise ShopError(f"Você precisa de {item.price} BETS.")
    ch.bets -= item.price
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

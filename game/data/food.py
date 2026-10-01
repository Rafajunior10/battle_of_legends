"""Cardápio da Lanchonete da Vila Carta. Sem Pygame.

Comer dá PV a mais na PRÓXIMA batalha (o lanche é "gasto" quando a batalha começa). Só cabe um lanche por
vez: de barriga cheia, a atendente não vende outro. As regras de compra ficam em game/core/food.py.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FoodItem:
    id: str
    name: str        # como aparece no cardápio e nas falas
    price: int       # BETS
    hp: int          # PV a mais na próxima batalha
    bite: str        # o que aparece no balão em cima do personagem


MENU = [
    FoodItem("maca", "MAÇÃ", 5, 3, "Nham! Maçã"),
    FoodItem("banana", "BANANA", 5, 3, "Nham! Banana"),
    FoodItem("cafe", "CAFÉ", 10, 5, "Ahh, café!"),
    FoodItem("refri", "REFRIGERANTE", 10, 5, "Gluglu! Refri"),
    FoodItem("sorvete", "SORVETE", 15, 8, "Hmm, sorvete!"),
    FoodItem("xburguer", "X-BURGUER", 25, 12, "Nham! X-Burguer"),
]
FOOD = {item.id: item for item in MENU}

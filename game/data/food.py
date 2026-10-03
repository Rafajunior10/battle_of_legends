"""Cardápio da Lanchonete da Vila Carta. Sem Pygame.

Comer mata a FOME (core/hunger.py) e ainda dá PV a mais na PRÓXIMA batalha (o bônus é "gasto" quando a
batalha começa; vale o maior dos lanches comidos). De barriga cheia, a atendente não vende. As regras de compra
ficam em game/core/food.py.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FoodItem:
    id: str
    name: str        # como aparece no cardápio e nas falas
    price: int       # BETS
    hp: int          # PV a mais na próxima batalha
    fill: int        # quanto mata a fome (0 a 100)
    bite: str        # o que aparece no balão em cima do personagem


MENU = [
    FoodItem("maca", "MAÇÃ", 5, 3, 12, "Nham! Maçã"),
    FoodItem("banana", "BANANA", 5, 3, 12, "Nham! Banana"),
    FoodItem("cafe", "CAFÉ", 10, 5, 10, "Ahh, café!"),
    FoodItem("refri", "REFRIGERANTE", 10, 5, 10, "Gluglu! Refri"),
    FoodItem("sorvete", "SORVETE", 15, 8, 18, "Hmm, sorvete!"),
    FoodItem("xburguer", "X-BURGUER", 25, 12, 40, "Nham! X-Burguer"),
]
FOOD = {item.id: item for item in MENU}

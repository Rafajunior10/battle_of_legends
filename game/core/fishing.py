"""Pescaria: o que pode vir no anzol e quanto vale. Regras puras, sem Pygame.

Na cena (scenes/fishing.py): A de frente para a água joga a linha; depois de alguns segundos o peixe morde
("!") e é preciso apertar A rápido (BITE_WINDOW). Cada peixe vira BETS na hora (vendido para a peixaria).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.data.character import Character

WAIT = (2.0, 6.0)          # quanto tempo até o peixe morder
BITE_WINDOW = 0.9          # segundos para puxar depois do "!"


@dataclass(frozen=True)
class Catch:
    id: str
    name: str
    bets: int
    weight: int            # chance relativa
    night: bool = False    # só aparece à noite


CATCHES = [
    Catch("lambari", "LAMBARI", 3, 40),
    Catch("tilapia", "TILÁPIA", 6, 28),
    Catch("traira", "TRAÍRA", 10, 14),
    Catch("tucunare", "TUCUNARÉ", 18, 8),
    Catch("dourado", "PEIXE DOURADO", 50, 2),
    Catch("bagre", "BAGRE DA NOITE", 25, 8, night=True),
    Catch("bota", "BOTA VELHA", 0, 6),
]


def bite_delay(rng: random.Random | None = None) -> float:
    return (rng or random.Random()).uniform(*WAIT)


def catch(rng: random.Random | None = None, night: bool = False) -> Catch:
    rng = rng or random.Random()
    options = [c for c in CATCHES if night or not c.night]
    return rng.choices(options, weights=[c.weight for c in options])[0]


def reward(ch: Character, item: Catch) -> int:
    """Guarda o peixe na conta: BETS e o contador de peixes. Devolve os BETS ganhos."""
    ch.bets += item.bets
    if item.bets:
        ch.fish_caught += 1
    return item.bets

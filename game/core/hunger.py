"""Fome do personagem (0 = morrendo de fome, 100 = de barriga cheia). Regras puras, sem Pygame.

- Cai 1 ponto a cada DECAY_SECONDS andando pelo mundo e BATTLE_COST pontos a cada batalha.
- Comer (core/food.py) devolve pontos. Com FULL ou mais, a barriga está cheia: não dá para comer.
- Abaixo de WEAK, o personagem está fraco demais: não duela até comer alguma coisa.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.data.character import Character

MAX_HUNGER = 100
FULL = 90                 # a partir daqui: barriga cheia
WEAK = 20                 # abaixo daqui: fraco demais para duelar
DECAY_SECONDS = 40.0      # 1 ponto a cada 40 s andando pelo mundo (100 pontos = pouco mais de 1 hora)
BATTLE_COST = 5
WEAK_TEXT = "Você está com fome demais para duelar! Coma alguma coisa na LANCHONETE para recuperar as forças."


def tick(ch: Character, clock: float, dt: float) -> float:
    """Passa o tempo. `clock` guarda os segundos que ainda não viraram um ponto; devolve o novo `clock`."""
    clock += dt
    while clock >= DECAY_SECONDS:
        clock -= DECAY_SECONDS
        ch.hunger = max(0, ch.hunger - 1)
    return clock


def after_battle(ch: Character) -> None:
    ch.hunger = max(0, ch.hunger - BATTLE_COST)


def can_eat(ch: Character) -> bool:
    return ch.hunger < FULL


def can_duel(ch: Character) -> bool:
    return ch.hunger >= WEAK


def eat(ch: Character, fill: int) -> int:
    """Soma `fill` pontos (até o máximo). Devolve quanto subiu."""
    before = ch.hunger
    ch.hunger = min(MAX_HUNGER, ch.hunger + fill)
    return ch.hunger - before


def label(ch: Character) -> str:
    """Como o personagem está, para a ficha e a barra na tela."""
    if ch.hunger >= FULL:
        return "Satisfeito"
    if ch.hunger >= 50:
        return "Bem"
    if ch.hunger >= WEAK:
        return "Com fome"
    return "Fraco de fome"

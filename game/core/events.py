"""Eventos da batalha: o que aconteceu, para a interface animar e narrar.

As regras mudam o estado e devolvem eventos; quem desenha só lê os eventos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .combat import Combatant


@dataclass(frozen=True)
class Event:
    who: Combatant


# ------------------------------------------------------------ dano e proteção
@dataclass(frozen=True)
class Damaged(Event):
    amount: int          # dano que passou para o PV
    blocked: int         # dano segurado por aura + defesa + proteção do legend
    burn_bonus: int = 0  # parte do dano que veio da queimadura
    strength: int = 0    # parte do dano que veio da força de quem atacou
    protected: int = 0   # parte segurada pela proteção (fixa) do legend


@dataclass(frozen=True)
class ProtectionBroken(Event):
    layer: str           # "defesa" ou "aura"


@dataclass(frozen=True)
class DefenseGained(Event):
    amount: int


@dataclass(frozen=True)
class AuraGained(Event):
    amount: int


@dataclass(frozen=True)
class Healed(Event):
    amount: int          # 0 = PV já estavam cheios


# ------------------------------------------------------------ marcadores
@dataclass(frozen=True)
class Burned(Event):
    total: int


@dataclass(frozen=True)
class Chilled(Event):
    total: int           # marcadores de gelo depois de aplicar


@dataclass(frozen=True)
class Frozen(Event):
    """O alvo chegou ao limite de gelo: vai perder o próximo turno."""


@dataclass(frozen=True)
class Poisoned(Event):
    total: int


@dataclass(frozen=True)
class Stunned(Event):
    total: int           # energia que vai perder no próximo turno


# ------------------------------------------------------------ recursos e efeitos especiais
@dataclass(frozen=True)
class EnergyGained(Event):
    amount: int


@dataclass(frozen=True)
class CardsDrawn(Event):
    amount: int


@dataclass(frozen=True)
class IceCloneReady(Event):
    pass


@dataclass(frozen=True)
class IceCloneTriggered(Event):
    """O clone de gelo pegou `who`: a energia dele foi zerada."""


@dataclass(frozen=True)
class NextUtilityFree(Event):
    pass


# ------------------------------------------------------------ turno
@dataclass(frozen=True)
class StunTick(Event):
    amount: int


@dataclass(frozen=True)
class TurnSkipped(Event):
    """Congelado: perdeu o turno."""


@dataclass(frozen=True)
class PoisonTick(Event):
    amount: int


# ------------------------------------------------------------ habilidades dos legends
@dataclass(frozen=True)
class AbilityUsed(Event):
    """`who` usou a habilidade do legend dele."""


@dataclass(frozen=True)
class CardsDiscarded(Event):
    amount: int


@dataclass(frozen=True)
class CardsToBottom(Event):
    amount: int


@dataclass(frozen=True)
class IceShattered(Event):
    """O Cold quebrou o gelo de `who`: descongelou, os marcadores zeraram e o golpe causou `bonus` a mais."""
    bonus: int


@dataclass(frozen=True)
class CloneBlocked(Event):
    """O clone de gelo de `who` (Cold) anulou o ataque do oponente."""

"""Efeitos reutilizáveis das cartas. Uma carta é uma lista de efeitos aplicados em ordem."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from . import abilities
from . import events as ev
from .rules import ICE_LIMIT

if TYPE_CHECKING:
    from .combat import Combatant


class Effect(Protocol):
    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        ...


# ------------------------------------------------------------ dano
@dataclass(frozen=True)
class DamageEffect:
    """Dano = valor da carta + força de quem ataca (+ queimadura do alvo, +1 por marcador).
    Bate na aura, depois na defesa, depois a proteção do legend segura um tanto fixo, e o resto vai no PV.

    pierce_aura / pierce_defense: a camada é anulada (zerada) e o golpe passa direto por ela.
    """
    amount: int
    pierce_defense: bool = False
    pierce_aura: bool = False

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        events: list[ev.Event] = []
        if self.pierce_aura and target.aura:
            target.aura = 0
            events.append(ev.ProtectionBroken(target, "aura"))
        if self.pierce_defense and target.defense:
            target.defense = 0
            events.append(ev.ProtectionBroken(target, "defesa"))
        strength = abilities.attack_bonus(user, target) if user is not target else 0
        total = self.amount + strength + target.burn
        left = total
        for layer in ("aura", "defense"):
            absorbed = min(getattr(target, layer), left)
            setattr(target, layer, getattr(target, layer) - absorbed)
            left -= absorbed
        protected = min(target.protection, left)
        left -= protected
        target.hp = max(0, target.hp - left)
        events.append(ev.Damaged(target, left, total - left, target.burn, strength, protected))
        events += abilities.after_attack(user, target)
        if target.ice_clone and total > 0 and user is not target:
            target.ice_clone = False
            user.energy = 0
            events.append(ev.IceCloneTriggered(user))
        return events


# ------------------------------------------------------------ proteção e cura
@dataclass(frozen=True)
class DefenseEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        user.defense += self.amount
        return [ev.DefenseGained(user, self.amount)]


@dataclass(frozen=True)
class AuraEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        user.aura += self.amount
        return [ev.AuraGained(user, self.amount)]


@dataclass(frozen=True)
class HealEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        healed = min(self.amount, user.max_hp - user.hp)
        user.hp += healed
        return [ev.Healed(user, healed)]


# ------------------------------------------------------------ marcadores no oponente
@dataclass(frozen=True)
class BurnEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        if not target.alive:
            return []
        target.burn += self.amount
        return [ev.Burned(target, target.burn)]


@dataclass(frozen=True)
class IceEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        if not target.alive:
            return []
        target.ice += self.amount
        events: list[ev.Event] = [ev.Chilled(target, min(target.ice, ICE_LIMIT))]
        if target.ice >= ICE_LIMIT:
            target.ice = 0
            target.frozen = True
            events.append(ev.Frozen(target))
        return events


@dataclass(frozen=True)
class PoisonEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        if not target.alive:
            return []
        target.poison += self.amount
        return [ev.Poisoned(target, target.poison)]


@dataclass(frozen=True)
class StunEffect:
    """Paralisar: o alvo perde 1 de energia no próximo turno para cada paralisia (acumula)."""
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        if not target.alive:
            return []
        target.stun = min(target.max_energy, target.stun + self.amount)
        return [ev.Stunned(target, target.stun)]


# ------------------------------------------------------------ recursos
@dataclass(frozen=True)
class EnergyEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        user.energy += self.amount
        return [ev.EnergyGained(user, self.amount)]


@dataclass(frozen=True)
class DrawEffect:
    amount: int

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        return [ev.CardsDrawn(user, user.draw_cards(self.amount))]


# ------------------------------------------------------------ efeitos especiais
@dataclass(frozen=True)
class IceCloneEffect:
    """Até o seu próximo turno: se o oponente causar dano, a energia dele zera."""

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        user.ice_clone = True
        return [ev.IceCloneReady(user)]


@dataclass(frozen=True)
class FreeUtilityEffect:
    """O próximo ataque de utilidade não custa energia."""

    def apply(self, user: Combatant, target: Combatant) -> list[ev.Event]:
        user.free_utility = True
        return [ev.NextUtilityFree(user)]

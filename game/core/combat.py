"""Estado de quem está duelando e as regras de turno. Nada aqui desenha nada.

Turno:
  começo  -> defesa e aura somem, energia volta (a do legend, menos as paralisias), congelado perde o turno
  meio    -> joga cartas
  fim     -> veneno tira 1 PV por marcador (de QUEM estiver envenenado: nas duas passagens de turno),
             compra até ter HAND_SIZE cartas na mão
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..cards import CardDef, Deck
from . import abilities
from . import events as ev
from .rules import HAND_MAX, HAND_SIZE, MAX_ENERGY

if TYPE_CHECKING:
    from ..legends import LegendDef


@dataclass(eq=False)
class Combatant:
    name: str
    level: int
    max_hp: int
    deck: Deck
    is_player: bool = False
    hp: int = -1                  # -1 = começa com o PV cheio
    defense: int = 0
    aura: int = 0
    energy: int = 0
    burn: int = 0                 # marcadores de queimadura (+1 de dano recebido cada)
    ice: int = 0                  # marcadores de gelo (congela ao chegar em ICE_LIMIT)
    poison: int = 0               # marcadores de veneno (1 PV por marcador no fim do turno)
    stun: int = 0                 # energia que vai perder no próximo turno
    frozen: bool = False          # vai perder o próximo turno
    ice_clone: bool = False       # clone de gelo armado até o próximo turno
    free_utility: bool = False    # próximo ataque de utilidade sai de graça
    hand: list[CardDef] = field(default_factory=list)
    legend: LegendDef | None = None   # em quem se transformou (None = monstro, sem legend)
    strength: int = 0             # força: somada ao dano de cada golpe
    protection: int = 0           # proteção fixa: tirada de cada golpe que chega ao PV
    max_energy: int = MAX_ENERGY  # energia recebida por turno
    ability_used: bool = False    # habilidade ativa já usada neste turno

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def draw_cards(self, n: int) -> int:
        """Compra até n cartas (respeitando o limite da mão). Devolve quantas comprou."""
        got = 0
        for _ in range(n):
            if len(self.hand) >= HAND_MAX:
                break
            card = self.deck.draw()
            if card is None:
                break
            self.hand.append(card)
            got += 1
        return got

    def refill_hand(self) -> int:
        return self.draw_cards(max(0, HAND_SIZE - len(self.hand)))

    def cost_of(self, card: CardDef) -> int:
        """Custo real da carta agora (Golpe Duplo deixa o próximo ataque de utilidade de graça)."""
        return 0 if self.free_utility and card.is_utility_attack else card.cost

    def can_play(self, card: CardDef) -> bool:
        return card in self.hand and self.cost_of(card) <= self.energy

    def playable(self) -> list[CardDef]:
        return [c for c in self.hand if self.cost_of(c) <= self.energy]


def start_turn(c: Combatant) -> list[ev.Event]:
    """Começo do turno. Se vier TurnSkipped nos eventos, o combatente não joga neste turno."""
    events: list[ev.Event] = []
    c.defense = 0
    c.aura = 0
    c.ice_clone = False
    c.ability_used = False
    c.energy = max(0, c.max_energy - c.stun)
    if c.stun:
        events.append(ev.StunTick(c, c.stun))
        c.stun = 0
    if c.frozen:
        c.frozen = False
        c.energy = 0
        events.append(ev.TurnSkipped(c))
    return events


def poison_tick(c: Combatant) -> list[ev.Event]:
    """O veneno tira 1 PV por marcador."""
    if not c.poison or not c.alive:
        return []
    dmg = min(c.poison, c.hp)
    c.hp -= dmg
    return [ev.PoisonTick(c, dmg)]


def end_turn(c: Combatant, foe: Combatant | None = None) -> list[ev.Event]:
    """Fim do turno de `c`: o veneno age em quem estiver envenenado (os dois lados: o veneno pega em toda
    passagem de turno) e a mão de `c` é completada até HAND_SIZE."""
    events = poison_tick(c)
    if foe is not None:
        events += poison_tick(foe)
    if c.alive:
        events.append(ev.CardsDrawn(c, c.refill_hand()))
    return events


def pay_card(user: Combatant, card: CardDef, free: bool = False) -> None:
    """Gasta a energia e manda a carta da mão para o descarte. Os efeitos vêm depois.
    `free`: a carta não está na mão nem custa nada (ex.: a habilidade do Mimo já cuidou dela)."""
    if free:
        return
    if not user.can_play(card):
        raise ValueError(f"{user.name} não pode jogar {card.name} agora")
    cost = user.cost_of(card)
    if cost < card.cost:
        user.free_utility = False     # o desconto do Golpe Duplo foi usado
    user.energy -= cost
    user.hand.remove(card)
    user.deck.discard.append(card)


def play_card(user: Combatant, target: Combatant, card: CardDef) -> list[ev.Event]:
    """Joga a carta inteira de uma vez (usado pela IA e pelos testes; a cena anima efeito por efeito)."""
    pay_card(user, card)
    if abilities.clone_blocks(target, card):
        return abilities.block_with_clone(user, target)
    events: list[ev.Event] = []
    for effect in card.effects:
        events += effect.apply(user, target)
    return events


def loser(*fighters: Combatant) -> Combatant | None:
    return next((f for f in fighters if not f.alive), None)

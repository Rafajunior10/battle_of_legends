"""Habilidades dos legends (game/data/legends.py). Regras puras: mudam o estado e devolvem eventos.

Ativas (o jogador aciona, 1 vez por turno):
    Drogoz  descarta 3 cartas da mão e cura 15.
    Mimo    revela as 3 cartas do topo; joga de graça 1 carta de VENENO (ou NINJA) entre elas; as outras vão
            para o fundo do baralho.
Passivas (funcionam sozinhas):
    Blitz   +9 de força enquanto a defesa + aura que ele ganhou no turno for 9 ou mais (zeram no começo do turno).
    Cold    atacar um oponente congelado quebra o gelo: +5 de dano, ele descongela e o gelo zera.
            Com o Clone de Gelo ativo, o 1º ataque do oponente é anulado (sem dano nem efeito) e ganha 1 de gelo.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import events as ev

if TYPE_CHECKING:          # só para as dicas de tipo: importar de verdade criaria um ciclo (cards -> effects -> aqui)
    from game.core.combat import Combatant
    from game.data.cards import CardDef
    from game.data.legends import LegendDef

DROGOZ_DISCARD, DROGOZ_HEAL = 3, 15
MIMO_REVEAL = 3
MIMO_TYPES = {"veneno", "ninja"}       # cartas que o Mimo pode jogar de graça (arquétipo ou classe)
BLITZ_GUARD, BLITZ_BONUS = 9, 9        # defesa + aura do turno necessária / força extra
COLD_SHATTER = 5                        # dano extra ao quebrar o gelo de um congelado
COLD_CLONE_ICE = 1                      # gelo no atacante que bate no clone do Cold


def become(c: Combatant, legend_id: str | None) -> LegendDef | None:
    """Transforma o duelista no legend: vida, força, proteção e energia passam a ser as dele."""
    from game.data.legends import LEGENDS
    legend = LEGENDS.get(legend_id) if legend_id else None
    if legend is None:
        return None
    c.legend = legend
    c.max_hp = c.hp = legend.hp
    c.strength = legend.strength
    c.protection = legend.protection
    c.max_energy = legend.energy
    return legend


def legend_id(c: Combatant) -> str | None:
    return c.legend.id if c.legend else None


# ------------------------------------------------------------ passivas
def attack_bonus(user: Combatant, target: Combatant | None = None) -> int:
    """Quanto soma ao dano de cada golpe de `user`: força (+ Blitz) (+ Cold contra um congelado). Não muda nada."""
    bonus = user.strength
    if legend_id(user) == "blitz" and user.defense + user.aura >= BLITZ_GUARD:
        bonus += BLITZ_BONUS
    if target is not None and legend_id(user) == "cold" and target.frozen:
        bonus += COLD_SHATTER
    return bonus


def after_attack(user: Combatant, target: Combatant) -> list[ev.Event]:
    """Depois do golpe do Cold num congelado: o gelo quebra (descongela e os marcadores zeram)."""
    if legend_id(user) != "cold" or not target.frozen:
        return []
    target.frozen = False
    target.ice = 0
    return [ev.IceShattered(target, COLD_SHATTER)]


def clone_blocks(target: Combatant, card: CardDef) -> bool:
    """O clone de gelo do Cold anula este ataque? (o 1º ataque do oponente depois de armado)"""
    return bool(card.damage) and target.ice_clone and legend_id(target) == "cold"


def block_with_clone(user: Combatant, target: Combatant) -> list[ev.Event]:
    """Anula o ataque de `user` no clone do Cold `target`: sem dano, sem efeito, e `user` ganha gelo."""
    from game.core.effects import IceEffect
    target.ice_clone = False
    return [ev.CloneBlocked(target), *IceEffect(COLD_CLONE_ICE).apply(target, user)]


# ------------------------------------------------------------ ativas
def can_use(c: Combatant) -> bool:
    """O botão HABILIDADE está liberado agora?"""
    if not c.legend or not c.legend.active or c.ability_used:
        return False
    if c.legend.id == "drogoz":
        return len(c.hand) >= DROGOZ_DISCARD
    if c.legend.id == "mimo":
        return bool(c.deck.draw_pile or c.deck.discard)
    return False


def drogoz(c: Combatant, discards: list[CardDef]) -> list[ev.Event]:
    """Descarta as 3 cartas escolhidas e cura 15."""
    if not can_use(c) or legend_id(c) != "drogoz":
        raise ValueError("habilidade indisponível")
    if len(discards) != DROGOZ_DISCARD or any(card not in c.hand for card in discards):
        raise ValueError(f"escolha {DROGOZ_DISCARD} cartas da mão")
    c.ability_used = True
    for card in discards:
        c.hand.remove(card)
        c.deck.discard.append(card)
    healed = min(DROGOZ_HEAL, c.max_hp - c.hp)
    c.hp += healed
    return [ev.AbilityUsed(c), ev.CardsDiscarded(c, len(discards)), ev.Healed(c, healed)]


def mimo_reveal(c: Combatant) -> list[CardDef]:
    """Tira as 2 cartas do topo do baralho para o Mimo escolher (gasta a habilidade do turno)."""
    if not can_use(c) or legend_id(c) != "mimo":
        raise ValueError("habilidade indisponível")
    c.ability_used = True
    revealed = []
    for _ in range(MIMO_REVEAL):
        card = c.deck.draw()
        if card is None:
            break
        revealed.append(card)
    return revealed


def mimo_can_play(card: CardDef) -> bool:
    return card.archetype in MIMO_TYPES


def mimo_finish(c: Combatant, revealed: list[CardDef], chosen: CardDef | None) -> list[ev.Event]:
    """A escolhida vai para o descarte (a cena aplica os efeitos dela de graça); as outras vão para o fundo."""
    if chosen is not None and (chosen not in revealed or not mimo_can_play(chosen)):
        raise ValueError("o Mimo só joga cartas de VENENO ou NINJA reveladas")
    rest = [card for card in revealed if card is not chosen]
    for card in rest:
        c.deck.draw_pile.insert(0, card)          # fundo do baralho = começo da lista (compra sai do fim)
    if chosen is not None:
        c.deck.discard.append(chosen)
    return [ev.CardsToBottom(c, len(rest))] if rest else []

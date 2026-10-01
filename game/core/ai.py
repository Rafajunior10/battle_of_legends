"""IA dos oponentes. Só olha o estado e devolve a carta escolhida; nunca altera o duelo real.

easy   — joga meio no aleatório, com preferência por atacar.
normal — segue regras simples: mata se puder, fura proteção grande, cura se estiver mal, aplica marcadores.
hard   — simula as sequências de jogadas deste turno em cópias do estado e escolhe a melhor.
"""
from __future__ import annotations

import random
from dataclasses import replace

from game.core import abilities
from game.core.combat import Combatant, play_card
from game.data.cards import CardDef

DIFFICULTIES = ("easy", "normal", "hard")
SEARCH_DEPTH = 4          # máximo de cartas simuladas em sequência
AVG_DAMAGE_PER_ENERGY = 3.0
KILL_SOONER_BONUS = 100.0
BIG_PROTECTION = 6        # a partir daqui vale a pena furar a camada


def choose_card(me: Combatant, foe: Combatant, difficulty: str = "normal",
                rng: random.Random | None = None) -> CardDef | None:
    """Carta que `me` vai jogar agora, ou None para encerrar o turno."""
    rng = rng or random.Random()
    playable = me.playable()
    if not playable:
        return None
    if difficulty == "easy":
        return _easy(playable, rng)
    if difficulty == "hard":
        return _hard(me, foe, rng)
    return _normal(me, foe, playable, rng)


def expected_damage(card: CardDef, foe: Combatant, me: Combatant | None = None) -> int:
    """Dano que a carta tiraria do PV agora: força de `me`, queimadura, aura, defesa, proteção e perfuração."""
    if not card.damage:
        return 0
    aura = 0 if card.pierce_aura else foe.aura
    defense = 0 if card.pierce_defense else foe.defense
    bonus = abilities.attack_bonus(me, foe) if me is not None else 0
    total = 0
    for _ in range(card.repeat):
        hit = card.damage + bonus + foe.burn
        soaked = min(aura, hit)
        aura -= soaked
        hit -= soaked
        soaked = min(defense, hit)
        defense -= soaked
        hit -= soaked
        total += max(0, hit - foe.protection)
    return total


def _breaks_big_protection(card: CardDef, foe: Combatant) -> bool:
    return ((card.pierce_aura and foe.aura >= BIG_PROTECTION)
            or (card.pierce_defense and foe.defense >= BIG_PROTECTION))


def _easy(playable: list[CardDef], rng: random.Random) -> CardDef:
    attacks = [c for c in playable if c.damage]
    if attacks and rng.random() < 0.6:
        return rng.choice(attacks)
    return rng.choice(playable)


def _normal(me: Combatant, foe: Combatant, playable: list[CardDef], rng: random.Random) -> CardDef:
    attacks = [c for c in playable if c.damage]
    lethal = [c for c in attacks if expected_damage(c, foe, me) >= foe.hp]
    if lethal:
        return min(lethal, key=me.cost_of)
    piercers = [c for c in attacks if _breaks_big_protection(c, foe)]
    if piercers:
        return max(piercers, key=lambda c: expected_damage(c, foe, me))
    heals = [c for c in playable if c.heal and not c.damage]
    if me.hp <= me.max_hp * 0.5 and heals:
        return max(heals, key=lambda c: c.heal)
    markers = [c for c in playable if c.burn or c.ice or c.poison or c.stun]
    if markers and rng.random() < 0.6:
        return max(markers, key=lambda c: c.burn + c.ice + c.poison + c.stun + expected_damage(c, foe, me))
    guards = [c for c in playable if (c.defense or c.aura) and not c.damage]
    if me.defense + me.aura == 0 and guards and rng.random() < 0.35:
        return max(guards, key=lambda c: c.defense + c.aura)
    if attacks:
        return max(attacks, key=lambda c: (expected_damage(c, foe, me), -me.cost_of(c)))
    return rng.choice(playable)


# ------------------------------------------------------------ IA difícil
def _hard(me: Combatant, foe: Combatant, rng: random.Random) -> CardDef | None:
    low_hp = me.hp <= me.max_hp * 0.5
    _, best_id = _search(me, foe, SEARCH_DEPTH, low_hp, rng)
    if best_id is None:
        return None
    return next(c for c in me.hand if c.id == best_id)


def _search(me: Combatant, foe: Combatant, depth: int, low_hp: bool,
            rng: random.Random) -> tuple[float, str | None]:
    """Melhor valor alcançável a partir daqui e a primeira carta para chegar lá (None = parar)."""
    best: tuple[float, str | None] = (_value(me, foe, low_hp), None)
    if depth == 0:
        return best
    tried = set()
    for card in me.playable():
        if card.id in tried:
            continue
        tried.add(card.id)
        sim_me, sim_foe = _clone(me), _clone(foe)
        play_card(sim_me, sim_foe, next(c for c in sim_me.hand if c.id == card.id))
        if sim_foe.alive:
            value, _ = _search(sim_me, sim_foe, depth - 1, low_hp, rng)
        else:
            value = _value(sim_me, sim_foe, low_hp) + depth * KILL_SOONER_BONUS   # vencer já é melhor que depois
        value += rng.random() * 0.01     # desempate aleatório: não ficar previsível
        if value > best[0]:
            best = (value, card.id)
    return best


def _value(me: Combatant, foe: Combatant, low_hp: bool) -> float:
    """Quão bom é este estado para `me` no fim do turno."""
    if not foe.alive:
        return 10_000.0
    threat = max(0.0, (foe.max_energy - foe.stun) * AVG_DAMAGE_PER_ENERGY) * (0 if foe.frozen else 1)
    value = -foe.hp * 3.0
    value += foe.poison * 4.0                      # tira PV todo turno até o fim do duelo
    value += foe.burn * 3.0                        # cada golpe futuro bate mais forte
    value += foe.ice * 2.0 + (20.0 if foe.frozen else 0.0)
    value += foe.stun * 4.0
    value += min(me.defense + me.aura, threat) * 2.0
    value += 6.0 if me.ice_clone else 0.0
    value += me.hp * (2.0 if low_hp else 1.0)
    value += len(me.hand) * 0.5
    return value


def _clone(c: Combatant) -> Combatant:
    """Cópia para simular jogadas sem mexer no duelo real."""
    return replace(c, deck=c.deck.clone(), hand=list(c.hand))



# ------------------------------------------------------------ habilidades dos legends
def mimo_pick(revealed: list[CardDef], me: Combatant, foe: Combatant) -> CardDef | None:
    """Mimo: das cartas reveladas que ele pode jogar de graça, a que causa mais estrago."""
    options = [c for c in revealed if abilities.mimo_can_play(c)]
    if not options:
        return None
    return max(options, key=lambda c: (expected_damage(c, foe, me) + 2 * (c.poison + c.burn + c.ice + c.stun),
                                       c.cost))


def drogoz_discards(me: Combatant) -> list[CardDef] | None:
    """Drogoz: no fim do turno (a mão vai ser completada de qualquer jeito), descarta as 3 cartas mais caras
    para curar, se ele estiver machucado."""
    if not abilities.can_use(me) or me.max_hp - me.hp < 10:
        return None
    return sorted(me.hand, key=lambda c: c.cost, reverse=True)[:abilities.DROGOZ_DISCARD]

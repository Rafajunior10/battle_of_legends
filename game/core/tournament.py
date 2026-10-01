"""Torneio do Coliseu: 3 rodadas eliminatórias contra oponentes gerados pelo nível do jogador.

- Cada rodada é um duelo; perder elimina, vencer libera a próxima.
- Rodada 1: nível do jogador; rodada 2: +1; final: +2 e IA difícil.
- Todo duelo do torneio dá XP em dobro; o campeão ainda leva TOURNAMENT_PRIZE BETS.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..cards import ARCHETYPE_NAMES, CARD_LIST, DECK_MIN, MAX_CARD_LEVEL, MAX_COPIES, UTILITY
from ..legends import default_legend
from ..looks import (
    BOTTOMS,
    CLOTH_COLORS,
    GENDERS,
    HAIR_COLORS,
    HAIR_STYLES,
    HATS,
    SHOE_COLORS,
    SKIN_TONES,
    TOPS,
    Look,
)
from ..opponents import trainer_hp

ROUNDS = 3
TOURNAMENT_PRIZE = 500
XP_MULTIPLIER = 2
DECK_SIZE = DECK_MIN
ARCHETYPES = [a for a in ARCHETYPE_NAMES if a != UTILITY]
ROUND_AI = ("normal", "normal", "hard")
ROUND_RARITIES = (("comum",), ("comum", "rara"), ("comum", "rara", "epica"))
ROUND_TITLES = ("PRIMEIRA RODADA", "SEMIFINAL", "GRANDE FINAL")
FIGHTER_NAMES = ["KAI", "LUNA", "DANTE", "IRIS", "TORO", "MEL", "RUBI", "OTTO", "NINA B.", "VICTOR",
                 "ZOE", "BENTO", "JADE", "IGOR", "LARA"]



def random_look(rng: random.Random) -> Look:
    """Aparência sorteada para os lutadores do torneio."""
    gender = rng.choice(GENDERS)
    hat = rng.choice(["nenhum", "nenhum", "nenhum", *HATS])        # chapéu é mais raro
    colors = list(CLOTH_COLORS)
    return Look(gender=gender, hair=rng.choice(HAIR_STYLES), hair_color=rng.choice(list(HAIR_COLORS)),
                skin=rng.randrange(len(SKIN_TONES)), top=rng.choice(TOPS[gender]), shirt=rng.choice(colors),
                bottom=rng.choice(BOTTOMS[gender]), legs=rng.choice(colors), shoes=rng.choice(list(SHOE_COLORS)),
                hat=hat, hat_color=rng.choice(HATS[hat]) if HATS[hat] else "").fitted()


def _fighter(round_index: int, player_level: int, name: str, rng: random.Random) -> dict:
    level = player_level + round_index
    rarities = ROUND_RARITIES[round_index]
    archetype = rng.choice(ARCHETYPES)     # 1 arquétipo + Utilidades, como qualquer deck
    pool = [c.id for c in CARD_LIST if c.rarity in rarities and c.archetype in (archetype, UTILITY)]
    deck: list[str] = []
    while len(deck) < DECK_SIZE:
        cid = rng.choice(pool)
        if deck.count(cid) < MAX_COPIES:
            deck.append(cid)
    card_level = min(MAX_CARD_LEVEL, 1 + round_index)
    return {
        "legend": default_legend(archetype),
        "id": f"torneio{round_index + 1}", "kind": "tournament", "name": name, "level": level,
        "hp": trainer_hp(level), "ai": ROUND_AI[round_index], "deck": deck,
        "card_levels": {c: card_level for c in deck}, "xp_mult": XP_MULTIPLIER,
        "look": random_look(rng),
        "intro": f"{ROUND_TITLES[round_index]}! {name} (Nv. {level}, {ARCHETYPE_NAMES[archetype]}) entra na arena!",
        "lose": "Você mereceu. Vá até o fim!", "win": "O Coliseu não perdoa!",
    }


@dataclass
class Tournament:
    player_level: int
    rng: random.Random = field(default_factory=random.Random)
    round: int = 0              # índice da rodada atual (0, 1, 2)
    eliminated: bool = False
    opponents: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.opponents:
            names = self.rng.sample(FIGHTER_NAMES, ROUNDS)
            self.opponents = [_fighter(i, self.player_level, names[i], self.rng) for i in range(ROUNDS)]

    @property
    def champion(self) -> bool:
        return self.round >= ROUNDS

    @property
    def over(self) -> bool:
        return self.champion or self.eliminated

    def current(self) -> dict:
        if self.over:
            raise RuntimeError("o torneio já acabou")
        return dict(self.opponents[self.round])

    def record(self, won: bool) -> None:
        """Registra o resultado da rodada atual."""
        if self.over:
            raise RuntimeError("o torneio já acabou")
        if won:
            self.round += 1
        else:
            self.eliminated = True

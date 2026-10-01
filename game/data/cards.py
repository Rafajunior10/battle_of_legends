"""Cartas, arquétipos, raridades, evolução, packs e o baralho de batalha.

Uma carta é só dados. O que ela faz vem de `effects` (game/core/effects.py) e a descrição
é gerada a partir dos números, então uma carta evoluída sempre mostra os valores certos.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace

from game.core.effects import (
    AuraEffect,
    BurnEffect,
    DamageEffect,
    DefenseEffect,
    DrawEffect,
    Effect,
    EnergyEffect,
    FreeUtilityEffect,
    HealEffect,
    IceCloneEffect,
    IceEffect,
    PoisonEffect,
    StunEffect,
)

UTILITY = "utilidades"
ARCHETYPE_NAMES = {"fogo": "Fogo", "gelo": "Gelo", "raio": "Raio", "veneno": "Veneno", UTILITY: "Utilidades"}
ELEMENTS = [a for a in ARCHETYPE_NAMES if a != UTILITY]     # os tipos de deck (Utilidades combina com todos)

MAX_CARD_LEVEL = 3
LEVEL_BONUS = 0.25     # por nível, sobre o valor base (dano, defesa, aura e cura)
MAX_COPIES = 3         # cópias de uma mesma carta na coleção

RARITY_PRICES = {"comum": 40, "rara": 90, "epica": 180}
RARITY_NAMES = {"comum": "Comum", "rara": "Rara", "epica": "Épica"}


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


@dataclass(frozen=True)
class CardDef:
    id: str
    name: str
    archetype: str         # fogo | gelo | raio | veneno | utilidades
    cost: int
    rarity: str            # comum | rara | epica
    icon: str              # desenho 12x12 em pixelart.ICONS
    damage: int = 0
    defense: int = 0
    aura: int = 0
    heal: int = 0
    burn: int = 0          # marcadores de queimadura no oponente
    ice: int = 0           # marcadores de gelo no oponente
    poison: int = 0        # marcadores de veneno no oponente
    stun: int = 0          # paralisias (energia que o oponente perde no próximo turno)
    energy: int = 0
    draw: int = 0
    pierce_defense: bool = False   # atravessa e anula a defesa
    pierce_aura: bool = False      # atravessa e anula a aura
    ice_clone: bool = False        # próximo turno: se o oponente causar dano, zera a energia dele
    free_next_utility: bool = False
    repeat: int = 1                # quantas vezes todos os efeitos acontecem
    fx: str = "slash"              # animação do golpe na batalha
    label: str = ""                # nome curto desenhado na carta (padrão: name)
    level: int = 1                 # evolução (1 a MAX_CARD_LEVEL), comprada na loja

    # ------------------------------------------------------------ apresentação
    @property
    def short(self) -> str:
        return self.label or self.name

    @property
    def is_utility_attack(self) -> bool:
        return self.archetype == UTILITY and self.damage > 0

    @property
    def price(self) -> int:
        return RARITY_PRICES[self.rarity]

    @property
    def sell_price(self) -> int:
        return self.price // 2

    @property
    def stats(self) -> list[tuple[str, int]]:
        """Números de destaque desenhados na carta: (tipo, valor)."""
        pairs = [("dano", self.damage), ("defesa", self.defense), ("aura", self.aura), ("cura", self.heal)]
        shown = [(kind, value) for kind, value in pairs if value]
        if not shown:
            shown = [(kind, value) for kind, value in (("energia", self.energy), ("compra", self.draw)) if value]
        return shown

    @property
    def value_label(self) -> str:
        return "/".join(str(value) for _, value in self.stats)

    @property
    def text(self) -> str:
        """Descrição gerada a partir dos números da carta."""
        markers = [(n, name) for n, name in ((self.burn, "queimadura"), (self.ice, "gelo"), (self.poison, "veneno"))
                   if n]
        phrases = [
            (self.pierce_aura, "Atravessa a aura e anula ela."),
            (self.pierce_defense, "Atravessa a defesa e anula ela."),
            (self.damage, f"Causa {self.damage} de dano."),
            (self.defense, f"+{self.defense} de defesa."),
            (self.aura, f"+{self.aura} de aura."),
            (self.heal, f"Cura {self.heal} PV."),
            *((True, f"Adiciona {n} {_plural(n, 'marcador', 'marcadores')} de {name}.") for n, name in markers),
            (self.stun, f"Paralisa o oponente {self.stun} {_plural(self.stun, 'vez', 'vezes')}."),
            (self.energy, f"Ganha {self.energy} de energia."),
            (self.draw, f"Compra {self.draw} {_plural(self.draw, 'carta', 'cartas')}."),
            (self.ice_clone, "No próximo turno, se o oponente causar dano, a energia dele zera."),
            (self.free_next_utility, "Seu próximo ataque de utilidade não tem custo."),
            (self.repeat > 1, f"Dano e efeitos acontecem {self.repeat} vezes."),
        ]
        return " ".join(text for show, text in phrases if show)

    # ------------------------------------------------------------ regras
    @property
    def effects(self) -> list[Effect]:
        """Efeitos da carta, na ordem em que acontecem."""
        once: list[Effect] = []
        if self.damage:
            once.append(DamageEffect(self.damage, self.pierce_defense, self.pierce_aura))
        for amount, effect in ((self.burn, BurnEffect), (self.ice, IceEffect), (self.poison, PoisonEffect),
                               (self.stun, StunEffect), (self.defense, DefenseEffect), (self.aura, AuraEffect),
                               (self.heal, HealEffect), (self.energy, EnergyEffect), (self.draw, DrawEffect)):
            if amount:
                once.append(effect(amount))
        if self.ice_clone:
            once.append(IceCloneEffect())
        if self.free_next_utility:
            once.append(FreeUtilityEffect())
        return once * self.repeat

    def at_level(self, level: int) -> CardDef:
        """A mesma carta evoluída. Dano/defesa/aura/cura sobem ~25% do valor base por nível;
        cartas só de recurso ganham +1 de compra (ou de energia) por nível. Marcadores não mudam."""
        level = max(1, min(MAX_CARD_LEVEL, level))
        if level == self.level:
            return self
        base = CARDS.get(self.id, self)
        steps = level - 1

        def up(value: int) -> int:
            return value + max(1, math.ceil(value * LEVEL_BONUS)) * steps if value else 0

        changes = {"level": level, "damage": up(base.damage), "defense": up(base.defense), "aura": up(base.aura),
                   "heal": up(base.heal)}
        if not (base.damage or base.defense or base.aura or base.heal):
            if base.draw:
                changes["draw"] = base.draw + steps
            else:
                changes["energy"] = base.energy + steps
        return replace(base, **changes)


C = CardDef
CARD_LIST = [
    # ---- fogo
    C("bola_de_fogo", "Bola de Fogo", "fogo", 3, "epica", "meteor", damage=8, burn=2, fx="flame",
      label="Bola Fogo"),
    C("queimar", "Queimar", "fogo", 2, "comum", "flame", damage=4, aura=4, burn=1, fx="flame"),
    C("fenix", "Fênix", "fogo", 1, "rara", "heart", defense=6, heal=6),
    C("fumaca", "Fumaça", "fogo", 1, "comum", "smoke", damage=1, aura=10, stun=1, fx="smoke"),
    # ---- gelo
    C("fica_frio_ai", "Fica Frio Aí", "gelo", 3, "epica", "ice", damage=6, ice=4, fx="ice", label="Fica Frio"),
    C("clone_de_gelo", "Clone de Gelo", "gelo", 2, "rara", "crystal", defense=5, aura=8, ice_clone=True,
      label="Clone Gelo"),
    C("bola_de_gelo", "Bola de Gelo", "gelo", 2, "comum", "ice", damage=4, ice=2, fx="ice", label="Bola Gelo"),
    C("gelo_fino", "Gelo Fino", "gelo", 1, "comum", "crystal", damage=2, defense=4, ice=1, fx="ice"),
    # ---- raio
    C("choque_do_trovao", "Choque do Trovão", "raio", 3, "rara", "bolt", damage=7, stun=2, fx="bolt",
      label="Trovão"),
    C("zeus_luz", "Zeus Luz", "raio", 1, "comum", "stun", damage=4, stun=1, fx="stun"),
    C("tela_de_luz", "Tela de Luz", "raio", 2, "rara", "wall", defense=5, aura=5, label="Tela Luz"),
    C("chicote_de_raios", "Chicote de Raios", "raio", 1, "comum", "bolt", damage=1, energy=2, draw=2, fx="bolt",
      label="Chicote"),
    # ---- veneno
    C("agulha_escarlate", "Agulha Escarlate", "veneno", 3, "epica", "dagger", damage=2, poison=4, fx="poison",
      label="Agulha"),
    C("garras_de_veneno", "Garras de Veneno", "veneno", 1, "rara", "fang", poison=2, fx="poison", label="Garras"),
    C("cortina_de_veneno", "Cortina de Veneno", "veneno", 2, "rara", "poison", aura=8, poison=1, fx="poison",
      label="Cortina"),
    C("picadura_de_mosquito", "Picadura de Mosquito", "veneno", 1, "comum", "slime", damage=1, poison=1,
      fx="poison", label="Picadura"),
    # ---- utilidades (combinam com qualquer arquétipo)
    C("pocao_da_vida", "Poção da Vida", UTILITY, 1, "rara", "potion", heal=15, label="Poção Vida"),
    C("defender", "Defender", UTILITY, 1, "comum", "shield", defense=10),
    C("farma_aura", "Farma Aura", UTILITY, 1, "comum", "aura", aura=10),
    C("foco", "Foco", UTILITY, 0, "comum", "star", energy=2, draw=1),
    C("murrao", "Murrão", UTILITY, 1, "comum", "fist", damage=4),
    C("amansa_loko", "Amansa Loko", UTILITY, 2, "comum", "sword", damage=6, label="Amansa"),
    C("chute_violento", "Chute Violento", UTILITY, 1, "comum", "boot", damage=4, pierce_aura=True, fx="pierce",
      label="Chute"),
    C("golpe_perfurante", "Golpe Perfurante", UTILITY, 1, "comum", "spear", damage=4, pierce_defense=True,
      fx="pierce", label="Perfurante"),
    C("contra_golpe", "Contra Golpe", UTILITY, 2, "rara", "thorn", damage=6, defense=4, aura=4, label="Contra"),
    C("golpe_duplo", "Golpe Duplo", UTILITY, 2, "rara", "dagger", damage=4, free_next_utility=True,
      label="G. Duplo"),
    C("golpes_rapidos", "Golpes Rápidos", UTILITY, 2, "rara", "sword", damage=4, repeat=2, label="G. Rápidos"),
]
del C
CARDS = {c.id: c for c in CARD_LIST}


def make_deck(**counts: int) -> list[str]:
    """Monta uma lista de ids a partir de contagens: make_deck(queimar=3, defender=2)."""
    for card_id in counts:
        if card_id not in CARDS:
            raise KeyError(f"carta desconhecida: {card_id}")
    return [card_id for card_id, n in counts.items() for _ in range(n)]


# Deck inicial do jogador: Fogo + Utilidades, 20 cartas
PLAYER_DECK = make_deck(queimar=3, fumaca=3, fenix=1, murrao=3, amansa_loko=2, defender=3, farma_aura=2, foco=2,
                        chute_violento=1)
DECK_MIN, DECK_MAX = 20, 30
START_BETS = 100

# Cartas avulsas vendidas na loja (com os packs desligados, todas estão à venda)
SHOP_STOCK = [c.id for c in CARD_LIST]


@dataclass(frozen=True)
class Pack:
    id: str
    name: str
    price: int
    color: tuple
    cards: tuple    # 10 cartas diferentes entre si


_PACK_UTILITIES = ("murrao", "amansa_loko", "defender", "farma_aura", "chute_violento", "golpe_perfurante")

# Packs: um por arquétipo (as 4 cartas dele + 6 utilidades). A aba de packs da loja está
# desligada por enquanto (veja scenes/shop.py); o sistema continua pronto para ser reativado.
PACKS = [
    Pack("pack_fogo", "Pack de Fogo", 150, (216, 88, 48),
         ("bola_de_fogo", "queimar", "fenix", "fumaca", *_PACK_UTILITIES)),
    Pack("pack_gelo", "Pack de Gelo", 150, (72, 160, 216),
         ("fica_frio_ai", "clone_de_gelo", "bola_de_gelo", "gelo_fino", *_PACK_UTILITIES)),
    Pack("pack_raio", "Pack de Raio", 150, (216, 168, 32),
         ("choque_do_trovao", "zeus_luz", "tela_de_luz", "chicote_de_raios", *_PACK_UTILITIES)),
    Pack("pack_veneno", "Pack de Veneno", 150, (136, 72, 184),
         ("agulha_escarlate", "garras_de_veneno", "cortina_de_veneno", "picadura_de_mosquito", *_PACK_UTILITIES)),
]
PACK_SIZE = 3
RARITY_WEIGHTS = {"comum": 6, "rara": 3, "epica": 1}


def open_pack(pack: Pack, rng: random.Random | None = None) -> list[str]:
    """Sorteia PACK_SIZE cartas diferentes do pack, com peso pela raridade."""
    rng = rng or random.Random()
    pool = list(pack.cards)
    got = []
    for _ in range(PACK_SIZE):
        weights = [RARITY_WEIGHTS[CARDS[c].rarity] for c in pool]
        pick = rng.choices(pool, weights)[0]
        pool.remove(pick)
        got.append(pick)
    return got


class Deck:
    """Pilha de compra + descarte. Quando a pilha acaba, o descarte é embaralhado de volta."""

    def __init__(self, card_ids: list[str], rng: random.Random | None = None,
                 levels: dict[str, int] | None = None):
        self.rng = rng or random.Random()
        levels = levels or {}
        self.draw_pile = [CARDS[i].at_level(levels.get(i, 1)) for i in card_ids]
        self.rng.shuffle(self.draw_pile)
        self.discard: list[CardDef] = []

    def clone(self) -> Deck:
        """Cópia independente (inclusive do sorteio), para simulações da IA."""
        copy = Deck.__new__(Deck)
        copy.rng = random.Random()
        copy.rng.setstate(self.rng.getstate())
        copy.draw_pile = list(self.draw_pile)
        copy.discard = list(self.discard)
        return copy

    def draw(self) -> CardDef | None:
        if not self.draw_pile:
            if not self.discard:
                return None
            self.draw_pile, self.discard = self.discard, []
            self.rng.shuffle(self.draw_pile)
        return self.draw_pile.pop()

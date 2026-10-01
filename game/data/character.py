"""Dados do personagem do jogador e o save em JSON."""
from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict, dataclass, field, fields

from game.data.cards import (
    ARCHETYPE_NAMES,
    CARD_LIST,
    CARDS,
    DECK_MAX,
    DECK_MIN,
    ELEMENTS,
    MAX_CARD_LEVEL,
    MAX_COPIES,
    PLAYER_DECK,
    START_BETS,
    UTILITY,
    CardDef,
)
from game.data.legends import LEGENDS, default_legend
from game.data.looks import Look
from game.engine.settings import SAVE_PATH

DECK_SLOTS = 3
# campo do looks.Look -> atributo do Character (o penteado tem outro nome por causa de saves antigos)
LOOK_FIELDS = {"gender": "gender", "hair": "hair_style", "hair_color": "hair_color", "skin": "skin", "top": "top",
               "shirt": "shirt", "bottom": "bottom", "legs": "legs", "shoes": "shoes", "hat": "hat",
               "hat_color": "hat_color"}
BASE_HP = 40
HP_PER_LEVEL = 3
LEGACY_REFUND = 40     # BETS por carta de versões antigas que não existe mais
MAX_LEVEL = 20


CATALOG_ORDER = {c.id: i for i, c in enumerate(CARD_LIST)}


class DeckError(Exception):
    """Mudança de deck recusada; a mensagem é mostrada ao jogador."""


def deck_archetype(deck: list[str]) -> str | None:
    """Arquétipo principal do deck (Utilidades não conta), ou None se ainda não tiver."""
    return next((CARDS[c].archetype for c in deck if CARDS[c].archetype != UTILITY), None)


def archetypes_ok(deck: list[str]) -> bool:
    """Regra de montagem: no máximo 1 arquétipo, mais cartas de Utilidades."""
    return len({CARDS[c].archetype for c in deck} - {UTILITY}) <= 1


def xp_to_next(level: int) -> int:
    """XP necessária para sair do nível `level`."""
    return 20 + 15 * level


@dataclass
class Character:
    name: str
    skin: int = 0
    gender: str = ""                              # "Masculino" / "Feminino"
    hair_style: str = "curto"                     # penteado (looks.HAIR_STYLES)
    hair_color: str = "castanho"
    top: str = ""                                 # peça de cima (looks.TOPS); vazio = a primeira do gênero
    shirt: str = "azul"                           # cor da peça de cima (looks.CLOTH_COLORS)
    bottom: str = ""                              # peça de baixo (looks.BOTTOMS); vazio = a primeira do gênero
    legs: str = "jeans"                           # cor da peça de baixo
    shoes: str = "branco"                         # cor do tênis (looks.SHOE_COLORS)
    hat: str = ""                                 # chapéu (looks.HATS); vazio = nenhum
    hat_color: str = ""
    wins: int = 0
    losses: int = 0
    beaten: list[str] = field(default_factory=list)   # treinadores já derrotados
    bets: int = START_BETS                        # moeda do jogo
    level: int = 1
    xp: int = 0                                   # XP dentro do nível atual
    battle_xp: int = 0                            # XP de batalha: gasto para evoluir cartas
    card_levels: dict[str, int] = field(default_factory=dict)   # {id da carta: nível}; ausente = 1
    collection: list[str] = field(default_factory=lambda: list(PLAYER_DECK))   # todas as cartas que você tem
    decks: list[list[str]] = field(default_factory=lambda: [list(PLAYER_DECK)] + [[] for _ in range(DECK_SLOTS - 1)])
    active_deck: int = 0
    deck_elements: list[str] = field(default_factory=lambda: [ELEMENTS[0]] * DECK_SLOTS)   # tipo de cada deck
    deck_legends: list[str] = field(default_factory=lambda: [default_legend(ELEMENTS[0])] * DECK_SLOTS)

    @property
    def appearance(self) -> Look:
        """Aparência do personagem (o que for inválido, como em saves antigos, vira um valor padrão)."""
        return Look(**{name: getattr(self, attr) for name, attr in LOOK_FIELDS.items()}).fitted()

    def wear(self, look: Look) -> None:
        """Veste uma aparência (usado na criação; a futura loja de roupas também pode usar)."""
        look = look.fitted()
        for name, attr in LOOK_FIELDS.items():
            setattr(self, attr, getattr(look, name))

    @property
    def max_hp(self) -> int:
        return BASE_HP + HP_PER_LEVEL * (self.level - 1)

    @property
    def deck(self) -> list[str]:
        """Deck ativo, usado nas batalhas."""
        return self.decks[self.active_deck]

    @property
    def xp_next(self) -> int:
        return xp_to_next(self.level)

    def gain_xp(self, amount: int) -> int:
        """Soma XP ao nível do personagem e à carteira de XP de batalha. Devolve quantos níveis subiu."""
        ups = 0
        self.battle_xp += amount
        self.xp += amount
        while self.level < MAX_LEVEL and self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            ups += 1
        if self.level >= MAX_LEVEL:
            self.xp = 0
        return ups

    # ------------------------------------------------------------ coleção
    def owned(self, card_id: str) -> int:
        return self.collection.count(card_id)

    def can_add(self, card_id: str) -> bool:
        return self.owned(card_id) < MAX_COPIES

    def card_level(self, card_id: str) -> int:
        return self.card_levels.get(card_id, 1)

    def card(self, card_id: str) -> CardDef:
        """A carta no nível em que o jogador a evoluiu."""
        return CARDS[card_id].at_level(self.card_level(card_id))

    def spare(self, card_id: str) -> int:
        """Cópias que não estão sendo usadas em nenhum deck (podem ser vendidas/trocadas)."""
        return self.owned(card_id) - max(d.count(card_id) for d in self.decks)

    def spare_cards(self) -> list[str]:
        return [c for c in CARDS if c in self.collection and self.spare(c) > 0]

    def add_card(self, card_id: str) -> None:
        if not self.can_add(card_id):
            raise ValueError(f"já tem {MAX_COPIES} cópias de {card_id}")
        self.collection.append(card_id)

    def remove_card(self, card_id: str) -> bool:
        """Remove uma cópia sobrando da coleção."""
        if self.spare(card_id) <= 0:
            return False
        self.collection.remove(card_id)
        return True

    def deck_valid(self, index: int) -> bool:
        deck = self.decks[index]
        return DECK_MIN <= len(deck) <= DECK_MAX and archetypes_ok(deck)

    def deck_element(self, slot: int) -> str:
        """Tipo do deck (Fogo, Gelo...): só cartas desse tipo e de Utilidades podem entrar nele."""
        return self.deck_elements[slot]

    def fits_deck(self, slot: int, card_id: str) -> bool:
        return CARDS[card_id].archetype in (UTILITY, self.deck_element(slot))

    def deck_legend(self, slot: int) -> str:
        """Legend que lidera o deck (no começo da batalha você se transforma nele)."""
        return self.deck_legends[slot]

    @property
    def legend(self) -> str:
        """Legend do deck de batalha."""
        return self.deck_legend(self.active_deck)

    def set_deck_legend(self, slot: int, legend_id: str) -> None:
        legend = LEGENDS.get(legend_id)
        if legend is None:
            raise DeckError("Esse legend não existe.")
        if legend.archetype != self.deck_element(slot):
            element = ARCHETYPE_NAMES[self.deck_element(slot)]
            raise DeckError(f"Este deck é de {element}: o legend também precisa ser de {element}.")
        self.deck_legends[slot] = legend_id

    def set_deck_element(self, slot: int, element: str) -> list[str]:
        """Troca o tipo do deck. As cartas do tipo antigo saem (as de Utilidades ficam); devolve as que saíram.
        O legend troca junto (ele precisa ser do mesmo tipo do deck)."""
        if element not in ELEMENTS:
            raise DeckError("Esse tipo de deck não existe.")
        self.deck_elements[slot] = element
        if LEGENDS[self.deck_legends[slot]].archetype != element:
            self.deck_legends[slot] = default_legend(element)
        removed = [c for c in self.decks[slot] if not self.fits_deck(slot, c)]
        self.decks[slot] = [c for c in self.decks[slot] if self.fits_deck(slot, c)]
        return removed

    def add_to_deck(self, slot: int, card_id: str) -> None:
        deck = self.decks[slot]
        if len(deck) >= DECK_MAX:
            raise DeckError(f"O deck pode ter no máximo {DECK_MAX} cartas.")
        if deck.count(card_id) >= self.owned(card_id):
            raise DeckError("Todas as suas cópias já estão no deck.")
        if not self.fits_deck(slot, card_id):
            element = ARCHETYPE_NAMES[self.deck_element(slot)]
            raise DeckError(f"Este deck é de {element}: só entram cartas de {element} e de Utilidades.")
        deck.append(card_id)
        deck.sort(key=CATALOG_ORDER.__getitem__)

    def remove_from_deck(self, slot: int, card_id: str) -> None:
        if card_id not in self.decks[slot]:
            raise DeckError("Essa carta não está no deck.")
        self.decks[slot].remove(card_id)

    def set_active_deck(self, slot: int) -> None:
        if not self.deck_valid(slot):
            raise DeckError(f"Um deck precisa ter de {DECK_MIN} a {DECK_MAX} cartas.")
        self.active_deck = slot

    # ------------------------------------------------------------ save
    def save(self) -> None:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @staticmethod
    def exists() -> bool:
        return os.path.exists(SAVE_PATH)

    @classmethod
    def load(cls) -> Character | None:
        try:
            with open(SAVE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            known = {f.name for f in fields(cls)}
            ch = cls(**{k: v for k, v in data.items() if k in known})
        except (OSError, ValueError, TypeError):
            return None
        if "decks" not in data and "deck" in data:   # save da versão antiga (um deck só)
            ch.collection = list(data["deck"])        # sanitize() reembolsa as cartas que saíram do jogo
            ch.decks = [list(data["deck"])] + [[] for _ in range(DECK_SLOTS - 1)]
        ch.sanitize()
        return ch

    def sanitize(self) -> None:
        """Garante que o save é coerente: cartas existem e os decks cabem na coleção."""
        legacy = [c for c in self.collection if c not in CARDS]   # cartas que saíram do jogo viram BETS
        self.bets += LEGACY_REFUND * len(legacy)
        self.collection = [c for c in self.collection if c in CARDS]
        have = Counter()
        kept = []
        for c in self.collection:            # limite de cópias: o excesso vira BETS
            if have[c] < MAX_COPIES:
                have[c] += 1
                kept.append(c)
            else:
                self.bets += CARDS[c].sell_price
        self.collection = kept
        decks = []
        for deck in (list(self.decks) + [[]] * DECK_SLOTS)[:DECK_SLOTS]:
            used = Counter()
            clean = []
            for c in deck:
                if c in CARDS and used[c] < have[c]:
                    used[c] += 1
                    clean.append(c)
            decks.append(clean if archetypes_ok(clean) else [])
        self.decks = decks
        elements = (list(self.deck_elements) + [ELEMENTS[0]] * DECK_SLOTS)[:DECK_SLOTS]
        # o tipo de cada deck: o das cartas que já estão nele (saves antigos) ou o que estava salvo
        self.deck_elements = [deck_archetype(deck) or (e if e in ELEMENTS else ELEMENTS[0])
                              for deck, e in zip(self.decks, elements, strict=True)]
        legends = (list(self.deck_legends) + [""] * DECK_SLOTS)[:DECK_SLOTS]
        self.deck_legends = [lg if lg in LEGENDS and LEGENDS[lg].archetype == element else default_legend(element)
                             for lg, element in zip(legends, self.deck_elements, strict=True)]
        if not 0 <= self.active_deck < DECK_SLOTS or not self.deck_valid(self.active_deck):
            self.active_deck = next((i for i in range(DECK_SLOTS) if self.deck_valid(i)), 0)
        if not self.deck_valid(self.active_deck):   # nenhum deck válido: garante o deck inicial
            starter = Counter(PLAYER_DECK)
            for card_id, n in starter.items():
                self.collection += [card_id] * max(0, n - self.owned(card_id))
            self.decks[self.active_deck] = list(PLAYER_DECK)
        self.level = max(1, min(MAX_LEVEL, int(self.level)))
        self.bets = max(0, int(self.bets))
        self.battle_xp = max(0, int(self.battle_xp))
        self.card_levels = {c: max(1, min(MAX_CARD_LEVEL, int(n))) for c, n in dict(self.card_levels).items()
                            if c in CARDS}

"""Duelo online entre dois jogadores (PvP). Regras puras: nada de Pygame nem de rede aqui.

Como os dois computadores veem o MESMO duelo sem mandar a batalha inteira pela rede:
    1. O servidor sorteia uma "semente" e manda para os dois. Cada baralho embaralha com o seu próprio
       random.Random(semente + lado), então os dois PCs embaralham igualzinho, na mesma ordem.
    2. Durante o duelo só viajam as JOGADAS (que carta da mão, fim do turno, habilidade). Cada PC aplica a
       jogada do outro nas mesmas regras (game/core) e chega no mesmo resultado.
Lado 0 é quem desafiou (começa jogando); lado 1 é quem aceitou.
"""
from __future__ import annotations

import random
from dataclasses import asdict, fields

from game.data.cards import CARDS
from game.data.legends import LEGENDS
from game.data.looks import Look

CHALLENGER, CHALLENGED = 0, 1
MAX_DECK = 40
LOOK_KEYS = {f.name for f in fields(Look)}


def look_from(data: dict | None) -> Look:
    """Aparência que veio pela rede: ignora campos desconhecidos e troca valores inválidos."""
    return Look(**{k: v for k, v in (data or {}).items() if k in LOOK_KEYS}).fitted()


def fighter(ch) -> dict:
    """O que o outro jogador precisa saber de você para duelar (vai junto com o desafio)."""
    return {"name": ch.name.upper(), "level": ch.level, "hp": ch.max_hp, "deck": list(ch.deck),
            "card_levels": dict(ch.card_levels), "legend": ch.legend, "look": asdict(ch.appearance)}


def duel_spec(foe: dict, side: int = CHALLENGER) -> dict:
    """Transforma o `fighter` do outro jogador no formato de oponente da batalha (como trainer_spec).
    Confere tudo: o que vem pela rede pode vir errado."""
    deck = [card for card in foe.get("deck", []) if card in CARDS][:MAX_DECK]
    if not deck:
        raise ValueError("deck do oponente vazio")
    name = str(foe.get("name") or "???")[:12]
    legend = foe.get("legend") if foe.get("legend") in LEGENDS else None
    levels = {k: int(v) for k, v in (foe.get("card_levels") or {}).items() if k in CARDS}
    intro = f"{name} aceitou o seu desafio!" if side == CHALLENGER else f"Duelo contra {name}!"
    return {"id": "pvp", "kind": "pvp", "name": name, "level": max(1, int(foe.get("level", 1))),
            "hp": max(1, int(foe.get("hp", 1))), "deck": deck, "card_levels": levels, "legend": legend,
            "look": look_from(foe.get("look")), "intro": intro}


def deck_rngs(seed: int, side: int) -> tuple[random.Random, random.Random]:
    """(sorteio do MEU baralho, sorteio do baralho do OPONENTE). O baralho do lado 0 usa sempre seed*2 e o
    do lado 1 usa seed*2+1, então cada PC chega nos mesmos sorteios, seja qual for o lado dele."""
    mine, theirs = random.Random(seed * 2 + side), random.Random(seed * 2 + (1 - side))
    return mine, theirs

"""Treinadores e criaturas selvagens, com nível, balanceamento e recompensas."""
from __future__ import annotations

import random

from .cards import MAX_CARD_LEVEL, make_deck
from .legends import default_legend
from .looks import Look

# look = aparência (game/looks.py): gênero, penteado, cor do cabelo, pele, camisa, calça/saia
# requires = treinador que precisa ser vencido antes; ai = easy | normal | hard (core/ai.py)
WILD_HP_FACTOR = 2.5   # você vira um legend (70-95 PV, força): monstros precisam aguentar mais

TRAINERS = {
    "tico": {
        "name": "TICO", "level": 1, "legend": "blitz",      # deck só de Utilidades: legend escolhido à mão
        "look": Look("Masculino", "curto", "loiro", 0, top="regata", shirt="verde",
                     bottom="bermuda", legs="jeans", shoes="vermelho"),
        "ai": "easy",
        "deck": make_deck(murrao=3, amansa_loko=3, defender=3, farma_aura=3, foco=3, chute_violento=2,
                          golpe_perfurante=3),
        "intro": "TICO quer duelar!",
        "lose": "Puxa! Você é bom nisso!",
        "win": "Eba, ganhei! Treine no mato alto!",
    },
    "rafa": {
        "name": "RAFA", "level": 2,
        "look": Look("Masculino", "curto", "ruivo", 0, top="camisa", shirt="vermelho",
                     bottom="calça", legs="preto", shoes="preto"),
        "ai": "easy",
        "deck": make_deck(queimar=3, fumaca=3, fenix=1, murrao=3, amansa_loko=2, defender=3, farma_aura=2, foco=2,
                          golpe_perfurante=1),
        "intro": "RAFA quer duelar!",
        "lose": "Aff! Você mandou muito bem!",
        "win": "Haha! Treine mais um pouco!",
    },
    "duda": {
        "name": "DUDA", "level": 3,
        "look": Look("Feminino", "chanel", "castanho", 1, top="top", shirt="azul",
                     bottom="saia", legs="branco", shoes="rosa"),
        "ai": "easy",
        "deck": make_deck(bola_de_gelo=3, gelo_fino=3, clone_de_gelo=1, murrao=3, amansa_loko=2, defender=2,
                          farma_aura=2, foco=2, chute_violento=2),
        "intro": "DUDA, a pescadora, aceitou o duelo!",
        "lose": "Os peixes nunca me deram tanto trabalho!",
        "win": "Fisguei a vitória!",
    },
    "bruno": {
        "name": "BRUNO", "level": 4,
        "look": Look("Masculino", "raspado", "preto", 2, top="regata", shirt="verde",
                     bottom="bermuda", legs="marrom", shoes="branco"),
        "ai": "normal",
        "deck": make_deck(picadura_de_mosquito=3, garras_de_veneno=2, cortina_de_veneno=2, murrao=2, amansa_loko=2,
                          defender=3, farma_aura=2, foco=2, golpe_perfurante=2),
        "intro": "BRUNO, o guarda do mato, bloqueia o caminho!",
        "lose": "Você passou pela minha defesa...",
        "win": "Ninguém atravessa a minha guarda!",
    },
    "lia": {
        "name": "LIA", "level": 5,
        "look": Look("Feminino", "longo", "preto", 1, top="manga longa", shirt="roxo",
                     bottom="calça", legs="preto", shoes="roxo"),
        "ai": "normal", "requires": "rafa",
        "deck": make_deck(zeus_luz=3, chicote_de_raios=3, choque_do_trovao=2, tela_de_luz=2, amansa_loko=3, murrao=2,
                          defender=2, golpe_perfurante=1, chute_violento=1, foco=1),
        "intro": "A Mestra LIA aceitou o desafio!",
        "lose": "Incrível... Seu deck é muito forte.",
        "win": "Ainda falta estratégia. Volte quando estiver pronto.",
    },
    "sofia": {
        "name": "SOFIA", "level": 6,
        "look": Look("Feminino", "chanel", "loiro", 0, top="camisa", shirt="laranja",
                     bottom="vestido", legs="laranja", shoes="amarelo"),
        "ai": "hard",
        "deck": make_deck(bola_de_fogo=2, queimar=3, fumaca=2, fenix=2, amansa_loko=3, contra_golpe=2, golpe_duplo=1,
                          golpes_rapidos=1, defender=2, foco=2),
        "intro": "SOFIA, a viajante, sorri e embaralha o deck!",
        "lose": "Você me paralisou de surpresa!",
        "win": "Viaje mais e volte mais forte!",
    },
    "zeca": {
        "name": "ZECA", "level": 8,
        "look": Look("Masculino", "raspado", "grisalho", 1, top="camisa", shirt="branco",
                     bottom="calça", legs="cinza", shoes="marrom"),
        "ai": "hard", "requires": "lia",
        "deck": make_deck(fica_frio_ai=2, bola_de_gelo=3, gelo_fino=3, clone_de_gelo=2, contra_golpe=2,
                          golpes_rapidos=2, pocao_da_vida=2, defender=2, foco=2),
        "intro": "O Grão-Mestre ZECA se levanta devagar...",
        "lose": "Há décadas ninguém me vencia. Parabéns, campeão!",
        "win": "Paciência, jovem. A sabedoria vem com o tempo.",
    },
    # ---- Bosque Sussurro
    "kaio": {
        "name": "KAIO", "level": 6,
        "look": Look("Masculino", "curto", "azul", 2, top="camisa", shirt="amarelo",
                     bottom="bermuda", legs="preto", shoes="azul"),
        "ai": "normal",
        "deck": make_deck(choque_do_trovao=2, zeus_luz=3, chicote_de_raios=3, tela_de_luz=2, amansa_loko=3,
                          murrao=2, golpe_perfurante=2, chute_violento=1, foco=2),
        "intro": "KAIO, o caçador de tempestades, saca o deck!",
        "lose": "Fui eletrocutado pela sua estratégia!",
        "win": "Rápido como um raio!",
    },
    "mila": {
        "name": "MILA", "level": 7,
        "look": Look("Feminino", "longo", "verde", 0, top="top", shirt="verde",
                     bottom="calça", legs="roxo", shoes="verde"),
        "ai": "hard",
        "deck": make_deck(agulha_escarlate=2, garras_de_veneno=3, cortina_de_veneno=2, picadura_de_mosquito=3,
                          contra_golpe=2, defender=2, farma_aura=2, golpes_rapidos=2, foco=2),
        "intro": "MILA surge entre as folhas, sem fazer barulho...",
        "lose": "O antídoto foi a sua coragem.",
        "win": "O veneno sempre vence no fim.",
    },
}

# (nome, monstro do pacote de arte, cor da gosma desenhada por código, PV base)
WILD_TYPES = [("GOSMA", "Slime", "green", 18), ("GOSMA AZUL", "Slime2", "blue", 20),
              ("GOSMA ROSA", "Slime3", "pink", 22)]
FOREST_WILD_TYPES = [("COGUMELO", "Mushroom", "pink", 22), ("COBRA", "Snake", "green", 20),
                     ("MORCEGO", "BlueBat", "blue", 18), ("ARANHA", "SpiderRed", "pink", 24)]
WILD_DECK = make_deck(picadura_de_mosquito=3, garras_de_veneno=1, murrao=3, amansa_loko=2, defender=3, farma_aura=3,
                      foco=3, chute_violento=2)
WILD_DECK_STRONG = make_deck(picadura_de_mosquito=3, garras_de_veneno=2, cortina_de_veneno=2, murrao=3, amansa_loko=2,
                             defender=2, farma_aura=2, foco=2, chute_violento=2)


def trainer_hp(level: int) -> int:
    return 24 + 6 * level


def trainer_card_level(level: int) -> int:
    """Treinadores mais fortes usam cartas evoluídas: Nv 4+ -> cartas Nv 2, Nv 8+ -> Nv 3."""
    return min(MAX_CARD_LEVEL, 1 + level // 4)


def trainer_legend(trainer: dict) -> str:
    """Legend do treinador: o escolhido na ficha dele ou o do arquétipo do deck."""
    from .character import deck_archetype
    return trainer.get("legend") or default_legend(deck_archetype(trainer["deck"]) or "raio")


def trainer_spec(trainer_id: str) -> dict:
    t = TRAINERS[trainer_id]
    card_level = trainer_card_level(t["level"])
    return dict(t, id=trainer_id, kind="trainer", hp=trainer_hp(t["level"]), legend=trainer_legend(t),
                card_levels={c: card_level for c in t["deck"]})


def random_wild(player_level: int, rng: random.Random | None = None, types=None) -> dict:
    """Os monstros acompanham o nível do jogador (entre -1 e +1)."""
    rng = rng or random.Random()
    level = max(1, player_level + rng.choice((-1, 0, 0, 1)))
    name, monster, color, hp = rng.choice(types or WILD_TYPES)
    return {
        "id": "wild", "kind": "wild", "name": name, "level": level,
        "hp": round((hp + 3 * (level - 1)) * WILD_HP_FACTOR),
        "monster": monster, "slime": color, "ai": "easy", "deck": WILD_DECK_STRONG if level >= 4 else WILD_DECK,
        "intro": f"Uma {name} selvagem (Nv. {level}) apareceu!",
    }


def level_factor(opponent_level: int, player_level: int) -> float:
    """Balanceamento: vencer alguém mais forte rende mais; mais fraco, menos."""
    gap = opponent_level - player_level
    if gap >= 2:
        return 1.5
    if gap == 1:
        return 1.25
    if gap == 0:
        return 1.0
    if gap == -1:
        return 0.75
    if gap == -2:
        return 0.5
    return 0.25


def rewards(spec: dict, player_level: int, first_win: bool,
            rng: random.Random | None = None) -> tuple[int, int]:
    """Devolve (bets, xp) ganhos por vencer esse oponente. spec["xp_mult"] multiplica o XP (torneio)."""
    rng = rng or random.Random()
    level = spec.get("level", 1)
    factor = level_factor(level, player_level)
    if spec["kind"] == "wild":
        bets, xp = 8 * level + rng.randint(0, 6), 6 * level
    else:
        bets, xp = 20 * level, 14 * level
        if first_win:
            bets *= 2
    xp *= spec.get("xp_mult", 1)
    return max(1, round(bets * factor)), max(1, round(xp * factor))

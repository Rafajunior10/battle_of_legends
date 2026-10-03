"""Companheiros que moram com o jogador (hoje, só a REBECA, esposa de quem tem `Character.spouse = "rebeca"`).
Só dados, sem Pygame: aparência, falas e a ROTINA (as atividades que ela escolhe fazer pela casa e pela vila).

Uma atividade diz em que mapa e tile ela fica (`spot`, olhando para `facing`), quanto tempo, o que aparece no
balão e, se for o caso, um assento/cama/box (`seat`) onde ela entra com uma pose (sentada, deitada, no banho).
`talk_to`: um NPC que responde com outro balão. `then`: a próxima atividade (ex.: pedir no balcão e depois sentar
para comer). Quem anda e escolhe é game/core/companion.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from game.data.looks import Look


@dataclass(frozen=True)
class Activity:
    id: str
    map_id: str
    spot: tuple[int, int]
    facing: str
    duration: float
    bubble: str = ""
    seat: tuple[int, int] | None = None
    pose: str = "stand"            # stand | sit | lie | shower
    weight: int = 1
    talk_to: str = ""
    reply: str = ""
    then: str = ""


@dataclass(frozen=True)
class CompanionDef:
    id: str
    name: str
    look: Look
    home: tuple[str, int, int]     # onde ela está quando o jogo começa
    lines: tuple[str, ...]          # conversa ({name} = o jogador)
    activities: tuple[Activity, ...]
    sleep: Activity                 # "vamos dormir": deita e fica até o jogador acordar


REBECA_ACTIVITIES = (
    # em casa, térreo
    Activity("cozinhar", "casa_terreo", (4, 4), "up", 16, "Cozinhando algo gostoso...", weight=3),
    Activity("geladeira", "casa_terreo", (9, 4), "up", 5, "Hmm, o que tem pra comer?"),
    Activity("tv", "casa_terreo", (21, 7), "down", 22, "Adoro essa novela!", seat=(21, 8), pose="sit", weight=3),
    Activity("ler", "casa_terreo", (3, 11), "right", 14, "Lendo uma revista...", seat=(4, 11), pose="sit"),
    Activity("plantas", "casa_terreo", (16, 16), "right", 7, "Regando as plantinhas!"),
    Activity("trofeus", "casa_terreo", (26, 3), "up", 5, "Que orgulho desses troféus!"),
    # em casa, andar de cima
    Activity("banho", "casa_superior", (16, 5), "up", 10, "Lá lá lá... (no banho)", seat=(16, 4), pose="shower",
             weight=2),
    Activity("cochilo", "casa_superior", (11, 5), "left", 14, "Zzz...", seat=(10, 6), pose="lie"),
    Activity("closet", "casa_superior", (2, 4), "up", 7, "Qual roupa eu uso hoje?"),
    Activity("hospedes", "casa_superior", (20, 5), "up", 6, "Arrumando o quarto de hóspedes."),
    # na vila e na lanchonete
    Activity("praca", "vila", (31, 21), "down", 8, "Que dia lindo na vila!", weight=2),
    Activity("beto", "vila", (26, 26), "left", 8, "Oi, Beto! Tudo bem?", talk_to="beto", reply="Tudo ótimo, Rebeca!"),
    Activity("nina", "vila", (23, 15), "up", 8, "Nina, alguma carta rara hoje?", talk_to="nina",
             reply="Pra você sempre tem, Rebeca!"),
    Activity("tico", "vila", (14, 18), "up", 6, "Treinando muito, Tico?", talk_to="tico",
             reply="Todo dia, tia Rebeca!"),
    Activity("lanchonete", "lanchonete", (5, 6), "up", 5, "Um sorvete, por favor!", talk_to="lu",
             reply="Saindo um sorvete!", weight=2, then="lanchar"),
    Activity("lanchar", "lanchonete", (22, 11), "up", 14, "Nham! Que delícia!", seat=(22, 10), pose="sit", weight=0),
)

REBECA = CompanionDef(
    id="rebeca",
    name="REBECA",
    look=Look("Feminino", "cacheado", "castanho", 3, top="top", shirt="preto", bottom="shorts", legs="preto",
              shoes="branco"),
    home=("casa_terreo", 6, 4),
    lines=(
        "REBECA: Oi, amor! Como foram os duelos hoje?",
        "REBECA: Já viu a estante da sala? Cada troféu do Coliseu vai pra lá. Tô orgulhosa de você!",
        "REBECA: Lá em cima tem o closet do nosso quarto, se quiser trocar de roupa antes de sair.",
        "REBECA: Passei na lanchonete hoje. A Lu mandou um beijo!",
        "REBECA: Não esquece de comer, hein? Com fome você não consegue duelar.",
        "REBECA: {name}, vê se não perde pro Zeca! Eu acredito em você.",
    ),
    activities=REBECA_ACTIVITIES,
    sleep=Activity("dormir", "casa_superior", (11, 5), "left", 0, "Boa noite, amor...", seat=(10, 6), pose="lie"),
)
COMPANIONS = {REBECA.id: REBECA}

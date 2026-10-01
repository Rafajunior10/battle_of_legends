"""Legends: os heróis em que os duelistas se transformam no começo da batalha. Só dados, sem Pygame.

Cada deck escolhe um legend do MESMO arquétipo (deck de Fogo -> legend de Fogo). Na batalha o legend define:
    vida       PV do duelo
    força      somada ao dano de cada golpe
    proteção   defesa fixa: tira esse tanto de cada golpe que passar pela aura e pela defesa das cartas
    energia    energia recebida a cada turno
    habilidade "ativa" = botão HABILIDADE na batalha (1 vez por turno); "passiva" = funciona sozinha
As regras das habilidades ficam em game/core/abilities.py; a arte, em assets/legends/<id>/.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegendDef:
    id: str
    name: str
    title: str
    cls: str               # classe: NINJA, MAGO, FERA, LUTADOR
    archetype: str         # fogo, gelo, raio, veneno
    hp: int
    strength: int
    protection: int
    energy: int
    ability: str           # texto da habilidade (mostrado no jogo)
    active: bool           # True = o jogador aciona (botão HABILIDADE); False = passiva
    short: str = ""        # resumo da habilidade (cabe no painel da batalha)

    @property
    def full_name(self) -> str:
        return f"{self.name}, {self.title}"


LEGEND_LIST = [
    LegendDef("mimo", "Mimo", "a Salamandra Assassina", "NINJA", "veneno", 80, 7, 4, 4,
              "Uma vez por turno: revele as 3 cartas do topo do seu baralho. Escolha 1 carta NINJA ou VENENO "
              "entre elas e você pode jogá-la sem pagar seu custo. Coloque as outras cartas no fundo do baralho.",
              active=True, short="Revela 3 do topo: joga 1 de Veneno de graça; as outras vão pro fundo."),
    LegendDef("drogoz", "Drogoz", "o Dracomante de Fogo", "MAGO", "fogo", 70, 8, 5, 5,
              "Uma vez por turno: descarte 3 cartas; depois, CURE 15.", active=True,
              short="Descarte 3 cartas da mão e cure 15 PV."),
    LegendDef("blitz", "Blitz", "a Fera do Relâmpago", "FERA", "raio", 95, 5, 9, 4,
              "No seu turno, este personagem recebe +9 de FORÇA enquanto a DEFESA + AURA que ele ganhou no turno "
              "for 9 ou mais.", active=False,
              short="Passiva: +9 de força enquanto tiver 9+ de defesa e aura no turno."),
    LegendDef("cold", "Cold", "o Bruto Glacial", "LUTADOR", "gelo", 70, 7, 7, 5,
              "Atacar um oponente CONGELADO quebra o gelo: ele descongela, os marcadores de gelo zeram e o ataque "
              "causa +5 de dano. Com o CLONE DE GELO ativo, o primeiro ataque do oponente não causa dano nem efeito "
              "e coloca 1 marcador de gelo nele.", active=False,
              short="Passiva: quebra o gelo do congelado (+5). Clone de Gelo anula o 1º ataque."),
]
LEGENDS = {legend.id: legend for legend in LEGEND_LIST}


def legends_for(archetype: str) -> list[LegendDef]:
    """Legends que podem liderar um deck desse arquétipo."""
    return [legend for legend in LEGEND_LIST if legend.archetype == archetype]


def default_legend(archetype: str) -> str:
    options = legends_for(archetype)
    return options[0].id if options else LEGEND_LIST[0].id


"""Aparência dos personagens ("boneco de papel"): só dados, sem Pygame.

Um Look diz o penteado, a pele, as peças de roupa (e as cores) e o chapéu. Quem desenha é game/mana_seed.py
(arte do pacote Mana Seed, em camadas, com as roupas de game/wardrobe.py); sem o pacote, game/people.py.
Trocar de roupa (a futura loja de roupas) é só trocar os campos aqui.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

# Pele: (claro, escuro) tirados dos 7 tons humanos do Mana Seed (humn v01..v07)
SKIN_TONES = [((248, 208, 152), (208, 136, 96)), ((248, 192, 176), (208, 128, 112)),
              ((255, 199, 132), (222, 134, 75)), ((240, 192, 128), (200, 128, 40)),
              ((247, 162, 115), (181, 97, 49)), ((224, 144, 96), (171, 85, 68)),
              ((188, 102, 51), (142, 50, 30))]
HAIR_COLORS = {   # as 12 cores de cabelo do Mana Seed (o desenho de reserva usa estes tons)
    "preto": ((70, 64, 98), (44, 37, 62)), "castanho": ((120, 70, 48), (78, 43, 32)),
    "loiro": ((236, 190, 80), (166, 114, 34)), "ruivo": ((214, 92, 40), (148, 56, 24)),
    "acobreado": ((190, 110, 110), (138, 79, 87)), "rosa": ((236, 120, 200), (174, 69, 147)),
    "vermelho": ((214, 70, 90), (160, 50, 70)), "roxo": ((130, 110, 190), (78, 72, 120)),
    "verde": ((110, 180, 160), (86, 116, 126)), "azul": ((70, 120, 210), (45, 81, 145)),
    "grisalho": ((150, 150, 166), (77, 77, 90)), "branco": ((226, 232, 232), (124, 137, 137)),
}
HAIR_STYLES = ["curto", "raspado", "chanel", "longo", "careca"]
GENDERS = ["Masculino", "Feminino"]
DEFAULT_HAIR = {"Masculino": "curto", "Feminino": "longo"}

# Chapéus do Mana Seed: cada um tem as suas cores prontas (a ordem = arquivo v01, v02...)
HATS = {
    "nenhum": [],
    "capuz": ["vermelho", "creme", "cinza", "marrom", "verde"],
    "mago": ["azul", "marrom", "verde", "roxo", "amarelo"],
}

# Peças de roupa (montadas em game/wardrobe.py) e as suas cores
CLOTH_COLORS = {   # cores vivas, estilo NES
    "vermelho": ((232, 60, 56), (158, 36, 40)), "azul": ((56, 116, 232), (36, 72, 168)),
    "verde": ((64, 184, 80), (40, 120, 56)), "amarelo": ((252, 204, 56), (200, 148, 32)),
    "roxo": ((156, 84, 224), (106, 56, 160)), "laranja": ((252, 136, 40), (196, 88, 28)),
    "branco": ((244, 244, 240), (188, 188, 196)), "preto": ((64, 64, 84), (36, 36, 52)),
    "rosa": ((252, 140, 196), (204, 92, 148)), "marrom": ((160, 100, 56), (110, 66, 40)),
    "jeans": ((72, 108, 176), (46, 70, 128)), "cinza": ((156, 156, 168), (104, 104, 120)),
    "ciano": ((48, 200, 220), (28, 136, 160)),
}
SHOE_COLORS = {   # cor do tênis (a sola é sempre branca)
    "branco": (236, 236, 236), "preto": (56, 56, 72), "vermelho": (224, 52, 52), "azul": (52, 108, 228),
    "verde": (60, 176, 76), "amarelo": (248, 200, 48), "rosa": (248, 128, 188), "roxo": (150, 80, 220),
    "marrom": (150, 96, 56),
}
TOPS = {"Masculino": ["camisa", "regata", "manga longa"], "Feminino": ["camisa", "top", "manga longa"]}
BOTTOMS = {"Masculino": ["calça", "bermuda"], "Feminino": ["saia", "calça", "vestido"]}


@dataclass(frozen=True)
class Look:
    gender: str = "Masculino"
    hair: str = "curto"             # penteado (HAIR_STYLES) — qualquer gênero pode usar qualquer um
    hair_color: str = "castanho"
    skin: int = 0                   # índice em SKIN_TONES
    top: str = "camisa"             # peça de cima (TOPS)
    shirt: str = "azul"             # cor da peça de cima (CLOTH_COLORS)
    bottom: str = "calça"           # peça de baixo (BOTTOMS); o vestido usa a cor `legs` no corpo todo
    legs: str = "jeans"             # cor da peça de baixo
    shoes: str = "branco"           # cor do tênis (SHOE_COLORS)
    hat: str = "nenhum"             # chapéu (HATS)
    hat_color: str = ""             # uma das cores do chapéu

    def fitted(self) -> Look:
        """Mesma aparência, trocando por um valor válido o que não existir (ex.: saves antigos)."""
        gender = _pick(self.gender, GENDERS, GENDERS[0])
        hat = _pick(self.hat, HATS, "nenhum")
        hat_colors = HATS[hat]
        return replace(
            self, gender=gender,
            hair=_pick(self.hair, HAIR_STYLES, DEFAULT_HAIR[gender]),
            hair_color=_pick(self.hair_color, HAIR_COLORS, "castanho"),
            skin=_pick(self.skin, range(len(SKIN_TONES)), 0),
            top=_pick(self.top, TOPS[gender], TOPS[gender][0]),
            shirt=_pick(self.shirt, CLOTH_COLORS, "azul"),
            bottom=_pick(self.bottom, BOTTOMS[gender], BOTTOMS[gender][0]),
            legs=_pick(self.legs, CLOTH_COLORS, "jeans"),
            shoes=_pick(self.shoes, SHOE_COLORS, "branco"),
            hat=hat,
            hat_color=_pick(self.hat_color, hat_colors, hat_colors[0] if hat_colors else ""),
        )


def _pick(value, options, default):
    """O valor, se ele for uma das opções; senão, o padrão."""
    try:
        return value if value in options else default
    except TypeError:          # ex.: um texto no lugar do número da pele
        return default

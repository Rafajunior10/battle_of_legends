"""Relógio do mundo: manhã, tarde e noite. Regras puras, sem Pygame.

1 minuto do jogo = 1 segundo de verdade (um dia inteiro = 24 minutos jogando).
    MANHÃ  05:00 - 11:59      TARDE  12:00 - 17:59      NOITE  18:00 - 04:59
Dormir à noite (todos os jogadores deitados, ou só você) pula para as 06:00 do dia seguinte.
`tint(minutos)` diz a cor e a força da camada que pinta a tela: nada de dia, alaranjado no fim da tarde, azul
escuro à noite. Entre um ponto e outro da tabela (KEYS) as cores se misturam aos poucos.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

DAY = 24 * 60
MINUTES_PER_SECOND = 1.0
MORNING, AFTERNOON, NIGHT = 5 * 60, 12 * 60, 18 * 60
WAKE_UP = 6 * 60
START = 8 * 60                     # um mundo novo começa às 8 da manhã do dia 1
NIGHT_BLUE = (14, 18, 56)
KEYS = [                           # (minuto do dia, cor, opacidade 0-255)
    (0, NIGHT_BLUE, 150),
    (4 * 60 + 30, NIGHT_BLUE, 150),
    (6 * 60, (255, 170, 120), 50),        # amanhecer rosado
    (7 * 60 + 30, (0, 0, 0), 0),
    (15 * 60 + 30, (0, 0, 0), 0),
    (17 * 60, (255, 150, 60), 45),        # fim de tarde dourado
    (18 * 60 + 30, (150, 70, 110), 85),   # pôr do sol roxo
    (20 * 60, NIGHT_BLUE, 150),
    (DAY, NIGHT_BLUE, 150),
]


def phase(minutes: float) -> str:
    m = minutes % DAY
    if MORNING <= m < AFTERNOON:
        return "MANHÃ"
    if AFTERNOON <= m < NIGHT:
        return "TARDE"
    return "NOITE"


def is_night(minutes: float) -> bool:
    return phase(minutes) == "NOITE"


def tint(minutes: float) -> tuple[tuple[int, int, int], int]:
    m = minutes % DAY
    for (t0, c0, a0), (t1, c1, a1) in pairwise(KEYS):
        if t0 <= m <= t1:
            k = (m - t0) / (t1 - t0) if t1 > t0 else 0.0
            color = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1, strict=True))
            if a0 == 0:                   # saindo do "sem camada": usa a cor de destino desde o começo
                color = c1
            elif a1 == 0:
                color = c0
            return color, round(a0 + (a1 - a0) * k)
    return NIGHT_BLUE, 150


def lights_on(minutes: float) -> bool:
    """Postes acesos (do fim da tarde até o amanhecer)."""
    m = minutes % DAY
    return m >= 18 * 60 or m < 6 * 60


@dataclass
class WorldClock:
    minutes: float = START          # minuto do dia (0 a 1439)
    day: int = 1

    def advance(self, seconds: float) -> None:
        self.minutes += seconds * MINUTES_PER_SECOND
        while self.minutes >= DAY:
            self.minutes -= DAY
            self.day += 1

    def sleep_until_morning(self) -> None:
        """Dormiu: acorda às 06:00. Antes da meia-noite, é o dia seguinte; de madrugada, o mesmo dia."""
        if self.minutes >= AFTERNOON:
            self.day += 1
        self.minutes = WAKE_UP

    @property
    def phase(self) -> str:
        return phase(self.minutes)

    @property
    def is_night(self) -> bool:
        return is_night(self.minutes)

    def label(self) -> str:
        hours, minutes = divmod(int(self.minutes), 60)
        return f"DIA {self.day}  {hours:02d}:{minutes:02d}"

    def to_dict(self) -> dict:
        return {"minutes": self.minutes, "day": self.day}

    @classmethod
    def from_dict(cls, data) -> WorldClock:
        try:
            return cls(float(data.get("minutes", START)) % DAY, max(1, int(data.get("day", 1))))
        except (AttributeError, TypeError, ValueError):
            return cls()

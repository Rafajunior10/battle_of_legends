"""Passos da fila da batalha: mensagens, esperas, animações e efeitos de partículas.

A batalha empilha passos numa fila e executa um de cada vez, na ordem, como nos jogos clássicos.
Nada aqui decide regra de jogo: só anima e narra o que as regras (game/core) já resolveram.
"""
import math
import random
from typing import NamedTuple

import pygame

from .. import pixelart as art
from .. import sfx
from ..settings import GAME_W
from ..ui import overlay

RED = (232, 64, 48)
DARK = (40, 40, 48)
CARD_CENTER = (GAME_W // 2, 84)   # onde a carta jogada para no meio da tela
SLIDE_DISTANCE = 300
GLOW_COLORS = {"flame": (255, 120, 40), "bolt": (255, 230, 90), "ice": (120, 200, 255), "heal": (90, 255, 120),
               "aura": (200, 120, 255), "stun": (255, 220, 60), "energy": (255, 220, 80), "poison": (180, 80, 255)}


# ============================================================ passos básicos
class Step:
    def start(self, scene):
        self.scene = scene

    def update(self, dt):
        """Devolve True quando o passo terminou."""
        return True

    def draw(self, surf):
        pass


class Msg(Step):
    def __init__(self, text, auto=0.7):
        self.text = text
        self.auto = auto

    def start(self, scene):
        super().start(scene)
        scene.dialog.show(self.text, auto=self.auto)

    def update(self, dt):
        return not self.scene.dialog.active


class Wait(Step):
    def __init__(self, seconds):
        self.left = seconds

    def update(self, dt):
        self.left -= dt
        return self.left <= 0


class Call(Step):
    """Executa uma função; se ela devolver passos, eles entram na frente da fila."""

    def __init__(self, fn):
        self.fn = fn

    def start(self, scene):
        super().start(scene)
        steps = self.fn()
        if steps:
            scene.run_now(steps)


class WaitBars(Step):
    """Espera as barras de PV terminarem de animar."""

    def update(self, dt):
        return all(abs(f.disp_hp - f.hp) < 0.05 for f in self.scene.fighters)


class Timed(Step):
    """Passo com duração fixa. `p` vai de 0 a 1 ao longo de `dur` segundos."""
    dur = 0.3

    def start(self, scene):
        super().start(scene)
        self.t = 0.0
        self.p = 0.0
        self.begin()

    def update(self, dt):
        self.t += dt
        self.p = min(1.0, self.t / self.dur)
        self.tick()
        if self.t >= self.dur:
            self.finish()
            return True
        return False

    def begin(self):
        pass

    def tick(self):
        pass

    def finish(self):
        pass


# ============================================================ animações dos lutadores
class SlideIn(Timed):
    dur = 0.9

    def tick(self):
        k = (1 - self.p) ** 2
        self.scene.enemy.offset.x = -SLIDE_DISTANCE * k
        self.scene.player.offset.x = SLIDE_DISTANCE * k


class Lunge(Timed):
    """O atacante dá um "pulo" na direção do alvo."""
    dur = 0.26

    def __init__(self, fighter):
        self.f = fighter

    def tick(self):
        direction = pygame.Vector2(1, -0.6) if self.f.is_player else pygame.Vector2(-1, 0.6)
        self.f.offset = direction * math.sin(math.pi * self.p) * 16

    def finish(self):
        self.f.offset = pygame.Vector2()


class Hit(Timed):
    """O alvo pisca e treme, com o número de dano subindo."""
    dur = 0.5

    def __init__(self, fighter, label):
        self.f = fighter
        self.label = label

    def begin(self):
        sfx.play("hit")
        self.scene.add_float(self.label, self.f.center, RED)
        amount = int(self.label.lstrip("-") or 0) if self.label.lstrip("-").isdigit() else 0
        self.scene.impact(amount)

    def tick(self):
        self.f.flash = self.p < 0.6 and int(self.p * 12) % 2 == 0   # pisca em branco
        self.f.offset.x = (2 if int(self.t * 40) % 2 else -2) if self.p < 0.7 else 0

    def finish(self):
        self.f.flash = False
        self.f.offset.x = 0


class Faint(Timed):
    """Derrotado: afunda para fora da plataforma."""
    dur = 0.7

    def __init__(self, fighter):
        self.f = fighter

    def begin(self):
        sfx.play("faint")

    def tick(self):
        self.f.offset.y = self.f.sprite.get_height() * 1.1 * self.p * self.p

    def finish(self):
        self.f.visible = False


class Fly(Timed):
    """A carta jogada voa da mão até o centro da tela, crescendo."""
    dur = 0.6

    def __init__(self, card, start):
        self.card = card
        self.start_pos = start

    def begin(self):
        sfx.play("card")
        self.img = art.render_card(self.card)

    def draw(self, surf):
        q = min(1.0, self.p / 0.5)
        e = 1 - (1 - q) ** 2
        w, h = int(art.CARD_W * (1 + e)), int(art.CARD_H * (1 + e))
        x = self.start_pos[0] + (CARD_CENTER[0] - self.start_pos[0]) * e
        y = self.start_pos[1] + (CARD_CENTER[1] - self.start_pos[1]) * e
        card = pygame.transform.rotozoom(self.img, (1 - e) * -14, 1.0)   # gira enquanto voa
        card = pygame.transform.scale(card, (int(card.get_width() * w / art.CARD_W),
                                             int(card.get_height() * h / art.CARD_H)))
        surf.blit(card, (x - card.get_width() // 2, y - card.get_height() // 2))


# ============================================================ efeitos de partículas
_glows = {}


def glow(color, radius):
    """Mancha de luz redonda que some nas bordas (para somar à cena com BLEND_ADD)."""
    key = (color, radius)
    if key not in _glows:
        s = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -2):
            k = (1 - r / radius) ** 1.6 * 0.55
            pygame.draw.circle(s, [int(c * k) for c in color], (radius, radius), r)
        _glows[key] = s
    return _glows[key]


class Particle(NamedTuple):
    x: float       # deslocamento inicial
    y: float
    speed: float
    delay: float   # fração da animação antes de aparecer


FX_SOUNDS = {"slime": "poison", "drain": "slash"}   # o resto usa o som de mesmo nome


class FX(Timed):
    """Efeitos de partículas: corte, fogo, raio, escudo, cura, veneno... Um método _draw_<tipo> por efeito."""
    dur = 0.55

    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.painter = getattr(self, f"_draw_{kind}")

    def begin(self):
        sfx.play(FX_SOUNDS.get(self.kind, self.kind))
        self.parts = [Particle(random.uniform(-18, 18), random.uniform(-6, 16), random.uniform(20, 50),
                               random.uniform(0, 0.35)) for _ in range(16)]
        cx, cy = self.pos
        self.bolt = [(cx + random.randint(-8, 8), y) for y in range(-10, int(cy), 12)] + [(cx, cy)]

    def _q(self, delay):
        """Progresso local de uma partícula que só começa depois de `delay`."""
        return max(0.0, min(1.0, (self.p - delay) / max(0.01, 1 - delay)))

    def _live(self, count):
        """Partículas visíveis agora, com o progresso de cada uma."""
        for part in self.parts[:count]:
            q = self._q(part.delay)
            if 0 < q < 1:
                yield part, q

    def draw(self, surf):
        color = GLOW_COLORS.get(self.kind)
        if color:   # brilho somado à cena (luz), mais forte no meio da animação
            strength = math.sin(self.p * math.pi)
            surf.blit(glow(color, 40), (self.pos[0] - 40, self.pos[1] - 40), special_flags=pygame.BLEND_ADD)
            if strength > 0.5:
                surf.blit(glow(color, 22), (self.pos[0] - 22, self.pos[1] - 22), special_flags=pygame.BLEND_ADD)
        self.painter(surf, *self.pos)

    def _draw_slash(self, surf, cx, cy, color=(248, 248, 248)):
        for i in range(3):
            q = max(0.0, min(1.0, (self.p - i * 0.15) / 0.4))
            if 0 < q < 1:
                x0, y0 = cx - 20 + i * 10, cy - 20
                pygame.draw.line(surf, DARK, (x0, y0), (x0 + 24 * q, y0 + 40 * q), 4)
                pygame.draw.line(surf, color, (x0, y0), (x0 + 24 * q, y0 + 40 * q), 2)

    def _draw_drain(self, surf, cx, cy):
        self._draw_slash(surf, cx, cy, color=(248, 96, 120))

    def _draw_flame(self, surf, cx, cy):
        for part, q in self._live(16):
            color = (248, 232, 96) if q < 0.35 else (248, 144, 48) if q < 0.7 else (216, 56, 40)
            size = 4 if q < 0.5 else 3
            pygame.draw.rect(surf, color, (cx + part.x, cy + part.y - part.speed * q, size, size))

    def _draw_bolt(self, surf, cx, cy):
        if self.p < 0.25:
            surf.blit(overlay((255, 255, 255), 120), (0, 0))
        if int(self.p * 12) % 2 == 0:
            pygame.draw.lines(surf, DARK, False, self.bolt, 5)
            pygame.draw.lines(surf, (248, 224, 64), False, self.bolt, 3)
            pygame.draw.lines(surf, (255, 255, 255), False, self.bolt, 1)

    def _draw_shield(self, surf, cx, cy):
        for k in range(2):
            r = 8 + (self.p - k * 0.25) * 40
            if r > 8:
                pygame.draw.circle(surf, (96, 160, 248), (int(cx), int(cy)), int(r), 2)

    def _draw_heal(self, surf, cx, cy):
        for part, q in self._live(10):
            px, py = cx + part.x, cy + part.y - part.speed * q
            pygame.draw.rect(surf, (72, 200, 96), (px - 1, py - 3, 3, 7))
            pygame.draw.rect(surf, (72, 200, 96), (px - 3, py - 1, 7, 3))
            surf.set_at((int(px), int(py)), (220, 255, 220))

    def _draw_poison(self, surf, cx, cy):
        for part, q in self._live(12):
            px, py = int(cx + part.x), int(cy + part.y - part.speed * q)
            pygame.draw.circle(surf, (112, 56, 160), (px, py), 3)
            pygame.draw.circle(surf, (200, 128, 240), (px - 1, py - 1), 1)

    def _draw_energy(self, surf, cx, cy):
        for i, part in enumerate(self.parts[:10]):   # cada partícula sai num ângulo fixo
            q = self._q(part.delay)
            if not 0 < q < 1:
                continue
            ang = i / 10 * math.tau
            px, py = cx + math.cos(ang) * 30 * q, cy + math.sin(ang) * 30 * q
            pygame.draw.polygon(surf, (248, 216, 64), [(px, py - 3), (px + 3, py), (px, py + 3), (px - 3, py)])

    def _draw_slime(self, surf, cx, cy):
        for part, q in self._live(10):
            px = cx + part.x * q * 1.5
            py = cy - 10 + part.y - 30 * q + 50 * q * q
            pygame.draw.circle(surf, (104, 200, 96), (int(px), int(py)), 3)

    def _draw_pierce(self, surf, cx, cy):
        """Estocada rápida atravessando o alvo, soltando lascas."""
        q = min(1.0, self.p / 0.45)
        tip = (cx - 34 + 60 * q, cy + 10 - 24 * q)
        tail = (tip[0] - 26, tip[1] + 10)
        pygame.draw.line(surf, DARK, tail, tip, 5)
        pygame.draw.line(surf, (248, 248, 248), tail, tip, 2)
        if self.p <= 0.35:
            return
        for part in self.parts[:8]:
            q2 = self._q(0.35 + part.delay * 0.5)
            if 0 < q2 < 1:
                pygame.draw.rect(surf, (200, 216, 248),
                                 (cx + part.x * q2 * 1.8, cy + part.y - 8 - part.speed * q2 * 0.4, 2, 2))

    def _draw_ice(self, surf, cx, cy):
        """Cristais de gelo caindo e girando."""
        for part, q in self._live(12):
            px, py = cx + part.x * 1.3, cy - 24 + part.y + 40 * q
            r = 3 if q < 0.6 else 2
            pygame.draw.line(surf, (232, 248, 255), (px - r, py), (px + r, py))
            pygame.draw.line(surf, (232, 248, 255), (px, py - r), (px, py + r))
            pygame.draw.line(surf, (136, 200, 248), (px - r + 1, py - r + 1), (px + r - 1, py + r - 1))

    def _draw_aura(self, surf, cx, cy):
        """Anéis roxos se abrindo em volta de quem ganhou aura."""
        for k in range(3):
            r = 6 + (self.p - k * 0.2) * 44
            if r > 6:
                pygame.draw.circle(surf, (192, 128, 240), (int(cx), int(cy)), int(r), 1)

    def _draw_smoke(self, surf, cx, cy):
        """Nuvem cinza subindo."""
        for part, q in self._live(14):
            radius = int(3 + 5 * q)
            px, py = int(cx + part.x * 1.4), int(cy + part.y - part.speed * q * 0.6)
            pygame.draw.circle(surf, (120, 120, 128), (px, py), radius)
            pygame.draw.circle(surf, (184, 184, 192), (px - 1, py - 1), max(1, radius - 2))

    def _draw_break(self, surf, cx, cy):
        """Escudo se partindo em cacos."""
        if self.p >= 0.95:
            return
        for i in range(12):
            ang = i / 12 * math.tau
            r = 14 + 36 * self.p
            px, py = cx + math.cos(ang) * r, cy + math.sin(ang) * r + 30 * self.p * self.p
            pygame.draw.polygon(surf, (96, 160, 248), [(px, py - 3), (px + 3, py + 2), (px - 2, py + 2)])

    def _draw_stun(self, surf, cx, cy):
        """Faíscas amarelas girando em volta do alvo."""
        for i in range(6):
            ang = self.p * math.tau * 2 + i / 6 * math.tau
            px, py = cx + math.cos(ang) * 24, cy - 6 + math.sin(ang) * 10
            if int(self.p * 16 + i) % 3:
                pts = [(px, py - 4), (px + 2, py - 1), (px - 1, py + 1), (px + 1, py + 4)]
                pygame.draw.lines(surf, DARK, False, pts, 3)
                pygame.draw.lines(surf, (248, 224, 64), False, pts, 1)


# ============================================================ transformação em legend
class Transform(Timed):
    """O duelista vira o legend: energia da cor do elemento sobe em volta dele, o corpo treme e brilha,
    um clarão branco cobre tudo e, no auge do clarão, a cena troca o desenho (`scene.become(f)`)."""
    dur = 2.1
    CHARGE, FLASH = 0.45, 0.55       # frações da animação: carga até 45%, clarão até 55%

    def __init__(self, fighter, color):
        self.f = fighter
        self.color = color
        self.swapped = False

    def begin(self):
        sfx.play("transform")
        self.parts = [Particle(random.uniform(-34, 34), random.uniform(-6, 30), random.uniform(40, 90),
                               random.uniform(0, 0.4)) for _ in range(40)]

    def tick(self):
        charging = self.p < self.CHARGE
        self.f.offset.x = random.choice((-1, 0, 1)) * (2 if charging and self.p > 0.15 else 0)
        self.f.flash = self.CHARGE - 0.08 < self.p < self.FLASH and int(self.t * 30) % 2 == 0
        if not self.swapped and self.p >= (self.CHARGE + self.FLASH) / 2:
            self.swapped = True
            self.scene.become(self.f)

    def finish(self):
        self.f.offset.x = 0
        self.f.flash = False
        if not self.swapped:
            self.scene.become(self.f)

    def draw(self, surf):
        cx, cy = self.f.center
        power = min(1.0, self.p / self.CHARGE) if self.p < self.FLASH else max(0.0, 1 - (self.p - self.FLASH) / 0.3)
        radius = int(30 + 40 * power)
        surf.blit(glow(self.color, radius), (cx - radius, cy - radius), special_flags=pygame.BLEND_ADD)
        for part in self.parts:                      # energia subindo em espiral
            q = (self.p * 1.6 - part.delay) % 1.0
            x = cx + part.x * (1 - q * 0.5) + math.sin(q * 9 + part.speed) * 6
            y = cy + part.y - q * part.speed
            size = 3 if q < 0.5 else 2
            pygame.draw.rect(surf, self.color, (int(x), int(y), size, size))
        if self.CHARGE <= self.p < self.FLASH + 0.15:  # clarão e anel
            k = (self.p - self.CHARGE) / (self.FLASH + 0.15 - self.CHARGE)
            surf.blit(overlay((255, 255, 255), 230 * (1 - k)), (0, 0))
            pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy)), int(20 + 160 * k), max(1, int(6 * (1 - k))))


class CutIn(Timed):
    """Faixa de apresentação: atravessa a tela com o retrato e o nome do legend (como nos animes)."""
    dur = 2.0

    def __init__(self, portrait, name, subtitle, color, from_left=True):
        self.portrait = portrait
        self.name = name
        self.subtitle = subtitle
        self.color = color
        self.from_left = from_left

    def draw(self, surf):
        from ..ui import draw_outlined, draw_text
        p = self.p
        slide = 1 - (1 - min(1.0, p / 0.18)) ** 3 if p < 0.82 else 1 - ((p - 0.82) / 0.18) ** 2
        band_h = 64
        y = 52
        offset = int((1 - slide) * GAME_W) * (-1 if self.from_left else 1)
        band = pygame.Rect(offset, y, GAME_W, band_h)
        surf.blit(overlay((0, 0, 0), 120 * slide), (0, 0))
        pygame.draw.rect(surf, DARK, band.inflate(0, 6))
        pygame.draw.rect(surf, self.color, band)
        for i in range(0, GAME_W, 12):               # listras diagonais correndo (sensação de velocidade)
            x = band.x + (i + int(self.t * 240)) % (GAME_W + 40) - 40
            pygame.draw.line(surf, [min(255, c + 40) for c in self.color], (x, band.bottom), (x + 18, band.y), 3)
        face = self.portrait
        surf.blit(face, (band.x + (24 if self.from_left else GAME_W - face.get_width() - 24),
                         band.centery - face.get_height() // 2))
        text_x = band.x + (face.get_width() + 40 if self.from_left else 24)
        draw_outlined(surf, self.name, (text_x, band.y + 12), (255, 255, 255), DARK, size=24)
        draw_text(surf, self.subtitle, (text_x, band.y + 42), color=(255, 255, 255), shadow=DARK)

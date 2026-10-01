"""Desenho da batalha: campo, lutadores, painéis de vida, marcadores, mão de cartas, botões e a tela do Mimo.

`BattleHUD` é um "mixin": a BattleScene herda dele e ganha estes métodos de desenho. A cena fica só com a
lógica (fila de passos, turnos, narração, entrada do jogador) e este arquivo só com o visual. Nada aqui muda
regra de jogo: tudo é lido do estado (`self.player`, `self.enemy`, `self.state`, `self.cursor`...).
"""
import math

import pygame

from game.core import abilities
from game.core.rules import HAND_SIZE, ICE_LIMIT
from game.data.cards import ARCHETYPE_NAMES
from game.engine.settings import GAME_H, GAME_W, HIGHLIGHT
from game.engine.ui import draw_box, draw_outlined, draw_text, overlay, text_width, wrap
from game.graphics import backgrounds
from game.graphics import pixelart as art
from game.scenes.battle_fx import DARK

GREEN = (72, 200, 96)
FIELD_H = backgrounds.BATTLE_H                  # parte de cima: o campo; embaixo: o painel das cartas
# onde ficam os pés de cada lutador (no meio da plataforma); o resto sai do tamanho do desenho
PLAYER_FEET = (backgrounds.PLAYER_PLATFORM.centerx, backgrounds.PLAYER_PLATFORM.centery + 6)
ENEMY_FEET = (backgrounds.ENEMY_PLATFORM.centerx, backgrounds.ENEMY_PLATFORM.centery + 4)
MONSTER_SCALE = 4                    # monstro do pacote: 16 x 16 -> 64 px
PLAYER_HEIGHT, ENEMY_HEIGHT = 88, 88  # altura das pessoas na tela antes da transformação
PLAYER_LEGEND_H, ENEMY_LEGEND_H = 96, 78     # altura dos legends: quem está no fundo é menor (perspectiva)
PORTRAIT_H = 56                              # retrato na faixa de apresentação
HUD_ICON = 30                                # retrato pequeno no painel de vida
PANEL = pygame.Rect(0, FIELD_H, GAME_W, GAME_H - FIELD_H)
ENEMY_BOX = pygame.Rect(8, 8, 172, 42)
PLAYER_BOX = pygame.Rect(GAME_W - 180, FIELD_H - 48, 172, 42)
HUD_FILL = (20, 24, 40, 215)
MESSAGE_BOX = pygame.Rect(8, FIELD_H + 26, GAME_W - 16, 50)   # caixa de mensagens (menor que o painel)
INFO_PANEL = pygame.Rect(GAME_W - 146, FIELD_H + 6, 138, 70)
ABILITY_BUTTON = pygame.Rect(GAME_W - 146, GAME_H - 22, 68, 16)
END_BUTTON = pygame.Rect(GAME_W - 76, GAME_H - 22, 68, 16)
DISCARD_MARK = (232, 64, 48)
HAND_X = 10
HAND_Y = FIELD_H + 14
HAND_AREA = INFO_PANEL.x - HAND_X - 6        # largura disponível para as cartas da mão
CARD_STEP = 62                                # espaço entre cartas quando cabem sem sobrepor
SELECT_LIFT = 10                              # quanto a carta escolhida sobe
DEFENSE_RING = (120, 176, 248)
AURA_RING = (192, 128, 240)


_hud_backgrounds = {}


def hud_icon(img):
    """Retratinho do painel de vida (HUD_ICON x HUD_ICON)."""
    if img is None:
        return None
    return pygame.transform.smoothscale(img.convert_alpha() if pygame.display.get_surface() else img,
                                        (HUD_ICON, HUD_ICON))


def hud_background(size):
    """Fundo escuro translúcido dos painéis de vida (criado uma vez por tamanho)."""
    if size not in _hud_backgrounds:
        box = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(box, HUD_FILL, box.get_rect(), border_radius=4)
        _hud_backgrounds[size] = box
    return _hud_backgrounds[size]


class BattleHUD:
    """Métodos de desenho da BattleScene (veja o topo do arquivo)."""

    def card_x(self, index):
        n = len(self.player.hand)
        step = CARD_STEP if n <= 5 else (HAND_AREA - art.CARD_W) // (n - 1)
        return HAND_X + index * step

    def card_pos(self, index):
        return (self.card_x(index) + art.CARD_W // 2, HAND_Y + art.CARD_H // 2)

    # ------------------------------------------------------------ desenho
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        backgrounds.draw_clouds(surf, self.time)
        for f in (self.enemy, self.player):
            self.draw_fighter(surf, f)
        self.draw_info(surf, self.enemy, ENEMY_BOX)
        self.draw_markers(surf, self.enemy, ENEMY_BOX.right + 4, ENEMY_BOX.y + 2)
        self.draw_info(surf, self.player, PLAYER_BOX)
        self.draw_markers(surf, self.player, PLAYER_BOX.x - 4, PLAYER_BOX.bottom - 11, align="right")
        if self.current is not None:
            self.current.draw(surf)
        for text, x, y, t, color in self.floats:   # número salta, cresce e vai subindo
            hop = math.sin(min(1.0, t / 0.35) * math.pi) * 8
            size = 24 if t < 0.18 else 16
            draw_outlined(surf, text, (int(x), int(y - t * 20 - hop)), color, size=size, align="center")
        if self.shake_t > 0:
            k = self.shake_t * 40
            dx = round(math.sin(k * 3.1) * self.shake_power)
            dy = round(math.cos(k * 2.3) * self.shake_power * 0.6)
            surf.subsurface((0, 0, GAME_W, FIELD_H)).scroll(dx, dy)
        self.draw_panel(surf)
        if self.dialog.visible:                       # mensagem na tela: o painel de baixo escurece atrás dela
            surf.blit(overlay((16, 20, 36), 170, PANEL.size), PANEL)
        self.dialog.draw(surf)

    def draw_fighter(self, surf, f):
        if not f.visible:
            return
        bob = 0
        if self.state == "choose" and not self.busy:
            bob = round(math.sin(self.time * 4 + (0 if f.is_player else 2)))
        x = f.base.x + f.offset.x
        y = f.base.y + f.offset.y + bob
        center = (int(x + 32), int(y + 36))
        pulse = math.sin(self.time * 5) * 2
        if f.aura > 0:
            pygame.draw.circle(surf, AURA_RING, center, int(33 + pulse), 1)
        if f.defense > 0:
            pygame.draw.circle(surf, DEFENSE_RING, center, int(29 + pulse), 1)
        surf.set_clip(pygame.Rect(0, 0, GAME_W, int(f.feet_y)))
        surf.blit(f.white if f.flash else f.sprite, (round(x), round(y)))
        surf.set_clip(None)

    def draw_hp_bar(self, surf, x, y, w, f):
        ratio = max(0.0, f.disp_hp) / f.max_hp
        color = (88, 208, 104) if ratio > 0.5 else (248, 200, 48) if ratio > 0.2 else (240, 72, 56)
        pygame.draw.rect(surf, (64, 72, 64), (x - 1, y - 1, w + 2, 6))
        pygame.draw.rect(surf, (96, 104, 96), (x, y, w, 4))
        if ratio > 0:
            fill_w = max(1, int(w * ratio))
            pygame.draw.rect(surf, color, (x, y, fill_w, 4))
            pygame.draw.line(surf, (255, 255, 255), (x, y), (x + fill_w - 1, y))

    def draw_info(self, surf, f, rect):
        """Painel de vida compacto: retrato, nome do legend, dono e nível, barra de PV, energia e cartas."""
        legend = f.state.legend
        accent = art.ARCHETYPE_COLORS[legend.archetype][0] if legend else (190, 196, 210)
        surf.blit(hud_background(rect.size), rect)
        pygame.draw.rect(surf, accent, rect, 1, border_radius=4)
        icon = pygame.Rect(rect.x + 5, rect.y + 6, HUD_ICON, HUD_ICON)
        pygame.draw.rect(surf, accent, icon.inflate(2, 2))
        if f.icon is not None:
            surf.blit(f.icon, icon)
        x = icon.right + 6
        draw_text(surf, f.name, (x, rect.y + 4), size=12, color=(255, 255, 255), shadow=(0, 0, 0))
        owner = f"{f.owner} Nv{f.level}" if f.owner else f"Nv{f.level}"
        draw_text(surf, owner, (rect.right - 6, rect.y + 4), size=12, color=(168, 176, 200), shadow=None,
                  align="right")
        self.draw_hp_bar(surf, x, rect.y + 18, rect.right - 6 - x, f)
        for i in range(max(f.max_energy, f.energy)):           # energia: bolinhas douradas
            center = (x + 3 + i * 8, rect.y + 32)
            pygame.draw.circle(surf, (8, 8, 16), center, 3)
            pygame.draw.circle(surf, (248, 216, 64) if i < f.energy else (88, 92, 110), center, 2)
        cards = f"DECK {len(f.deck.draw_pile)}" if f.is_player else f"MÃO {len(f.hand)}"
        draw_text(surf, cards, (x + 46, rect.y + 27), size=12, color=(168, 176, 200), shadow=None)
        draw_text(surf, f"{math.ceil(f.disp_hp)}/{f.max_hp}", (rect.right - 6, rect.y + 27), size=12,
                  color=(255, 255, 255), shadow=(0, 0, 0), align="right")

    def draw_markers(self, surf, f, x, y, align="left"):
        """Fileira de marcadores: força, proteção, defesa, aura, queimadura, gelo, veneno, paralisia e efeitos.
        align="right": a fileira termina em x (crescendo para a esquerda)."""
        chips = [
            ("sword", f.strength, str(f.strength), (184, 64, 48)),      # força do legend (fixa)
            ("wall", f.protection, str(f.protection), (88, 88, 104)),   # proteção do legend (fixa)
            ("shield", f.defense, str(f.defense), (48, 88, 200)),
            ("aura", f.aura, str(f.aura), (136, 64, 184)),
            ("flame", f.burn, str(f.burn), (216, 88, 40)),
            ("ice", f.ice, f"{f.ice}/{ICE_LIMIT}", (48, 136, 200)),
            ("poison", f.poison, str(f.poison), (120, 56, 168)),
            ("stun", f.stun, str(f.stun), (184, 136, 16)),
        ]
        items = [("chip", icon_name, label, color, 14 + len(label) * 6)
                 for icon_name, active, label, color in chips if active]
        items += [("flag", None, text, color, text_width(text, 12) + 6)
                  for flag, text, color in ((f.frozen, "CONGELADO", (48, 136, 200)),
                                            (f.ice_clone, "CLONE", (48, 136, 200)),
                                            (f.free_utility, "GRÁTIS", (40, 144, 64))) if flag]
        if align == "right":
            x -= sum(width + 2 for *_, width in items)
        for kind, icon_name, label, color, width in items:
            if kind == "chip":
                chip = pygame.Rect(x, y, width, 11)
                pygame.draw.rect(surf, DARK, chip, border_radius=3)
                pygame.draw.rect(surf, (248, 248, 232), chip.inflate(-2, -2), border_radius=3)
                surf.blit(pygame.transform.scale(art.icon(icon_name), (9, 9)), (x + 2, y + 1))
                draw_text(surf, label, (x + 12, y + 1), size=12, color=color, shadow=None)
            else:
                draw_text(surf, label, (x + 2, y + 1), size=12, color=color, shadow=(0, 0, 0))
            x += width + 2

    def draw_panel(self, surf):
        draw_box(surf, PANEL)
        p = self.player
        choosing = self.state in ("choose", "discard") and not self.busy
        on_card = choosing and self.cursor < len(p.hand)
        for i, card in enumerate(p.hand):
            if not (on_card and i == self.cursor):
                self.draw_hand_card(surf, card, i, False)
        if on_card:                                   # a selecionada fica por cima das outras
            self.draw_hand_card(surf, p.hand[self.cursor], self.cursor, True)
        self.draw_info_panel(surf, choosing)
        self.draw_button(surf, ABILITY_BUTTON, "HABILIDADE", choosing and self.cursor == self.ability_slot,
                         usable=abilities.can_use(p.state))
        self.draw_button(surf, END_BUTTON, "FIM TURNO", self.state == "choose" and self.cursor == self.end_slot)
        if self.state == "mimo" and not self.busy:
            self.draw_mimo(surf)

    def draw_button(self, surf, rect, label, selected, usable=True):
        pygame.draw.rect(surf, DARK, rect, border_radius=3)
        fill = HIGHLIGHT if selected else (216, 216, 208) if usable else (176, 176, 168)
        pygame.draw.rect(surf, fill, rect.inflate(-2, -2), border_radius=3)
        draw_text(surf, label, (rect.centerx, rect.y + 3), size=12, shadow=None, align="center",
                  color=(72, 72, 80) if usable else (128, 128, 136))

    def info_text(self):
        """(título, linha 2, texto) do painel de informações, conforme o que está no cursor."""
        p = self.player
        legend = p.state.legend
        if self.state == "discard":
            return ("DESCARTAR", f"Marcadas {len(self.picked)}/{abilities.DROGOZ_DISCARD}",
                    "A marca ou desmarca a carta. Com 3 marcadas: descarta e cura 15. B cancela.")
        if self.cursor < len(p.hand):
            card = p.hand[self.cursor]
            return (card.name.upper(), f"{ARCHETYPE_NAMES[card.archetype]} - Custo {p.state.cost_of(card)}",
                    card.text)
        if self.cursor == self.ability_slot and legend:
            kind = "ATIVA" if legend.active else "PASSIVA"
            used = " (usada)" if legend.active and p.state.ability_used else ""
            return (legend.name.upper(), f"Habilidade {kind}{used}", legend.short)
        return ("FIM DO TURNO", "", f"Terminar o turno. Você compra até ter {HAND_SIZE} cartas.")

    def draw_info_panel(self, surf, choosing):
        info = INFO_PANEL
        pygame.draw.rect(surf, (232, 232, 224), info, border_radius=3)
        if not choosing:
            draw_text(surf, "...", (info.centerx, info.y + 20), align="center")
            return
        title, sub, text = self.info_text()
        draw_text(surf, title, (info.x + 5, info.y + 3), size=12 if len(title) > 11 else 16)
        too_costly = self.cursor < len(self.player.hand) and self.player.state.cost_of(
            self.player.hand[self.cursor]) > self.player.energy
        draw_text(surf, sub, (info.x + 5, info.y + 16), size=12, color=(208, 64, 56) if too_costly else (72, 72, 80))
        for i, line in enumerate(wrap(text, info.w - 10, 12)[:4]):
            draw_text(surf, line, (info.x + 5, info.y + 28 + i * 10), size=12, shadow=None)

    def draw_mimo(self, surf):
        """As cartas reveladas pelo Mimo no meio da tela; as que ele não pode jogar ficam apagadas."""
        surf.blit(overlay((16, 8, 32), 190), (0, 0))
        draw_outlined(surf, "MIMO REVELOU:", (GAME_W // 2, 3), (255, 255, 255), DARK, align="center")
        big_w, big_h = art.CARD_W * 2, art.CARD_H * 2
        gap = 24
        total = len(self.revealed) * (big_w + gap) - gap
        x0 = GAME_W // 2 - total // 2
        for i, card in enumerate(self.revealed):
            x = x0 + i * (big_w + gap)
            y = 20 - (6 if i == self.option else 0)
            if i == self.option:
                pygame.draw.rect(surf, HIGHLIGHT, (x - 3, y - 3, big_w + 6, big_h + 6), 3, border_radius=6)
            surf.blit(art.card_zoom(card, 2), (x, y))
            if not abilities.mimo_can_play(card):          # só VENENO/NINJA: as outras ficam apagadas
                shade = pygame.Rect(x, y, big_w, big_h)
                surf.blit(overlay((0, 0, 0), 150, shade.size), shade)
                draw_outlined(surf, "NÃO PODE", (shade.centerx, shade.centery - 6), (255, 160, 160), DARK,
                              align="center")
        skip = pygame.Rect(GAME_W // 2 - 50, 20 + big_h + 8, 100, 16)
        self.draw_button(surf, skip, "NÃO JOGAR", self.option == len(self.revealed))
        draw_text(surf, "Só cartas de VENENO ou NINJA podem ser jogadas de graça.", (GAME_W // 2, skip.bottom + 8),
                  size=12, color=(255, 255, 255), shadow=DARK, align="center")

    def draw_hand_card(self, surf, card, index, selected):
        x = self.card_x(index)
        sway = math.sin(self.time * 2.2 + index * 0.8) * 1.5 if self.state == "choose" else 0
        y = round(HAND_Y + sway - (SELECT_LIFT if selected else 0))
        marked = self.state == "discard" and index in self.picked
        if marked:                                    # Drogoz: carta marcada para descartar
            y -= SELECT_LIFT
            pygame.draw.rect(surf, DISCARD_MARK, (x - 2, y - 2, art.CARD_W + 4, art.CARD_H + 4), 2, border_radius=4)
        if selected:
            pygame.draw.rect(surf, HIGHLIGHT, (x - 2, y - 2, art.CARD_W + 4, art.CARD_H + 4), 2, border_radius=4)
        surf.blit(art.render_card(card, dim=not self.player.state.can_play(card)), (x, y))

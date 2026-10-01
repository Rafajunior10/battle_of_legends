"""Mesa de troca da lanchonete: escolher a carta que você dá e a que quer do outro jogador online.

Etapa 1: suas cartas sobrando (fora dos decks). Etapa 2: as cartas sobrando do outro jogador.
Confirmando, a proposta vai pela rede (swap_offer) e a tela volta para a lanchonete; a resposta chega lá
(scenes/cafe.py). As regras da troca ficam em core/economy.py (`can_swap`, `swap_card`).
"""
import pygame

from game.core import economy
from game.core.economy import ShopError
from game.data.cards import CARDS
from game.engine import sfx
from game.engine.config import action_label
from game.engine.settings import CANCEL_KEYS, CONFIRM_KEYS, DOWN_KEYS, GAME_W, UP_KEYS
from game.engine.ui import Prompt, draw_box, draw_text, vertical_gradient
from game.graphics import pixelart as art
from game.scenes.base import Scene
from game.scenes.common import (
    INFO_RECT,
    LIST_RECT,
    LIST_ROWS,
    ROW_H,
    ScrollList,
    draw_card_info,
    draw_row,
    draw_scrollbar,
)

GIVE, WANT = 0, 1


class TradeTableScene(Scene):
    def __init__(self, game, lobby, partner_id, partner_name, their_cards):
        super().__init__(game)
        self.ch = game.character
        self.lobby = lobby
        self.partner_id, self.partner = partner_id, partner_name
        self.cards = [self.ch.spare_cards(), list(their_cards)]
        self.lists = [ScrollList(LIST_ROWS), ScrollList(LIST_ROWS)]
        self.step = GIVE
        self.give = None
        self.prompt = Prompt()
        self.bg = vertical_gradient((GAME_W, 270), (40, 96, 64), (120, 176, 120))

    @property
    def current(self):
        rows, lst = self.cards[self.step], self.lists[self.step]
        return rows[lst.index] if rows else None

    # ------------------------------------------------------------ entrada
    def handle(self, event):
        if self.prompt.handle(event) or event.type != pygame.KEYDOWN:
            return
        rows, lst = self.cards[self.step], self.lists[self.step]
        if event.key in UP_KEYS or event.key in DOWN_KEYS:
            lst.move(-1 if event.key in UP_KEYS else 1, len(rows))
            sfx.play("cursor")
        elif event.key in CONFIRM_KEYS and rows:
            self.choose(self.current)
        elif event.key in CANCEL_KEYS:
            sfx.play("cancel")
            if self.step == WANT:
                self.step = GIVE
            else:
                self.leave(None, None)

    def choose(self, card_id):
        if self.step == GIVE:
            sfx.play("confirm")
            self.give, self.step = card_id, WANT
            return
        try:
            economy.can_swap(self.ch, self.give, card_id)
        except ShopError as err:
            sfx.play("error")
            self.prompt.say(str(err))
            return
        sfx.play("confirm")
        give, want = CARDS[self.give].name.upper(), CARDS[card_id].name.upper()
        self.prompt.ask(f"Oferecer a sua {give} pela {want} de {self.partner}?",
                        lambda yes: self.leave(self.give, card_id) if yes else None)

    def leave(self, give, want):
        """Manda a proposta (ou a desistência, com give=None) e volta para a lanchonete."""
        net = self.game.net
        if net:
            net.send({"t": "swap_offer", "to": self.partner_id, "give": give, "want": want})
        self.lobby.banner(f"Proposta enviada! Esperando {self.partner}..." if give else "Você desistiu da troca.")
        self.game.transition_to(lambda: self.lobby)

    def update(self, dt):
        self.prompt.update(dt)

    # ------------------------------------------------------------ desenho
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_box(surf, (4, 4, GAME_W - 8, 40))
        draw_text(surf, f"MESA DE TROCA: VOCÊ x {self.partner}", (14, 8))
        if self.step == GIVE:
            step = "1. Escolha a carta que você DÁ (só as que estão sobrando)."
        else:
            step = f"2. Você dá {CARDS[self.give].name.upper()}. Escolha a que você QUER de {self.partner}."
        draw_text(surf, step, (14, 26), size=12, color=(72, 72, 80), shadow=None)
        hint = f"{action_label('a')} escolhe   {action_label('b')} volta"
        draw_text(surf, hint, (GAME_W - 14, 9), size=12, align="right")
        self.draw_list(surf)
        if self.current:
            mine = self.step == GIVE
            extra = f"Sobrando: {self.ch.spare(self.current)}" if mine else f"Você tem: {self.ch.owned(self.current)}"
            draw_card_info(surf, self.ch.card(self.current), rect=INFO_RECT, extra=extra)
        self.prompt.draw(surf)

    def draw_list(self, surf):
        box = LIST_RECT
        draw_box(surf, box)
        rows, lst = self.cards[self.step], self.lists[self.step]
        for line, i in enumerate(lst.visible(len(rows))):
            card = self.ch.card(rows[i])
            rect = pygame.Rect(box.x + 6, box.y + 8 + line * ROW_H, box.w - 16, ROW_H)
            draw_row(surf, rect, i == lst.index)
            surf.blit(art.icon(card.icon), (rect.x + 12, rect.y + 2))
            full = self.step == WANT and not self.ch.can_add(rows[i])
            color = (150, 150, 158) if full else (
                art.RARITY_COLORS[card.rarity] if card.rarity != "comum" else (72, 72, 80))
            draw_text(surf, card.name if len(card.name) <= 14 else card.short, (rect.x + 28, rect.y + 2), color=color)
            if full:
                draw_text(surf, "MÁX", (rect.right - 4, rect.y + 3), size=12, color=(208, 64, 56), align="right")
        draw_scrollbar(surf, lst, len(rows), box)

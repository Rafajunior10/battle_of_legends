"""Loja de cartas: comprar cartas avulsas, abrir packs, vender cartas e montar decks."""
import math

import pygame

from game.core import economy
from game.core.economy import ShopError
from game.data.cards import ARCHETYPE_NAMES, CARDS, ELEMENTS, MAX_COPIES, PACKS, RARITY_NAMES, SHOP_STOCK, UTILITY
from game.data.legends import LEGENDS
from game.engine import sfx
from game.engine.config import action_label
from game.engine.settings import CANCEL_KEYS, CONFIRM_KEYS, DOWN_KEYS, GAME_H, GAME_W, LEFT_KEYS, RIGHT_KEYS, UP_KEYS
from game.engine.ui import Prompt, draw_box, draw_outlined, draw_text, overlay, vertical_gradient, wrap
from game.graphics import pixelart as art
from game.scenes.base import Scene
from game.scenes.common import (
    INFO_RECT,
    LIST_RECT,
    LIST_ROWS,
    ROW_H,
    SUB_INFO_RECT,
    SUB_LIST_RECT,
    SUB_LIST_ROWS,
    TYPE_ICONS,
    ScrollList,
    draw_bets,
    draw_card_info,
    draw_coin,
    draw_row,
    draw_scrollbar,
    draw_tabs,
    draw_type_tabs,
)

TABS = [
    "COMPRAR",
    # "PACKS",   # packs desligados por enquanto: descomente esta linha para a aba voltar (tudo abaixo continua pronto)
    "EVOLUIR",
    "VENDER",
    "DECKS",
]
TYPES = [*ELEMENTS, UTILITY]                 # sub-abas: as cartas separadas por tipo
TYPED_TABS = {"COMPRAR", "EVOLUIR", "VENDER"}   # abas que têm as sub-abas de tipo
LEFT, RIGHT, UP, DOWN = LEFT_KEYS, RIGHT_KEYS, UP_KEYS, DOWN_KEYS


class PackOpening:
    """Animação: o pack treme, abre e as 3 cartas viram uma de cada vez."""
    SHAKE = 0.9
    FLIP = 0.45

    def __init__(self, pack, result, card_for):
        """card_for(id) devolve a carta no nível do jogador."""
        self.pack = pack
        self.cards = result.cards
        self.new = result.new
        self.converted = result.converted
        self.t = 0.0
        self.revealed = 0
        self.back = art.scale(art.card_back(), 2)
        self.faces = [art.scale(art.render_card(card_for(c)), 2) for c in self.cards]
        self.pack_img = art.scale(art.pack_image(pack.color), 3)
        sfx.play("pack")

    @property
    def done(self):
        return self.revealed >= len(self.cards) and self.t > self.flip_start(len(self.cards) - 1) + self.FLIP

    def flip_start(self, i):
        return self.SHAKE + 0.35 + i * 0.6

    def skip(self):
        self.t = self.flip_start(len(self.cards) - 1) + self.FLIP + 0.01
        self.revealed = len(self.cards)

    def update(self, dt):
        self.t += dt
        for i in range(self.revealed, len(self.cards)):
            if self.t >= self.flip_start(i) + self.FLIP / 2:
                self.revealed = i + 1
                sfx.play("reveal")

    def draw(self, surf):
        surf.blit(overlay((16, 16, 40), 200), (0, 0))
        draw_outlined(surf, self.pack.name.upper(), (GAME_W // 2, 14), (248, 216, 96), size=16, align="center")
        if self.t < self.SHAKE:
            dx = math.sin(self.t * 60) * 3 * (self.t / self.SHAKE)
            img = self.pack_img
            surf.blit(img, (GAME_W // 2 - img.get_width() // 2 + dx, 50))
            return
        if self.t < self.SHAKE + 0.2:   # clarão
            surf.blit(overlay((255, 255, 255), 255 * (1 - (self.t - self.SHAKE) / 0.2)), (0, 0))
        for i in range(len(self.cards)):
            cx = GAME_W // 2 + (i - 1) * 140
            local = self.t - self.flip_start(i)
            face = self.faces[i] if local >= self.FLIP / 2 else self.back
            if 0 <= local < self.FLIP:
                width = abs(math.cos(local / self.FLIP * math.pi)) * face.get_width()
            else:
                width = face.get_width()
            img = pygame.transform.scale(face, (max(1, int(width)), face.get_height()))
            y = 46 if local < self.FLIP else 40
            surf.blit(img, (cx - img.get_width() // 2, y))
            if i < self.revealed:
                card = CARDS[self.cards[i]]
                draw_text(surf, card.name, (cx, 204), color=(248, 248, 248), shadow=(40, 40, 48),
                          size=12 if len(card.name) > 10 else 16, align="center")
                if self.cards[i] in self.converted:
                    tag = pygame.Rect(cx - 30, 26, 60, 12)
                    pygame.draw.rect(surf, (40, 40, 48), tag, border_radius=3)
                    pygame.draw.rect(surf, (200, 144, 24), tag.inflate(-2, -2), border_radius=3)
                    draw_text(surf, f"+{self.converted[self.cards[i]]} BETS", (cx, 27), color=(255, 255, 255),
                              size=12, shadow=None, align="center")
                elif self.cards[i] in self.new:
                    tag = pygame.Rect(cx - 16, 26, 32, 12)
                    pygame.draw.rect(surf, (40, 40, 48), tag, border_radius=3)
                    pygame.draw.rect(surf, (232, 64, 48), tag.inflate(-2, -2), border_radius=3)
                    draw_text(surf, "NOVA", (cx, 27), color=(255, 255, 255), size=12, shadow=None, align="center")
        if self.done:
            draw_text(surf, f"{action_label('a')}: continuar", (GAME_W // 2, 226), color=(248, 248, 248),
                      shadow=(40, 40, 48), size=12, align="center")


class ShopScene(Scene):
    def __init__(self, game, back):
        super().__init__(game)
        self.ch = game.character
        self.back = back
        self.tab = 0
        self.kind = 0                 # sub-aba de tipo (índice em TYPES)
        self.focus = "tabs"           # onde o cursor está: "tabs" (abas), "types" (sub-abas) ou "list"
        self.lists = {(t, k): ScrollList(SUB_LIST_ROWS if t in TYPED_TABS else LIST_ROWS)
                      for t in TABS for k in range(len(TYPES))}
        self.prompt = Prompt()
        self.opening = None
        self.time = 0.0
        self.bg = vertical_gradient((GAME_W, GAME_H), (120, 72, 56), (216, 176, 120))

    def on_enter(self):
        sfx.music("lobby")

    # ------------------------------------------------------------ dados de cada aba
    @property
    def tab_name(self):
        return TABS[self.tab]

    @property
    def typed(self):
        """A aba atual tem as sub-abas de tipo?"""
        return self.tab_name in TYPED_TABS

    def of_kind(self, card_ids):
        """Só as cartas do tipo da sub-aba atual."""
        return [c for c in card_ids if CARDS[c].archetype == TYPES[self.kind]]

    def items(self):
        name = self.tab_name
        if name == "COMPRAR":
            return self.of_kind(SHOP_STOCK)
        if name == "PACKS":
            return PACKS
        if name == "EVOLUIR":
            return self.of_kind(self.owned_types())
        if name == "VENDER":
            return self.of_kind(self.ch.spare_cards())
        return [0, 1, 2]

    def owned_types(self):
        have = set(self.ch.collection)
        return [c for c in CARDS if c in have]

    @property
    def lst(self):
        return self.lists[(self.tab_name, self.kind if self.typed else 0)]

    @property
    def list_rect(self):
        return SUB_LIST_RECT if self.typed else LIST_RECT

    @property
    def info_rect(self):
        return SUB_INFO_RECT if self.typed else INFO_RECT

    # ------------------------------------------------------------ diálogo
    def say(self, text, then=None):
        self.prompt.say(text, then)

    def attempt(self, action, success):
        """Roda uma regra da economia; se ela recusar, mostra o motivo."""
        try:
            result = action()
        except ShopError as err:
            sfx.play("error")
            self.say(str(err))
            return
        self.ch.save()
        success(result)

    # ------------------------------------------------------------ input
    def handle(self, event):
        if self.opening:
            self.handle_opening(event)
            return
        if self.prompt.handle(event):
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key in CANCEL_KEYS:
            sfx.play("cancel")
            self.ch.save()
            self.game.transition_to(self.back)
        elif key in UP or key in DOWN:
            self.move_focus(-1 if key in UP else 1)
        elif key in LEFT or key in RIGHT:
            step = 1 if key in RIGHT else -1
            if self.focus == "tabs":
                self.tab = (self.tab + step) % len(TABS)
            elif self.typed:                       # na sub-aba ou na lista: troca o tipo de carta
                self.kind = (self.kind + step) % len(TYPES)
            sfx.play("cursor")
        elif key in CONFIRM_KEYS:
            self.confirm()

    def handle_opening(self, event):
        """Durante a abertura do pack: A/B pula a animação ou fecha quando acabou."""
        if event.type == pygame.KEYDOWN and (event.key in CONFIRM_KEYS or event.key in CANCEL_KEYS):
            if self.opening.done:
                self.close_opening()
            else:
                self.opening.skip()

    def confirm(self):
        """A: nas abas, desce para a lista; na lista, faz a ação da aba com o item escolhido."""
        if self.focus != "list":
            self.move_focus(1)
        elif self.items():
            actions = {"COMPRAR": self.buy_card, "PACKS": self.buy_pack, "EVOLUIR": self.upgrade,
                       "VENDER": self.sell_card, "DECKS": self.edit_deck}
            actions[self.tab_name](self.items()[self.lst.index])

    def move_focus(self, step):
        """Cima/baixo: abas -> sub-abas de tipo -> lista. Dentro da lista, anda pelas linhas."""
        levels = ["tabs", "types", "list"] if self.typed else ["tabs", "list"]
        count = len(self.items())
        if self.focus == "list" and count and not (step < 0 and self.lst.index == 0):
            if step > 0 and self.lst.index == count - 1:
                return
            self.lst.move(step, count)
        else:
            i = levels.index(self.focus) if self.focus in levels else 0
            self.focus = levels[max(0, min(len(levels) - 1, i + step))]
            if self.focus == "list":
                self.lst.index = 0
                self.lst.clamp(count)
        sfx.play("cursor")

    def buy_card(self, cid):
        card = CARDS[cid]

        def bought(_):
            sfx.play("coin")
            self.say(f"Você comprou {card.name.upper()}! Ela foi para a sua coleção.")

        def done(yes):
            if yes:
                self.attempt(lambda: economy.buy_card(self.ch, cid), bought)
        self.prompt.ask(f"Comprar {card.name.upper()} por {card.price} BETS?", done)

    def buy_pack(self, pack):
        def opened(result):
            self.opening = PackOpening(pack, result, self.ch.card)

        def done(yes):
            if yes:
                self.attempt(lambda: economy.buy_pack(self.ch, pack), opened)
        self.prompt.ask(f"Comprar o {pack.name.upper()} por {pack.price} BETS?", done)

    def close_opening(self):
        converted = self.opening.converted
        self.opening = None
        sfx.play("confirm")

        def go(yes):
            if yes:
                self.edit_deck(self.ch.active_deck)
        question = "As cartas foram para a sua coleção! Quer montar o deck agora?"
        if converted:
            total = sum(converted.values())
            question = (f"Você já tinha {MAX_COPIES} cópias de algumas cartas, então elas viraram {total} BETS. "
                        + question)
        self.prompt.ask(question, go)

    def upgrade(self, cid):
        card = self.ch.card(cid)
        cost = economy.upgrade_cost(self.ch, cid)
        if cost is None:
            sfx.play("error")
            self.say(f"{card.name.upper()} já está no nível máximo!")
            return
        xp, bets = cost

        def evolved(level):
            sfx.play("levelup")
            self.say(f"{card.name.upper()} evoluiu para o nível {level}!")

        def done(index):
            if index in (0, 1):
                currency = "xp" if index == 0 else "bets"
                self.attempt(lambda: economy.upgrade_card(self.ch, cid, currency), evolved)
        self.prompt.choose(f"Evoluir {card.name.upper()} para o nível {card.level + 1}. Pagar com:",
                    [f"{xp} XP", f"{bets} BETS", "CANCELAR"], done)

    def sell_card(self, cid):
        card = CARDS[cid]

        def sold(price):
            sfx.play("coin")
            self.say(f"Você vendeu {card.name.upper()} por {price} BETS.")
            self.lst.clamp(len(self.items()))

        def done(yes):
            if yes:
                self.attempt(lambda: economy.sell_card(self.ch, cid), sold)
        self.prompt.ask(f"Vender {card.name.upper()} por {card.sell_price} BETS?", done)

    def edit_deck(self, slot):
        from game.scenes.deckedit import DeckEditScene
        self.game.transition_to(lambda: DeckEditScene(self.game, lambda: self, slot))

    # ------------------------------------------------------------ update / desenho
    def update(self, dt):
        self.time += dt
        self.prompt.update(dt)
        self.lst.clamp(len(self.items()))
        if self.opening:
            self.opening.update(dt)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_box(surf, (4, 4, GAME_W - 8, 24))
        draw_text(surf, "LOJA DE CARTAS", (14, 9))
        draw_bets(surf, self.ch.bets, GAME_W - 14, 9)
        draw_text(surf, f"XP DE BATALHA {self.ch.battle_xp}", (GAME_W - 150, 11), size=12, color=(128, 64, 176),
                  align="right")
        draw_tabs(surf, TABS, self.tab, focused=self.focus == "tabs")
        if self.typed:
            draw_type_tabs(surf, TYPES, self.kind, focused=self.focus == "types")
        {"COMPRAR": self.draw_buy, "PACKS": self.draw_packs, "EVOLUIR": self.draw_upgrade,
         "VENDER": self.draw_sell, "DECKS": self.draw_decks}[TABS[self.tab]](surf)
        if self.opening:
            self.opening.draw(surf)
        self.prompt.draw(surf)

    def list_rows(self, surf, items):
        """Desenha a caixa da lista e devolve (índice, item, retângulo) das linhas visíveis."""
        box = self.list_rect
        draw_box(surf, box)
        draw_scrollbar(surf, self.lst, len(items), box)
        rows = []
        for row, i in enumerate(self.lst.visible(len(items))):
            rect = pygame.Rect(box.x + 6, box.y + 8 + row * ROW_H, box.w - 16, ROW_H)
            draw_row(surf, rect, i == self.lst.index, active=self.focus == "list")
            rows.append((i, items[i], rect))
        return rows

    def empty(self, surf, text):
        """Lista vazia: mensagem na lista e o quadro da carta em branco."""
        box = self.list_rect
        for i, line in enumerate(wrap(text, box.w - 24, 12)):
            draw_text(surf, line, (box.x + 12, box.y + 12 + i * 11), size=12, shadow=None)
        draw_box(surf, self.info_rect)
        icon = art.scale(art.icon(TYPE_ICONS[TYPES[self.kind]]), 4)
        surf.blit(icon, icon.get_rect(center=self.info_rect.center))

    def card_row(self, surf, card, rect, right_text, right_color):
        card = self.ch.card(card.id)
        surf.blit(art.icon(card.icon), (rect.x + 12, rect.y + 2))
        draw_text(surf, card.name if len(card.name) <= 12 else card.short, (rect.x + 28, rect.y + 2),
                  color=art.RARITY_COLORS[card.rarity] if card.rarity != "comum" else (72, 72, 80))
        art.draw_level_stars(surf, card.level, rect.x + 146, rect.y + 4)
        draw_text(surf, right_text, (rect.right - 4, rect.y + 3), size=12, color=right_color, align="right")

    def draw_buy(self, surf):
        items = self.items()
        for _, cid, rect in self.list_rows(surf, items):
            card = CARDS[cid]
            full = not self.ch.can_add(cid)
            color = (72, 72, 80) if self.ch.bets >= card.price else (208, 64, 56)
            self.card_row(surf, card, rect, "MÁX" if full else str(card.price), (136, 136, 144) if full else color)
        if not items:
            self.empty(surf, "Nenhuma carta deste tipo à venda.")
            return
        cid = items[self.lst.index]
        draw_card_info(surf, self.ch.card(cid), rect=self.info_rect,
                       extra=f"Você tem {self.ch.owned(cid)}/{MAX_COPIES}")

    def draw_upgrade(self, surf):
        items = self.items()
        if not items:
            self.list_rows(surf, items)
            self.empty(surf, f"Você ainda não tem cartas de {ARCHETYPE_NAMES[TYPES[self.kind]]}. "
                             "Compre na aba COMPRAR!")
            return
        for _, cid, rect in self.list_rows(surf, items):
            cost = economy.upgrade_cost(self.ch, cid)
            if cost is None:
                self.card_row(surf, CARDS[cid], rect, "MÁX", (200, 144, 16))
            else:
                color = (128, 64, 176) if self.ch.battle_xp >= cost[0] else (136, 136, 144)
                self.card_row(surf, CARDS[cid], rect, f"{cost[0]} XP", color)
        cid = items[self.lst.index]
        card = self.ch.card(cid)
        if card.level >= 3:
            extra = "NÍVEL MÁXIMO"
        else:
            nxt = card.at_level(card.level + 1)
            extra = f"Nv{card.level}>{card.level + 1}:  {card.value_label} > {nxt.value_label}"
        draw_card_info(surf, card, rect=self.info_rect, extra=extra)

    def draw_packs(self, surf):
        for _, pack, rect in self.list_rows(surf, PACKS):
            surf.blit(pygame.transform.scale(art.pack_image(pack.color), (10, 14)), (rect.x + 13, rect.y + 1))
            draw_text(surf, pack.name, (rect.x + 28, rect.y + 2))
            color = (72, 72, 80) if self.ch.bets >= pack.price else (208, 64, 56)
            draw_text(surf, str(pack.price), (rect.right - 4, rect.y + 3), size=12, color=color, align="right")
        tip = "Cada pack tem 10 cartas diferentes. Ao abrir, você ganha 3 delas! Cartas raras e épicas saem menos."
        for i, line in enumerate(wrap(tip, LIST_RECT.w - 24, 12)):
            draw_text(surf, line, (LIST_RECT.x + 12, LIST_RECT.y + 70 + i * 11), size=12, shadow=None)

        pack = PACKS[self.lst.index]
        rect = INFO_RECT
        draw_box(surf, rect)
        bob = round(math.sin(self.time * 3) * 2)
        surf.blit(art.pack_image(pack.color), (rect.x + 10, rect.y + 8 + bob))
        draw_coin(surf, rect.x + 56, rect.y + 16)
        draw_text(surf, str(pack.price), (rect.x + 70, rect.y + 15))
        draw_text(surf, "3 cartas", (rect.x + 56, rect.y + 33), size=12)
        draw_text(surf, pack.name.upper(), (rect.centerx, rect.y + 68), size=12, align="center")
        draw_text(surf, "CONTÉM:", (rect.x + 8, rect.y + 82), size=12, color=(208, 64, 56))
        for i, cid in enumerate(pack.cards):
            card = CARDS[cid]
            x = rect.x + 8 + (i % 2) * 56
            y = rect.y + 94 + (i // 2) * 11
            color = art.RARITY_COLORS[card.rarity]
            name = card.short if len(card.short) <= 9 else card.short[:8] + "."
            draw_text(surf, name, (x, y), size=12, color=color, shadow=None)
        x = rect.x + 12
        for rarity in ("comum", "rara", "epica"):
            x += 6 + draw_text(surf, RARITY_NAMES[rarity].lower(), (x, rect.bottom - 18), size=12, shadow=None,
                               color=art.RARITY_COLORS[rarity])

    def draw_sell(self, surf):
        items = self.items()
        for _, cid, rect in self.list_rows(surf, items):
            card = CARDS[cid]
            self.card_row(surf, card, rect, f"x{self.ch.spare(cid)} +{card.sell_price}", (40, 144, 64))
        if not items:
            self.empty(surf, f"Nenhuma carta de {ARCHETYPE_NAMES[TYPES[self.kind]]} sobrando. Só dá para vender "
                             "cópias que não estão em nenhum deck.")
            return
        card = self.ch.card(items[self.lst.index])
        draw_card_info(surf, card, rect=self.info_rect, extra=f"Sobrando {self.ch.spare(card.id)}")

    def draw_decks(self, surf):
        for _, slot, rect in self.list_rows(surf, [0, 1, 2]):
            deck = self.ch.decks[slot]
            label = f"DECK {slot + 1}" + ("  *" if slot == self.ch.active_deck else "")
            element = self.ch.deck_element(slot)
            surf.blit(art.icon(TYPE_ICONS[element]), (rect.x + 12, rect.y + 2))
            draw_text(surf, label, (rect.x + 28, rect.y + 2))
            draw_text(surf, LEGENDS[self.ch.deck_legend(slot)].name.upper(), (rect.x + 104, rect.y + 3), size=12,
                      color=art.ARCHETYPE_COLORS[element][0])
            draw_text(surf, f"{len(deck)} cartas", (rect.right - 4, rect.y + 3), size=12, align="right")
        tip = (f"{action_label('a')}: editar o deck. O deck com * é o que você usa nas batalhas. "
               "Cada deck tem um tipo (Fogo, Gelo...): nele entram as cartas desse tipo e as de Utilidades.")
        for i, line in enumerate(wrap(tip, LIST_RECT.w - 24, 12)):
            draw_text(surf, line, (LIST_RECT.x + 12, LIST_RECT.y + 64 + i * 11), size=12, shadow=None)
        rect = INFO_RECT
        draw_box(surf, rect)
        draw_text(surf, "COLEÇÃO", (rect.centerx, rect.y + 10), align="center")
        total = len(self.ch.collection)
        kinds = len(set(self.ch.collection))
        rows = [("Cartas", str(total)), ("Diferentes", f"{kinds}/{len(CARDS)}"),
                ("Sobrando", str(sum(self.ch.spare(c) for c in set(self.ch.collection))))]
        for i, (label, value) in enumerate(rows):
            y = rect.y + 30 + i * 14
            draw_text(surf, label, (rect.x + 10, y), size=12)
            draw_text(surf, value, (rect.right - 10, y), size=12, align="right")
        deck = self.ch.decks[self.lst.index]
        preview = [art.render_card(CARDS[c]) for c in deck[:8]]
        for i, img in enumerate(preview):
            small = pygame.transform.scale(img, (19, 27))
            surf.blit(small, (rect.x + 10 + (i % 4) * 26, rect.y + 82 + (i // 4) * 31))
        if len(deck) > 8:
            draw_text(surf, f"+{len(deck) - 8}", (rect.right - 10, rect.bottom - 22), size=12, align="right")

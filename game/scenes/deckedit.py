"""Editor de deck: cada um dos 3 decks tem um TIPO (Fogo, Gelo, Raio ou Veneno).

Na lista só aparecem as cartas da sua coleção que podem entrar nele: as do tipo do deck e as de Utilidades,
separadas por um título. Trocar o tipo tira do deck as cartas do tipo antigo (a cena pergunta antes).

Controles: cima/baixo passam pelas fileiras (DECK 1/2/3 -> tipo do deck -> lista);
na lista, > (ou A) põe a carta e < tira.
"""
from collections import Counter

import pygame

from game.data.cards import ARCHETYPE_NAMES, CARD_LIST, CARDS, DECK_MAX, DECK_MIN, ELEMENTS, UTILITY
from game.data.character import DECK_SLOTS, DeckError
from game.data.legends import LEGENDS, legends_for
from game.engine import sfx
from game.engine.config import action_label
from game.engine.settings import CANCEL_KEYS, CONFIRM_KEYS, DOWN_KEYS, GAME_H, GAME_W, LEFT_KEYS, RIGHT_KEYS, UP_KEYS
from game.engine.ui import Prompt, draw_box, draw_text, vertical_gradient, wrap
from game.graphics import pixelart as art
from game.graphics import sprites
from game.scenes.base import Scene
from game.scenes.common import (
    ROW_H,
    SUB_INFO_RECT,
    SUB_LIST_RECT,
    SUB_LIST_ROWS,
    TYPE_ICONS,
    ScrollList,
    draw_card_info,
    draw_row,
    draw_scrollbar,
    draw_tabs,
    draw_type_tabs,
)

LEFT, RIGHT, UP, DOWN = LEFT_KEYS, RIGHT_KEYS, UP_KEYS, DOWN_KEYS
FOCUS = ["slots", "element", "list"]


class DeckEditScene(Scene):
    def __init__(self, game, back, slot=None):
        """back: função que devolve a cena para onde voltar."""
        super().__init__(game)
        self.ch = game.character
        self.back = back
        self.slot = self.ch.active_deck if slot is None else slot
        self.list = ScrollList(SUB_LIST_ROWS)
        self.focus = "list"
        self.element_cursor = ELEMENTS.index(self.ch.deck_element(self.slot))
        self.prompt = Prompt()
        self.toast = None
        self.toast_t = 0.0
        self.bg = vertical_gradient((GAME_W, GAME_H), (56, 88, 152), (120, 168, 216))
        self.list.index = self.first_card()

    def on_enter(self):
        sfx.music("lobby")

    # ------------------------------------------------------------ dados
    @property
    def deck(self):
        return self.ch.decks[self.slot]

    @property
    def element(self):
        return self.ch.deck_element(self.slot)

    @property
    def rows(self):
        """Linhas da lista: um título por tipo ("fogo"...) e, embaixo, os ids das cartas que você tem."""
        have = set(self.ch.collection)
        rows = []
        for kind in (self.element, UTILITY):
            rows.append(("title", kind))
            rows += [c.id for c in CARD_LIST if c.archetype == kind and c.id in have]
        return rows

    def first_card(self):
        return next((i for i, row in enumerate(self.rows) if isinstance(row, str)), 0)

    @property
    def current(self):
        """Id da carta no cursor (None se a lista estiver vazia)."""
        rows = self.rows
        row = rows[self.list.index] if self.list.index < len(rows) else None
        return row if isinstance(row, str) else None

    def say(self, text, ok=True):
        self.toast = text
        self.toast_t = 1.8
        sfx.play("confirm" if ok else "error")

    # ------------------------------------------------------------ input
    def handle(self, event):
        if self.prompt.handle(event):
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key in CANCEL_KEYS:
            self.leave()
        elif key in UP or key in DOWN:
            self.move(-1 if key in UP else 1)
        elif self.focus == "slots":
            self.handle_slots(key)
        elif self.focus == "element":
            self.handle_element(key)
        elif self.current:
            if key in RIGHT or key in CONFIRM_KEYS:
                self.add(self.current)
            elif key in LEFT:
                self.remove(self.current)

    def move(self, step):
        """Cima/baixo: anda pela lista pulando os títulos; passando do topo, sobe para as fileiras."""
        sfx.play("cursor")
        rows = self.rows
        if self.focus == "list":
            i = self.list.index + step
            while 0 <= i < len(rows) and not isinstance(rows[i], str):
                i += step
            if 0 <= i < len(rows):
                self.list.index = i
                self.list.clamp(len(rows))
                if self.list.index == self.first_card():
                    self.list.top = 0             # mostra o título de cima também
            elif step < 0:
                self.focus = "element"
            return
        self.focus = FOCUS[max(0, min(len(FOCUS) - 1, FOCUS.index(self.focus) + step))]
        if self.focus == "list":
            self.list.index = self.first_card()
            self.list.top = 0
        self.element_cursor = ELEMENTS.index(self.element)

    def handle_slots(self, key):
        if key in LEFT or key in RIGHT:
            self.slot = (self.slot + (1 if key in RIGHT else -1)) % DECK_SLOTS
            self.element_cursor = ELEMENTS.index(self.element)
            self.list.index, self.list.top = self.first_card(), 0
            sfx.play("cursor")
        elif key in CONFIRM_KEYS:
            self.activate()

    def handle_element(self, key):
        if key in LEFT or key in RIGHT:
            self.element_cursor = (self.element_cursor + (1 if key in RIGHT else -1)) % len(ELEMENTS)
            sfx.play("cursor")
        elif key in CONFIRM_KEYS:
            self.choose_element(ELEMENTS[self.element_cursor])

    def choose_element(self, element):
        """Troca o tipo do deck. Se isso tirar cartas do deck, pergunta antes."""
        if element == self.element:
            self.focus = "list"
            self.list.index, self.list.top = self.first_card(), 0
            return
        old = ARCHETYPE_NAMES[self.element]
        leaving = sum(1 for c in self.deck if CARDS[c].archetype == self.element)

        def apply(yes=True):
            if not yes:
                self.element_cursor = ELEMENTS.index(self.element)
                return
            self.ch.set_deck_element(self.slot, element)
            self.list.index, self.list.top = self.first_card(), 0
            options = legends_for(element)
            if len(options) > 1:          # mais de um legend do mesmo tipo: o jogador escolhe
                self.prompt.choose("Qual legend vai liderar o deck?", [lg.name.upper() for lg in options],
                                   lambda i: self.ch.set_deck_legend(self.slot, options[i].id) if i >= 0 else None)
                return
            self.say(f"DECK {self.slot + 1} agora é de {ARCHETYPE_NAMES[element]}: "
                     f"{LEGENDS[self.ch.deck_legend(self.slot)].name.upper()} lidera!")
        if leaving:
            self.prompt.ask(f"Mudar o DECK {self.slot + 1} para {ARCHETYPE_NAMES[element].upper()}? "
                            f"As {leaving} cartas de {old} saem do deck.", apply)
        else:
            apply()

    def add(self, cid):
        try:
            self.ch.add_to_deck(self.slot, cid)
        except DeckError as err:
            self.say(str(err), ok=False)
        else:
            sfx.play("card")

    def remove(self, cid):
        try:
            self.ch.remove_from_deck(self.slot, cid)
        except DeckError:
            sfx.play("error")
        else:
            sfx.play("cancel")

    def activate(self):
        try:
            self.ch.set_active_deck(self.slot)
        except DeckError as err:
            self.say(str(err), ok=False)
        else:
            self.say(f"DECK {self.slot + 1} agora é o seu deck de batalha!")

    def leave(self):
        if not self.ch.deck_valid(self.ch.active_deck):
            self.slot = self.ch.active_deck
            self.focus = "slots"
            self.say(f"O deck de batalha precisa de pelo menos {DECK_MIN} cartas!", ok=False)
            return
        sfx.play("cancel")
        self.ch.save()
        self.game.transition_to(self.back)

    def update(self, dt):
        self.toast_t = max(0.0, self.toast_t - dt)
        self.prompt.update(dt)
        self.list.clamp(len(self.rows))

    # ------------------------------------------------------------ desenho
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        draw_box(surf, (4, 4, GAME_W - 8, 24))
        draw_text(surf, "MONTAR DECK", (14, 9))
        if self.focus == "element":
            hint = f"{action_label('a')}: escolher o tipo"
        else:
            hint = f"< tira   > põe   {action_label('b')} sai"
        draw_text(surf, hint, (GAME_W // 2 + 20, 11), size=12, align="center")
        n = len(self.deck)
        count_color = (40, 144, 64) if DECK_MIN <= n <= DECK_MAX else (208, 64, 56)
        draw_text(surf, f"{n}/{DECK_MAX}", (GAME_W - 14, 9), color=count_color, align="right")
        labels = [f"DECK {i + 1}" + ("  *" if i == self.ch.active_deck else "") for i in range(DECK_SLOTS)]
        draw_tabs(surf, labels, self.slot, focused=self.focus == "slots")
        draw_type_tabs(surf, ELEMENTS, self.element_cursor, focused=self.focus == "element", marked=self.element)
        self.draw_list(surf)
        if self.focus == "list" and self.current:
            cid = self.current
            counts = f"No deck {self.deck.count(cid)}  /  Tem {self.ch.owned(cid)}"
            draw_card_info(surf, self.ch.card(cid), rect=SUB_INFO_RECT, extra=counts)
        else:
            self.draw_summary(surf)
        if self.toast_t > 0:
            rect = pygame.Rect(10, GAME_H - 34, GAME_W - 20, 26)
            draw_box(surf, rect)
            draw_text(surf, self.toast, (rect.centerx, rect.y + 6), size=12, align="center")
        self.prompt.draw(surf)

    def draw_list(self, surf):
        box = SUB_LIST_RECT
        draw_box(surf, box)
        rows = self.rows
        in_deck = Counter(self.deck)
        for line, i in enumerate(self.list.visible(len(rows))):
            row = rows[i]
            rect = pygame.Rect(box.x + 6, box.y + 8 + line * ROW_H, box.w - 16, ROW_H)
            if isinstance(row, tuple):
                self.draw_title(surf, rect, row[1], i + 1 >= len(rows) or isinstance(rows[i + 1], tuple))
                continue
            card = self.ch.card(row)
            draw_row(surf, rect, i == self.list.index, active=self.focus == "list")
            surf.blit(art.icon(card.icon), (rect.x + 12, rect.y + 2))
            draw_text(surf, card.name if len(card.name) <= 12 else card.short, (rect.x + 28, rect.y + 2),
                      color=art.RARITY_COLORS[card.rarity] if card.rarity != "comum" else (72, 72, 80))
            art.draw_level_stars(surf, card.level, rect.x + 146, rect.y + 4)
            used, have = in_deck[row], self.ch.owned(row)
            color = (40, 144, 64) if used else (136, 136, 144)
            draw_text(surf, f"{used}/{have}", (rect.right - 4, rect.y + 3), size=12, color=color, align="right")
        draw_scrollbar(surf, self.list, len(rows), box)

    def draw_title(self, surf, rect, kind, empty):
        """Título de seção ('VENENO', 'UTILIDADES') na cor do tipo; sem cartas, avisa onde conseguir."""
        main = art.ARCHETYPE_COLORS[kind][0]
        pygame.draw.rect(surf, main, rect.inflate(0, -2), border_radius=3)
        surf.blit(art.icon(TYPE_ICONS[kind]), (rect.x + 4, rect.y + 2))
        text = ARCHETYPE_NAMES[kind].upper() + ("  (nenhuma: compre na loja)" if empty else "")
        draw_text(surf, text, (rect.x + 20, rect.y + 3), size=12, color=(255, 255, 255), shadow=(40, 40, 48))

    def draw_summary(self, surf):
        rect = SUB_INFO_RECT
        draw_box(surf, rect)
        active = self.slot == self.ch.active_deck
        draw_text(surf, f"DECK {self.slot + 1}", (rect.x + 10, rect.y + 8))
        draw_text(surf, "DE BATALHA" if active else "RESERVA", (rect.right - 10, rect.y + 10), size=12,
                  color=(40, 144, 64) if active else (136, 136, 144), align="right")
        hovering = self.focus == "element"
        element = ELEMENTS[self.element_cursor] if hovering else self.element
        # olhando outro tipo na fileira: mostra o legend que viria com ele
        legend = LEGENDS[self.ch.deck_legend(self.slot)] if element == self.element else legends_for(element)[0]
        self.draw_legend(surf, legend, rect.x + 8, rect.y + 26, rect.w - 16)
        deck = self.deck
        counts = Counter(CARDS[c].archetype for c in deck)
        cost = sum(CARDS[c].cost for c in deck) / len(deck) if deck else 0
        rows = [(ARCHETYPE_NAMES[self.element], str(counts[self.element])),
                ("Utilidades", str(counts[UTILITY])), ("Custo médio", f"{cost:.1f}")]
        for i, (label, value) in enumerate(rows):
            y = rect.y + 128 + i * 12
            draw_text(surf, label, (rect.x + 10, y), size=12)
            draw_text(surf, value, (rect.right - 10, y), size=12, align="right")
        if hovering:
            hint = (f"{action_label('a')}: o DECK {self.slot + 1} passa a ser de "
                    f"{ARCHETYPE_NAMES[element]}, liderado por {legend.name.upper()}.")
        elif len(deck) < DECK_MIN:
            hint = f"Faltam {DECK_MIN - len(deck)} cartas para este deck poder batalhar."
        elif active:
            hint = "Este é o deck usado nas batalhas."
        else:
            hint = f"{action_label('a')} (em DECK {self.slot + 1}): usar este deck nas batalhas."
        for i, line in enumerate(wrap(hint, rect.w - 16, 12)[:2]):
            draw_text(surf, line, (rect.x + 8, rect.y + 168 + i * 10), size=12, shadow=None)

    def draw_legend(self, surf, legend, x, y, width):
        """Ficha do legend que lidera o deck: retrato, nome, classe, atributos e habilidade."""
        main = art.ARCHETYPE_COLORS[legend.archetype][0]
        portrait = sprites.legend_image(legend.id, "portrait", 44)
        pygame.draw.rect(surf, main, (x - 1, y - 1, portrait.get_width() + 2, 46))
        surf.blit(portrait, (x, y))
        tx = x + portrait.get_width() + 6
        draw_text(surf, "LEGEND", (tx, y), size=12, color=main)
        draw_text(surf, legend.name.upper(), (tx, y + 10))
        draw_text(surf, f"{legend.cls} de {ARCHETYPE_NAMES[legend.archetype]}", (tx, y + 24), size=12)
        stats = f"PV {legend.hp}  FOR {legend.strength}  PROT {legend.protection}  EN {legend.energy}"
        draw_text(surf, stats, (x, y + 50), size=12, color=(72, 72, 80))
        for i, line in enumerate(wrap(legend.short, width, 12)[:3]):
            draw_text(surf, line, (x, y + 64 + i * 10), size=12, shadow=None, color=(96, 96, 104))

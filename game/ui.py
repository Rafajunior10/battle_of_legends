"""Interface estilo GBA: fontes, caixas de diálogo e menus com cursor."""
import pygame

from . import pixelfont, sfx
from .settings import (
    BOX_BORDER,
    BOX_FILL,
    BOX_INNER,
    CANCEL_KEYS,
    CONFIRM_KEYS,
    DOWN_KEYS,
    GAME_H,
    GAME_W,
    TEXT,
    TEXT_SHADOW,
    UP_KEYS,
)


def text_width(text, size=16):
    return pixelfont.width(text, size)


def _aligned(x, width, align):
    if align == "center":
        return x - width // 2
    if align == "right":
        return x - width
    return x


_rendered = {}
RENDER_CACHE_LIMIT = 4000   # textos guardados; ao passar disso o cache é esvaziado


def render_text(text, size, color):
    """Texto já desenhado, guardado em cache: a maior parte dos textos se repete a cada quadro."""
    key = (text, size, tuple(color))
    img = _rendered.get(key)
    if img is None:
        if len(_rendered) > RENDER_CACHE_LIMIT:
            _rendered.clear()
        img = _rendered[key] = pixelfont.render(text, size, color)
    return img


def draw_text(surf, text, pos, color=TEXT, size=16, shadow=TEXT_SHADOW, align="left"):
    """Texto na fonte pixel (game/pixelfont.py) com a sombra clássica dos jogos de GBA."""
    img = render_text(text, size, color)
    x, y = _aligned(pos[0], img.get_width(), align), pos[1]
    if shadow:
        surf.blit(render_text(text, size, shadow), (x + 1, y + 1))
    surf.blit(img, (x, y))
    return img.get_width()


def draw_outlined(surf, text, pos, color, outline=(40, 40, 48), size=16, align="left"):
    img = render_text(text, size, color)
    out = render_text(text, size, outline)
    x, y = _aligned(pos[0], img.get_width(), align), pos[1]
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        surf.blit(out, (x + ox, y + oy))
    surf.blit(img, (x, y))


def wrap(text, width, size=16):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            test = word if not line else f"{line} {word}"
            if text_width(test, size) <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


_overlays = {}


def overlay(color, alpha, size=(GAME_W, GAME_H)):
    """Camada de cor sólida semitransparente, criada uma vez e reaproveitada (escurecer, flash...).

    O alpha é arredondado de 8 em 8 para o cache não crescer em animações contínuas.
    """
    alpha = max(0, min(255, int(alpha) // 8 * 8))
    key = (tuple(color), alpha, size)
    surf = _overlays.get(key)
    if surf is None:
        surf = pygame.Surface(size)
        surf.fill(color)
        surf.set_alpha(alpha)
        _overlays[key] = surf
    return surf


def dither_gradient(size, top, bottom, bands=8):
    """Degradê em faixas com pontilhado (xadrez) na transição, o jeitão dos jogos de 16 bits."""
    w, h = size
    surf = pygame.Surface(size)
    colors = [[round(a + (b - a) * i / max(1, bands - 1)) for a, b in zip(top, bottom, strict=True)]
              for i in range(bands)]
    band_h = h / bands
    for i, color in enumerate(colors):
        y0 = int(i * band_h)
        pygame.draw.rect(surf, color, (0, y0, w, int((i + 1) * band_h) - y0 + 1))
        if i + 1 < bands:   # linha pontilhada misturando esta faixa com a próxima
            y = int((i + 1) * band_h) - 1
            for x in range(y % 2, w, 2):
                surf.set_at((x, y), colors[i + 1])
    return surf


def vertical_gradient(size, top, bottom):
    w, h = size
    surf = pygame.Surface(size)
    for y in range(h):
        t = y / max(1, h - 1)
        color = [round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)]
        pygame.draw.line(surf, color, (0, y), (w, y))
    return surf


_boxes = {}


def _shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color)


def _render_box(size, fill):
    """Caixa 16 bits: borda dupla com brilho em cima e fundo em degradê suave."""
    rect = pygame.Rect((0, 0), size)
    box = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(box, BOX_BORDER, rect, border_radius=4)
    pygame.draw.rect(box, BOX_INNER, rect.inflate(-4, -4), border_radius=3)
    pygame.draw.line(box, _shade(BOX_INNER, 48), (rect.x + 4, rect.y + 2), (rect.right - 5, rect.y + 2))
    inner = rect.inflate(-8, -8)
    if inner.w > 0 and inner.h > 0:
        gradient = dither_gradient(inner.size, fill, _shade(fill, -20), bands=max(2, min(6, inner.h // 12)))
        fade = pygame.Surface(inner.size, pygame.SRCALPHA)
        fade.blit(gradient, (0, 0))
        corners = pygame.Surface(inner.size, pygame.SRCALPHA)   # recorta os cantos arredondados
        pygame.draw.rect(corners, (255, 255, 255, 255), corners.get_rect(), border_radius=2)
        fade.blit(corners, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        box.blit(fade, inner.topleft)
    return box.convert_alpha() if pygame.display.get_surface() else box


def draw_box(surf, rect, fill=BOX_FILL):
    """Caixa com borda dupla arredondada (estilo FireRed), guardada em cache por tamanho."""
    rect = pygame.Rect(rect)
    key = (rect.size, tuple(fill))
    box = _boxes.get(key)
    if box is None:
        box = _boxes[key] = _render_box(rect.size, fill)
    surf.blit(box, rect.topleft)


def draw_cursor(surf, x, y, color=TEXT):
    pygame.draw.polygon(surf, color, [(x, y), (x, y + 8), (x + 4, y + 4)])


def draw_more_arrow(surf, x, y, color=(224, 72, 56)):
    pygame.draw.polygon(surf, color, [(x, y), (x + 8, y), (x + 4, y + 5)])


FACE_SPACE = 54      # espaço reservado para o rosto (38 px + moldura + folga)


class DialogBox:
    """Caixa de texto com efeito de máquina de escrever e várias páginas."""

    def __init__(self, rect=(4, GAME_H - 58, GAME_W - 8, 54), size=16, line_h=16, speed=45):
        self.rect = pygame.Rect(rect)
        self.size = size
        self.line_h = line_h
        self.speed = speed
        self.active = False     # recebendo input
        self.visible = False    # sendo desenhada
        self.pages = [[""]]
        self.page = 0
        self.shown = 0.0
        self.on_done = None
        self.auto = None
        self.keep = False
        self.wait = 0.0
        self.blink = 0.0
        self.face = None        # rosto de quem fala (opcional), desenhado à esquerda

    @property
    def text_x(self):
        """Onde o texto começa: mais para a direita quando há um rosto."""
        return self.rect.x + (FACE_SPACE if self.face else 14)

    def show(self, text, on_done=None, auto=None, keep=False, face=None):
        """auto: segundos para avançar sozinho; keep: continua visível ao terminar; face: rosto de quem fala."""
        self.face = face
        texts = [text] if isinstance(text, str) else list(text)
        self.pages = []
        for t in texts:
            lines = wrap(t, self.rect.right - self.text_x - 14, self.size)
            for i in range(0, len(lines), 2):
                self.pages.append(lines[i:i + 2])
        self.page = 0
        self.shown = 0.0
        self.wait = 0.0
        self.on_done = on_done
        self.auto = auto
        self.keep = keep
        self.active = self.visible = True

    def hide(self):
        self.visible = False

    def _page_len(self):
        return sum(len(line) for line in self.pages[self.page])

    @property
    def page_done(self):
        return self.shown >= self._page_len()

    def update(self, dt):
        self.blink += dt
        if not self.active:
            return
        if not self.page_done:
            self.shown = min(self._page_len(), self.shown + dt * self.speed)
        elif self.auto is not None:
            self.wait += dt
            if self.wait >= self.auto:
                self._next()

    def handle(self, event):
        """Consome os eventos de teclado enquanto estiver ativa."""
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN and (event.key in CONFIRM_KEYS or event.key in CANCEL_KEYS):
            if not self.page_done:
                self.shown = self._page_len()
            else:
                sfx.play("cursor")
                self._next()
        return True

    def _next(self):
        self.page += 1
        self.shown = 0.0
        self.wait = 0.0
        if self.page >= len(self.pages):
            self.page = len(self.pages) - 1
            self.shown = self._page_len()
            self.active = False
            self.visible = self.keep
            callback, self.on_done = self.on_done, None
            if callback:
                callback()

    def draw(self, surf):
        if not self.visible:
            return
        draw_box(surf, self.rect)
        if self.face:
            frame = pygame.Rect(self.rect.x + 7, self.rect.centery - 20, 40, 40)
            pygame.draw.rect(surf, BOX_BORDER, frame, border_radius=3)
            surf.blit(self.face, (frame.x + 1, frame.y + 1))
        remaining = int(self.shown)
        top = self.rect.y + (self.rect.h - 2 * self.line_h) // 2
        for i, line in enumerate(self.pages[self.page]):
            draw_text(surf, line[:max(0, remaining)], (self.text_x, top + i * self.line_h), size=self.size)
            remaining -= len(line)
        if self.active and self.page_done and self.auto is None and int(self.blink * 3) % 2 == 0:
            draw_more_arrow(surf, self.rect.right - 20, self.rect.bottom - 13)


class Prompt:
    """Caixa de diálogo + pergunta de múltipla escolha, usada por qualquer tela que conversa com o jogador."""

    def __init__(self, dialog=None):
        self.dialog = dialog or DialogBox()
        self.menu = None
        self._callback = None

    @property
    def choosing(self):
        return self.menu is not None

    @property
    def busy(self):
        """True enquanto houver texto ou pergunta esperando o jogador."""
        return self.dialog.active or self.choosing

    @property
    def visible(self):
        return self.dialog.visible or self.choosing

    def say(self, text, then=None, face=None):
        self.dialog.show(text, on_done=then, face=face)

    def choose(self, question, options, callback, face=None):
        """Mostra a pergunta e depois as opções. callback(índice escolhido, -1 = cancelou)."""
        def open_menu():
            width = max(60, max(text_width(o) for o in options) + 30)
            height = len(options) * 16 + 14
            self.menu = Menu(options, GAME_W - 4 - width, self.dialog.rect.y - height - 2, width=width)
            self._callback = callback
        self.dialog.show(question, on_done=open_menu, keep=True, face=face)

    def ask(self, question, callback, face=None):
        """Pergunta de SIM/NÃO. callback(True/False)."""
        self.choose(question, ["SIM", "NÃO"], lambda index: callback(index == 0), face=face)

    def handle(self, event):
        """Consome o evento se o diálogo ou a pergunta estiverem abertos."""
        if self.dialog.active:
            self.dialog.handle(event)
            return True
        if not self.menu:
            return False
        result = self.menu.handle(event)
        if result is not None:
            callback = self._callback
            self.menu = self._callback = None
            self.dialog.hide()
            callback(result)
        return True

    def update(self, dt):
        self.dialog.update(dt)

    def draw(self, surf):
        self.dialog.draw(surf)
        if self.menu:
            self.menu.draw(surf)


class Menu:
    """Lista de opções com cursor ▶. handle() devolve o índice escolhido, -1 ao cancelar."""

    def __init__(self, options, x, y, width=None, size=16, line_h=16):
        self.options = list(options)
        self.index = 0
        self.size = size
        self.line_h = line_h
        w = width or max(text_width(o, size) for o in self.options) + 30
        self.rect = pygame.Rect(x, y, w, len(self.options) * line_h + 14)

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in UP_KEYS:
            self.index = (self.index - 1) % len(self.options)
            sfx.play("cursor")
        elif event.key in DOWN_KEYS:
            self.index = (self.index + 1) % len(self.options)
            sfx.play("cursor")
        elif event.key in CONFIRM_KEYS:
            sfx.play("confirm")
            return self.index
        elif event.key in CANCEL_KEYS:
            sfx.play("cancel")
            return -1
        return None

    def draw(self, surf):
        draw_box(surf, self.rect)
        for i, option in enumerate(self.options):
            y = self.rect.y + 8 + i * self.line_h
            draw_text(surf, option, (self.rect.x + 18, y), size=self.size)
            if i == self.index:
                draw_cursor(surf, self.rect.x + 9, y + 1)

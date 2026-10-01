"""Fonte pixel: todo texto do jogo tem letra desenhada (nada de '?' trocando acentos)."""
import glob
import re

import pygame
import pytest

from game.engine import config
from game.graphics import pixelfont


def textos_do_jogo():
    chars = set()
    for path in glob.glob("game/**/*.py", recursive=True):
        with open(path, encoding="utf-8") as f:
            for text in re.findall(r'"([^"\n]*)"', f.read()):
                chars |= set(text)
    return sorted(c for c in chars if c.isprintable() and c not in r"\`{}|@&$^~")


@pytest.mark.parametrize("ch", textos_do_jogo())
def test_todo_caractere_usado_tem_letra(ch):
    if ch in {" ", "?"}:
        return
    assert pixelfont.glyph(pixelfont.NORMAL, ch) != pixelfont.glyph(pixelfont.NORMAL, "?"), ch


def test_acentos_ficam_acima_da_letra():
    a, a_acento = pixelfont.glyph(pixelfont.NORMAL, "a"), pixelfont.glyph(pixelfont.NORMAL, "á")
    assert "#" not in "".join(a[:2]) and "#" in "".join(a_acento[:3])
    assert "#" in "".join(pixelfont.glyph(pixelfont.NORMAL, "ç")[-2:])     # cedilha embaixo


def test_largura_bate_com_o_desenho():
    for size in (10, 12, 16, 24, 48):
        img = pixelfont.render("Golpe Perfurante: 6 de dano!", size, (0, 0, 0))
        assert img.get_width() == pixelfont.width("Golpe Perfurante: 6 de dano!", size)
        assert img.get_height() == pixelfont.height(size)


def test_fonte_pequena_cabe_nos_nomes_das_cartas():
    from game.data.cards import CARD_LIST
    assert all(pixelfont.width(c.short, 10) <= 46 for c in CARD_LIST)


def test_config_antigo_nao_duplica_tecla_da_ficha(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(f'{{"bindings": {{"a": [{pygame.K_e}, {pygame.K_z}]}}}}', encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", str(path))
    config.load()
    assert pygame.K_e in config.bindings["a"]
    assert pygame.K_e not in config.bindings["profile"]

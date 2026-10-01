"""Fixtures dos testes. Nada aqui abre janela: as regras ficam em game/core e não dependem de tela."""
import os
import random

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import character as character_module
from game import config
from game.cards import Deck
from game.character import Character
from game.core.combat import Combatant


@pytest.fixture
def rng():
    return random.Random(1234)


@pytest.fixture
def save_path(tmp_path, monkeypatch):
    """Save isolado: os testes nunca tocam no save.json de verdade."""
    path = tmp_path / "save.json"
    monkeypatch.setattr(character_module, "SAVE_PATH", str(path))
    return path


@pytest.fixture
def hero(save_path):
    return Character(name="Teste")


@pytest.fixture
def make_fighter(rng):
    def make(deck=("murrao",) * 10, hp=30, name="A", hand=(), energy=3, **kwargs):
        from game.cards import CARDS
        c = Combatant(name, 1, hp, Deck(list(deck), rng), energy=energy, **kwargs)
        c.hand = [CARDS[i] for i in hand]
        return c
    return make


@pytest.fixture(autouse=True)
def default_bindings(tmp_path, monkeypatch):
    """Cada teste começa com as teclas padrão e um config.json descartável."""
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "config.json"))
    config.reset_bindings()
    yield
    config.reset_bindings()

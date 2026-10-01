import random

import pytest

from game.cards import CARDS, MAX_COPIES
from game.core.tournament import ROUNDS, XP_MULTIPLIER, Tournament
from game.opponents import TRAINERS, level_factor, random_wild, rewards, trainer_spec


def test_treinadores_validos():
    for tid in TRAINERS:
        spec = trainer_spec(tid)
        assert all(c in CARDS for c in spec["deck"])
        assert spec["ai"] in ("easy", "normal", "hard")
        assert spec.get("requires") in (None, *TRAINERS)


def test_balanceamento_por_nivel():
    assert level_factor(5, 3) > level_factor(5, 5) > level_factor(5, 7)


def test_primeira_vitoria_vale_o_dobro():
    spec = trainer_spec("lia")
    first, _ = rewards(spec, 5, True)
    again, _ = rewards(spec, 5, False)
    assert first == 2 * again


def test_xp_do_torneio_e_dobrado():
    spec = trainer_spec("lia")
    _, xp = rewards(spec, 5, False)
    _, doubled = rewards(dict(spec, xp_mult=XP_MULTIPLIER), 5, False)
    assert doubled == xp * XP_MULTIPLIER


def test_gosma_acompanha_nivel_do_jogador():
    rng = random.Random(1)
    levels = {random_wild(6, rng)["level"] for _ in range(100)}
    assert levels == {5, 6, 7}


def test_torneio_campeao():
    t = Tournament(4, random.Random(1))
    levels = [o["level"] for o in t.opponents]
    assert levels == [4, 5, 6]
    assert t.opponents[-1]["ai"] == "hard"
    for _ in range(ROUNDS):
        assert t.current()["xp_mult"] == XP_MULTIPLIER
        t.record(True)
    assert t.champion
    assert t.over
    with pytest.raises(RuntimeError):
        t.current()


def test_torneio_eliminacao():
    t = Tournament(1, random.Random(2))
    t.record(True)
    t.record(False)
    assert t.eliminated
    assert not t.champion
    assert t.round == 1


def test_decks_do_torneio_respeitam_limite_de_copias():
    for seed in range(20):
        for opp in Tournament(3, random.Random(seed)).opponents:
            assert all(opp["deck"].count(c) <= MAX_COPIES for c in opp["deck"])

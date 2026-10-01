import pygame

from game import config
from game.config import CONFIRM_KEYS, KEY_DIRS, RUN_KEYS, UP_KEYS


def test_trocar_tecla_vale_na_hora():
    assert config.bind("a", 0, pygame.K_j) is None
    assert pygame.K_j in CONFIRM_KEYS
    assert pygame.K_z not in CONFIRM_KEYS


def test_tecla_sai_da_acao_antiga():
    assert config.bind("run", 1, pygame.K_w) is None
    assert pygame.K_w not in UP_KEYS
    assert pygame.K_w in RUN_KEYS
    assert all(k != pygame.K_w for k, _ in KEY_DIRS)


def test_nao_deixa_acao_sem_tecla():
    config.bindings["up"] = [pygame.K_UP, 0]        # CIMA só com SETA CIMA
    assert config.bind("a", 0, pygame.K_UP) is not None
    assert pygame.K_UP in UP_KEYS


def test_teclas_reservadas():
    for key in config.RESERVED:
        assert config.bind("a", 0, key) is not None


def test_enter_e_esc_sempre_funcionam():
    config.bind("a", 0, pygame.K_j)
    config.bind("a", 1, pygame.K_k)
    assert pygame.K_RETURN in CONFIRM_KEYS
    assert pygame.K_ESCAPE in config.CANCEL_KEYS


def test_salvar_e_carregar():
    config.bind("b", 0, pygame.K_q)
    config.display["scale"] = 4
    config.save()
    config.reset_bindings()
    config.display["scale"] = 3
    config.load()
    assert config.bindings["b"][0] == pygame.K_q
    assert config.display["scale"] == 4

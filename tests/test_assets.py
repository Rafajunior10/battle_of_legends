"""Leitor do pacote de arte: funciona com pasta ou zip, e não quebra quando o pacote não existe."""
import zipfile

import pygame
import pytest

from game import assets

SHEET_PATH = "Ninja Adventure - Asset Pack/Actor/Character/Hero/SpriteSheet.png"


def fake_sheet():
    """Folha 64x112 em que cada quadro tem a cor (coluna, linha) para dar para conferir o recorte."""
    sheet = pygame.Surface((64, 112), pygame.SRCALPHA)
    for col in range(4):
        for row in range(7):
            sheet.fill((col * 60, row * 30, 10, 255), (col * 16, row * 16, 16, 16))
    return sheet


@pytest.fixture
def assets_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "ASSETS_DIR", str(tmp_path))
    assets.reset()
    yield tmp_path
    assets.reset()


def test_sem_pacote_devolve_none(assets_dir):
    assert not assets.pack().available
    assert assets.character_frames("Hero") is None


def test_le_pacote_extraido(assets_dir):
    path = assets_dir / "ninja_adventure" / SHEET_PATH
    path.parent.mkdir(parents=True)
    pygame.image.save(fake_sheet(), str(path))
    frames = assets.character_frames("hero")
    assert assets.character_names() == ["hero"]
    assert frames[("down", 0)].get_size() == (16, 16)
    assert frames[("up", 0)].get_at((0, 0))[:3] == (60, 0, 10)       # coluna 1 = cima
    assert frames[("right", 2)].get_at((0, 0))[:3] == (180, 90, 10)  # passo B = linha 3


def test_le_direto_do_zip(assets_dir, tmp_path_factory):
    png = tmp_path_factory.mktemp("png") / "sheet.png"
    pygame.image.save(fake_sheet(), str(png))
    with zipfile.ZipFile(assets_dir / "Ninja Adventure - Asset Pack.zip", "w") as zf:
        zf.write(png, SHEET_PATH)
    frames = assets.character_frames("Hero")
    assert frames is not None
    assert frames[("left", 1)].get_at((0, 0))[:3] == (120, 30, 10)


def test_folha_curta_e_monstro_com_spritesheet(assets_dir):
    """Regressão: OldWoman tem folha de 2 linhas; muitos monstros usam SpriteSheet.png."""
    base = assets_dir / "ninja_adventure" / "Actor"
    short = base / "Character" / "OldWoman" / "SpriteSheet.png"
    short.parent.mkdir(parents=True)
    pygame.image.save(fake_sheet().subsurface((0, 0, 64, 32)), str(short))
    bat = base / "Monster" / "BlueBat" / "SpriteSheet.png"
    bat.parent.mkdir(parents=True)
    pygame.image.save(fake_sheet().subsurface((0, 0, 64, 64)), str(bat))
    assert assets.character_frames("OldWoman")[("down", 2)].get_size() == (16, 16)
    assert assets.monster_frames("BlueBat") is not None


def test_todos_os_monstros_usados_existem_no_pacote_real():
    """Se o pacote estiver instalado, todo monstro usado no jogo precisa existir nele."""
    assets.reset()
    if not assets.pack().available:
        pytest.skip("pacote de arte não instalado")
    from game.opponents import FOREST_WILD_TYPES, WILD_TYPES
    for _, monster, _, _ in WILD_TYPES + FOREST_WILD_TYPES:
        assert assets.monster_frames(monster) is not None, monster

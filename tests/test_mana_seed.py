"""Bonecos do Mana Seed: toda escolha da criação vira um arquivo que existe e um boneco animado."""
import os

import pygame
import pytest

from game.data.looks import HAIR_COLORS, HAIR_STYLES, HATS, SKIN_TONES, Look
from game.graphics import mana_seed, sprites

pytestmark = pytest.mark.skipif(not mana_seed.available(), reason="sem a pasta assets/mana_seed")


def todas_as_escolhas():
    for hat, colors in HATS.items():
        for color in colors or [""]:
            yield Look(hat=hat, hat_color=color)
    for hair in HAIR_STYLES:
        for color in HAIR_COLORS:
            yield Look(hair=hair, hair_color=color)
    for skin in range(len(SKIN_TONES)):
        yield Look(skin=skin)


def test_toda_escolha_aponta_para_um_arquivo_que_existe():
    for look in todas_as_escolhas():
        for path in mana_seed.files(look).values():
            assert os.path.isfile(path), path


def test_quadros_parado_passos_e_caminhada():
    frames = mana_seed.character_frames(Look())
    for direction in ("down", "up", "left", "right"):
        assert frames[(direction, 0)].get_size() == mana_seed.CROP.size
        assert len(frames[(direction, "walk")]) == mana_seed.WALK_FRAMES
    for direction in ("down", "up", "left", "right"):  # os pés ficam no fim do recorte (o ator alinha por baixo)
        assert frames[(direction, 0)].get_bounding_rect().bottom >= mana_seed.CROP.h - 1
    assert max(f.get_bounding_rect().bottom for f in frames[("down", "walk")]) == mana_seed.CROP.h


def test_capuz_tira_o_cabelo_e_careca_nao_tem_cabelo():
    assert "hair" not in mana_seed.files(Look(hat="capuz", hat_color="verde"))
    assert "hair" not in mana_seed.files(Look(hair="careca"))


def test_sprites_usa_o_mana_seed_e_o_rosto_tem_38():
    assert sprites.character_frames(Look())[("down", 0)].get_size() == mana_seed.CROP.size
    assert sprites.face(Look()).get_size() == (38, 38)


def _pixels(surf):
    return pygame.image.tobytes(surf, "RGBA")


def _opacos(surf):
    w, h = surf.get_size()
    return sum(1 for x in range(w) for y in range(h) if surf.get_at((x, y)).a)


def test_regata_mostra_os_ombros_e_bermuda_mostra_a_canela():
    camisa = mana_seed.character_frames(Look(top="camisa"))[("down", 0)]
    regata = mana_seed.character_frames(Look(top="regata"))[("down", 0)]
    calca = mana_seed.character_frames(Look(bottom="calça"))[("down", 0)]
    bermuda = mana_seed.character_frames(Look(bottom="bermuda"))[("down", 0)]
    assert _pixels(camisa) != _pixels(regata)
    assert _pixels(calca) != _pixels(bermuda)


def test_saia_e_vestido_acrescentam_pano():
    calca = mana_seed.character_frames(Look("Feminino", bottom="calça"))[("down", 0)]
    saia = mana_seed.character_frames(Look("Feminino", bottom="saia"))[("down", 0)]
    vestido = mana_seed.character_frames(Look("Feminino", bottom="vestido"))[("down", 0)]
    assert _opacos(saia) > _opacos(calca)
    assert _opacos(vestido) > _opacos(saia)


def test_cabelo_longo_desce_mais_que_o_chanel_e_raspado_tem_menos_volume():
    chanel = mana_seed.character_frames(Look(hair="chanel"))[("up", 0)]
    longo = mana_seed.character_frames(Look(hair="longo"))[("up", 0)]
    curto = mana_seed.character_frames(Look(hair="curto"))[("down", 0)]
    raspado = mana_seed.character_frames(Look(hair="raspado"))[("down", 0)]
    assert _pixels(chanel) != _pixels(longo)
    assert _opacos(raspado) < _opacos(curto)


@pytest.mark.parametrize("gender", ["Masculino", "Feminino"])
def test_toda_combinacao_de_pecas_desenha(gender):
    from game.data.looks import BOTTOMS, TOPS
    for top in TOPS[gender]:
        for bottom in BOTTOMS[gender]:
            frames = mana_seed.character_frames(Look(gender, top=top, bottom=bottom))
            assert frames[("left", "walk")][3].get_bounding_rect().height > 30

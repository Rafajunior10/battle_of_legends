"""Bonecos de papel estilo Habbo: toda aparência usada no jogo é válida e vira quadros do mesmo tamanho."""
import random

import pytest

from game.core.tournament import random_look
from game.data.character import Character
from game.data.looks import (
    BOTTOMS,
    CLOTH_COLORS,
    GENDERS,
    HAIR_COLORS,
    HAIR_STYLES,
    SHOE_COLORS,
    SKIN_TONES,
    TOPS,
    Look,
)
from game.data.opponents import TRAINERS
from game.data.world import MAPS
from game.graphics import people


def all_looks():
    looks = [t["look"] for t in TRAINERS.values()]
    looks += [h.look for m in MAPS.values() for h in m.helpers.values()]
    looks += [random_look(random.Random(seed)) for seed in range(20)]
    return looks


@pytest.mark.parametrize("look", all_looks(), ids=str)
def test_aparencias_validas(look):
    assert look.gender in GENDERS
    assert look.hair in HAIR_STYLES
    assert look.hair_color in HAIR_COLORS
    assert look.top in TOPS[look.gender]
    assert look.bottom in BOTTOMS[look.gender]
    assert look.shirt in CLOTH_COLORS
    assert look.legs in CLOTH_COLORS
    assert look.shoes in SHOE_COLORS
    assert 0 <= look.skin < len(SKIN_TONES)
    assert look.fitted() == look


def test_quadros_tem_o_tamanho_certo():
    frames = people.character_frames(Look("Feminino", "rabo", "ruivo", 2, top="top", bottom="vestido"))
    assert len(frames) == 12                       # 4 direções x 3 quadros
    assert all(f.get_size() == (people.W, people.H) for f in frames.values())
    assert people.face(Look()).get_size() == (38, 38)


@pytest.mark.parametrize("gender", GENDERS)
def test_toda_combinacao_de_roupa_e_penteado_desenha(gender):
    for hair in HAIR_STYLES:
        for top in TOPS[gender]:
            for bottom in BOTTOMS[gender]:
                frames = people.character_frames(Look(gender, hair, top=top, bottom=bottom))
                assert frames[("down", 0)].get_bounding_rect().height >= people.H - people.TOP_PAD


def test_moldes_tem_a_largura_certa():
    for rows in (people.FRONT, people.BACK_HEAD, people.SKIRT, people.DRESS, people.CAP):
        assert all(len(r) == people.W for r in rows)
    for style, spec in people.HAIR.items():
        assert {"rows", "cap", "nape"} <= set(spec), style
        for key in ("rows", "back_extra"):
            assert all(len(r) in (0, people.W) for r in spec.get(key, [])), (style, key)


def test_corpo_ocupa_a_altura_toda_e_pes_ficam_no_chao():
    """Os pés ficam na última linha, parado ou andando, senão o boneco "pula" ao andar."""
    assert len(people.FRONT) == people.H - people.TOP_PAD
    frames = people.character_frames(Look())
    for step in range(3):
        rect = frames[("down", step)].get_bounding_rect()
        assert rect.bottom == people.H


def test_de_costas_nao_tem_rosto():
    look = Look(hair="curto")
    back = people.character_frames(look)[("up", 0)]
    front = people.character_frames(look)[("down", 0)]
    colors = {back.get_at((x, y))[:3] for x in range(people.W) for y in range(people.H)}
    assert people.EYE_WHITE not in colors
    assert people.EYE_WHITE in {front.get_at((x, y))[:3] for x in range(people.W) for y in range(people.H)}


def test_roupa_decide_o_que_fica_de_fora():
    skin = SKIN_TONES[0][0]
    regata = people.palette(Look(top="regata", bottom="bermuda"))
    assert regata["U"] == skin and regata["N"] == skin            # ombro e canela de fora
    camisa = people.palette(Look(top="camisa", bottom="calça"))
    assert camisa["U"] != skin and camisa["N"] != skin
    top = people.palette(Look("Feminino", top="top", bottom="saia"))
    assert top["Y"] == skin                                        # barriga de fora
    longa = people.palette(Look("Feminino", top="manga longa", shirt="verde", bottom="calça"))
    assert longa["A"] == CLOTH_COLORS["verde"][0]                  # braço coberto


def test_trocar_de_genero_ajusta_as_pecas():
    look = Look("Feminino", top="regata", bottom="bermuda").fitted()
    assert look.top in TOPS["Feminino"] and look.bottom in BOTTOMS["Feminino"]


def test_save_antigo_ganha_aparencia_padrao(hero):
    hero.hair_style = "inexistente"
    hero.shirt = "neon"
    look = hero.appearance
    assert look.hair == Look().hair
    assert look.shirt == Look().shirt
    assert look.top == "camisa" and look.bottom == "calça"
    assert isinstance(Character(name="X").appearance, Look)


def test_personagem_veste_a_aparencia_escolhida():
    hero = Character(name="Ana")
    escolhida = Look("Feminino", "chanel", "rosa", 1, top="top", shirt="roxo", bottom="saia",
                     legs="preto", shoes="rosa")
    hero.wear(escolhida)
    assert hero.appearance == escolhida

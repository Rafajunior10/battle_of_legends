Game art
========

ninja_adventure/  ->  "Ninja Adventure - Asset Pack" by pixel-boy (and AAA)
                      https://pixel-boy.itch.io/ninja-adventure-asset-pack
                      License: CC0 1.0 (public domain; commercial use allowed; credit optional)
                      See ninja_adventure/LICENSE.txt

O jogo lê os personagens, monstros e rostos daqui (game/assets.py).
Sem esta pasta, o jogo usa a arte desenhada por código (game/pixelart.py).

mana_seed/        ->  "Mana Seed Character Base" (FREE demo 2.0) by Seliel the Shaper
                      https://seliel-the-shaper.itch.io/character-base
                      Licença da demo: uso comercial e não comercial permitido (veja mana_seed/this is only a demo.txt)

O jogo monta as pessoas em camadas com esta pasta (game/mana_seed.py): corpo, roupa, cabelo e chapéu.
NÃO vai para o repositório (.gitignore): baixe a demo no link acima e extraia em assets/mana_seed/.
Sem ela, as pessoas são desenhadas por código (game/people.py).

static_creatures/ ->  "Static Creatures" (Update 1.05), 75 criaturas em pixel art (64 x 64, algumas .gif)
                      Autor/licença: confirmar na página onde o pacote foi baixado (o zip não traz licença).
                      Ainda não é usado pelo jogo e NÃO vai para o repositório (.gitignore).

legends/          ->  arte dos legends (Mimo, Drogoz, Blitz, Cold), enviada pelo dono do projeto.
                      As folhas originais ficam em legends/source/; tools/build_legends.py gera front/back/
                      portrait/splash.png (recorte + fundo removido).

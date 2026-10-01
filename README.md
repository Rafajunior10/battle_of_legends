# Battle of Legends (Card Quest)

RPG de cartas em pixel art, feito em Python com **pygame-ce**. Você anda por uma vila, desafia treinadores,
monta decks por elemento e, no começo de cada duelo, **se transforma no legend do seu deck**.

## Como rodar

Precisa de Python 3.12 ou mais novo.

```bash
pip install -r requirements.txt
python main.py
```

### Modo de desenvolvimento (reinicia sozinho)

```bash
python dev.py            # abre direto no lobby com o seu save
python dev.py --titulo   # abre na tela de título
```

Sempre que um arquivo `.py` do projeto é salvo, o jogo fecha e abre de novo com as mudanças.
Se der erro, o terminal mostra o traceback e espera você corrigir. Ctrl+C encerra.

### Testes e padrão de código

```bash
pip install -r requirements-dev.txt
python -m pytest        # regras, IA, save, telas e batalhas inteiras (sem abrir janela)
python -m ruff check .  # padrão de código (regras em pyproject.toml)
```

## Jogar online (mundo compartilhado)

Vocês andam juntos pela vila e pelo bosque, se veem em tempo real (com o nome em cima da cabeça), mandam
falas rápidas e veem quando o outro está em batalha. Cada um usa o próprio save (BETS, cartas e decks).

1. Os dois instalam o **Radmin VPN** (grátis) e entram na mesma rede dele.
   Na mesma casa (mesmo Wi-Fi) não precisa disso.
2. Quem hospeda: título > **ONLINE** > **HOSPEDAR**. Aparecem os endereços deste PC
   (o do Radmin começa com `26.`). Na primeira vez, o Windows pergunta se o jogo pode usar a rede: permita.
3. O amigo: título > **ONLINE** > **ENTRAR** e digita o endereço de quem hospeda.
4. Para falar com o outro, fique de frente para ele e aperte o botão A.

Os dois precisam estar com a **mesma versão** do jogo (baixem a última do GitHub).

## Legends

Cada deck tem um **tipo** (Fogo, Gelo, Raio ou Veneno) e é liderado por um **legend** do mesmo tipo.
No começo do duelo os dois duelistas se transformam: a vida, a força, a proteção e a energia passam a
ser as do legend.

| Legend | Classe | Tipo | Vida | Força | Proteção | Energia | Habilidade |
|---|---|---|---|---|---|---|---|
| Mimo, a Salamandra Assassina | Ninja | Veneno | 80 | 7 | 4 | 4 | **Ativa**: revela as 3 cartas do topo, joga 1 de Veneno de graça e as outras vão para o fundo do baralho |
| Drogoz, o Dracomante de Fogo | Mago | Fogo | 70 | 8 | 5 | 5 | **Ativa**: descarta 3 cartas da mão e cura 15 |
| Blitz, a Fera do Relâmpago | Fera | Raio | 95 | 5 | 9 | 4 | **Passiva**: +9 de força enquanto tiver 9 ou mais de defesa + aura ganhas no turno |
| Cold, o Bruto Glacial | Lutador | Gelo | 70 | 7 | 7 | 5 | **Passiva**: atacar um congelado quebra o gelo (+5 de dano, descongela). Com o Clone de Gelo, o 1º ataque do oponente é anulado e ele ganha 1 de gelo |

- **Força**: somada ao dano de cada golpe.
- **Proteção**: fixa; tira esse tanto de cada golpe que passar pela aura e pela defesa das cartas.
- **Habilidade ativa**: botão **HABILIDADE** na batalha, uma vez por turno.

## Regras do duelo

- No começo do duelo e **no fim de cada turno** você compra até ter **5 cartas** na mão.
- **Defesa** e **aura** protegem o PV: o dano bate primeiro na aura, depois na defesa, depois na proteção
  do legend. Defesa e aura somem quando o seu próximo turno começa.
- **Marcadores**:
  - **Queimadura**: cada marcador soma +1 em todo dano de carta que o alvo recebe.
  - **Gelo**: ao juntar 4, o alvo congela e perde o próximo turno.
  - **Veneno**: o alvo perde 1 PV por marcador **em toda passagem de turno** (no fim do seu turno e no do oponente).
  - **Paralisia**: cada uma tira 1 de energia do alvo no próximo turno.
- **Deck**: de 20 a 30 cartas do **tipo do deck** mais **Utilidades**, no máximo 3 cópias de cada.

## O que tem no jogo

- **Criação de personagem** em camadas: cabelo (curto, raspado, chanel, longo, careca), 12 cores de cabelo,
  7 tons de pele, camisa/regata/manga longa/top, calça/bermuda/saia/vestido, tênis e chapéu.
- **Vila Carta** e **Bosque Sussurro**, ligados por passagens, com construções que têm placas, NPCs,
  treinadores com nível e monstros no mato alto.
- **Loja de cartas** separada por tipo (sub-abas Fogo, Gelo, Raio, Veneno e Utilidades): comprar,
  evoluir cartas até o nível 3 (com XP de batalha ou BETS) e vender cópias que sobram.
- **Editor de deck**: escolha o tipo do deck (e o legend); a lista só mostra as cartas que podem entrar.
- **Coliseu**: torneio de 3 rodadas, XP em dobro e 500 BETS para o campeão.
- **Ficha do jogador** (tecla I ou E) com o tema do elemento do deck.
- **Batalha** com transformação animada, faixa de apresentação do legend, tremor de tela, números de dano
  e efeitos de partículas. Fonte pixel própria com acentos, música chiptune e sons gerados por código.

## Controles

Todas as teclas podem ser trocadas em **OPÇÕES**. Os padrões:

| Tecla | Ação |
|---|---|
| Setas / WASD | Andar e navegar nos menus |
| Z / Espaço | Confirmar e interagir (botão A) |
| X / Apagar | Voltar (botão B) |
| Shift (segurando) | Correr |
| M / Tab, Enter / Esc | Menu do lobby (com a opção **SAIR** para voltar ao título) |
| I / E | Ficha do jogador |
| F11 | Janela ou tela cheia |
| F3 | Mostrar o FPS |

## Arte e licenças

| Pasta | O que é | Vem no repositório? |
|---|---|---|
| `assets/ninja_adventure/` | **Ninja Adventure** de pixel-boy: tiles dos mapas e monstros (CC0) | Sim |
| `assets/legends/` | Arte dos legends (do dono do projeto) e `tools/build_legends.py`, que recorta as folhas | Sim |
| `assets/mana_seed/` | **Mana Seed Character Base (demo grátis)** de Seliel the Shaper: as pessoas, em camadas | **Não**: baixe em [seliel-the-shaper.itch.io/character-base](https://seliel-the-shaper.itch.io/character-base) e extraia o conteúdo do zip em `assets/mana_seed/` |

Sem o Mana Seed o jogo funciona igual: as pessoas são desenhadas por código (`game/graphics/people.py`).
Detalhes em `assets/README.txt`.

## Estrutura

Cada pasta de `game/` responde a uma pergunta: **regras** (`core`), **dados** (`data`), **desenho**
(`graphics`), **motor** (`engine`) e **telas** (`scenes`). As regras não dependem de Pygame: as cenas só leem o
estado, chamam as regras e animam os **eventos** que voltam. Dados (cartas, legends, mapas, NPCs) ficam separados do comportamento.

```
main.py, dev.py              ponto de entrada e modo de desenvolvimento (reinicia ao salvar)
tools/build_legends.py       recorta a arte dos legends e tira o fundo
game/
  core/                      REGRAS puras, sem Pygame (testadas em tests/)
    combat.py                estado de quem duela e o turno
    effects.py, events.py    efeitos das cartas e eventos para a interface narrar
    abilities.py             transformação e habilidades dos legends
    ai.py                    IA fácil / normal / difícil (inclui as habilidades)
    economy.py, tournament.py  loja, evolução, trocas e o torneio do coliseu
    rules.py                 números da batalha (mão, energia, gelo...)
  data/                      DADOS do jogo
    cards.py                 as 27 cartas, tipos, raridades e o deck
    legends.py               os legends
    character.py             personagem, coleção, decks, legends e save
    opponents.py, world.py   treinadores, monstros, mapas, NPCs e falas
    looks.py, props.py       aparência das pessoas e catálogo de objetos do mapa
  graphics/                  DESENHO e arte
    sprites.py               ponto único para pedir pessoas, monstros, legends e rostos
    mana_seed.py, wardrobe.py  pessoas em camadas e as peças de roupa e cortes derivados
    people.py                pessoas desenhadas por código (quando não há Mana Seed)
    assets.py                lê o pacote Ninja Adventure
    tilemap.py               chão, objetos e sombras dos mapas (pacote Ninja Adventure)
    buildings.py, backgrounds.py  construções com placa e o cenário da batalha
    pixelart.py, pixelfont.py     cartas, ícones e a fonte pixel própria
  engine/                    MOTOR
    app.py, display.py       laço principal, janela, FPS
    transition.py, ui.py     transições, caixas de texto, menus
    config.py, settings.py   opções (config.json), resolução, cores e controles
    sfx.py                   música e sons gerados por código
  net/                       ONLINE: protocolo, servidor (quem hospeda) e cliente
  scenes/                    TELAS
    battle.py                batalha: fila de passos, turnos, narração e habilidades
    battle_hud.py            desenho da batalha (painéis, marcadores, mão, botões)
    battle_fx.py             animações: transformação, faixa do legend, golpes, partículas
    lobby.py, actors.py      mundo andável e personagens em grade
    online.py                tela ONLINE: hospedar ou entrar no mundo de um amigo
    shop.py, deckedit.py, create.py, profile.py, options.py, title.py, common.py
tests/                       pytest
```

## Como expandir

- **Nova carta**: um `CardDef` em `game/data/cards.py` (a planilha em `tests/test_cards.py` confere os números).
- **Novo efeito**: classe em `game/core/effects.py` + evento em `game/core/events.py` + narração em
  `BattleScene.NARRATORS` (um teste avisa se faltar).
- **Novo legend**: um `LegendDef` em `game/data/legends.py`, a folha em `assets/legends/source/<id>.jpg`, os
  recortes em `tools/build_legends.py` (`python tools/build_legends.py`) e a habilidade em
  `game/core/abilities.py`. Com mais de um legend do mesmo tipo, o editor de deck pergunta qual usar.
- **Novo treinador**: entrada em `TRAINERS` (`game/data/opponents.py`) e posição e falas em `game/data/world.py`.
- **Novo mapa**: função `build_...()` e um `MapDef` em `game/data/world.py` (os testes conferem se dá para
  chegar em tudo e se as passagens batem).

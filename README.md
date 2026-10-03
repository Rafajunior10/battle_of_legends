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
falas rápidas e veem quando o outro está em batalha.

Cada jogador tem uma **conta** (usuário e senha) com **um personagem**. As contas e os personagens ficam
num banco SQLite (`world.db`) no PC de quem hospeda; a senha é guardada só como hash (PBKDF2).

1. Pela internet, os dois instalam o **Radmin VPN** (grátis) e entram na mesma rede dele.
   Na mesma casa (mesmo Wi-Fi) não precisa disso.
2. Quem hospeda: título > **JOGAR** > **HOSPEDAR**. Aparecem os endereços deste PC
   (na mesma casa, o que começa com `192.168.`). Na primeira vez, o Windows pergunta se o jogo pode usar a
   rede: permita em "Redes privadas".
3. O amigo: título > **JOGAR** > **ENTRAR** e digita o endereço de quem hospeda.
4. Login: digite usuário e senha e vá em **ENTRAR**; na primeira vez, **CRIAR CONTA**. Conta nova pode
   importar o personagem salvo no PC (`save.json`) ou criar um novo.
5. Fique de frente para o outro jogador e aperte o botão A: **DUELAR** ou **FALAR** (falas rápidas).

### Duelo entre jogadores (PvP)

Escolha **DUELAR**: o outro recebe o convite e aceita ou recusa. Quem desafiou começa jogando. Cada um usa o
próprio deck e o próprio legend. O duelo conta vitória/derrota na ficha, mas não dá BETS nem XP. Se alguém sai
do jogo no meio do duelo, o outro vence por W.O.

Por dentro: o servidor sorteia uma "semente" e os dois PCs embaralham os baralhos com ela, então os dois veem
as mesmas cartas. Pela rede só passam as jogadas (qual carta, fim do turno, habilidade), e cada PC aplica a
jogada do outro nas mesmas regras (`game/core/duel.py` e `game/scenes/duel.py`).

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

- **Criação de personagem** em camadas: cabelo (curto, raspado, chanel, longo, cacheado, careca), 12 cores de
  cabelo, 7 tons de pele, camisa/regata/manga longa/top, calça/bermuda/shorts/saia/vestido, tênis e chapéu.
- **Vila Carta** e **Bosque Sussurro**, ligados por passagens, com construções que têm placas, NPCs,
  treinadores com nível e monstros no mato alto.
- **Loja de cartas** separada por tipo (sub-abas Fogo, Gelo, Raio, Veneno e Utilidades): comprar,
  evoluir cartas até o nível 3 (com XP de batalha ou BETS) e vender cópias que sobram.
- **Editor de deck**: escolha o tipo do deck (e o legend); a lista só mostra as cartas que podem entrar.
- **Coliseu**: torneio de 3 rodadas, XP em dobro e 500 BETS para o campeão.
- **Sua casa** (a porta com o seu nome, na vila), uma casa moderna de 2 andares. Cada jogador online tem a
  sua: ninguém aparece na casa do outro.
  - Térreo: cozinha americana com ilha e banquetas, sala de jantar, sala de TV (TV grande) com sofá e mesa de
    centro, **estante de troféus** (um troféu por título do Coliseu e as medalhas dos mestres) e lavabo.
  - Andar de cima (pela escada): suíte do casal com a cama de frente para a TV grande, **closet** (troca de
    roupa) e banheiro com box; quarto de hóspedes; banheiro do corredor.
  - **Deitar** na cama (A; qualquer direção levanta; deitado, A pergunta se quer dormir e salva o jogo) e
    **tomar banho** no box.
- **Rebeca** (só para quem é casado com ela, `spouse` no personagem): tem rotina própria. Cozinha, vê TV,
  toma banho, cochila, rega as plantas, sai para a praça, conversa com o Beto, a Nina e o Tico, e vai à
  lanchonete pedir um sorvete e sentar para comer. Falando com ela: CONVERSAR, ME SEGUE (ela vai junto, até
  entre mapas), ABRAÇAR, BEIJAR e VAMOS DORMIR (ela vai para a cama; deite do lado dela e vocês dormem).
  No online, os outros jogadores veem a Rebeca quando ela está na vila ou na lanchonete.
- **Dia, tarde e noite**: um dia do jogo dura 24 minutos (relógio no canto de baixo). O céu fica dourado
  no fim da tarde e azul à noite, e os postes acendem. À noite os NPCs vão para casa. Deitar na cama à noite é
  ir dormir: jogando sozinho (ou se só você está online) a noite passa e amanhece às 6h, com o jogo salvo. Com
  mais gente online, a noite só passa quando TODOS estiverem deitados; enquanto isso ela continua normal.
- **Lago e pescaria** (depois da ponte, a leste): A de frente para a água joga a linha; quando aparecer "!"
  na boia, aperte A rápido. Cada peixe é vendido na hora (o PEIXE DOURADO vale 50 BETS; de noite aparece o
  BAGRE DA NOITE). Ali perto há um ESTÁBULO em obras, e acima do Coliseu um SHOPPING em obras.
- **NPCs com vida própria** em todos os mapas (vila, bosque, lanchonete e os que vierem): passeiam, param
  para conversar uns com os outros, os duelistas fazem duelos de treino entre si, e todos vão à lanchonete
  pedir comida para a Lu e sentar para comer. De vez em quando (aleatório, com intervalo mínimo para não
  cansar) um duelista vem até você, mostra um "!" e desafia: é só aceitar ou recusar. A Lu (no caixa) e a
  Gabi (sentada) não saem do lugar. No online o servidor controla os NPCs: os dois jogadores veem igual. A
  conversa entre NPCs só aparece quando você está perto (de longe, só um "...").
- **Fome** (barra no canto da tela e na ficha): cai com o tempo e a cada batalha. Comer na lanchonete
  recupera; de barriga cheia não dá para comer. Abaixo de 20, você não duela (nem as gosmas aparecem) até comer.
- **Lanchonete** (na vila, ao lado da loja): entre pela porta e ande lá dentro.
  - A atendente **LU**, no caixa, vende maçã, banana, café, refrigerante, sorvete e X-burguer. Comer mata a
    fome e dá PV a mais na **próxima batalha** (de +3 a +12). No duelo PvP o bônus não vale.
  - Sente nas cadeiras e nos **puffs**: A de frente para o assento; qualquer direção levanta. Os outros
    jogadores online veem você sentado.
  - A **TV** tem 3 canais que trocam sozinhos; A de frente para ela (ou sentado no puff) mostra o programa.
  - Na **MESA DE TROCA**, você troca uma carta sobrando (fora dos decks) com outro jogador online: chame-o,
    escolha a carta que dá e a que quer, e ele aceita ou recusa.
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
    economy.py, tournament.py  loja, evolução, trocas (Nina e entre jogadores) e o torneio do coliseu
    food.py, duel.py         lanches da lanchonete; regras do duelo online (semente, ficha do jogador)
    hunger.py, companion.py  fome; a Rebeca (rotina, seguir, dormir)
    nav.py, townsfolk.py     caminhos dentro e entre mapas; a vida dos NPCs (passear, conversar, desafiar)
    clock.py, fishing.py     relógio do mundo (manhã, tarde, noite, dormir); o que vem no anzol
    rules.py                 números da batalha (mão, energia, gelo...)
  data/                      DADOS do jogo
    cards.py                 as 27 cartas, tipos, raridades e o deck
    legends.py               os legends
    character.py             personagem, coleção, decks, legends e save
    opponents.py, world.py   treinadores, monstros, mapas (com o interior da lanchonete), NPCs e falas
    food.py, companion.py    cardápio da lanchonete; a Rebeca (aparência, falas e atividades da rotina)
    looks.py, props.py       aparência das pessoas e catálogo de objetos do mapa
  graphics/                  DESENHO e arte
    sprites.py               ponto único para pedir pessoas, monstros, legends e rostos
    mana_seed.py, wardrobe.py  pessoas em camadas e as peças de roupa e cortes derivados
    people.py                pessoas desenhadas por código (quando não há Mana Seed)
    assets.py                lê o pacote Ninja Adventure
    tilemap.py               chão, objetos e sombras dos mapas (pacote Ninja Adventure)
    buildings.py, backgrounds.py  construções com placa e o cenário da batalha
    interiors.py             interiores por código: chão e paredes, móveis da lanchonete e canais da TV
    house.py                 a casa: chão e paredes a partir da planta, móveis e a estante de troféus
    pixelart.py, pixelfont.py     cartas, ícones e a fonte pixel própria
  engine/                    MOTOR
    app.py, display.py       laço principal, janela, FPS
    transition.py, ui.py     transições, caixas de texto, menus
    config.py, settings.py   opções (config.json), resolução, cores e controles
    sfx.py                   música e sons gerados por código
  net/                       ONLINE: protocolo, servidor (quem hospeda), cliente e banco (contas)
  scenes/                    TELAS
    battle.py                batalha: fila de passos, turnos, narração e habilidades
    battle_hud.py            desenho da batalha (painéis, marcadores, mão, botões)
    battle_fx.py             animações: transformação, faixa do legend, golpes, partículas
    lobby.py, actors.py      mundo andável e personagens em grade (andando ou sentados)
    cafe.py, trade_table.py  interiores (lanchonete: atendente, assentos, TVs) e a mesa de troca
    home.py                  a casa: cama, banho, dormir, estante, closet e a Rebeca (conversa, seguir, carinho)
    town.py                  os NPCs na tela: andando, balões, "!" e o desafio quando um duelista vem até você
    daynight.py, fishing.py  a cor do dia/noite, postes, relógio na tela e o dormir; a pescaria
    closet.py                closet da suíte: trocar de roupa (a tela de criação só com as roupas)
    online.py                tela JOGAR: hospedar ou entrar no mundo, login e criação de conta
    duel.py                  duelo online contra outro jogador (a batalha, com o oponente vindo da rede)
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
  chegar em tudo e se as passagens batem). Interior: `interior="..."` no `MapDef`, o chão desenhado em
  `game/graphics/interiors.py` (`GROUNDS`) e uma porta com ação nova em `LobbyScene.door_action`.
- **Novo lanche**: um `FoodItem` em `game/data/food.py` (o cardápio da parede e o da LU saem dali).

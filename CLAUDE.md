# Card Quest — guia para o Claude

RPG de cartas em pixel art com pygame-ce. Texto do jogo, comentários e nomes de testes em português.

## Skills do projeto

Use as skills em `.claude/skills/` ao mexer no código (python-game-developer, card-game,
game-architecture, game-ai, game-ui-pygame, game-testing, game-design, game-debugging).

## Convenções

- **Pastas de `game/`**: `core/` regras puras (sem Pygame), `data/` dados (cartas, legends, mapas, personagem),
  `graphics/` desenho e arte, `engine/` motor (app, janela, som, ui, opções), `scenes/` telas. Arquivo novo vai
  na pasta do assunto dele. Imports sempre absolutos (`from game.data.cards import ...`).
- **Regras em `game/core/`, sem Pygame.** Cenas (`game/scenes/`) leem o estado, chamam as regras e
  animam. Nunca calcule dano, preço ou limite de deck dentro de uma cena.
- **Cartas são dados + efeitos.** `CardDef` gera `effects` a partir dos campos; nada de `if card.id == ...`.
  Efeito novo = classe em `core/effects.py` + evento em `core/events.py` + entrada em `BattleScene.NARRATORS`.
- **Regras recusadas levantam exceção com mensagem para o jogador**: `ShopError` (economia),
  `DeckError` (decks). A cena captura e mostra o texto.
- **Aleatoriedade injetável**: funções com sorteio recebem `rng: random.Random | None`.
- **Teclas** vêm de `game/engine/config.py` (`CONFIRM_KEYS`, `UP_KEYS`...), nunca `pygame.K_*` direto em cena
  (exceção: digitação do nome em `create.py`).
- **Cada deck tem um TIPO** (`Character.deck_elements`: fogo/gelo/raio/veneno; `cards.ELEMENTS`): só entram
  cartas desse tipo e de Utilidades (`Character.fits_deck`, `add_to_deck` recusa as outras). A loja separa as
  cartas em sub-abas por tipo (`shop.TYPES`) e o editor de deck só lista o tipo do deck + Utilidades.
- **Legends** (`game/data/legends.py`, tabela do usuário em `tests/test_legends.py`): cada deck tem 1 legend do mesmo
  tipo (`Character.deck_legends`). No começo da batalha os dois duelistas se transformam (`battle_fx.Transform` +
  `CutIn`, `core.abilities.become`): PV, força (+dano por golpe), proteção (tira de cada golpe depois de aura e
  defesa) e energia por turno passam a ser os do legend. Habilidades em `core/abilities.py` (ativas: botão
  HABILIDADE; passivas: automáticas); a IA usa as ativas (`ai.mimo_pick`, `ai.drogoz_discards`). Monstros
  selvagens não têm legend. Arte: `tools/build_legends.py` recorta as folhas de `assets/legends/source/`.
- **Batalha**: `scenes/battle.py` = lógica (fila de passos, turnos, narração, entrada); `scenes/battle_hud.py` =
  só desenho (mixin `BattleHUD` com painéis, marcadores, mão, botões); `scenes/battle_fx.py` = animações.
- **Repositório**: github.com/Rafajunior10/battle_of_legends. `assets/mana_seed/` e `assets/static_creatures/`
  ficam fora do git (licença); o jogo e os testes precisam funcionar sem elas.
- **Online** (`game/net/`): mundo compartilhado. `protocol.py` (mensagens JSON por linha), `server.py` (roda em
  quem hospeda, numa thread; repassa posições e guarda contas), `database.py` (SQLite `world.db`: contas com
  senha em hash + personagem em JSON), `client.py` (`open`/`host` -> `authenticate` -> `enter`; depois thread de
  leitura + fila `poll()`). Online, `Character.save()` manda para o servidor (`character.remote_save`).
  O lobby manda `move` a cada passo (`send_position`) e anima os outros com `actors.RemotePlayer`. Mudou o
  formato das mensagens? Suba `protocol.VERSION`. Testes de verdade com sockets em `tests/test_net.py` e
  `tests/test_online.py`.
- **PvP** (duelo online): lockstep. O servidor só pareia (`challenge`/`answer` -> `duel_start {seed, side}`) e
  repassa jogadas (`duel {action}`). Cada PC roda a mesma batalha: `core/duel.deck_rngs` dá um sorteio por
  baralho a partir da semente; `DuelScene` (subclasse de `BattleScene`) envia as jogadas pelo gancho `sent` e
  aplica as do oponente em `remote_steps`. Por isso a batalha não pode sortear nada fora dos baralhos, e toda
  decisão nova do jogador precisa virar `sent({...})` + tratamento em `remote_steps`. `tests/test_duel.py`
  confere que os dois lados terminam idênticos.
- **Dados do mundo** (mapa, NPCs, falas) ficam em `game/data/world.py`; `lobby.py` só tem comportamento.
- **Lanchonete** (mapa `lanchonete`, porta "cafe" na vila): interior = `MapDef.interior` + chão/paredes por código
  em `graphics/interiors.py` (`GROUNDS`), móveis em `interiors.FURNITURE` (entram em `lobby.BUILDERS`). Objetos
  com `Placed.action` "seat:<direção>" são assentos (`MapDef.seats`, sentar = `Actor.sitting`, desenho cortado
  na cintura + frente do assento por cima) e "use:<coisa>" fazem algo (`MapDef.uses`: "tv", "swap"). Balcão
  (`ObjectDef.counter`) deixa falar com quem está atrás. Comportamento em `scenes/cafe.py` (mixin `CafeMixin`
  do LobbyScene). Lanches: `data/food.py` + `core/food.py`; `Character.snack` é gasto no começo da próxima
  batalha (`BattleScene.take_snacks`/`eat_snacks`; no PvP não vale). Mesa de troca entre jogadores: mensagens
  `swap_*` que o servidor só repassa (`RELAY_MESSAGES`), regras em `economy.can_swap`/`swap_card`, tela
  `scenes/trade_table.py`.
- **Diálogo com pergunta**: use `ui.Prompt` (`say`, `ask`, `choose`), não recrie DialogBox + Menu na cena.
- **Cartas vêm da planilha de regras** do usuário; `tests/test_cards.py` (SPREADSHEET) confere os números.
  Mudou carta? Atualize os dois. A descrição é gerada pelos campos (`CardDef.text`), não escreva à mão.
- **Visual 16 bits e desempenho**: imagens estáticas são desenhadas uma vez e guardadas (tileset, backgrounds,
  `ui.draw_box`, `ui.overlay`, `pixelart.optimize`). Não crie `pygame.Surface` dentro de `draw()` por quadro.
- **Tela 480x270 (16:9)**: use `GAME_W`/`GAME_H` e retângulos derivados deles, nunca coordenadas fixas
  pensadas para outra resolução. Cartas têm `art.CARD_W x art.CARD_H` (56x80).
- **Mapas** são dados (`world.MapDef` em `MAPS`) com objetos `Placed` do catálogo `props.OBJECTS`; portas
  são calculadas dos objetos; comportamento de portas fica em `LobbyScene.door_action`. Objetos e personagens
  são desenhados juntos por profundidade (`LobbyScene.draw_standing`).
- **Pessoas = Mana Seed Character Base** (demo grátis, `assets/mana_seed/`), montadas em CAMADAS por
  `game/graphics/mana_seed.py`: corpo (`0bas`) -> roupas -> cabelo (`4har`) -> chapéu (`5hat`). As ROUPAS (camisa, regata,
  top, manga longa, calça, bermuda, saia, vestido, tênis) e os cortes raspado/longo saem de `game/graphics/wardrobe.py`:
  a roupa do lenhador (`fstr`) é o molde das partes do corpo (cada cor = uma parte), o corpo base é nu (apagar
  roupa mostra a pele), as cores são trocadas mantendo o tom relativo e saia/vestido são desenhados seguindo as
  pernas. Antes de mudar uma peça, gere uma folha de prévia e confira em todas as direções e passos. Quadros recortados em 32 x 44 com
  os pés embaixo; a caminhada tem 6 quadros (`(direção, "walk")`, usada por `Actor.image`). Peça nova = arquivo
  do pacote + entrada nas tabelas de `mana_seed.py`/`looks.py`. NÃO desenhe pessoas por código: o usuário rejeitou
  todas as tentativas; `game/graphics/people.py` só existe como reserva quando a pasta do Mana Seed não está instalada.
- **Ampliar pixel art** só por inteiro: use `sprites.fit_scale(img, altura)` em vez de escala fixa.
- **Texto** sempre por `ui.draw_text`/`draw_outlined`/`text_width` (fonte pixel própria em `game/graphics/pixelfont.py`,
  com acentos). `size` < 12 = fonte pequena só maiúsculas; 12-19 = normal; 20+ = normal ampliada. Caractere
  novo num texto do jogo precisa de letra lá (`tests/test_pixelfont.py` confere).
- **Ficha do jogador** (`scenes/profile.py`) tem o tema do elemento do deck ativo (`THEMES`); abre pelo menu ou
  pela ação de teclado `profile` (I/E).
- **Construções** da vila são modernas e desenhadas por código (`game/graphics/buildings.py`); toda construção com
  porta tem placa com o nome (`Placed(..., label="CASA DO RAFA")`).
- **Arte**: telas pedem desenhos sempre por `game/graphics/sprites.py` (nunca `assets`/`pixelart` direto para
  personagens e monstros). O pacote `assets/ninja_adventure/` (CC0) vem no repositório e é OBRIGATÓRIO
  para os mapas (a arte antiga do mapa feita por código foi removida a pedido do usuário); sem ele o lobby
  levanta um erro explicando o que falta. Monstros ainda caem na gosma de `pixelart.py` sem o pacote.
- Save (`save.json`) precisa continuar carregando saves antigos: migre em `Character.load()/sanitize()`.

## Comandos

- Rodar: `python main.py` — modo dev com recarga automática: `python dev.py`
- Testes: `python -m pytest` (sempre rode depois de mexer; bug corrigido = teste de regressão)
- Padrão de código: `python -m ruff check .` precisa passar limpo (config em `pyproject.toml`)

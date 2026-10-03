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
- **Casa do jogador** (mapas `casa_terreo` e `casa_superior`, porta "home" na vila): `MapDef.private` = cada jogador
  tem a sua (a rede usa `LobbyScene.map_key` = "casa_terreo@NOME"). A planta é a grade (`#` parede, `_` madeira,
  `t` azulejo, `c` carpete, `s` escada) e `graphics/house.py` desenha chão e paredes a partir dela. Escada = warps
  no último degrau. Móveis em `house.FURNITURE`; `house.FROM_CHARACTER` desenha a partir do personagem (troféus).
  Sofá visto de costas usa `ObjectDef.seat_row=0`. Comportamento em `scenes/home.py` (mixin `HomeMixin`): usos
  "closet", "bed" (deitar), "shower" (banho), "trophies". Poses dos personagens: `Actor.pose` = stand/sit/lie/shower;
  deitado/no banho a cena dá `anchor`/`depth` (`house.BEDS`, `house.SHOWER`) e desenha a frente por cima
  (`draw_pose_front`: assento, edredom ou vidro). Cabelo `cacheado` = `wardrobe._curly`; `shorts` = `Mold.thigh`.
- **Rebeca** (companheira, `Character.spouse = "rebeca"`; só a conta do usuário tem): dados e ROTINA em
  `data/companion.py` (atividades com mapa, tile, duração, balão, assento/pose, NPC que responde, `then`); regras em
  `core/companion.py` (`Nav`: caminho dentro do mapa e entre mapas por warps e portas de `world.DOOR_TARGETS`;
  `Companion.tick`: rotina, "follow", "sleep", `hold`). A cena alimenta um `RemotePlayer` com o estado dela.
  Atividade nova = entrada em `REBECA_ACTIVITIES` (`tests/test_companion.py` confere caminhos). Online: mensagem
  `companion` (protocolo v6), os outros a veem só em mapa público.
- **Vida dos NPCs** (`core/townsfolk.py`, `NpcWorld`): TODOS os treinadores e ajudantes de mapas públicos passeiam
  (passeio perto de casa, ir para casa, conversar, duelo de treino, comer na lanchonete) e um duelista às vezes vai
  até um jogador e desafia (chance + `APPROACH_COOLDOWN` por NPC + `PLAYER_COOLDOWN` por jogador). Mapa novo funciona
  sem configurar nada; `Spot.roams=False` deixa um NPC parado (a Lu). Caminhos em `core/nav.py` (`Nav(private=False)`
  para NPCs). Quem roda: sozinho, o lobby (`scenes/town.py`, `TownMixin`); online, o SERVIDOR (thread `_npc_loop`,
  mensagens `npc`, `npc_say`, `npc_challenge`, `npc_hold`; `welcome` traz `npcs`; protocolo v7). Os NPCs de todos
  os mapas existem sempre em `LobbyScene.npc_actors` (`NPC` anda pela fila de passos, como `RemotePlayer`);
  `lobby.npcs` = os do mapa atual. Falar com um NPC chama `talk_npc` (segura ele parado). Nos testes que precisam do
  NPC num lugar, mova o NPC no mundo (`npc_world.folk`) e no desenho (`npc_actors`).
- **Dia e noite** (`core/clock.py`, `WorldClock`; 1 min do jogo = 1 s real): sozinho, o relógio vai no save
  (`Character.world_day/world_minutes`); online, o SERVIDOR manda (anda no `_npc_loop`, `welcome` traz `clock`,
  mensagem `clock` a cada 10 s, guardado no banco em `meta`). Cena em `scenes/daynight.py` (`DayNightMixin`: camada
  `tint`, mais fraca em interiores; brilho dos postes; relógio na tela). Dormir: deitado à noite = dormindo; sozinho
  a noite passa na hora (`start_sleep(skip=True)`); online o cliente manda `bed` e o servidor só pula para as 06:00
  quando TODOS os jogadores estão deitados (`clock` com `slept`). À noite os NPCs vão para casa (`tick(night=True)`).
- **Pescaria** (`core/fishing.py` + `scenes/fishing.py`): A de frente para a água (qualquer `W`); o lago fica no
  leste da vila (`world.LAKE_CENTER`, píer em `PIER_X`). Cada peixe vira BETS na hora (`Character.fish_caught`).
- **Vila** tem 88 x 44 tiles; obras sem uso ainda (`stable_site`, `mall_site`) são construções com tapume e porta
  "locked:". Conversa de NPC só aparece de perto (`lobby.NEAR_TALK`); de longe vira "...".
- **Fome** (`core/hunger.py`, `Character.hunger` 0-100): cai com o tempo no lobby e `BATTLE_COST` por batalha;
  comer (`core/food.buy`) só abaixo de `FULL`; abaixo de `WEAK` o lobby recusa duelos (`LobbyScene.hungry_check`) e
  não há encontros no mato. Barra em `LobbyScene.draw_hunger` e linha FOME na ficha.
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
- **Casa do jogador** (mapas `casa_terreo` e `casa_superior`, porta "home" na vila): `MapDef.private` = cada jogador
  tem a sua (a rede usa `LobbyScene.map_key` = "casa_terreo@NOME"). A planta é a grade (`#` parede, `_` madeira,
  `t` azulejo, `c` carpete, `s` escada) e `graphics/house.py` desenha chão e paredes a partir dela (parede com piso
  embaixo mostra a frente, com a cor do cômodo). Escada = warps no último degrau. Móveis em `house.FURNITURE`;
  `house.FROM_CHARACTER` desenha a partir do personagem (estante de troféus). Sofá visto de costas usa
  `ObjectDef.seat_row=0`. Usos da casa: "closet" (`scenes/closet.py`, a CreateScene só com roupas), "bed" (salva),
  "trophies". NPC REBECA = esposa do jogador (falas em `world.REBECA_LINES`). Trocar de roupa manda `look` pela
  rede. Cabelo `cacheado` sai do chanel em `wardrobe._curly`; `shorts` = calça cortada em `Mold.thigh`.
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

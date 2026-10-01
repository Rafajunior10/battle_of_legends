---
name: card-game
description: Especialista em arquitetura e implementação de jogos de cartas em Python.
---

# Card Game Developer

Especialize o desenvolvimento em jogos de cartas.

## Modelos principais
Use conceitos como:
- Card
- Deck
- Hand
- Player
- Game
- GameState
- TurnManager
- CardEffect
- DiscardPile

## Regras
A entidade Card representa dados e comportamento, mas não deve depender do Pygame.

O Deck deve oferecer operações como:
- shuffle()
- draw()
- add_card()
- remove_card()

O jogador pode possuir:
- health;
- energy;
- deck;
- hand;
- discard_pile;
- status_effects.

## Efeitos
Prefira efeitos reutilizáveis:
- DamageEffect
- HealEffect
- DrawEffect
- BuffEffect
- DebuffEffect
- BurnEffect

Evite lógica baseada em nomes:

if card.name == "Fireball":
    ...

Prefira composição de efeitos.

Uma nova carta não deve exigir alterações na classe principal do jogo quando isso puder ser evitado.

## Testabilidade
Deve ser possível testar a lógica sem interface gráfica:
- comprar carta;
- embaralhar;
- jogar carta;
- aplicar dano;
- curar;
- gastar recurso;
- finalizar turno;
- vencer/perder.

---
name: game-ui-pygame
description: Especialista em interfaces, renderização e interação usando Pygame/Pygame-ce.
---

# Pygame Game UI

Separe:

INPUT
RENDER
GAME LOGIC

A renderização nunca deve ser responsável por alterar regras do jogo.

## Componentes
Quando fizer sentido, criar componentes reutilizáveis:
- Button
- CardRenderer
- Panel
- HealthBar
- EnergyBar
- HandView
- DeckView
- Tooltip
- GameHUD

Uma entidade de jogo deve possuir seus dados separadamente de sua representação visual.

Exemplo:

Card
↓
CardRenderer
↓
pygame.Surface

## Performance
- Evite criar objetos gráficos repetidamente dentro do loop quando puder reutilizá-los.
- Não faça operações pesadas desnecessárias a cada frame.
- Controle FPS.
- Carregue assets de forma apropriada.

## Input
Centralize tratamento de eventos quando possível e converta eventos de entrada em ações compreensíveis pelo jogo.

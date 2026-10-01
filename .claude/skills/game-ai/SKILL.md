---
name: game-ai
description: Especialista em inteligência artificial para jogos de cartas e jogos 2D em Python.
---

# Game AI

Crie IA desacoplada da interface.

Fluxo preferencial:

GameState
    ↓
AI
    ↓
Action
    ↓
Game

A IA não deve alterar diretamente o GameState.

## Para jogos de cartas
A IA pode avaliar:
- vida;
- energia;
- cartas disponíveis;
- custo;
- dano;
- defesa;
- efeitos;
- alvo;
- risco;
- consequências futuras.

## Dificuldades

Easy:
- decisões simples e parcialmente aleatórias.

Normal:
- avalia o estado atual e escolhe ações razoáveis.

Hard:
- considera múltiplas possibilidades e consequências.

Não torne dificuldades diferentes apenas aumentando HP ou dano.

Use randomização controlada quando necessário para evitar comportamento previsível.

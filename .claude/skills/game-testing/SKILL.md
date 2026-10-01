---
name: game-testing
description: Especialista em testes automatizados para lógica de jogos Python usando pytest.
---

# Game Testing

Use pytest para testar a lógica do jogo.

## Prioridades
Teste principalmente:
- criação de cartas;
- deck;
- shuffle;
- draw;
- descarte;
- efeitos;
- dano;
- cura;
- recursos;
- turnos;
- vitória;
- derrota;
- estados inválidos.

## Bugs
Quando encontrar um bug:
1. Reproduza o problema.
2. Crie um teste que reproduza o comportamento.
3. Corrija a implementação.
4. Execute o teste.
5. Execute os testes relacionados.

Nunca remova um teste apenas para fazer a suíte passar.

Prefira testes determinísticos.

Quando houver randomização, permita injetar uma seed ou uma fonte de aleatoriedade controlável nos testes.

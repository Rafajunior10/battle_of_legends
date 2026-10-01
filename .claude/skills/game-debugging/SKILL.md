---
name: game-debugging
description: Especialista em diagnóstico e correção de bugs em jogos Python.
---

# Game Debugging

Ao investigar um bug:

1. Reproduza o problema.
2. Identifique o estado esperado.
3. Identifique o estado real.
4. Encontre o ponto onde eles divergem.
5. Corrija a causa, não apenas o sintoma.
6. Adicione um teste de regressão.
7. Execute a suíte relacionada.

## Pygame
Ao investigar problemas visuais, diferencie:
- problema de estado;
- problema de renderização;
- problema de coordenadas;
- problema de input;
- problema de asset;
- problema de timing/FPS.

## Regras
Não aplique mudanças aleatórias tentando "fazer funcionar".

Não esconda erros com try/except genérico.

Não remova validações sem entender por que existem.

Sempre preservar o comportamento funcional existente que não esteja relacionado ao bug.

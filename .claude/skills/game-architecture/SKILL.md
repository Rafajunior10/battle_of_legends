---
name: game-architecture
description: Especialista em arquitetura limpa e escalável para jogos Python.
---

# Game Architecture

Priorize separação de responsabilidades.

Estrutura sugerida:

src/
  core/
  entities/
  systems/
  cards/
  scenes/
  ui/
  data/
tests/

## Camadas

Game State
    ↓
Systems / Rules
    ↓
Actions
    ↓
UI / Renderer

A UI não deve decidir regras de negócio.

Evite dependências circulares.

Não coloque lógica de combate dentro de componentes visuais.

Prefira composição em vez de hierarquias complexas de herança.

Quando uma funcionalidade puder ser representada como uma ação ou efeito independente, faça isso.

Antes de criar uma abstração, verifique se ela realmente reduz complexidade.

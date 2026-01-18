Para desenvolver um jogo RPG com visão top-down totalmente modular (Projeto Pandorha), aqui está o plano técnico definido:

## 1. Arquitetura do Projeto

O projeto será dividido em dois softwares distintos que compartilham apenas os dados (Data-Driven Design):

1.  **Pandorha Engine (O Jogo):** Responsável apenas por ler dados e renderizar.
2.  **Pandorha Forge (O Editor):** Ferramenta visual para criar conteúdo.

### Estrutura de Pastas Sugerida:

- `/core`: Lógica base do jogo.
- `/editor`: Código fonte da ferramenta visual.
- `/data`: Arquivos JSON/TOML gerados pelo editor (Mapas, Itens, NPCs).
- `/assets`: Imagens, sons e fontes.

## 2. Stack Tecnológico

- **Linguagem:** Python 3.11+
- **Engine de Jogo:** `pygame-ce` (Community Edition) - Mais performático que o pygame padrão.
- **Interface do Editor:** `dearpygui` - Framework GPU-accelerated para criar ferramentas complexas (nós, gráficos, mapas) de forma fácil.
- **Gerenciamento de Dados:** `pydantic` - Para validação rigorosa dos dados criados no editor.

## 3. Extensões Recomendadas (VSCode)

1.  **Python (Microsoft):** Essencial.
2.  **Pylance:** Para autocompletar código inteligente.
3.  **Git Graph:** Para ver a árvore de branches visualmente.
4.  **Error Lens:** Mostra erros na mesma linha do código (ajuda muito iniciantes).
5.  **Todohighlight:** Para marcar lugares onde precisamos voltar a mexer.

## 4. Funcionalidades do Editor (Pandorha Forge)

O editor deve ser capaz de:

- **Editor de Mapas:** Grid visual para pintar tiles.
- **Editor de Entidades:** Criar NPCs e definir atributos (Vida, Força) via sliders e inputs.
- **Editor de Missões:** Sistema de nós (Nodes) para ligar eventos (Ex: Falar com Rei -> Libera Missão X).

## 5. Padrão de Projeto: ECS (Entity Component System)

Para garantir a modularidade total:

- **Entidade:** Apenas um ID (ex: Player).
- **Componente:** Dados puros (ex: ComponentePosicao = {x: 10, y: 20}).
- **Sistema:** Lógica (ex: SistemaMovimento atualiza a posição de todos que têm ComponentePosicao).

Isso permite adicionar novos recursos (ex: SistemaDeFome) sem quebrar o SistemaDeMovimento.

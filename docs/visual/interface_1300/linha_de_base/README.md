# Linha de base (Fase 0), 16/10/2026, antes de qualquer correção

| O quê | Valor |
|---|---|
| PokeNexus | `APP_VERSION = "1.1.0"` |
| PokeIdle no ar | **1.300.2** (rodapé do jogo e `app.js?v=1.300.2` lido da página real, tela de login) |
| Seletores do farm (`game/selectors.py`) | lidos do `app.js` 1.279.2 (não mexidos aqui) |
| Commit | `ae36d08cdc49d12f1a67a54e56a4f212c1efc9d5` ("v1") |
| `git status` antes | só os 9 `PROMPT_*.md` da raiz apagados (já estavam assim; nenhum código modificado) |
| PC | 2 monitores 1920×1080, escala do Windows 100% (96 DPI) |
| Placa de vídeo | NVIDIA GeForce RTX 5070 + AMD Radeon (integrada); `tem_gpu()` = True |
| Qt | PySide6 6.12.0 / Qt 6.12.0 |
| Config do usuário (só lido: zoom e modo) | `zoom = 1.0`, `modo_leve = true`, `painel_conta = true`, `layout_ver_todas = "celulares"` |
| Testes automáticos | **não existem** (nenhum `test_*.py` no projeto) |

## Arquivos

- `hashes.json`: SHA-256 de todos os arquivos do projeto (fora `.venv`, `build`, `dist`, `docs`, caches).
- `ligacoes.json`: leitura do código (AST) de `app/*.py`: 117 ligações (64 `.connect`, 25 `button(...)`,
  23 `Botao(...)`, 2 `addAction` de menu, a lista de atalhos), sem número de linha.
- `widgets.json`: a janela montada de verdade (offscreen, pasta temporária): 43 botões na janela, 41 nos
  Ajustes, e os atalhos `Ctrl+, Ctrl+0 Ctrl+1 Ctrl+2 Ctrl+3 Ctrl+4 Ctrl+B Ctrl+H Ctrl+M F1 F8`.

Gerado por `ferramentas/interface/impressao.py --saida docs/visual/interface_1300/linha_de_base`.

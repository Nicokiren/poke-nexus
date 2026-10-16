# V0 — Inventário visual do PokeNexus (antes da identidade nova)

Prints feitos em 14/10/2026 com o código atual, numa pasta de dados nova (sem login; nenhuma conta real
tocada). Estão em `docs/visual/v0/`.

## Telas

| Print | O que mostra |
|---|---|
| [01](v0/01_estados_das_abas.png) | Abas com 4 estados (Farming, Batalha, Pausado, Erro), conta parada |
| [02](v0/02_uma_conta_login.png) | Uma conta, com o jogo na tela de login |
| [03](v0/03_dashboard_e_log.png) | Dashboard e log abertos embaixo |
| [04](v0/04_ver_todas_grade.png) | VER TODAS em grade |
| [05](v0/05_ver_todas_celulares.png) | VER TODAS em celulares |
| [06](v0/06_celulares_sem_painel.png) | Celulares com o painel da conta recolhido |
| [07](v0/07_hunts.png) | Hunt Analyzer (conta sem login: vazio) |
| [08](v0/08_rmt.png) | RMT (conta sem login) |
| [09](v0/09_configuracoes.png), [10](v0/10_configuracoes_fim.png) | Configurações (começo e fim) |
| [11](v0/11_regra_rmt.png) | Janela de regra do RMT |
| [12](v0/12_aviso_do_windows.png) | Aviso nativo do Windows ("Parar todas") |
| [13](v0/13_uma_conta_1366.png), [14](v0/14_ver_todas_1366.png) | Uma conta e VER TODAS em 1366×768 |
| [01 Leve](v0/01_estados_das_abas_leve.png), [02 Leve](v0/02_uma_conta_login_leve.png), [03 Leve](v0/03_ver_todas_grade_leve.png) | Os mesmos no Modo Leve |

Não foi possível fotografar com dados reais (em batalha de verdade, Hunt Analyzer com ranking, RMT com
regras e saldo): isso pede as contas logadas. Os estados das abas foram simulados só na aparência.

## Componentes encontrados

| Componente | Onde | Arquivo |
|---|---|---|
| Marca (pokébola + "POKENEXUS" + subtítulo espaçado) | topo | `gui.py` `_build_header` |
| Contador "CONECTADAS x/4" | topo | `gui.py` (`counter`) |
| Botões do topo (Dashboard e log, Configurações, Iniciar todas, Parar todas) | topo | `gui.py` |
| Aba da conta (mascote, nome, atalho, selo de status, nível) | barra de contas | `gui.py` `AccountTab` |
| Aba VER TODAS (4 pokébolas) | barra de contas | `gui.py` `AllTab` |
| Barra do jogo (ícone, título, selo, nick/hunt, Jogo/Hunts/RMT, Grade/Celulares, zoom, recarregar, « Conta) | área do jogo | `gui.py` `GameArea` |
| Quadro da conta no VER TODAS (cabeçalho + página) | VER TODAS | `gui.py` `AccountCell` |
| Tela "conta parada" (sprite cinza + texto + Iniciar) | área do jogo | `gui.py` `AccountCell` |
| Painel da conta (título, palco com brilho, mascote, nome, selo grande, grade de 8 números, 6 botões, menu de Login) | direita | `gui.py` `SidePanel`, `Stage` |
| Selo de status (pílula em caixa alta) | abas, barra, painel | `widgets.py` `StatusPill` |
| Sprite animada | abas, painel, Hunt Analyzer | `widgets.py` `PixelSprite` |
| Fundo xadrez | janela | `widgets.py` `CheckerBackground` |
| Tabela do dashboard | embaixo | `gui.py` `_build_dashboard` |
| Log com filtros | embaixo | `gui.py` `_build_log` |
| Rodapé com atalhos | embaixo | `gui.py` `_texto_rodape` |
| Hunt Analyzer: botões de ordenar, caixas, ranking com botão desenhado "Caçar aqui", coroa (master_ball), caixa vazia (poke_ball) | Hunts | `hunt_ui.py` |
| RMT: cartões de saldo/limites, tabela de regras, extrato, botões Ligar/Parar | RMT | `rmt_ui.py` |
| Janela de regra do RMT | RMT | `rmt_ui.py` `RegraDialog` |
| Configurações: cartões, caminhos, selos "vale na hora", campos, atalhos | janela | `settings_ui.py` |
| Avisos nativos (`QMessageBox`) | 13 lugares | `gui.py` (7), `rmt_ui.py` (4), `settings_ui.py` (2) |

Estilos de componente por nome (`setObjectName`): `muted` 15, `tool` 9, `card` 7, `primary` 6,
`cardTitle` 5, `danger` 2, `statKey` 2, `tab` 2, `selo` 2 e mais 11 usados uma vez. Cores fixas: 117
(53 diferentes); `setStyleSheet` soltos: 28; `border-radius`: 17; `letter-spacing`: 8.

## Problemas que já existem hoje (independentes do tema)

1. **Avisos do Windows em inglês:** os botões aparecem "Yes" / "No" ([12](v0/12_aviso_do_windows.png)).
   O Qt não carrega a tradução para português. Some com o diálogo próprio da V3.
2. **Texto cortado na conta parada:** "Conta 1 está parada. Ao iniciar, o" ([01](v0/01_estados_das_abas.png));
   o texto inteiro é "...Ao iniciar, o PokeIdle dela aparece aqui." (`gui.py` linha 346, rótulo sem
   quebra de linha).
3. **1366×768:** o painel da conta não cabe na altura e os botões de ação ficam embaixo da rolagem
   ([13](v0/13_uma_conta_1366.png)).
4. **Selo "LOGIN" × "SESSÃO EXPIRADA":** a aba diz "LOGIN" e o painel diz "SESSÃO EXPIRADA" para o mesmo
   estado ([07](v0/07_hunts.png)).
5. **Ruído de texto:** caminhos com `PAULOA~1` nas Configurações, rodapé com 9 itens, explicações longas
   no topo do Hunt Analyzer e do RMT.

## O que isso confirma da seção 3 do prompt

Emojis nos botões (🎮 🎯 🛒 ⚙ 💾 📁 🔑 ✋), amarelo `#FFCB05` como único destaque, cartões arredondados
iguais em todo lugar, títulos em CAIXA ALTA espaçada ("CONTA SELECIONADA", "SALDO E LIMITES DESTA
CONTA", "HUNT ANALYZER"), fonte do sistema, selos em pílula, brilho radial atrás do mascote e a moldura
azul-marinho em volta de um jogo todo em madeira e roxo. A moldura do app e o jogo parecem dois produtos
diferentes, e isso é o mais visível nos prints 02 e 13.

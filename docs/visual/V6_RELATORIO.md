# Identidade visual: relatório final (15/10/2026)

**Todas as funcionalidades continuam iguais.** Mudou só a aparência e o texto mostrado: os botões
chamam as mesmas funções, os nomes internos de status (FARMING, BATALHA…) e o log não mudaram, e nada na
automação, no WebSocket, no farm, no Mercado (RMT) ou no Hunt Analyzer foi tocado.

## Direção: A, "Base do Treinador" (escolhida pelo usuário)

Molduras de madeira escura em pixel art, tiradas das cores do próprio PokeIdle (`estilo.css`), para o
programa e o jogo parecerem uma coisa só. Prancha: [v1/prancha_A.png](v1/prancha_A.png).

## Antes e depois

| Tela | Antes | Depois |
|---|---|---|
| Uma conta | [v0/02](v0/02_uma_conta_login.png) | [depois/02](depois/02_uma_conta_login.png) |
| Estados das contas | [v0/01](v0/01_estados_das_abas.png) | [depois/01](depois/01_estados_das_abas.png) |
| Todas as contas (grade) | [v0/04](v0/04_ver_todas_grade.png) | [depois/04](depois/04_ver_todas_grade.png) |
| Todas as contas (celulares) | [v0/05](v0/05_ver_todas_celulares.png) | [depois/05](depois/05_ver_todas_celulares.png) |
| Hunts | [v0/07](v0/07_hunts.png) | [depois/07](depois/07_hunts.png) |
| Mercado | [v0/08](v0/08_rmt.png) | [depois/08](depois/08_rmt.png) |
| Ajustes | [v0/09](v0/09_configuracoes.png) | [depois/09](depois/09_configuracoes.png) |
| Regra do Mercado | [v0/11](v0/11_regra_rmt.png) | [depois/11](depois/11_regra_rmt.png) |
| Aviso | [v0/12](v0/12_aviso_do_windows.png) | [depois/12](depois/12_dialogo_do_tema.png) |
| 1366×768 | [v0/13](v0/13_uma_conta_1366.png) | [depois/13](depois/13_uma_conta_1366.png) |
| Modo Leve | [v0/02 Leve](v0/02_uma_conta_login_leve.png) | [depois/02 Leve](depois/02_uma_conta_login_leve.png) |

## O que mudou

- **Tema num lugar só:** `app/tema.py` (cores, fontes, folha de estilo). Cores fixas fora dele: 117 → 0.
- **Molduras de pixel** (contorno, bisel claro em cima, degrau escuro embaixo) em painéis, fichas, botões
  (normal, em cima, apertado, desligado, ligado, principal, perigo) e caixas de seleção.
- **124 ícones de pixel próprios** no lugar dos 24 tipos de emoji (`app/icones.py`).
- **Selo de status** com ícone + nome ("Caçando", "Em batalha", "Pausado", "Você no controle", "Faça
  login", "Parado"…), não depende só da cor.
- **Diálogo próprio** (`app/dialogos.py`) no lugar dos 13 avisos do Windows. Os botões agora são em
  português (antes saíam "Yes"/"No") e as respostas são as mesmas: só "Sim" confirma; fechar, Esc e
  Enter = "Não".
- **Textos aprovados:** Registro, Ajustes, Mercado, Começar tudo / Parar tudo, Ficha do treinador, Jogar
  eu mesmo, Todas as contas; títulos em caixa normal; rodapé curto; **F1** mostra os atalhos.
- **Marca:** o ícone do programa e o logo do topo continuam a Poké Ball (o usuário pediu para voltar,
  depois de ver o mascote "Broto" no lugar). Saíram a Master Ball do Hunt Analyzer e as 4 Poké Balls do
  "Todas as contas" (ícone de pixel próprio).
- **Palco do mascote:** chão de grama em pixel no lugar do brilho redondo.
- **Corrigidos de passagem:** texto da conta parada que era cortado, botões dos avisos em inglês.

## Paleta (contraste WCAG conferido em 53 pares, todos acima do mínimo)

| Token | Cor | | Token | Cor |
|---|---|---|---|---|
| fundo | `#1A1016` | | texto | `#F6E9DC` (13,9:1 no painel) |
| painel | `#2A1A22` | | texto fraco | `#C9AFA4` (8,0:1) |
| moldura | `#8C4A3E` | | destaque (ouro) | `#E8B04A` (8,5:1) |
| filete | `#2B0C14` | | foco | `#3CCFC0` |

## Medições

**Área do jogo (nenhum pixel a menos):**

| | Antes | Depois |
|---|---|---|
| Uma conta, 1920×1080 | 1532 × 798 | 1532 × 802 |
| Todas as contas (grade) | 1530 × 768 | 1530 × 774 |
| Uma conta, 1366×768 | 978 × 486 | 978 × 490 |

**Memória e CPU** (pacote final, sem Python, 4 páginas na tela de login, 2 rodadas cada):

| | PokeNexus.exe | CPU até 45 s |
|---|---|---|
| Versão anterior | 345–346 MB | 10,5–11,5 s |
| Versão nova | 346–347 MB | 11,4–11,5 s |

As páginas do jogo variaram de uma rodada para outra nas duas versões (732 a 1.015 MB); elas não dependem
do tema.

## Testes (todos OK)

`test_painel`, `test_celulares` (em 1920), `test_settings_live` (4 páginas, nada recarrega),
`test_settings_ui`, `test_rmt_ui`, `test_roda`, `test_dialogos` (Sim/Não/X/Esc/Enter), `test_tema`
(contraste + nenhuma cor fixa, emoji em botão, `QMessageBox` ou arte da franquia na interface), pacote
sem Python abre e fecha sem sobrar processo.

## O que não foi testado, e por quê

- **Com as contas reais** (batalha de verdade, Hunt Analyzer com ranking, Mercado com saldo): o usuário
  estava dormindo e as contas reais só são usadas com autorização. A lógica não mudou; o que mudou foi
  testado com páginas de verdade na tela de login.
- **Escala 125% e 150% do Windows:** a tela do PC estava em 1024×768 durante o trabalho (provavelmente o
  monitor desligado). Os prints em 1920 foram feitos com a janela sem moldura.

## Otimização depois do tema (15/10/2026)

O usuário sentiu o app mais travado. Medido: o problema eram as molduras desenhadas por `border-image`
no QSS (o Qt recortava e esticava a imagem a cada pintura; repintar a janela ia de ~5 ms para 8–10 ms,
e as fichas repintam ~40×/s por causa das sprites animadas). Agora `app/molduras.py` (`Moldura`,
`Botao`) copia a moldura já montada em memória.

| | Com border-image | Otimizado |
|---|---|---|
| Repintar a janela | 7,8–10,2 ms | 4,0–4,2 ms |
| Trocar de tela | 10,4–13,6 ms | 5,6–6,2 ms |

Visual idêntico: 47 casos (todos os estados de botão, ficha e painel) comparados pixel a pixel,
diferença máxima 1/255 (a suavização que o `border-image` fazia nas emendas). Todos os testes passam.

## Observações

- **Mascotes:** continuam sendo os Pokémon originais, por decisão do usuário (15/10/2026). Os mascotes
  da prancha (Broto, Brasa, Gota, Pedrisco) não serão usados.
- O texto "sessão expirada - faça login: botão 'Login' do programa" vem do worker (e vai para o log);
  ficou como estava para não mexer no farm.
- As linhas de dados do Hunt Analyzer ainda usam "·" entre os números.

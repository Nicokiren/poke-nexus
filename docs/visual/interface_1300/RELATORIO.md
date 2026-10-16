# Vistoria da interface depois do PokeIdle 1.300.2 (16/10/2026)

## Resumo

1. **8 problemas** achados: 1 Alta, 3 Média, 4 Baixa (I-08 só apareceu com a conta logada).
2. **Corrigidos: 4.** I-01 Market cortado (Alta), I-02 o mesmo na Grade (Média, com limite em telas pequenas),
   I-03 Ajustes maior que a tela (Média), I-04 barra do jogo cortada em janela estreita (Baixa).
3. O Market cortado é **defeito do próprio jogo** (tipo B, provado no Edge comum). O PokeNexus piorava
   (tipo C). Por decisão do usuário, o PokeNexus baixa o zoom **só enquanto o Market do jogo está aberto**.
   Provado com o Market **real** da Conta 4: antes 4 cartões sem botão, depois 0.
4. **Pendentes: 4.** I-08 Ginásios (mesmo defeito do jogo, precisa de decisão), I-05, I-06, I-07 (Baixa,
   janela estreita: as saídas encolhem a área do jogo ou escondem texto).
5. Nada da lista proibida mudou (hashes iguais), todo botão e atalho chama o mesmo método.
   **Fora do escopo e urgente:** o commit `v1`, que já está no GitHub, tem 983 arquivos de perfis de navegador.

## Tabela final

| ID | Onde | Gravidade | Origem | Correção | Arquivos | Antes | Depois |
|---|---|---|---|---|---|---|---|
| I-01 | Visão individual > Jogo > Market > Comprar (Pokébolas, Poções...) | Alta | B + C | zoom só com o Market aberto | `app/gui.py` | `inventario/I-01_antes_*.png`, `conta4/*/01_market_antes.png` | `depois/I-01_*.png`, `conta4/*/02_market_depois.png` |
| I-02 | Todas as contas > Grade > Market | Média | B + C | a mesma regra nos quadros | `app/gui.py` | `inventario/I-02_antes_grade_1920.png` | `conta4/e100_1920/05_market_grade.png` |
| I-03 | Ajustes em tela 1366×768 a 100% ou 1080p a 150% | Média | A | tamanho inicial cabe na área útil | `app/settings_ui.py` | `inventario/I-03_antes_ajustes_1366.png` | `depois/I-03_depois_ajustes_1366.png` |
| I-04 | Barra do jogo em janela estreita | Baixa | A | botões de texto só com o ícone (título longo da Grade ainda corta) | `app/gui.py` | `inventario/I-04_antes_barra_estreita.png` | `depois/I-04_depois_*.png` |
| I-05 | Topo e aba "Todas as contas" em janela estreita | Baixa | A | **pendente** | | `inventario/I-05_antes_aba_todas.png` | |
| I-06 | Hunts "Ordenar por" na janela mínima | Baixa | A | **pendente** | | `inventario/I-06_antes_hunts_760.png` | |
| I-07 | Janela no mínimo (760×600) / 1366×768 a 125% | Baixa | A | **pendente** | | `inventario/I-07_antes_minimo.png` | |
| I-08 | Jogo > Ginásios | Média | B + C | **pendente (decisão)** | | `conta4/e100_1920/10_ginasios.png` | |

Detalhes, medidas e prova de cada item: `INVENTARIO.md`. Plano: `PLANO.md`.

### Como ficou o I-01 / I-02

- `CellsHost.MARKET_CSS_H = 982`: a altura de página em que o próprio jogo desenha o Market inteiro
  (o modal é 88% da página, até 864 px CSS).
- A cada 0,8 s a área do jogo pergunta a cada página **visível** (visão individual e Grade) se o modal do
  Market está aberto: `#modal` sem `hidden`, `data-modal="market"`, e a página no layout de computador.
  É só leitura (`runJavaScript` que devolve true/false). Nenhum CSS ou JS do jogo é mudado; nenhum clique.
- Enquanto estiver aberto: zoom = o menor entre o zoom escolhido e `altura do quadro / 982`. Um zoom menor
  escolhido com − é respeitado. Ao fechar o Market, volta sozinho ao zoom de antes (medido: 100%).
- O rótulo do zoom mostra o zoom em uso (ex.: **78%**), e a dica no mouse diz que é por causa do Market e
  para quanto volta.
- Página estreita (layout de celular do jogo, ≤ 720 px CSS): nada muda, lá o Market rola e não corta
  (provado: 1366×768 a 125% com a ficha aberta, `conta4/1366_e125_ficha1`).
- Celulares: nada muda (layout de celular do jogo).

Zoom usado com o Market aberto (página de teste e conta real dão o mesmo):

| Tela | Escala | Zoom escolhido | Zoom com o Market | Cartões sem botão antes → depois |
|---|---|---|---|---|
| 1920×1080 | 100% | 100% | 78% | 4 → 0 (conta real), 6 → 0 (teste) |
| 1920×1080, ficha fechada, modo normal | 100% | 100% | 78% | 4 → 0 (conta real) |
| 1920×1080 | 125% | 100% | 55% | 4 → 0 (conta real) |
| 1366×768, ficha fechada | 100% | 100% | 46% | 4 → 0 (conta real) |
| 1366×768, ficha aberta | 125% | 100% | (layout de celular, sem zoom) | 0 → 0 (conta real) |
| 1600×900 | 100% | 100% | 59% | 6 → 0 (teste) |
| 2560×1440 | 100% | 100% | 100% (já cabe) | 0 → 0 |
| 2560×1440 | 125% | 100% | 85% | 6 → 0 (teste) |
| 1920×1080 | 150% | 100% | 41% | 6 → 0 (teste) |
| 1920×1080, Registro aberto | 100% | 100% | 54% | 6 → 0 (teste) |
| 1920×1080 | 100% | 80% | 78% | 0 → 0 |
| 1920×1080 | 100% | 50% | 50% (o da pessoa) | 0 → 0 |
| Grade 1920×1080 | 100% | auto 49% | 35% | 4 → 0 (conta real) |
| Grade 1366×768 / janela mínima (100%), Grade 1920×1080 a 125% e 150% | | auto 30–34% | 25% (o mínimo do Qt) | **continua cortado** |

**Limite honesto:** em telas pequenas e escala alta o Market fica pequeno (46% em 1366×768), porque o jogo
exige ~982 px CSS de altura. Na Grade em telas pequenas nem o zoom mínimo do Qt (25%) basta: lá a saída é
abrir a conta sozinha (duplo clique no nome do quadro). A correção de verdade é do jogo, e é uma linha de
CSS (testada só na cópia de teste): ver `AVISO_POKEIDLE.md`.

## Hipóteses do Market

| | Resultado | Prova |
|---|---|---|
| H1 | **Confirmada, com ajuste**: o que mudou na 1.300 foi a altura fixa do modal (15/10/2026); a grade deveria rolar, mas o cartão tem `overflow: hidden` e as linhas encolhem | conta real: cartão de 225 px com 301 px de conteúdo; teste: grade 533 px com `scrollHeight` 533 |
| H2 | **Confirmada** | 1920×1080: página de 763 px CSS a 100%, 544 a 125%, 400 a 150% |
| H3 | **Descartada** | página real: escondida = celular; ao aparecer, 1531×763 e sem `mobile`, também ao voltar do Celulares |
| H4 | **Descartada** | normal, Leve com placa e Leve sem placa: mesmos px CSS e mesmo corte em todos os cenários |
| H5 | **Confirmada (B)**, e o PokeNexus piora (C) | Edge comum corta com 1896×908 e 1896×948 px CSS; não corta com 968 |

## Prova da Fase 5

**Arquivos mudados** (`git status`): `app/gui.py`, `app/settings_ui.py` (lista permitida) e `AGENTS.md`
(só "Próximos passos"). Novos: `docs/visual/interface_1300/`, `ferramentas/interface/` (ferramentas de teste,
fora do pacote: o `PokeNexus.spec` só leva `assets`, `config.toml` e `hunts/bridge.js`) e `dist_novo/`
(o pacote de teste; `dist\` não foi tocado). Os 9 `PROMPT_*.md` apagados já estavam assim antes.

**Hashes** (`linha_de_base/hashes.json` × `depois/impressao/hashes.json`, todos os arquivos do projeto):
diferentes só `app/gui.py`, `app/settings_ui.py` e as ferramentas novas. `workers/`, `game/`, `rmt/`,
`hunts/`, `browser/` (inclusive `web_host.py`), `app/manager.py`, `app/config.py`, `app/config_edit.py`,
`main.py`, `PokeNexus.spec`, `build.bat` e `config.toml`: **idênticos**.

**Botões e atalhos** (`ligacoes.json`, leitura do código): nenhuma ligação sumiu ou mudou. Entrou uma só:
`self._market_timer.timeout → self._olhar_market` (o relógio que lê se o Market está aberto).
`widgets.json` (a janela montada): os 43 botões da janela, os 41 dos Ajustes e os 11 atalhos **iguais**
(nome, texto, dica, métodos ligados).

**Comportamento** (`ferramentas/interface/atalhos.py`, código de antes × depois, 4 contas na tela de login
numa pasta temporária): Começar tudo, Ctrl+2/3/4/1, Ctrl+0, Celulares, Grade, Ctrl+H ×2, Ctrl+M ×2,
Ctrl+B ×2, F8 ×2 (pausa e retoma), Ctrl+, (Ajustes), F1, Parar tudo (respondendo Parar): **19 de 19
passos iguais** (conta selecionada, modo, área, ficha, diálogos, contas rodando e modo).
`depois/impressao/atalhos_antes.json` e `atalhos_depois.json`.

**Diff lido linha por linha:** nenhuma linha mexe em farm, Mercado (RMT), login, chamadas aos workers,
condições de automação, gravação em disco, mensagens de log ou valores padrão. Muda só: o zoom das páginas
enquanto o Market do jogo está aberto, o texto/dica do rótulo do zoom, o texto dos 5 botões da barra em
janela estreita e o tamanho inicial dos Ajustes. Nada fora de `app/gui.py` lê o zoom.

**Área do jogo:** em todos os 193 cenários da matriz (5 rodadas × 37, mais 8 da tela 1366×768), o tamanho da
área do jogo e de cada quadro é **igual** antes × depois (`area_jogo_px` e `quadro_px_logicos` nos
`medidas.json`). Nenhum cenário passou a cortar mais cartões.

**Contraste:** nenhuma cor nova ou mudada (nenhuma linha de `app/tema.py` mexida; o rótulo e a dica usam
os estilos que já existiam). Os pares do `V6_RELATORIO.md` continuam valendo.

**Desempenho** (`ferramentas/interface/repintura.py`, repintar a janela 1920×1001, Modo Leve, 200 vezes,
3 rodadas alternadas): antes 4,74 / 4,16 / 4,18 ms (mediana), depois 4,32 / 4,01 / 4,48 ms. Igual dentro do
ruído. A leitura do Market é um `runJavaScript` por página visível a cada 0,8 s, só na área Jogo.

**Pacote:** `PyInstaller --distpath dist_novo --workpath build_novo`; pasta de 321 MB, ZIP de 133 MB
(`dist_novo/PokeNexus-1.1.0-interface1300.zip`). Descompactado numa pasta nova e aberto sem Python no PATH
(PATH só com `C:\Windows`), com pasta de dados temporária: abriu ("PokeNexus"), fechou no X com código 0,
**nenhum processo sobrou**.

**Limpeza:** 43 pastas temporárias dos testes apagadas; a cópia do código de antes (que trazia os perfis
versionados, ver "Fora do escopo") apagada; `build_novo` apagado.

## Telas do jogo vistas com a Conta 4 (autorizada pelo usuário)

PokeNexus do usuário fechado; Opera sem a Conta 4 (confirmado pelo usuário); nenhum worker iniciado
(sem farm, sem Mercado RMT); perfil web dela usado direto pelo navegador embutido, sem ler nem copiar
cookies. Cliques feitos: só abrir e fechar telas (`button[data-modal]`, Mochila), categorias e as abas
Comprar/Vender do Market, e o × do aviso do Discord do jogo. **Nenhum clique em comprar, vender, Shop,
RMT, Diamantes ou Gema.** Prints e medidas em `conta4/`.

| Tela | 1920×1080, 100%, zoom 100% |
|---|---|
| Market > Comprar (4 categorias) | cortado antes; inteiro depois (I-01) |
| Market > Vender | inteiro, rola (com o zoom do Market) |
| Mochila | ok |
| Pokédex | ok |
| Mapa | ok |
| Ranking | ok |
| Pokepédia | ok |
| Ginásios | **I-08**: os 18 cartões espremidos (201 de 241 px), o rótulo de ação do pé de cada um fica de fora |

Não vistas (decisão minha, por segurança): Shop e RMT do jogo (dinheiro), Bosses, PvP, Torneio, Casa,
Passe, Centro (podem mudar o estado do jogo), modais de configuração do jogo.

## Fora do escopo

1. **URGENTE: logins versionados no Git.** O commit `ae36d08` ("v1"), que **já está no GitHub**
   (`origin/main`, `github.com/PauloAfonsoGR/poke-nexus`), contém 983 arquivos de `profiles/conta_01` a
   `conta_04` (perfis de navegador antigos; pelos nomes, 12 arquivos de `Cookies`, 8 de `Login Data` e o
   `Local Storage`). Não abri nenhum. Uma cópia temporária que extraí do commit para comparar o código foi apagada na hora. Sugestão
   para um prompt separado: deixar o repositório privado (se não estiver), sair das sessões no PokeIdle
   (trocar as senhas), tirar `profiles/` do histórico e pôr `profiles/` e `logs/` no `.gitignore`.
2. Seletores do farm (`game/selectors.py`, lidos do 1.279.2): não testei o farm (nenhum worker rodou). O
   `#app`, `#modal`, `#modal-fechar` e `button[data-modal="market"]` continuam existindo na 1.300.2.
3. O jogo mostra um aviso de cookies na tela de login e um aviso do Discord por cima do jogo ao entrar
   (do próprio jogo; o PokeNexus não mexe).

## Pendentes (precisam de decisão do usuário)

- **I-08 Ginásios:** mesmo defeito do jogo. O cartão inteiro continua clicável; só o rótulo de ação do pé
  some. Dá para estender a mesma regra de zoom aos Ginásios (`data-modal="ginasios"`), se o usuário quiser.
- **I-05 topo e aba "Todas as contas"** (só com ~1100 px lógicos ou menos): as saídas são o topo em duas
  linhas (a área do jogo encolhe ~50 px nessas telas) ou esconder o "Ctrl+0" da aba. As duas vão contra
  regras do projeto; ficou como está.
- **Resto do I-04:** na Grade em janela bem estreita (1366×768 a 125%), mesmo com os botões só com o
  ícone, o título longo ("Todas as contas: Conta 1 selecionada") e o selo de status ainda são cortados
  (`depois/bruto/e125_leve/1366x768_grade.png`). Encurtar o título muda o texto; ficou como está.
- **I-06 Hunts "Ordenar por"** (só na janela mínima): os botões não têm ícone; quebrar em duas linhas
  encolhe a lista. Ficou como está.
- **I-07 janela mínima / 1366×768 a 125%:** baixar o mínimo de 760×600 mexe no layout inteiro. Ficou.

## O que NÃO foi testado

- Escala real do Windows a 125%/150% (simulei com `QT_SCALE_FACTOR`, que muda os px lógicos do mesmo jeito)
  e um monitor 2560×1440 de verdade (a janela de 2560×1361 foi aberta sem moldura num monitor 1080p).
- O farm com o zoom do Market ligado (nenhum worker rodou). O zoom não é lido por nada fora de
  `app/gui.py`, e a Grade já trocava o zoom das páginas o tempo todo.
- Compra de verdade (proibido nesta tarefa).

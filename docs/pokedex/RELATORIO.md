# Pokédex do PokeNexus (17/10/2026)

Uma Pokédex por conta, que abre na área do jogo (como o Hunts) pelo botão **Pokédex** no topo ou por **Ctrl+D**.
Cada pokémon aparece como **silhueta preta** até a conta tê-lo; aí ele aparece colorido, com o nome e uma
Pokébola no canto. **Só mostra:** não captura, não clica no jogo, não abre tela do jogo, não troca de hunt e não
manda nada ao servidor. Todos os testes usaram pasta de dados temporária; nenhuma conta real foi aberta.

Reconhecimento (Fase 1, mostrado ao usuário): `RECONHECIMENTO.md`.

## Decisões do usuário

| Pergunta | Escolha |
|---|---|
| A lista | **385 pokémon**: Kanto 151, Johto 99 (sem o **#201 Unown**, que não tem sprite no PokeNexus), Hoenn 135 |
| Mega e Forma | **Seguem o jogo**: têm entrada própria lá e não marcam a espécie base. Os clones Orre (13xxx) o próprio jogo já junta na base |
| Inventário (mensagem durante o trabalho) | **"A pokedex deve identificar os pokémons já adquiridos no inventário"**: o inventário da conta (`pokemons`, com o Depot) conta sempre, inclusive pokémon vindo de evolução ou troca. Por isso o total do PokeNexus **pode passar** o da aba do jogo, que só conta capturas |
| Visual | **B, o aparelho**: lente e luzinhas no alto, a grade numa tela de LCD clara e a telinha do pokémon em que o mouse está (a proposta A, vitrine escura, ficou nos prints `A_*`) |
| Topo estreito | Na janela mínima (760×600) não cabia: **só nesse caso** a Pokédex fica só com o ícone e o contador vira "0/4" (dica "contas conectadas") |
| Pokébolas (mensagem durante o trabalho) | Usar as bolas enviadas "só onde for necessário": **só a Poké Ball, no canto das células capturadas**. Arquivo `poke.png` do pacote pokesprite (`Downloads\pokesprite-master\items\ball`), copiado sem mudança para `assets/sprites/ui/bola_capturado.png` |

## O que foi feito

| Arquivo | O quê |
|---|---|
| `game/pokedex.py` (novo, sem Qt) | `chave_pokedex` (a mesma conta do `shared/pokedex.mjs` do jogo), `montar_lista` (sprites ∩ espécies base do catálogo no ar), `capturados` (Pokédex do jogo `c > 0` + inventário + evento `capturado`), `progresso`, `PokedexConta` (arquivo por conta) e `juntar` (Todas as contas) |
| `game/pokeidle.py` | **só acréscimo** (diff em `pokeidle.diff`): guarda a Pokédex do jogo em `self.dex` (inteira no welcome/`cheio`, `dexMud` entra, `dexFora` sai, a mesma regra do `shared/estado-delta.mjs`), `dex_seq` e `dex_capturas` (speciesId do evento `capturado`). `_IGNORAR` e `_USADOS` iguais; a única linha que saiu é o comentário que dizia "a Pokédex não é usada" |
| `app/pokedex_ui.py` (novo) | `PokedexDados` (vive sempre, só grava espécies novas) e `PokedexPanel` (nasce na 1ª abertura): `QListView` + delegate que pinta pixmaps prontos, silhueta por `CompositionMode_SourceIn` em cima do próprio sprite, cache em memória, sem animação |
| `app/gui.py` | botão **Pokédex** no lugar do "N/4 conectadas" (o contador foi para a esquerda dele), área "pokedex" no `GameArea` (criada só quando abre), Ctrl+D, linha no F1, olhada a cada 2 s em `refresh`, topo compacto só na janela estreita |
| `app/manager.py` | uma função de leitura nova, `pokedex_catalogo()` (o mesmo catálogo do Hunt Analyzer, pela página de dados sem conta, sem bloquear a tela) |
| `app/config_edit.py`, `app/settings_ui.py` | atalho "Jogo / Pokédex" em Ajustes → Atalhos. O padrão **Ctrl+D** fica em `config_edit.ATALHO_PADRAO`, porque `app/config.py` (padrões) era proibido; vale enquanto o `config.toml` não tiver a chave |
| `app/tema.py` | 3 cores da tela de LCD (`tela_dex` e as duas de texto) e o estilo da grade |
| `ferramentas/arte/icones.py` + `assets/ui/ico_pokedex_*.png` | o ícone de pixel do aparelho, nas 5 variantes (os outros ícones e peças saíram idênticos) |
| `ferramentas/pokedex/` | `teste_dados.py`, `tela.py` (prints, testes, medidas, topo), `fechar_no_x.py`, `teste_build.ps1` |

**Onde fica cada coisa:** a Pokédex de cada conta em `profiles\conta_XX\pokedex.json`, só com números de
espécie, a data da primeira captura que o PokeNexus viu e o id da conta do jogo (para nunca misturar duas contas
do jogo que passem pelo mesmo lugar). O cache do catálogo (nomes e tipos, para abrir sem internet) fica em
`pokedex_especies.json` na pasta de dados. O catálogo só é pedido à página de dados do jogo sem cache ou com cache
de mais de 1 dia; se o Hunt Analyzer já carregou, ele é reaproveitado.

**Datas:** o jogo não guarda quando cada espécie foi capturada. Na primeira vez que o PokeNexus vê a conta, o que
ela já tem fica "capturado antes de <data>" (sem selo "Novo"). Daí em diante cada espécie nova ganha a data e o
selo "Novo" por 24 h.

## Testes

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 1 | reconhecimento com pasta de sprites e catálogo falsos (forma, Mega, Outland, clone Orre, espécie sem sprite, sprite sem espécie, arquivo que não é sprite) e a chave do jogo em 13 casos | **ok** | `testes/dados_saida.txt` |
| 2 | leitura pelas mensagens: welcome com a Pokédex inteira, estado sem Pokédex (nada muda), `dexMud`, `dexFora` (número ou texto), evento `capturado`, conta trocada (`cheio`), `cheio` sem Pokédex, só as últimas 50 capturas, mensagem que o PokeNexus não usa; o arquivo da conta (1ª vez, captura nova, solto/trocado continua, outra conta do jogo, arquivo quebrado); Todas as contas | **TUDO OK** (nenhum dado de conta real: tudo montado no teste) | `testes/dados_saida.txt` |
| 3 | conta real: o total do PokeNexus × a Pokédex do jogo | **não feito**: precisa da sua autorização (e do seu PokeNexus fechado). Com o inventário contando, o esperado é o PokeNexus ≥ aba do jogo, igual quando a conta não tem pokémon de evolução/troca | |
| 4 | tela: abrir, 385 na lista, Unown fora, total e fichas por região, inventário e Orre do inventário, os 4 filtros, busca por número e por nome (nome de quem falta **não** aparece), sem resultado, só os que faltam, Ctrl+2 com a Pokédex aberta e a conta vazia, Todas as contas e o dono na dica, captura nova (+1, selo Novo, data, gravado no perfil), Ctrl+H, Ctrl+D, Ctrl+M, Ctrl+0, Ctrl+D de volta, botão Jogo, F1 com "Ctrl+D: jogo ou Pokédex", Ajustes mostra e grava Ctrl+D, nenhum widget por pokémon | **38 ok** na janela de verdade; **TUDO OK** offscreen e no Modo Leve | `testes/janela_saida.txt` |
| 4 | prints | as duas propostas, a escolhida em 100% e 125%, normal e Modo Leve, conta vazia e com capturas, topo antes × depois | `prints/` |
| 5 | arquivos proibidos (`workers/farm_worker.py`, `rmt/`, `hunts/calculator.py`, `hunts/measure.py`, `browser/`, `app/config.py`, `main.py`, `config.toml`) | **18 arquivos, 0 diferentes** | `linha_de_base/` × `depois_impressao/` |
| 5 | botões, ligações e atalhos | nenhum botão antigo mudou; ligações antigas iguais (a lista de atalhos ganhou o par do Ctrl+D); atalhos antes + Ctrl+D | idem |
| 5 | o mesmo log | sessão de 40 s com as 4 contas iniciando (sem login), código de antes × depois: **12 linhas iguais**, nenhuma a mais | `testes/log_antes.txt`, `testes/log_depois.txt` |
| 5 | o catálogo de verdade | pelo `main.py`: chegou pela página de dados (sem conta), versão 1.305.9, cache com 385 espécies, nomes certos, Unown fora | |
| 6 | build em `dist_novo` → ZIP → pasta nova, **sem Python no PATH** → Ctrl+D | **ok**: a Pokédex abriu, fechou no X com código 0, nenhum processo sobrou, sem `crash.log`. ZIP 133,07 MB (era 133,0): as imagens novas somam **1.223 bytes** | `prints/build_pokedex.png` |
| — | fechar no X pelo `main.py` depois de usar a Pokédex (rolar, filtrar, buscar, trocar de conta e de modo, fechar e abrir) | **0** nas 8 vezes | `ferramentas/pokedex/fechar_no_x.py` |

## Desempenho (medido, janela de 1920×1001)

| Meta | Medido |
|---|---|
| abrir em menos de 300 ms | **80 a 86 ms** (montar a tela, a lista e pintar a 1ª tela de células) |
| rolar a grade inteira sem travar | 60 passos de 40 px: mediana **7,8 a 10,1 ms**, pior **18,8 a 26,4 ms** (o pior é a 1ª leitura dos sprites daquela faixa; depois vem do cache) |
| trocar de filtro sem reler imagem | **8 a 15 ms**, nenhuma leitura de disco |
| memória a mais com ela aberta abaixo de 25 MB | **+13,1 a 13,2 MB** (com os 385 sprites já lidos e as silhuetas prontas) |
| fechada: CPU e memória iguais | a olhada a cada 2 s custa **0,17 ms** sem mudança e **1,6 ms** com a Pokédex do jogo mudando nas 4 contas (menos de 0,1% de um núcleo). Sessões de 40 s antes × depois: 12,1 a 13,5 s × 13,1 a 14,2 s de CPU e 381 a 390 × 387 a 394 MB, dentro da variação da carga das páginas do jogo |
| farm de 4 contas sem diferença de batalhas/hora | **não medido**: precisa das contas reais |

O catálogo, quando ainda não há cache, vem da página de dados do jogo (a mesma do Hunt Analyzer, um processo à
parte que fecha sozinho depois de 10 min sem uso). Com o cache de menos de 1 dia, ela nem abre.

## Visto nos testes

- **Foco da janela:** os atalhos (Ctrl+1, Ctrl+D…) só chegam com a janela de teste ativa; com outra janela na
  frente, algumas rodadas falharam em cascata (ex.: o Ctrl+1 não chegou, a tela ficou na conta vazia). A rodada
  com a janela ativa deu 38 de 38.
- **Encerramento da ferramenta de teste:** a ferramenta `tela.py` (que não roda o `app.exec()`) às vezes terminou
  com "access violation" depois que o Python já tinha acabado, só nas rodadas com atalhos e o F1. Abrir, rolar,
  filtrar e fechar a Pokédex deu 0 em 6 de 6; o caminho do programa (fechar no X pelo `main.py`) deu 0 em 8 de 8,
  e o executável também. Para o encerramento ficar mais seguro, o modelo da grade tem dono no Qt e as imagens saem
  da memória antes do Qt fechar.
- **125% em 1366×768:** a janela inteira fica mais baixa que a tela (a ficha da direita também), como antes. A
  telinha da esquerda passou a usar o sprite em 1× quando falta altura, para não cobrir o nome.

## Prints

| | Antes | Depois |
|---|---|---|
| Topo 1366×768 | `prints/antes_topo_1366x768.png` | `prints/depois_topo_1366x768.png` |
| Topo 760×600 | `prints/antes_topo_minimo.png` | `prints/depois_topo_minimo.png` (compacto) |
| As duas propostas | `prints/A_*.png` | `prints/B_*.png` |
| A escolhida, 100% | | `prints/final_*.png` (conta com capturas, conta vazia, Todas, Johto só os que faltam) |
| 125% | | `prints/final125_*.png` |
| Modo Leve | | `prints/finalleve_*.png` |
| As células ampliadas 2× | | `prints/final_celulas_2x.png` |
| O executável | | `prints/build_pokedex.png` |

## Pendente (precisa de você)

- Teste 3 com uma conta real (autorização, uma conta só, seu PokeNexus fechado, a conta fora do Opera), só
  olhando: comparar o número do PokeNexus com a Pokédex do jogo.
- O farm de 4 contas com a Pokédex, para comparar batalhas/hora.

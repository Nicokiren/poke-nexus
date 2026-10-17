# Calculadora Gemas ⇄ Dólares no Mercado (16/10/2026)

Uma calculadora dentro do painel **Mercado**, recolhida no cartão do **Saldo** (botão **Calculadora**). Ela
converte Gemas em dólares e dólares em Gemas pela **taxa de referência do usuário: 1.000 Gemas = US$ 9,00**.
Só calcula: não compra, não liga item, não mexe em Gema, USDT, carteira ou Pix, não grava nada e não acessa a
internet. Todos os testes usaram pasta de dados temporária; nenhuma conta real conectou.

## O que foi feito

| Arquivo | O quê |
|---|---|
| `app/conversor_gemas.py` (novo) | a conta, com `Decimal`: `GEMAS_REF = 1000`, `CENTAVOS_REF = 900` (o único lugar da taxa), `gemas_para_dolares`, `dolares_para_gemas` (arredonda para baixo), formato brasileiro, validação do que se digita, fala do mascote. Sem Qt, sem rede, sem disco |
| `app/rmt_ui.py` | `CalculadoraGemas` (cartão `Moldura` "card"), `Balao` (balão de fala em pixel), `_Mascote` (Meowth), `_Numero` (validador); no `RmtPanel`: o botão **Calculadora** no Saldo, o cartão logo abaixo, `set_saldo` no `render` (só lê o saldo que o painel já recebe) e o alvo `calculadora` em `alvos_guia` |
| `app/textos_guia.py` | o passo novo do guia (3º de 11) e `FRASES_MEOWTH` (as falas, num lugar só) |
| `ferramentas/arte/icones.py` + `assets/ui/ico_inverter_*.png` | ícone novo de duas setas, nas 5 variantes (os outros 129 ícones e 17 peças saíram idênticos ao gerar de novo) |
| `ferramentas/calculadora/` | `teste_conta.py` (a conta), `tela.py` (prints, testes da tela, regressão, repintura), `fechar_no_x.py` (fecha pelo X no `main.py`), `teste_build.ps1` (o ZIP, sem Python) |
| `README.md`, `AGENTS.md` | o parágrafo da calculadora; a linha de arquivos e a regra "a taxa é a de referência do usuário, num lugar só" |

**Nada mudou** em `rmt/`, `workers/`, `game/`, `hunts/`, `browser/`, `app/manager.py`, `app/config.py`,
`app/config_edit.py`, `main.py`, `config.toml` (26 arquivos com o mesmo SHA-256 da linha de base em
`linha_de_base/hashes.json`). Nenhuma cor nova no tema e nenhuma chave nova no `config.toml`.

## Escolhas

- **Mascote: Meowth (Nº 52)**, o Pokémon que vive atrás de moedas. O 52 não aparece fixo em nenhum lugar (os
  fixos são 25, 1, 4, 258 e 7; o `52` do `gui.py` é tamanho em pixels). O sprite que existe é
  `assets/sprites/pokemon/52.gif`, e não `.png`: **todos** os sprites do projeto são `.gif`, e é esse o
  formato que o `PixelSprite` usa. Nada foi desenhado nem baixado. Tamanho 56 px: o desenho (47 px) fica em
  1×, sem borrar. Anima como os outros mascotes, pausa com o Mercado escondido ou a janela minimizada e fica
  parado no Modo Leve.
- **Layout: B, recolhida no Saldo** (escolha do usuário entre as duas propostas). Começa fechada; aberta
  ou fechada vale só enquanto o programa está aberto (`RmtPanel._calc_aberta`, na memória). Largura máxima de
  640 px, para os campos não esticarem em tela larga.
- **Inverter:** troca os dois campos de lugar e põe o cursor no da esquerda (a entrada). Os números não mudam
  ao inverter (recalcular a partir de "0,009" daria 0 Gemas).
- **Dólares abaixo de US$ 1:** 3 casas (`US$ 0,009`). Acima, 2 casas, **cortando** (112 Gemas =
  US$ 1,008 aparece `US$ 1,00`), como pede a tabela. A fala do Meowth usa o valor como aparece na tela.
- **"Meu saldo"** apagado sem conta conectada, com a dica "Conecte a conta para usar o saldo dela".
- Os campos têm nome acessível ("Gemas", "Dólares (US$)"): leitores de tela e a automação acham pelo nome.

## Testes

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 1 | a conta (tabela do pedido, tipos `Decimal`, ida e volta em 5.003 valores nunca ganha Gema, entradas válidas e inválidas, falas nas faixas) | **52 ok, 0 falha** | `testes/conta_saida.txt` |
| 2 | a tela: os dois campos, inverter (2×), as 4 fichas, "Meu saldo" com e sem conta, letras, sinal, vírgula, 3 casas, campo vazio, 9 dígitos nos dois campos, roda do mouse nos campos, no inverter e numa ficha (nada muda), balão nas faixas, só `Botao`, cartão `Moldura`, sem emoji, mascote 52, anima/pausa, nada gravado no disco | **44 ok, 0 falha** na janela de verdade; **TUDO OK** offscreen e no Modo Leve (sprite `NotRunning`) | `testes/janela_saida.txt`, `testes/*_teste_*.png` |
| 3 | prints | antes × depois, as duas propostas, a escolhida em 100% e 125%, normal e Modo Leve, o passo do guia, o executável | ver abaixo |
| 4 | regressão do Mercado com a calculadora **aberta e usada** (mesmo roteiro no código de antes e no de depois): adicionar item desligado, editar, ligar (com a confirmação), Parar todas as compras, o guia inteiro, Ctrl+2/3/4/1, Ctrl+M ida e volta, remover | **13 de 13 passos iguais** (textos, dicas, botões ligados, ordem dos cartões e o arquivo da lista); o guia tem os 10 passos antigos iguais + o novo | `regressao/antes_regressao.json`, `regressao/depois_regressao.json` |
| 4 | botões e atalhos da janela | nenhum botão antigo mudou ou sumiu; atalhos e Ajustes iguais; ligações antigas todas iguais (9 novas, só da calculadora) | `linha_de_base/` × `depois_impressao/` |
| 4 | repintura (1920×1001, 200 vezes) | Mercado: mediana 2,96 / 3,01 ms antes × 3,17 / 3,06 ms com a calculadora **aberta**; janela inteira 5,84 / 5,91 × 6,11 / 6,05 ms. Fechada, ela não é desenhada. Nenhum `setStyleSheet` por número digitado nem no `render()` | `regressao/*_repintura.json` |
| 5 | build em `dist_novo` → ZIP (133 MB) → pasta nova, **sem Python no PATH** → Ctrl+M → Calculadora → digitar 1000 → Dólares mostra **9,00** → fechar no X | **ok**: saiu com código 0, nenhum processo sobrou, sem `crash.log` | `build_calculadora.png` |
| — | fechar no X pelo `main.py` (Mercado + calculadora usada), 4 vezes antes e 4 depois | **0** nas 8 | `ferramentas/calculadora/fechar_no_x.py` |

**Contraste (WCAG):** texto do balão `#2B1608` sobre `#F6E9DC` = 14,4:1; linha da taxa 13,9:1; números nos
campos 14,8:1; "Valor de referência" 8,0:1. Nenhum par novo no tema (só cores que já existiam).

**Visto nos testes, sem mudar:** em 1366×768 o 1º item da lista **já** ficava 2 px cortado antes (com o convite
"Primeira vez aqui?" aberto). Com a calculadora fechada isso continua igual; aberta, a lista desce 220 px e é
preciso rolar (como a proposta B dizia). Em 125% o "Todas as contas" do topo aparece cortado nos dois códigos
(não é da calculadora).

**Encerramento forçado:** as ferramentas de teste antigas saíam com `os._exit(0)`. Com a calculadora montada,
isso dava às vezes "access violation" na saída. Isolando: acontece com qualquer botão ligado a uma função,
dentro de um cartão do app, mesmo **sem** a calculadora, então é do PySide6 ao matar o processo sem
terminar o Python. O caminho do programa (fechar no X, `sys.exit`) saiu limpo em todas as vezes (fonte e
executável). As ferramentas novas saem pelo X.

## Prints (antes × depois)

| | 1366×768 | 1920×1080 |
|---|---|---|
| Antes | `antes_1366x768.png` | `antes_1920x1080.png` |
| Proposta A (ao lado do Saldo) | `A_1366x768.png` | `A_1920x1080.png` |
| **Escolhida (B), fechada** | `B_1366x768_fechada.png` | `B_1920x1080_fechada.png` |
| **Escolhida (B), aberta** | `B_1366x768.png` | `B_1920x1080.png` |
| B em 125% | `B125_1366x768*.png` | `B125_1920x1080*.png` |
| B no Modo Leve | `Bleve_1366x768*.png` | `Bleve_1920x1080*.png` |
| A calculadora ampliada 2× | `B_1366x768_calc_2x.png` | |
| Passo do guia | `guia_calculadora.png` | |
| No executável | | `build_calculadora.png` |

## O valor da Gema no jogo

O jogo manda um preço da Gema em `welcome.economia`, que só chega com a conta **conectada**. Sem autorização
para conectar uma conta real, ele **não foi lido** nesta tarefa. A calculadora não usa esse valor.

## Como trocar

- **A taxa:** `app/conversor_gemas.py`, `GEMAS_REF` e `CENTAVOS_REF` (o resto do programa lê dali; o
  rodapé "1.000 Gemas = US$ 9,00" e o texto do guia acompanham, menos a frase do guia, que tem o número
  escrito e precisa ser trocada à mão em `app/textos_guia.py`). Depois, rode `ferramentas/calculadora/teste_conta.py`
  (os casos da tabela vão falhar de propósito: atualize os valores esperados).
- **As falas do Meowth:** `app/textos_guia.py`, `FRASES_MEOWTH` (até quantos US$, frase).

Nada foi enviado ao GitHub (um push na `main` publica atualização para todos).

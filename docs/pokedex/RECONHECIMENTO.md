# Pokédex do PokeNexus: reconhecimento (Fase 1, 17/10/2026)

Lido do PokeIdle **1.305.9** no ar, só pelos arquivos públicos (`app.js`, `assets/creatures*.json`,
`shared/pokedex.mjs`, `shared/estado-delta.mjs`, `shared/outland.mjs`, `shared/escala-hunt-level.mjs`,
`shared/sprite-jogo.mjs`). Nenhuma conta foi aberta.

## 1. Sprites que o PokeNexus tem

`assets/sprites/pokemon/`: **385 arquivos `.gif`**, todos com nome de número, de `1.gif` a `386.gif`.
**Buraco: só o 201 (Unown).** Nenhum arquivo que não seja de espécie, nenhum acima de 386, nenhuma pasta.

## 2. Espécies que o PokeIdle tem (catálogo da versão no ar)

Os três catálogos (`creatures.json` 486, `creatures-novos.json` 730, `creatures-outland-novos.json` 11)
somam 1.227 entradas. O `pokeId` **é o número da Pokédex nacional** de 1 a 1025. O resto são faixas próprias:

| Faixa do `pokeId` | O que é | Quantas | Na Pokédex do jogo |
|---|---|---|---|
| 1 a 1025 | espécie nacional | 1.029 (4 são formas nacionais acima de 1000) | chave = o próprio número |
| 13xxx | clones "Orre" (ex.: 13252 Treecko) | 132 | **contam como a espécie base** (`dexDe`: 13252 → 252) |
| 14xxx | 6 Megas antigas + Castform Fire (ex.: 14009 Mega Blastoise) | 7 | a conta do jogo também dá a base (14009 → 9) |
| 2001 a 2058 | Outland (ex.: 2050 Furious Scizor) | 58 | entrada própria (#2001…), aba "Outland" |
| 3001 a 3999 | Megas (`3000 + dex`, montadas pelo `shared/megas.mjs`) | geradas no boot | entrada **própria** (aba "Mega") |
| 4000 a 12999 | Formas (Alola, Galar, Hisui, Paldea, Rotom…) | geradas no boot | entrada **própria** (aba "Formas") |
| 10001 | "espelho fantasma" (Blastoise) | 1 | o jogo não lista |

**De 1 a 386:** o jogo tem as 386, todas com arte (`looktype` > 1). Nenhum número repetido, nenhum nome
diferente para o mesmo número.

## 3. A Pokédex do jogo

- **Formato:** `estado.pokedex` = `{ "<chave>": { k, c, sv?, sc? } }`. **`k` = derrotas** (o "visto"),
  **`c` = capturas**, `sv`/`sc` = shiny vistos/capturados (só aparecem acima de zero). A chave é
  `chavePokedex(pokeId)` (`shared/pokedex.mjs`): o número nacional, ou o #2001… do Outland.
- **Capturado = `c > 0`.** É o mesmo critério da tela da Pokédex do jogo (`contagemEspeciesDexPerfil`,
  `contagemPokedexPorGeracao`: o "90/151" de cada aba). O jogo **separa** visto de capturado.
- **Como chega:** inteira no `welcome` (`estado.pokedex`, com `cheio`). Depois, por diferença no `estado`:
  `dexMud` = `{chave: entrada}` (entra ou troca) e `dexFora` = `[chave]` (sai). É a mesma regra do
  `shared/estado-delta.mjs` que o jogo usa. O `dexMud` chega a cada derrota (o `k` sobe), e hoje o
  PokeNexus já lê essas mensagens e só joga esses campos fora (`_IGNORAR` em `game/pokeidle.py`).
- **Reforços:** a coleção da conta (`pokemons[].speciesId`) e o evento de batalha `capturado`, que traz
  `pokemon.speciesId` na hora. Os dois passam por `chavePokedex` (13xxx vira a base).

## 4. A lista final

**Sprites ∩ espécies do jogo, só a espécie base de 1 a 386: 385 pokémon.**

| Região | Na Pokédex do PokeNexus | No jogo |
|---|---|---|
| Kanto (1 a 151) | **151** | 151 |
| Johto (152 a 251) | **99** | 100 |
| Hoenn (252 a 386) | **135** | 135 |
| **Total** | **385** | 386 |

- **Do jogo, sem sprite no PokeNexus (fica de fora):** **#201 Unown**. Também ficam de fora as 643
  espécies nacionais acima de 386 (o PokeNexus só tem sprite até 386), o Outland, as Megas e as Formas.
- **Sprite sem espécie no jogo:** nenhum.
- **Casos estranhos:**
  1. As **Megas e Formas** têm entrada própria na Pokédex do jogo (#3xxx e #4000+), em abas separadas, e
     **não** contam na aba de Kanto/Johto/Hoenn do jogo. Se o PokeNexus contar a Mega como a espécie base,
     o número dele pode passar o da aba do jogo. Ver a pergunta abaixo.
  2. Os 7 "14xxx" (6 Megas antigas e Castform Fire) caem na base pela conta do próprio jogo (14009 → 9).
     Eles seguem a regra do jogo.
  3. O Johto do PokeNexus tem 99 e o do jogo tem 100 (o Unown). Uma conta com o Unown capturado vê
     1 a menos em Johto no PokeNexus.

A lista **não fica fixa no código**: ela é montada na hora com os `.gif` da pasta e o catálogo da versão no
ar (o mesmo que o Hunt Analyzer já carrega, `hunts/game_data.py`), com uma cópia em cache para abrir sem
internet. Uma espécie nova do jogo que já tenha sprite aparece sozinha.

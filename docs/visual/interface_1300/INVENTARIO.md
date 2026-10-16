# Inventário da interface depois do PokeIdle 1.300.2 (Fases 1 e 2)

Medido em 16/10/2026 com o PokeNexus de verdade (a mesma janela e as mesmas páginas), pasta de dados
temporária, sem login e sem tocar nenhuma conta. Ferramentas em `ferramentas/interface/`:

- `vistoria.py`: abre a janela, aplica cada cenário (tamanho, escala simulada com `QT_SCALE_FACTOR`, Modo
  Leve com e sem placa, visão, ficha, Registro, zoom, área, diálogos), tira o print e mede a página do jogo
  em px CSS. Medidas em `inventario/bruto/<rodada>/medidas.json`.
- `mercado_teste.py`: o Market do jogo (Comprar, Pokébolas) montado com o HTML do `app.js` 1.300.2 e o
  `estilo.css`/`mobile.css` **reais** do jogo, baixados do site. Serve para ver o Market sem login.
- `navegador_comum.py`: a mesma página do Market no Microsoft Edge comum, sem nada do PokeNexus.

Rodadas: `e100_leve` (100%, Modo Leve com placa, o caso do usuário), `e100_normal`, `e100_leve_semgpu`,
`e125_leve`, `e150_leve`, `tela1366_*` (tela de 1366×768 simulada) e `h3_jogo` (a página real do jogo).

## Telas do jogo que precisam de login (NÃO vistas)

Market real (Comprar e Vender, todas as categorias), Mochila, Mapa, Centro, modais de configuração do jogo
e o layout de celular do jogo com modais abertos. Só com a autorização do usuário (ver "Pendentes" no
RELATORIO). Suspeitos de ter o mesmo defeito do I-01, pelo CSS 1.300.2: o Market → Vender/Depot
(`.caixa-depot`, altura fixa `min(88vh, 680px)` desde 15/10/2026), a Pokédex (`height: min(88vh, 860px)`) e os
modais "quadrados" (Mochila, Loja, Casa, Comunidade: `min(88vh, 94vw, 880px)`).

---

```
ID: I-01
Onde: visão individual > Jogo > Market > Comprar > Pokébolas (e Poções: as duas categorias de 2 linhas)
Condição: 1920×1080, escala 100%, zoom 100%, ficha aberta ou fechada, normal ou Modo Leve (o caso do
          usuário). Também em 1366×768 e 1600×900 a 100%, e em TODAS as telas testadas a 125% e 150%.
O que acontece: a linha − 1 + aparece, mas os atalhos ×10/×100/Máx e o botão "Comprar" de cada cartão
          ficam de fora; as duas linhas de cartões são espremidas (226 px de 311 px).
Esperado: cartão inteiro visível (ou rolagem que chegue nele)
Gravidade: Alta (impede comprar no Market do jogo)
Print: inventario/I-01_antes_1920_e100.png, I-01_antes_1920_e125.png, I-01_antes_1366_e100.png
Origem: B + C (ver abaixo)
```

**Causa (com prova).** Na 1.300 o próprio jogo deu ao modal do Market uma **altura fixa**
(`estilo.css`: `html:not(.mobile) .modal-caixa[data-modal="market"] { height: min(88vh, 864px) }`,
comentário "ALTURA FIXA (pedido de 15/10/2026)"), e quem deveria rolar é a grade dos cartões. Só que cada
cartão (`.mk-pal`) tem `overflow: hidden`; com isso o Chromium deixa a linha da grade encolher até caber na
caixa em vez de rolar. Medido na página de teste (mesmo CSS): grade de 533 px, `scrollHeight` = 533
(**não rola**), linhas de `226px 226px`, cartão com 311 px de conteúdo, botão 84 px abaixo do fim do cartão.

O corte depende só da **altura da página em px CSS** (`innerHeight`). A caixa é 88% dela, até 864 px:

| Onde | Página (px CSS) | Modal | Cartões sem botão |
|---|---|---|---|
| PokeNexus 1920×1080, 100%, zoom 100% (ficha aberta ou fechada) | 1531×763 / 1856×763 | 671 | 6 de 6 |
| PokeNexus 1920×1080, 100%, com Registro aberto | 1531×528 | 465 | 6 de 6 |
| PokeNexus 1600×900, 100% | 1211×583 | 513 | 6 de 6 |
| PokeNexus 1366×768, 100% | 977×451 | 397 | 6 de 6 |
| PokeNexus 2560×1440, 100% | 2171×1123 | 864 | 0 |
| PokeNexus 1920×1080, 125% | 1147×544 | 479 | 6 de 6 |
| PokeNexus 2560×1440, 125% | 1659×832 | 732 | 6 de 6 |
| PokeNexus 1920×1080, 150% | 891×400 | 352 | 6 de 6 |
| PokeNexus 1920×1080, 100%, zoom 80% | 1913×953 | 839 | 0 |
| PokeNexus 1920×1080, 150%, zoom 50% (o menor) | 1782×800 | 704 | 6 de 6 |
| PokeNexus janela mínima / 1366×768 a 125% (página ≤ 720 px de largura) | 696×360 | (layout de celular) | 0 |
| **Edge comum**, página 1531×763 | 1531×763 | 671 | 6 de 6 |
| **Edge comum**, página 1896×908 (Edge maximizado em 1080p, aprox.) | 1896×908 | 799 | 6 de 6 |
| **Edge comum**, página 1896×948 | 1896×948 | 834 | 6 de 6 |
| **Edge comum**, página 1896×968 | 1896×968 | 852 | 0 |

Prints do Edge: `inventario/I-01_prova_edge_1531x763.png`, `I-01_prova_edge_1896x908.png`.

- **B (do jogo):** num navegador comum, sem nada do PokeNexus, o corte acontece igual em qualquer página
  com menos de ~960 px CSS de altura (inclusive um Edge maximizado num monitor 1080p).
- **C (da combinação):** o PokeNexus dá à página menos altura do que um navegador (topo, abas e barra do
  jogo: em 1920×1080 a página tem 763 px CSS), então lá o corte acontece sempre. Para caber, o jogo pede
  ~982 px CSS (864 / 0,88). Em 1920×1080 a 100% isso é zoom ≤ 77%; a 125%, ≤ 55%; em 1366×768, ≤ 46%; a
  150%, ≤ 41% (abaixo do mínimo de 50% do botão −).

```
ID: I-02
Onde: Todas as contas > Grade > Jogo > Market > Comprar
Condição: 1920×1080, 100% (zoom automático 49%: página 1544×704); igual em 1366×768 e na janela mínima
O que acontece: o mesmo corte do I-01 em todos os quadros
Esperado: cartão inteiro
Gravidade: Média (na grade o jogo já fica pequeno; quem compra abre a conta sozinha)
Print: inventario/I-02_antes_grade_1920.png
Origem: B + C (a grade encaixa a página em 1280×720 px CSS, e o Market pede ~982 de altura).
        No "Celulares" não corta (é o layout de celular do jogo, que rola).
```

```
ID: I-03
Onde: Ajustes (Ctrl+,)
Condição: tela de 1366×768 a 100% (simulada) e 1920×1080 a 150%
O que acontece: a janela abre com 880×780 fixos; a moldura dela (776 / 728 px) passa da área útil da
          tela (734 / 688 px) e a fileira de baixo, com Cancelar e Salvar, fica atrás da barra de tarefas
Esperado: a janela inteira dentro da tela (o conteúdo já rola por dentro)
Gravidade: Média (atrapalha salvar os ajustes)
Print: inventario/I-03_antes_ajustes_1366.png (medidas em bruto/tela1366_e1.40625/medidas.json)
Origem: A (app/settings_ui.py: `self.resize(880, 780)` sem olhar a tela). Não é da 1.300.
```

```
ID: I-04
Onde: barra em cima do jogo (título, selo, Jogo, Hunts, Mercado, Grade, Celulares)
Condição: janela estreita: ~1000 px lógicos ou menos (1366×768 a 150%, janela no mínimo de 760 px)
O que acontece: o texto dos botões e do título é cortado ("Jo", "Hu", "Mer", "Gr", "Toda", selo "Pa")
Esperado: botões legíveis (o ícone e a dica no mouse continuam)
Gravidade: Baixa (os botões funcionam; só em janela estreita)
Print: inventario/I-04_antes_barra_estreita.png, I-07_antes_minimo.png
Origem: A (gui.py, GameArea: a janela tem mínimo fixo 760×600, então o Qt espreme os botões abaixo do
        tamanho do texto). Não é da 1.300.
```

```
ID: I-05
Onde: topo (contador "0/4 conectadas", "Começar tudo") e aba "Todas as contas"
Condição: largura de ~1100 px lógicos ou menos (1366×768 a 125% e 150%, janela mínima)
O que acontece: "0/4 conectada", "Começar tud"; na aba, "Todas as con" encostado no "Ctrl+0"
Esperado: texto inteiro
Gravidade: Baixa
Print: inventario/I-05_antes_aba_todas.png, I-04_antes_barra_estreita.png
Origem: A. Não é da 1.300.
```

```
ID: I-06
Onde: Hunts > "Ordenar por"
Condição: janela mínima (760 px)
O que acontece: texto dos botões cortado ("P/I", "iro", "ates", "isc")
Gravidade: Baixa
Print: inventario/I-06_antes_hunts_760.png
Origem: A. Não é da 1.300.
```

```
ID: I-07
Onde: janela inteira no tamanho mínimo
Condição: 760×600; e 1366×768 a 125% (a área útil tem 566 px e o mínimo da janela é 600)
O que acontece: o topo e as abas quebram em duas linhas e a borda de baixo da área do jogo some atrás do
          rodapé; a 125% a janela fica maior que a tela
Gravidade: Baixa
Print: inventario/I-07_antes_minimo.png
Origem: A. Não é da 1.300.
```

```
ID: I-08 (achado com a Conta 4, autorizada)
Onde: Jogo > Ginásios
Condição: 1920×1080, 100%, zoom 100%
O que acontece: os 18 cartões ficam espremidos (201 px de 241 px de conteúdo); o rótulo de ação do pé de
          cada cartão fica de fora. O cartão inteiro continua clicável.
Gravidade: Média
Print: conta4/e100_1920/10_ginasios.png
Origem: B + C (mesmo jeito do I-01: `.gin-card` com `overflow: hidden` numa caixa de altura fixa)
```

## Situação (Fase 4)

| ID | Situação | Arquivo |
|---|---|---|
| I-01 | **Resolvido** (zoom só com o Market aberto; provado com o Market real da Conta 4) | `app/gui.py`: `CellsHost.MARKET_CSS_H`, `_com_market`, `zoom_individual`, `relayout`; `GameArea._olhar_market`, `_market`, `_mostrar_zoom`, `change_zoom`, `add_view`, `remove_view` |
| I-02 | **Resolvido em 1920×1080 a 100%**; em quadros pequenos (1366×768, janela mínima, 125%/150%) nem o zoom mínimo do Qt (25%) basta | `app/gui.py` (a mesma regra em `relayout`) |
| I-03 | **Resolvido** | `app/settings_ui.py` (`SettingsDialog.__init__`, tamanho inicial) |
| I-04 | **Resolvido para os botões**; o título longo da Grade e o selo ainda cortam numa janela bem estreita | `app/gui.py` (`GameArea._ajustar_barra`, `resizeEvent`, `update_info`) |
| I-05, I-06, I-07 | Pendentes (Baixa), ver RELATORIO | |
| I-08 | Pendente (decisão do usuário) | |

## Hipóteses do Market (Fase 2)

| | Resultado | Prova |
|---|---|---|
| H1 (cartões mais altos + modal limitado, sem rolagem) | **Confirmada, com um ajuste**: o que mudou na 1.300 foi a **altura fixa** do modal (15/10/2026); a grade deveria rolar, mas as linhas encolhem porque o cartão tem `overflow: hidden` | grade 533 px, `scrollHeight` 533, linhas 226 px, cartão 311 px |
| H2 (escala do Windows piora) | **Confirmada** | 1920×1080: 763 px CSS a 100%, 544 a 125%, 400 a 150% |
| H3 (conta escondida não recalcula) | **Descartada** | página real 1.300.2: escondida = celular; mostrada = 1531×763 e `mobile` sai sozinho (também ao voltar do Celulares) |
| H4 (Modo Leve muda o layout) | **Descartada** | normal, Leve com placa e Leve sem placa: os mesmos px CSS e o mesmo corte em todos os cenários |
| H5 (é do jogo) | **Confirmada (tipo B)**, e o PokeNexus piora (tipo C) | Edge comum corta até 948 px CSS de altura e não corta a partir de 968 |

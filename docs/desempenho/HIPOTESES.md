# Modo Leve 2.0: hipóteses

Escritas antes de mudar o código (15/10/2026). Cada uma diz o que a confirmaria ou derrubaria; o
**resultado** é preenchido com o número medido (ferramenta em `ferramentas/desempenho/`, dados brutos em
`docs/desempenho/dados/`).

Perfis: P1 forte (RTX 5070, sem limite), P2 sem GPU (Chromium `--disable-gpu` e Qt pelo adaptador de
software do Windows, WARP), P3 fraco (P2 + 2 núcleos lógicos). Cenários: C1 uma conta na tela, C2 Todas
em grade, C3 Todas em celulares, C4 minimizada.

## O que já se sabia antes de medir

- O Qt WebEngine 6.12 roda o trabalho de GPU do Chromium **dentro do processo do PokeNexus** (não existe
  processo de GPU separado: só o principal e um renderer por conta).
- A cena do jogo (`campo.mjs`, jogo 1.295) redesenha o canvas **inteiro a cada requestAnimationFrame**, e
  o canvas tem a resolução do palco em **px CSS** (`cv.width = clientWidth`), não a da tela. O jogo só usa
  canvas **2D** (nenhum `getContext('webgl')` nos 111 arquivos do jogo).
- Cada página mostra o que desenhou pelo widget interno do QWebEngineView (um QQuickWidget); a
  ferramenta conta as pinturas desse widget: é o quadro que de fato aparece na tela.

## H1. `--disable-gpu` é a principal causa de o Leve parecer travado nos PCs com GPU

- Confirma: no P1, o Leve atual com menos quadros/s, p95 de quadro maior ou entrada mais lenta que o
  normal; e o mesmo Leve **sem** `--disable-gpu` igual ou melhor que o normal.
- Derruba: Leve atual igual ao normal em quadros e entrada no P1.
- Primeiro sinal (teste curto, 15 s, P1): C1 normal 60,7 q/s e entrada p95 48 ms × Leve 45,0 q/s e
  88 ms, com **mais** CPU (6,1% × 2,9%).
- Resultado: _pendente da linha de base_.

## H2. Sem GPU, forçar `--disable-gpu` não ajuda em nada

- No PC sem GPU (ou com driver na lista de bloqueio), o próprio Chromium desenha por software. O flag só
  muda alguma coisa onde existe GPU, e lá ele piora (H1).
- Confirma: P2/P3 com e sem o flag iguais (no P2/P3 o flag já faz parte da simulação, então o Leve
  atual e o "Leve sem o flag" ficam idênticos por construção); e a GPU estando disponível, H1.
- Resultado: _pendente_.

## H3. As páginas escondidas (C1) ainda desenham sem ninguém ver

- Confirma: CPU dos renderers das 3 contas escondidas parecida com a da visível.
- Derruba: CPU das escondidas perto de zero (o Qt já esconde o widget, o Chromium marca a página como
  "hidden" e para o requestAnimationFrame; os timers e o WebSocket seguem pelos flags de segundo plano).
- Primeiro sinal: normal P1 C1 2,9% de CPU com 1 página visível × C3 8,6% com 4 visíveis.
- Resultado: _pendente_.

## H4. Menos pixels por página reduz o custo de desenho quase na mesma proporção

- No C2 (grade) o zoom fica em ~0,59 para a página ter 1280×720 px CSS: o canvas do jogo desenha ~2,9×
  os pixels que aparecem. No C3 (celulares) o zoom já é ~1 (412 px CSS ≈ largura do quadro).
- Confirma: no C2, subir o zoom (menos px CSS) baixa a CPU por software quase na proporção da área.
- Resultado: _pendente_.

## H5. A interface do PokeNexus pesa pouco perto das páginas do jogo

- Confirma: folga da thread da tela e repintura pequenas nos dois modos; diferença de CPU do processo
  principal entre normal e Leve explicada pelo desenho das páginas (que roda no mesmo processo), não pelas
  molduras e mascotes.
- Resultado: _pendente_.

## H6. A memória das páginas cresce com as horas; um teto menor no Leve segura o pico

- Só dá para ver com contas reais em horas de farm. Confirma: memória por página subindo ao longo da
  rodada real e voltando ao reabrir, sem perder batalhas.
- Resultado: _pendente das contas reais_.

## H7 (nova, achada na Fase 0). Sem GPU, o Qt gasta mais emulando a placa (WARP) do que desenhando por software

- Com `--disable-gpu`, o Chromium entrega cada quadro pronto como imagem; o Qt então sobe essa imagem
  para uma "placa" emulada pela CPU (WARP) e compõe a janela por ela.
- Primeiro sinal (sonda, 4 páginas de carga, 8 núcleos): WARP 3,37 núcleos e 90 pinturas/s ×
  `QT_QUICK_BACKEND=software` 1,66 núcleos e 105 pinturas/s, imagem igual.
- Resultado: _pendente_.

## Resultado (versão enxuta, 15/10/2026)

O usuário pediu para parar os testes longos e lançar. Medido: 1 rodada completa da linha de base (P1, P2 e
P3, C1 a C4, 3 min por cenário) e uma conferência do Leve 2.0 (P1 e P3, C1 e C3, 1 min por cenário),
sempre com a página de carga e sem contas reais. **Cada número abaixo é de UMA rodada** (não houve as 3
rodadas pedidas no protocolo).

| Perfil | Cenário | Modo | Quadros/s | Quadro p95 (ms) | Tecla→tela p95 (ms) | CPU média |
|---|---|---|---|---|---|---|
| P1 | C1 | normal | 60,0 | 21,6 | 48 | 3,4% |
| P1 | C1 | Leve antigo | 38,8 | 33,4 | 112 | 6,9% |
| P1 | C1 | Leve 2.0 | 60,2 | 21,8 | 32 | 2,6% |
| P1 | C3 | normal | 240,0 | 18,0 | 32 | 9,8% |
| P1 | C3 | Leve antigo | 240,1 | 23,6 | 56 | 12,7% |
| P1 | C3 | Leve 2.0 | 240,1 | 17,8 | 48 | 9,1% |
| P3 | C1 | normal | 24,5 | 49,7 | 192 | 9,3% |
| P3 | C1 | Leve antigo | 29,7 | 41,4 | 144 | 10,1% |
| P3 | C1 | Leve 2.0 | 38,1 | 33,4 | 128 | 6,3% |
| P3 | C3 | normal | 105,8 | 66,8 | 472 | 11,3% |
| P3 | C3 | Leve antigo | 97,8 | 113,1 | 512 | 11,3% |
| P3 | C3 | Leve 2.0 | 189,4 | 38,2 | 120 | 11,1% |

(No P3 a CPU fica perto do teto de 2 núcleos, ~12,5% deste PC; o ganho aparece em quadros e resposta.)

- **H1 confirmada:** no P1 o Leve antigo perdia 35% dos quadros numa conta e respondia 2,3× mais devagar,
  gastando mais CPU. Sem `--disable-gpu`, o Leve 2.0 empata com o normal e gasta um pouco menos.
- **H2:** sem placa o próprio Chromium já desenha por software; o flag só servia para piorar onde há placa.
- **H7 confirmada:** sem placa, `QT_QUICK_BACKEND=software` dá ao P3 +56% de quadros numa conta e +79%
  em celulares, com a resposta caindo de 472 para 120 ms.
- **H3:** C4 (minimizada) e as contas escondidas quase não gastam CPU (C4: 0,16%); o Qt já esconde.
- **H4, H5, H6 e o critério de RAM −30%:** não medidos (o Leve 2.0 com placa usa a mesma memória do
  normal: a economia de RAM do Leve antigo vinha justamente de desligar a placa, que travava o jogo).
- **Não testado:** contas reais (farm), P2 com o Leve 2.0, P4, Modo Economia do jogo.
- **Como desfazer:** desligar o Modo Leve nas Ajustes (o normal não mudou).
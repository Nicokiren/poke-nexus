# V1 — Pranchas das três direções

Prints: [A — Base do Treinador](v1/prancha_A.png), [B — Rota Noturna](v1/prancha_B.png),
[C — Caderno de Campo](v1/prancha_C.png). A página é `v1/prancha.html?tema=A` (ou `B`, `C`); abre em
qualquer navegador.

Cada prancha mostra a tela principal com o jogo no meio, as fichas das 4 contas, a ficha do treinador,
a paleta, os estados dos botões, os 8 status com ícone, os ícones de ação e um diálogo no lugar do aviso
do Windows. **Nada no app foi mudado ainda.**

## Arte

Toda a arte das pranchas é original, desenhada pixel a pixel no próprio código da página:
- 13 ícones de ação e 8 de status (10×10);
- 4 mascotes provisórios (16×16): Broto, Brasa, Gota e Pedrisco.
Nenhuma imagem da franquia, a não ser a tela do jogo (que é do PokeIdle).

## Fonte

Testadas em 12–32 px ([v1/fontes.png](v1/fontes.png)): Pixelify Sans, Silkscreen, Jersey 10, Tiny5,
Press Start 2P e VT323.
- **Escolhida: Jersey 10** (OFL) para títulos, números e botões. É a que lê melhor: "Conta 2", "312" e
  "36.341" sem confusão, acentos certos. Só nos tamanhos da grade dela: 20, 30 e 40 px, peso único.
- Pixelify Sans foi descartada: em tamanho pequeno o "C" parece "O" e o "2" parece "8".
- Textos corridos: Nunito (OFL).

## Textos novos sugeridos nas pranchas (para aprovar)

| Hoje | Na prancha |
|---|---|
| Dashboard e log | Registro |
| Configurações | Ajustes |
| RMT | Mercado |
| Iniciar todas / Parar todas | Começar tudo / Parar tudo |
| CONTA SELECIONADA | Ficha do treinador |
| Assumir controle | Jogar eu mesmo |
| VER TODAS | Todas as contas |

Só o texto muda: cada botão continua fazendo exatamente o que faz hoje.

## Observações

- Na C (tema claro) a tela azul do jogo fica bem "solta" no papel, como o prompt previa.
- Na B o conjunto fica perto do visual de hoje (azul + amarelo); a moldura de pixel ajuda, mas a A é a
  que mais combina com as molduras de madeira do jogo.

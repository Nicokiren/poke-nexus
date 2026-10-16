# Texto para avisar o PokeIdle (opcional, para o usuário mandar se quiser)

> **Market (1.300.2): botão "Comprar" some em telas mais baixas**
>
> Desde a altura fixa do Market (15/10), com a página do navegador abaixo de ~960 px de altura (ex.: Chrome
> ou Edge maximizado num monitor 1920×1080, ou qualquer notebook), as Pokébolas e as Poções aparecem com os
> cartões espremidos: a linha − 1 + aparece, mas os atalhos ×10/×100/Máx e o botão Comprar ficam escondidos.
> A grade não rola porque o `.mk-pal` tem `overflow: hidden`, e aí o navegador encolhe as linhas da grade em
> vez de deixar rolar.
>
> Testado só numa cópia de teste: com esta regra a grade rola e os cartões ficam inteiros, até com 544 px
> de altura:
>
> ```css
> html:not(.mobile) #mk-corpo .mk-grade { grid-auto-rows: max-content; }
> ```
>
> Os Ginásios têm o mesmo jeito (`.gin-card` com `overflow: hidden` dentro de uma caixa de altura fixa): o
> rodapé de cada cartão fica de fora.

Prova: `inventario/I-01_prova_edge_1896x908.png` (Edge comum, sem o PokeNexus) e
`inventario/I-01_sugestao_jogo_edge_1531x763.png` (a mesma página com a regra acima).

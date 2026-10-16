# Plano de correção (Fase 3)

Decisão do usuário (16/10/2026) para o I-01/I-02, que é do próprio jogo (tipo B + C): **zoom automático só
com o Market do jogo aberto**. Autorizou também usar a **Conta 4** para ver as telas com login (só abrir,
rolar e fechar; PokeNexus dele fechado; sem automação; Mercado RMT não roda porque nenhum worker é iniciado).

| ID | Arquivo(s) | O que muda | Por que não muda funcionalidade | Como provar |
|---|---|---|---|---|
| I-01 | `app/gui.py` (`CellsHost`, `GameArea`) | A cada 0,8 s a área do jogo **lê** em cada página visível (visão individual e Grade; o Celulares já usa o layout de celular do jogo, que rola) se o modal do Market está aberto (`#modal` sem `hidden` e `data-modal="market"`, página fora do layout de celular). Enquanto estiver, o zoom daquela página fica em `min(zoom escolhido, altura do quadro / 982)`; 982 px CSS é a altura em que o próprio jogo desenha o Market inteiro (864 = 88% de 982). Fechou o Market: volta ao zoom de antes. O rótulo do zoom mostra o zoom em uso e a dica diz por quê. | Só leitura da página (`runJavaScript` que devolve true/false, sem mudar nada); nenhum clique, nenhum CSS/JS do jogo mudado. Não mexe em `workers/`, `game/`, `rmt/`, no farm, no config nem no zoom salvo; − / + continuam iguais (com o Market aberto vale o menor dos dois, então um zoom menor escolhido pela pessoa é respeitado). | Prints antes × depois com a página de teste (1366×768, 1920×1080, 2560×1440; 100/125/150%; ficha aberta e fechada; normal e Leve) e com o Market **real** da Conta 4; medida `cortados = 0`; zoom volta ao fechar. |
| I-02 | `app/gui.py` (o mesmo código) | A mesma regra nos quadros da Grade. | Igual ao I-01. | Print da grade com o Market aberto. |
| I-03 | `app/settings_ui.py` | A janela de Ajustes abre com 880×780 **ou menos**, se a área útil da tela for menor (o conteúdo já rola por dentro). | Só o tamanho inicial da janela. | `frameGeometry` dentro de `availableGeometry` em 1366×768 a 100% e 1080p a 150%; print. |
| I-04 | `app/gui.py` (`GameArea`) | Em janela estreita (quando a barra não cabe), os botões Jogo/Hunts/Mercado/Grade/Celulares mostram só o ícone (a dica no mouse continua com o texto). | Os mesmos botões, os mesmos métodos; só o texto visível. | Prints a 760 px e 1366×768 a 150%; impressão digital (`ligacoes.json`, `widgets.json`). |
| I-05, I-06, I-07 | `app/gui.py`, `app/hunt_ui.py` | Ver no INVENTARIO depois da Fase 4: só corrijo se a mudança for pequena e não mudar a aparência na tela normal (1920×1080). | Só texto/tamanho. | Prints. |

Restrições respeitadas: nenhuma cor fixa fora de `tema.py`; nenhum botão ou painel novo; nada de
`setStyleSheet` em `refresh()`; a área do jogo não encolhe (o quadro do jogo tem o mesmo tamanho; só o zoom
muda enquanto o Market está aberto); nada no Ajustes nem no `config.toml`.

# PokeNexus — instruções para agentes de IA

Leia isto antes de mexer no projeto. Detalhes de uso estão no `README.md`.

## Idioma

Fale **sempre em português (pt-BR)** com o usuário, inclusive nas mensagens curtas de andamento. O
código, os comentários e os nomes já são em português: mantenha.

## O que é

App desktop para Windows (Python 3.11+, PySide6/Qt WebEngine) que roda até **4 contas** do PokeIdle
(https://pokeidle.io/app) ao mesmo tempo, com o jogo de cada conta embutido na janela.

- `main.py` — entrada. `browser/web_host.py` — uma página Qt WebEngine com perfil próprio por conta.
- `browser/cdp.py` — cliente DevTools de cada página. O app escuta o WebSocket do jogo
  (`game/pokeidle.py`) e o farm **age pelo DOM**, clicando nos botões do próprio jogo. **Exceção, por
  escolha do usuário (16/10/2026): o Mercado** (`rmt/canal.py`) manda pela conexão do jogo os mesmos
  pedidos que o botão manda (`market.item`, `market.comprar`), sem abrir tela: antes cada olhada abria e
  fechava o mercado por cima do jogo e a tela piscava. Um pedido por anúncio, sem rajada.
- `app/manager.py` + `workers/` — loop asyncio numa thread; uma tarefa por conta; vigias de travamento e
  de memória.
- Interface: `app/gui.py` (janela, VER TODAS em grade ou "celulares", painel da conta recolhível),
  `app/widgets.py`, `app/hunt_ui.py` (Hunt Analyzer), `app/rmt_ui.py` + `rmt/` (RMT/Mercado),
  `app/settings_ui.py` + `app/config_edit.py` (Configurações; grava o `config.toml` mantendo os
  comentários).
- `hunts/` — motor do Hunt Analyzer; `hunts/bridge.js` usa os módulos do próprio jogo.
- Modo Leve: só a opção `[desempenho] modo_leve` nas Configurações (vale ao reiniciar). **Não existe**
  mais executável separado "Leve" — o usuário não quer. **Leve 2.0** (`browser/web_host.py`): NÃO
  force `--disable-gpu` (num PC com placa deixava o jogo mais travado, medido). Com placa: GPU +
  "reduzir movimento". Sem placa (`tem_gpu()` pela DXGI): `--disable-gpu` + `QT_QUICK_BACKEND=software`.
  Ferramenta de medição em `ferramentas/desempenho/` (só para teste, não vai no pacote).
- **Visual (tema "Base do Treinador", aprovado pelo usuário):** toda cor, fonte e folha de estilo vem de
  `app/tema.py` (`T[...]`, `qss()`); **nenhuma cor fixa fora dele**. Ícones de pixel em `app/icones.py`
  (nada de emoji em botão); avisos/perguntas por `app/dialogos.py` (`avisar`, `perguntar`), nunca
  `QMessageBox`. A arte (molduras 9-slice, 124 ícones, logo, `.ico`) é própria, gerada por
  `ferramentas/arte/gerar_ui.py` e `gerar_marca.py` em `assets/ui`, `assets/marca`. Fontes Jersey 10
  (só 20/30/40 px, peso 400) e Nunito em `assets/fonts` (OFL). Textos curtos, sem "·" nem "—" na tela.
  A área do jogo não pode encolher (medir com o xadrez azul do jogo nos prints).
  **Desempenho:** as molduras NÃO usam `border-image` no QSS (o Qt recortava e esticava a imagem a
  cada pintura: repintar a janela levava ~8–10 ms). Painéis/fichas usam `Moldura` e todo botão usa
  `Botao` (`app/molduras.py`), que copiam a moldura já montada em memória (~4 ms). O QSS só reserva a
  largura da borda (`tema.moldura`). Botão novo: `Botao(...)`, nunca `QPushButton(...)`; painel novo:
  `Moldura()` com objectName "card". Não chame `setStyleSheet` em todo `refresh()` (refaz o estilo
  mesmo sem mudança).
- **Guias (tutoriais na tela):** `app/guia.py` (`Guia(painel, passos, alvos).abrir()`), textos em
  `app/textos_guia.py` (cada passo com o comentário da linha de código que prova o texto: mudou o
  código, mude o texto). O do Mercado abre pelo botão "Guia" (`RmtPanel.abrir_guia`). O guia só explica:
  não clica nem muda nada, não tem timer nem animação e é apagado ao fechar.
  **O ícone do programa (`assets/pokenexus.ico`) e o logo do topo são a Poké Ball, por escolha do
  usuário** (ele não gostou do mascote "Broto" no lugar). Não trocar sem ele pedir. O `.ico` precisa ter
  16/24/32/48/256 px (`ferramentas/arte/gerar_icone_pokebola.py`); com só 256 px o Windows mostrava o
  ícone velho do cache na pasta e na barra de tarefas. Depois de trocar o ícone:
  `ie4uinit.exe -ClearIconCache`.

## Dados do usuário

- Ficam em `%LOCALAPPDATA%\PokeNexus` (`config.toml`, `profiles\conta_XX` com os logins, `logs\`).
- `POKENEXUS_DATA=<pasta>` troca a pasta de dados. **Use sempre uma pasta temporária nos testes.**
- Nunca leia, copie ou envie tokens/cookies dos perfis. Cópias temporárias com logins têm de ser apagadas
  no fim.
- `profiles/`, `logs/` e saídas de build nunca vão para o Git; confira com a trava antes de todo push.

## Regras que não mudam

- **Máximo de 4 contas** (Termos do PokeIdle, seção 5). Nada para burlar anti-bot, limites, travas ou
  regras do jogo, nem para esconder a automação.
- **Contas reais:** nenhum teste conecta as contas reais sem o usuário autorizar. Antes, confira se o
  PokeNexus dele está aberto (`Get-Process PokeNexus`) — a mesma conta aberta em dois lugares derruba a
  sessão dele. Também não use as contas se ele estiver com elas abertas no navegador (Opera).
- **Mercado (RMT):** nenhuma compra real sem autorização do usuário caso a caso (item, preço, quantidade,
  conta). Nunca mexa em Gemas/USDT, carteira, Pix, cartão ou Diamantes. Mercado 2.0: lista de compras
  por conta em `profiles\conta_XX\rmt_compras.json` (`rmt/compras.py`), rotina em `rmt/rotina.py` (uma
  ação por vez, confere antes de cada passo que o item segue ligado e a conta segue caçando). A venda
  automática saiu (as regras de venda antigas ficam guardadas, desligadas). **Compra na liberação**
  (16/10/2026): olha a vitrine a cada `intervalo_s` (60 s; a retenção do jogo é 2 min) e marca UM pedido
  para o instante em que o anúncio libera (sorteio do jogo nos primeiros 3 s). Travas: nunca compra das
  contas próprias, duas contas suas nunca pedem o mesmo anúncio, 3 recusas seguidas desligam o item,
  para com a conta sem conexão ou pausada.
- **Não sobrescreva `dist\`** com o `PokeNexus.exe` do usuário aberto. Gere em outra pasta
  (`--distpath dist_novo`) e troque quando ele fechar.
- **Não diga que funciona sem testar.** Se um teste falhar, ache a causa; não remova a funcionalidade.
- Nas janelas com números e listas, a roda do mouse não pode mudar valores (`widgets.travar_roda`). Já
  aconteceu de "Contas no programa" cair de 4 para 1 sem o usuário ver.

## Rodar, testar e gerar

- Rodar do código: `.venv\Scripts\python.exe main.py`
- Testes de interface com WebEngine precisam de uma janela de verdade (rodam num terminal normal, não em
  sandbox). Use `POKENEXUS_DATA` numa pasta nova: as contas abrem na tela de login e nada das contas reais
  é tocado.
- Gerar a versão: `build.bat` (para no fim esperando uma tecla). Equivalente direto:
  `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean PokeNexus.spec`, depois compactar
  `dist\PokeNexus` em `dist\PokeNexus-<versão>.zip`. A pasta tem ~321 MB e o ZIP ~133 MB.
- Se o PyInstaller der "acesso negado" numa DLL de `dist`, algum processo está com ela aberta: gere com
  `--distpath dist_novo` e troque depois.
- Pacote para amigos testarem: `ferramentas\pacote_amigos\montar.ps1` (programa + LEIA-ME + .bat de
  relatório sem logins). Mudou um padrão do `config.toml` (ex.: mascote)? Quem já usou fica com o velho:
  acrescente uma migração em `app/config.py` `_migrar_config` (uma vez só, `migracoes.txt`).
- Testar o ZIP: descompactar numa pasta nova, rodar sem Python no PATH, abrir, fechar no X e conferir
  que não sobra nenhum processo.
- `$env:TEMP` aparece como `PAULOA~1`: resolva o caminho longo antes de comparar com caminhos de
  processos.

## Próximos passos (prompts na raiz)

1. `PROMPT_IDENTIDADE_VISUAL.md` — **feito** (15/10/2026, direção A). Relatório em
   `docs/visual/V6_RELATORIO.md`. **Os sprites de Pokémon (`assets/sprites/pokemon`) ficam**: o usuário
   quer os Pokémon originais como mascotes e não quer criaturas inventadas. Não troque nem remova.
2. `PROMPT_GUIA_MERCADO.md` — guia do Mercado (`app/guia.py`, `app/textos_guia.py`) já existe.
   `PROMPT_MERCADO_V2.md` — **feito no código** (15/10/2026): lista de compras, Ligado/Desligado por
   item, limites opcionais, guia novo, migração das regras antigas; testes offscreen e prints em
   `docs/visual/mercado2`. **Falta:** a prova com compra real pequena (só com autorização do usuário) e
   conferir que o farm não piora com o Mercado ligado.
3. `PROMPT_MODO_LEVE_V2.md` — **feito (15/10/2026), versão enxuta a pedido do usuário** (ele mandou parar os testes longos). Medido sem contas reais: P1 e P3. Faltou: as 3 rodadas completas, P2, Modo Economia (A8) e o farm com contas reais. Resultados em `docs/desempenho/HIPOTESES.md`.
4. `PROMPT_ASSINATURA_PREMIUM.md` — assinatura de R$ 5 por Pix, site com conta e confirmação de e-mail,
   app só para assinantes. Começa pela Etapa 0 (decisões do usuário: nome sem "Poke", autorização do
   PokeIdle, provedor de Pix, taxas, contador e advogado).
5. `PROMPT_GITHUB_E_LIMPEZA.md` — **parcialmente feito** (16/10/2026): `.gitignore` novo e histórico
   limpo pronto **só na pasta local** (branch `limpo`, 1 commit, sem `profiles/`, `logs/` nem builds;
   trava passou). **O GitHub não foi atualizado:** o usuário não quis apagar/recriar o repositório, e
   force push no antigo não tira os commits velhos do GitHub. Lá o histórico ainda tem `profiles/`:
   o repositório não pode voltar a ser público até isso ser resolvido. **Falta** também a limpeza do
   código não usado, **sem mudar nada do app**. Os `PROMPT_*.md` antigos ficam só na pasta local, em
   `docs/prompts_antigos/` (fora do Git, escolha do usuário).
6. Vistoria da interface após o PokeIdle 1.300.2 — **feita** (16/10/2026). Relatório em
   `docs/visual/interface_1300/RELATORIO.md`. O Market cortado é defeito do jogo (altura fixa desde
   15/10/2026); por escolha do usuário o PokeNexus baixa o zoom só enquanto o Market do jogo está aberto
   (`CellsHost.MARKET_CSS_H`, só lê a página). Ferramentas de teste em `ferramentas/interface/` (não vão
   no pacote). Pendentes no relatório (Ginásios com o mesmo defeito do jogo, itens Baixa de janela estreita).

Prompts antigos já executados: `PROMPT_CONFIG_MODO_LEVE.md`, `PROMPT_RMT_VERTICAL.md`.

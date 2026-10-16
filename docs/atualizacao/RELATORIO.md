# Instalador + aviso de atualização (16/10/2026)

Tudo testado nesta máquina com builds de verdade (1.1.1 e 1.1.2, gerados por
`ferramentas/atualizacao/build_teste.ps1`, o mesmo caminho do Actions), um servidor falso de Releases
(`ferramentas/atualizacao/servidor_falso.py`, com ETag/304 e uma porta lenta de 3 MB/s) e cliques de verdade
na janela pela automação de acessibilidade do Windows (`ferramentas/atualizacao/teste_app.ps1`). Nada foi
publicado. Nenhuma conta real: todas as pastas de dados foram temporárias (as contas abriram na tela de login).

## O que foi feito

| Arquivo | O quê |
|---|---|
| `instalador/PokeNexus.iss` | Inno Setup 6, pt-BR, por usuário, sem admin, `%LOCALAPPDATA%\Programs\PokeNexus`, `AppId` fixo `{1A74747E-E397-49F0-BC24-25F535B41F92}`, atalhos Menu Iniciar + Área de Trabalho, "Abrir o PokeNexus" no fim, reabre sozinho na atualização silenciosa, desinstalador avisa onde ficam os dados |
| `instalador/fumaca.ps1` | Trava 2: abre o .exe por 25 s com dados temporários, confere `crash.log`, fecha no X, confere processos |
| `instalador/requirements-build.txt` | versões exatas do `.venv` (PySide6 6.12.0, PyInstaller 6.22.3...) |
| `.github/workflows/release.yml` | push na `main` + manual; `paths-ignore` docs/md/ferramentas; pula `[sem atualização]`; Trava 1; versão; build; Trava 2; ZIP; instalador; SHA256SUMS; Release `v1.1.N` "Latest" com as notas; `contents: write` só no job |
| `app/atualizacao.py` | procura (30 s e 6 h, thread à parte, ETag, timeout 10 s), faixa, Depois/Pular, download com progresso e Cancelar, SHA-256, fecha pelo X, ajudante que roda o instalador |
| `app/config.py` | `APP_VERSION_BASE = "1.1"`; versão do `app/_build.py` ou `1.1-dev`; `[atualizacao]` nos padrões |
| `app/config_edit.py` | campo `atualizacao.avisar` (vale na hora) |
| `app/gui.py` | 4 linhas: a faixa abaixo do topo; `atualizacao` nas opções que valem na hora |
| `app/settings_ui.py` | cartão "Atualização": "Avisar quando tiver atualização" e "Procurar atualização agora" |
| `app/tema.py` | estilo da barra de progresso (só cores do tema; texto 9,75:1 sobre a parte cheia e 15,2:1 sobre a vazia) |
| `PokeNexus.spec`, `build.bat`, `.gitignore` | `app._build` no pacote quando existe; instalador opcional; `app/_build.py`, `build_*/` ignorados |

**Escolha do usuário:** faixa no topo (`prints/A_faixa_janela.png`) em vez do diálogo
(`prints/B_dialogo_janela.png`). Com a faixa à vista, a área do jogo fica 113 px mais baixa até Depois/Pular.

**Python:** o projeto usa **3.14.7** (o prompt dizia 3.11); o Actions usa 3.14 e as mesmas versões exatas.

## Testes

| # | Caso | Resultado | Prova |
|---|---|---|---|
| 1 | versão igual / maior / menor | **ok**: só a maior mostra a faixa | `prints/1a_igual.png`, `1b_maior.png`, `1c_menor.png`; log "em dia (instalada 1.1.1, no GitHub 1.1.1)", "versão nova 1.1.2 disponível", "em dia (... no GitHub 1.1.0)" |
| 2 | JSON quebrado / servidor fora | **ok**: nada na tela, programa segue aberto, uma linha no log | `prints/2a_json_quebrado.png`, `2b_servidor_fora.png`; log "não consegui procurar versão nova (resposta inválida ...)" e "(sem conexão ... recusou)" |
| 3 | Depois; Procurar agora; Pular e reabrir; opção desligada | **ok**: Depois esconde; "Procurar atualização agora" traz de volta (servidor respondeu **304**: ETag funciona); Pular grava `[atualizacao] versao_pulada = "1.1.2"` e a faixa não volta ao reabrir; desligada pelo Ajustes (grava `avisar = false`) não faz nenhum pedido, nem com a 1.1.3 no ar | `prints/3a_depois.png`, `3d_pulada_reaberto.png`, `3f_opcao_desligada.png` |
| 4 | SHA-256 errado | **ok**: não instala, apaga o arquivo, avisa, programa segue aberto | `prints/4_sha_errado_aviso.png`; log "NÃO instalada ... (esperado 000..., baixado a6f7...)" |
| 5 | atualizar de verdade 1.1.1 → 1.1.2 com 1 conta conectada | **ok**: pergunta "As contas vão parar para atualizar. Continuar?"; baixa com progresso; confere; fecha pelo X; o instalador roda sozinho; o PokeNexus **reabre na 1.1.2** em 8 s; Windows registra 1.1.2; processo velho não existe; `config.toml` com o mesmo SHA-256; pasta da conta igual; log continua no mesmo arquivo | `prints/5a_antes_111_faixa.png`, `5b_pergunta_contas.png`, `5c_baixando.png`, `5d_depois_112.png` |
| 6 | instalador | **ok**: `Administrative install mode: No`, registro em HKCU (nada em HKLM), atalhos no Menu Iniciar e na Área de Trabalho, instalar por cima usa a mesma pasta sem perguntar, desinstalar remove pasta/atalhos/registro e **não** apaga a pasta de dados (a real: 823 arquivos antes e depois; a de teste: 104) | `prints/6_desinstalar_aviso.png` |
| 7 | regressão: farm com a faixa aberta e durante o download | **ok**: 4 contas rodando; idade máxima do `heartbeat` 2,99 s (as contas checam a cada 3 s; o vigia só age acima de 150 s); atraso máximo da thread da tela 9,7 ms; download de 34,6 s com SHA ok | `prints/7a_faixa_com_4_contas.png`, `7b_baixando_*.png`, `prints/7_medidas.json` |
| 7 | pastas proibidas | **ok**: `workers/`, `game/`, `rmt/`, `hunts/`, `browser/` com os mesmos SHA-256 da linha de base (`docs/visual/interface_1300/linha_de_base/hashes.json`): 21 arquivos, 0 diferentes, 0 novos | |
| — | Trava 2 (fumaça) local | **ok**: "abriu, ficou 25 s de pé, sem crash.log, fechou e não sobrou processo" | |
| 8 | publicar de verdade no GitHub (com o OK do usuário) | **ok**: o commit `d6562ba` na `main` rodou o Actions (execução nº 1, sucesso: Trava 1, build, Trava 2, ZIP, instalador) e criou a Release **v1.1.1** "Latest" com `PokeNexus-Setup-1.1.1.exe` (95,6 MB), `PokeNexus-1.1.1.zip` (138,4 MB) e `SHA256SUMS.txt`; os dois arquivos baixados do GitHub conferem com o SHA256SUMS; o download real redireciona para `release-assets.githubusercontent.com` (aceito pelo programa). Um commit com `[sem atualização]` não publicou (ver abaixo) | https://github.com/PauloAfonsoGR/poke-nexus/releases/tag/v1.1.1 |

## Defeito achado e corrigido durante os testes

Na primeira tentativa do teste 5 o programa baixou, conferiu e fechou, mas **o instalador nunca rodou**. O
"ajudante" (PowerShell escondido que espera o PokeNexus fechar e então roda o instalador) era criado com
`DETACHED_PROCESS`: sem console nenhum, o PowerShell 5.1 sai sem rodar o script (medido: com
`DETACHED_PROCESS` não roda; com `CREATE_NO_WINDOW` roda). Corrigido para `CREATE_NO_WINDOW`, com saída de
"job" do Windows (`CREATE_BREAKAWAY_FROM_JOB`, para um lançador que abre o programa dentro de um job não
matar o ajudante junto), log próprio do ajudante (`%TEMP%\PokeNexus-atualizacao-ajudante.log`) e a linha
"instalador agendado" no log do programa. Os builds 1.1.1 e 1.1.2 foram refeitos e o teste 5 passou (acima).
Os testes 1 a 4 foram feitos no build anterior; a correção só mexeu na função do ajudante.

## Cuidados na máquina do usuário

- O PokeNexus do usuário (`dist\PokeNexus-1.1.0`) ficou aberto o tempo todo e não foi tocado.
- Já existia um `PokeNexus.lnk` dele na Área de Trabalho (aponta para outra pasta). O instalador de teste o
  trocaria e o desinstalador o apagaria: foi guardado antes e devolvido no fim (mesmo SHA-256).
- O Inno Setup 6.7.3 foi instalado por usuário (`winget --scope user`) para gerar os instaladores aqui.

## O que NÃO foi testado

- A publicação no GitHub (teste 8) e o download dos servidores reais do GitHub. O programa aceita
  `github.com`, `objects.githubusercontent.com` e `release-assets.githubusercontent.com` (o GitHub hoje
  redireciona os arquivos das Releases para este último; sem ele a atualização real falharia).
- O instalador e o programa não são assinados: o Windows mostra "O Windows protegeu o computador".

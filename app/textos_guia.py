"""Textos dos guias (tutoriais na tela), num lugar só para revisar.

Cada passo: `alvo` (o nome da parte da tela que fica em destaque; None = nenhuma), `titulo` e `texto`
(no máximo 3 frases curtas). O comentário de cada passo diz onde o código faz o que o texto promete:
se o código mudar, o texto tem de mudar junto.
"""

MERCADO = [
    # rmt/rotina.py + rmt/canal.py: olha a vitrine e compra pela conexão do jogo, sem abrir tela; só itens ligados
    {"alvo": "topo", "titulo": "O que o Mercado faz",
     "texto": "Aqui o PokeNexus compra itens sozinho para esta conta, sem abrir nada na tela do jogo. Você monta "
              "uma lista de compras e liga os itens que quer. Nada é comprado com o item desligado."},
    # rmt/rotina.py view(): saldo vem de game.eu (gold, orbs); sem conta conectada aparece "?"
    {"alvo": "saldo", "titulo": "Saldo",
     "texto": "Mostra quanto de Ouro e de Gema esta conta tem agora. A Gema vale dinheiro de verdade, então vá com "
              "calma com ela. Embaixo aparece se a conta está pronta para comprar."},
    # app/conversor_gemas.py: GEMAS_REF/CENTAVOS_REF (a taxa de referência do usuário, não a do jogo);
    # app/rmt_ui.py CalculadoraGemas só calcula: não compra, não grava nada e não acessa a internet;
    # RmtPanel.b_calc abre e fecha (fechada, o destaque é o botão)
    {"alvo": "calculadora", "titulo": "Calculadora de Gemas",
     "texto": "O botão Calculadora converte Gemas em dólares e dólares em Gemas, na hora. É só uma conta de "
              "referência (1.000 Gemas = US$ 9,00), não é cotação nem saque. Ela não compra nem mexe em nada."},
    # app/rmt_ui.py CompraDialog: item da lista do jogo, moeda e preço máximo (obrigatório, rmt/compras.py
    # validar_item); o servidor também confere o teto (comprarLote com precoMax/totalMax)
    {"alvo": "adicionar", "titulo": "Adicionar item",
     "texto": "Escolha o item, a moeda e o preço máximo por unidade. Exemplo: Ultra Ball até 100 de ouro cada: "
              "ele nunca paga mais que 100 por unidade. O item entra desligado."},
    # app/rmt_ui.py alternar(): ligar pede confirmação com o resumo; Gema pede marcar "Entendi"
    # rmt/compras.py: o "ligado" fica salvo no perfil da conta (vale depois de reabrir)
    {"alvo": "interruptor", "titulo": "Ligado e desligado",
     "texto": "Clique em Desligado para ligar: aparece um resumo para você confirmar. Ligado, compra todo anúncio "
              "até o seu preço assim que ele libera, e continua ligado mesmo se você reabrir o PokeNexus. Clique "
              "de novo para desligar na hora."},
    # rmt/decisao.py planejar_compra_item (limites 0 = sem limite); rmt/rotina.py _comprar: unidades ou
    # gasto atingido desliga o item; limite do dia espera o dia seguinte
    {"alvo": "limites", "titulo": "Limites (opcionais)",
     "texto": "Você pode mandar parar depois de X unidades, depois de gastar X, ou gastar no máximo X por dia. "
              "Sem nenhum limite, ele compra sem parar até você desligar. Os limites mudam em Editar, com o item "
              "desligado."},
    # rmt/rotina.py: _avaliar (agendado: "compra às HH:MM:SS"), _pedir (pedindo, comprou, perdeu o sorteio);
    # sem dinheiro espera e não desliga; conta sem conexão ou pausada: "Parado" com o motivo
    {"alvo": "status", "titulo": "Está funcionando?",
     "texto": "Esta frase diz o que o item está fazendo: Procurando (com o menor preço), compra marcada para a hora "
              "em que o anúncio libera, Comprou, ou se outro jogador levou no sorteio do jogo. Sem dinheiro, ele "
              "espera e volta sozinho."},
    # rmt/compras.py ItemCompra.registrar_compra: hoje e total, só compras de verdade, e a última compra
    {"alvo": "contadores", "titulo": "Quanto comprou e gastou",
     "texto": "Aqui ficam quantas unidades ele comprou e quanto gastou hoje e no total, e a hora da última compra. "
              "Só conta o que foi comprado de verdade."},
    # rmt/rotina.py: _de_outra_conta, _RESERVAS (duas contas suas nunca disputam o mesmo anúncio), um pedido
    # por anúncio, ERROS_PARA_DESLIGAR; _intervalo (de quanto em quanto olha a vitrine)
    {"alvo": "seguranca", "titulo": "Ritmo e segurança",
     "texto": "Aqui você escolhe de quanto em quanto ele olha a vitrine (1 minuto já pega todo anúncio novo, que "
              "fica 2 min retido). Ele nunca compra das suas outras contas, pede uma vez só por anúncio e desliga "
              "o item se o jogo recusar 3 compras seguidas."},
    # app/manager.py rmt_parar_todos -> rmt/rotina.py parar(): desliga todos os itens de todas as contas
    {"alvo": "parar", "titulo": "Parar todas as compras",
     "texto": "Este botão desliga na hora todos os itens da lista, em todas as contas. Para voltar a comprar, "
              "ligue cada item de novo."},
    {"alvo": "guia", "titulo": "Dica final",
     "texto": "Comece com um item barato e um limite de poucas unidades para ver funcionando. Depois, se quiser, "
              "tire o limite. Este guia abre de novo no botão Guia."},
]

CONVITE_MERCADO = "Primeira vez aqui? Veja o guia do Mercado."

# A fala do Meowth na calculadora do Mercado: (até quantos US$, frase), na ordem; None = acima de tudo.
# Pode trocar à vontade (curtas, sem "·" nem "—"). Quem escolhe: app/conversor_gemas.py frase_do_mascote.
FRASES_MEOWTH = [
    (0, "Quanto vale? Digite aí!"),
    (1, "Trocado de bolso"),
    (10, "Dá um lanche"),
    (100, "Agora sim, miau!"),
    (None, "Isso é muita moeda!"),
]

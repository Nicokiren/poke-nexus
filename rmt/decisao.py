"""Decisão do RMT: dado o que o mercado mostra agora, o que UMA regra faria. Sem rede e sem tela.

Compra: o caminho é a "compra em quantidade" do próprio jogo (cotarLote → comprarLote). A cotação
diz, por degrau de preço, quantas unidades há; aqui se escolhe quantas cabem no preço máximo, no
orçamento e sem passar por anúncio de outra conta do usuário. Depois o jogo cota de novo aquela
quantidade, e `conferir_cotacao` só libera se o preço máximo e o total da cotação NOVA couberem —
e são esses dois tetos que o servidor recebe e confere.
"""
from dataclasses import dataclass, field

from rmt.regras import NOME_MOEDA, Regra
from rmt.taxas import Taxas


@dataclass
class Plano:
    acao: str                     # nada | comprar | criar | editar | pausar
    motivo: str = ""
    qtd: int = 0
    preco: int = 0                # comprar: preço máximo por unidade; criar/editar: preço do anúncio
    total: int = 0                # comprar: custo estimado; vender: líquido estimado
    anuncio_id: object = None     # editar
    detalhes: dict = field(default_factory=dict)

    def texto(self, regra: Regra) -> str:
        m = NOME_MOEDA[regra.moeda]
        if self.acao == "comprar":
            return f"compraria {self.qtd}× {regra.item_nome} por até {self.preco} {m}/un (≈ {self.total} {m})"
        if self.acao == "criar":
            return f"anunciaria {self.qtd}× {regra.item_nome} por {self.preco} {m}/un (líquido ≈ {self.total} {m})"
        if self.acao == "editar":
            return f"mudaria o anúncio de {regra.item_nome} para {self.preco} {m}/un"
        if self.acao == "pausar":
            return f"pausou: {self.motivo}"
        return self.motivo


def _custo(degraus: list[tuple[int, int]], qtd: int) -> int:
    """Custo das `qtd` unidades mais baratas. degraus: [(preço, unidades)] em ordem crescente."""
    falta, total = qtd, 0
    for preco, n in degraus:
        usa = min(falta, n)
        total += usa * preco
        falta -= usa
        if falta <= 0:
            break
    return total


def _degraus_seguros(cot: dict, preco_max: int, proprios: set, bloquear: bool) -> tuple[list, str]:
    """Degraus (preço, unidades) que podem ser comprados, já sem as outras contas do usuário.

    Com o bloqueio ligado, só vale o trecho da lista de vendedores que a cotação mostrou, até o
    primeiro anúncio de uma conta do usuário: o que vem depois (ou o que a cotação não listou) pode
    ser dele, então não entra."""
    faixas = sorted(((int(f["preco"]), int(f["qtd"])) for f in cot.get("faixas") or [] if int(f.get("qtd") or 0) > 0))
    faixas = [(p, n) for p, n in faixas if p <= preco_max]
    if not bloquear:
        return faixas, ""
    vend = cot.get("vendedores") or []
    seguros, aviso = [], ""
    for v in sorted(vend, key=lambda v: int(v.get("preco") or 0)):
        p = int(v.get("preco") or 0)
        if p > preco_max:
            break
        if str(v.get("vendedor", "")).strip().lower() in proprios or v.get("vendedorId") in proprios:
            aviso = f"parei antes do anúncio de {v.get('vendedor')} (conta sua)"
            break
        seguros.append((p, int(v.get("qtd") or 0)))
    listados = sum(n for _, n in seguros)
    tem_no_preco = sum(n for _, n in faixas)
    if not vend and tem_no_preco:
        return [], "a cotação não disse quem vende — sem como conferir se é conta sua"
    if listados < tem_no_preco and not aviso and int(cot.get("anuncios") or 0) > len(vend):
        aviso = "só os vendedores que a cotação listou"
    return seguros, aviso


def planejar_compra(regra: Regra, cot: dict, saldo: int, gasto_hoje: int, limite_dia: int,
                    gasto_regra: int, proprios: set, bloquear: bool = True) -> Plano:
    """cot: resposta de market.cotarLote ({qtd, total, precoMax, faixas[{preco, qtd, anuncios}],
    vendedores[{vendedor, qtd, preco}], anuncios, disponivel}). proprios: nicks (minúsculos) e ids
    das contas do usuário."""
    m = NOME_MOEDA[regra.moeda]
    falta = regra.qtd_total - regra.comprado
    if falta <= 0:
        return Plano("nada", "meta de compra cumprida")
    if limite_dia <= 0:
        return Plano("nada", f"o limite de gasto por dia em {m} desta conta é 0")
    if not cot or not cot.get("faixas"):
        return Plano("nada", "ninguém vende este item nesta moeda agora")
    degraus, aviso = _degraus_seguros(cot, regra.preco_max, proprios, bloquear)
    disponivel = sum(n for _, n in degraus)
    if disponivel <= 0:
        menor = min(int(f["preco"]) for f in cot["faixas"])
        return Plano("nada", (aviso + "; " if aviso else "") + f"menor preço {menor} {m}, acima do máximo {regra.preco_max}")
    orcamento = min(saldo, limite_dia - gasto_hoje,
                    (regra.gasto_max - gasto_regra) if regra.gasto_max else saldo)
    if orcamento <= 0:
        return Plano("nada", f"sem orçamento: saldo {saldo}, gasto hoje {gasto_hoje}/{limite_dia} {m}")
    qtd = min(falta, regra.qtd_por_compra, disponivel)
    while qtd > 0 and _custo(degraus, qtd) > orcamento:
        qtd -= 1
    if qtd <= 0:
        return Plano("nada", f"nem 1 unidade cabe no orçamento ({orcamento} {m})")
    usados = []
    falta_q = qtd
    for p, n in degraus:
        if falta_q <= 0:
            break
        usados.append(p)
        falta_q -= n
    return Plano("comprar", aviso, qtd=qtd, preco=max(usados), total=_custo(degraus, qtd),
                 detalhes={"orcamento": orcamento})


def planejar_compra_item(item, cot: dict, saldo: int, proprios: set, bloquear: bool = True,
                         lote_max: int = 20) -> Plano:
    """Mercado 2.0 (rmt/compras.py ItemCompra): quantas unidades comprar agora, com a cotação na mão.
    Os limites são opcionais (0 = sem); sem nenhum, o teto é só o saldo e o preço máximo.
    `motivo` de "nada" começa com "saldo:" quando falta dinheiro (a rotina espera, não desliga)."""
    m = NOME_MOEDA[item.moeda]
    item.virar_dia()
    restam = item.lim_unidades - item.comprado_total if item.lim_unidades else lote_max
    if restam <= 0:
        return Plano("nada", f"limite: já comprou {item.comprado_total} de {item.lim_unidades} unidades")
    if not cot or not cot.get("faixas"):
        return Plano("nada", "ninguém vende este item nesta moeda agora")
    degraus, aviso = _degraus_seguros(cot, item.preco_max, proprios, bloquear)
    disponivel = sum(n for _, n in degraus)
    if disponivel <= 0:
        menor = min(int(f["preco"]) for f in cot["faixas"])
        return Plano("nada", (aviso + ". " if aviso else "")
                     + f"menor preço agora: {menor} {m} (o seu máximo é {item.preco_max})")
    # o teto de gasto agora: o saldo e, se houver, o que sobra de cada limite (o menor manda)
    tetos = [(saldo, "saldo")]
    if item.lim_gasto:
        tetos.append((item.lim_gasto - item.gasto_total, "gasto"))
    if item.lim_dia:
        tetos.append((item.lim_dia - item.gasto_hoje, "dia"))
    orcamento, quem = min(tetos)
    if orcamento <= 0:
        if quem == "saldo":
            return Plano("nada", f"saldo: sem {m} na conta")
        if quem == "gasto":
            return Plano("nada", f"limite: já gastou {item.gasto_total} de {item.lim_gasto} {m}")
        return Plano("nada", f"limite do dia: já gastou {item.gasto_hoje} de {item.lim_dia} {m} hoje")
    qtd = min(restam, lote_max, disponivel)
    while qtd > 0 and _custo(degraus, qtd) > orcamento:
        qtd -= 1
    if qtd <= 0:
        if quem == "saldo":
            return Plano("nada", f"saldo: {saldo} {m} não paga nem 1 unidade agora")
        if quem == "gasto":
            return Plano("nada", f"limite: o que sobra do limite de gasto ({orcamento} {m}) não paga nem 1 unidade")
        return Plano("nada", f"limite do dia: o que sobra hoje ({orcamento} {m}) não paga nem 1 unidade")
    usados, falta_q = [], qtd
    for p, n in degraus:
        if falta_q <= 0:
            break
        usados.append(p)
        falta_q -= n
    return Plano("comprar", aviso, qtd=qtd, preco=max(usados), total=_custo(degraus, qtd),
                 detalhes={"orcamento": orcamento})


def conferir_cotacao(plano: Plano, regra: Regra, cot: dict, proprios: set, bloquear: bool = True) -> str | None:
    """A cotação NOVA (da quantidade do plano) ainda cabe? None = pode comprar; senão, o motivo."""
    if not cot or int(cot.get("qtd") or 0) != plano.qtd:
        return f"a cotação mudou: agora entrega {cot.get('qtd') if cot else 0}, o plano era {plano.qtd}"
    if int(cot.get("precoMax") or 0) > regra.preco_max:
        return f"preço máximo da cotação {cot.get('precoMax')} passou do máximo da regra {regra.preco_max}"
    if int(cot.get("total") or 0) > plano.detalhes.get("orcamento", 0):
        return f"total {cot.get('total')} passou do orçamento {plano.detalhes.get('orcamento')}"
    if bloquear:
        degraus, _ = _degraus_seguros(cot, regra.preco_max, proprios, True)
        if sum(n for _, n in degraus) < plano.qtd:
            return "a cotação nova passa por anúncio de outra conta sua (ou não diz quem vende)"
    return None


def planejar_venda(regra: Regra, linhas: list[dict], meu: dict | None, estoque: int, taxas: Taxas,
                   ajustes_ultima_hora: int, proprios: set, agora_ms: float) -> Plano:
    """linhas: anúncios ativos do item nessa moeda (market.item: {id, vendedor, vendedorId, qtd,
    preco, compravelEm}). meu: o anúncio desta conta para o item (ou None). estoque: unidades na
    bolsa (fora do que já está anunciado)."""
    m = NOME_MOEDA[regra.moeda]
    pmin = taxas.preco_min(regra.moeda)
    if regra.modo == "fixo":
        alvo = regra.preco
        porque = "preço fixo"
    else:
        outros = [l for l in linhas or [] if l.get("vendedorId") not in proprios
                  and str(l.get("vendedor", "")).strip().lower() not in proprios
                  and not (meu and l.get("id") == meu.get("id"))]
        if outros:
            menor = min(int(l["preco"]) for l in outros)
            alvo = max(regra.piso, menor - regra.passo)
            porque = f"menor preço dos outros {menor} {m}" + (" (no piso)" if alvo == regra.piso else "")
        else:
            alvo = max(regra.piso, regra.preco)
            porque = "ninguém mais vende"
    alvo = max(alvo, pmin)
    liquido1 = taxas.liquido(alvo, 1, regra.moeda)
    if liquido1 < 1:
        return Plano("nada", f"a {alvo} {m} a taxa come tudo")
    if meu:
        if int(meu.get("preco") or 0) == alvo:
            return Plano("nada", f"anúncio já está em {alvo} {m}/un ({porque})")
        if (meu.get("compravelEm") or 0) > agora_ms:
            return Plano("nada", "o anúncio ainda está em retenção (o jogo só deixa remover por enquanto)")
        if ajustes_ultima_hora >= regra.ajustes_max_hora:
            return Plano("nada", f"já foram {ajustes_ultima_hora} ajustes de preço na última hora (máximo {regra.ajustes_max_hora})")
        q = int(meu.get("qtd") or 0)
        return Plano("editar", porque, qtd=q, preco=alvo, total=taxas.liquido(alvo, q, regra.moeda),
                     anuncio_id=meu.get("id"))
    disp = estoque - regra.manter_estoque
    qtd = min(regra.qtd_anunciar, disp)
    if qtd < 1:
        return Plano("nada", f"estoque {estoque}, manter {regra.manter_estoque}: nada a anunciar")
    return Plano("criar", porque, qtd=qtd, preco=alvo, total=taxas.liquido(alvo, qtd, regra.moeda))


def queda_estranha(menor_antes: int | None, menor_agora: int | None, queda_max_pct: int) -> bool:
    """O menor preço caiu demais de uma vez (erro de digitação de alguém, ou golpe)."""
    if not menor_antes or not menor_agora or queda_max_pct <= 0:
        return False
    return menor_agora < menor_antes * (1 - queda_max_pct / 100)

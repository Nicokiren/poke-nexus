"""Mercado da conta selecionada: a lista de compras (um cartão por item), o saldo, os ajustes e o guia.
Só desenha e edita a lista; quem compra é rmt/rotina.py (compra na liberação, sem abrir nada na tela).

Cada item: o item do jogo, a moeda, o preço máximo por unidade e um interruptor Ligado/Desligado.
Ligado, compra todo anúncio até esse preço assim que ele libera, sem fim, a não ser que um limite
opcional diga para parar. Ligar pede confirmação com o resumo (sem limite: "vai comprar sem parar";
Gema: dinheiro de verdade, com uma caixa para marcar).
"""
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QSpinBox, QVBoxLayout,
                               QWidget)

from app.dialogos import avisar, perguntar
from app.guia import Guia
from app.icones import TAM as ICO_TAM, icone, por_nome_do_botao
from app.molduras import Botao, Moldura
from app.tema import T, carregar_fontes, qss_campos, qss_dialogo
from app.textos_guia import CONVITE_MERCADO, MERCADO as PASSOS_GUIA
from app.widgets import travar_roda
from rmt.compras import ErroItem, ItemCompra, validar_item
from rmt.regras import NOME_MOEDA
from rmt.rotina import INTERVALO_MIN_S, INTERVALO_PADRAO_S

COR_STATUS = {"comprou": "ok", "agendado": "ok", "pedindo": "info", "procurando": "info", "perdeu": "aviso", "espera": "aviso",
              "parado": "erro"}


def _ico(b, nome, estilo=None):
    b.setText(" " + b.text())
    b.setIcon(icone(nome, por_nome_do_botao(estilo)))
    b.setIconSize(ICO_TAM)


def num(v) -> str:
    return "?" if v is None else f"{int(v):,}".replace(",", ".")


def _rot(t="", obj=None, estilo=None, wrap=False):
    l = QLabel(t)
    if obj:
        l.setObjectName(obj)
    if estilo:
        l.setStyleSheet(estilo)
    l.setWordWrap(wrap)
    return l


def _card(titulo=None):
    f = Moldura()
    f.setObjectName("card")
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 12, 14, 12)
    v.setSpacing(8)
    if titulo:
        v.addWidget(_rot(titulo, "cardTitle"))
    return f, v


def _spin(mn, mx, valor, sufixo="", passo=1):
    s = QSpinBox()
    s.setRange(mn, mx)
    s.setSingleStep(passo)
    s.setValue(int(valor))
    s.setSuffix(sufixo)
    return s


# ============================================================ adicionar / editar item
class CompraDialog(QDialog):
    """Adicionar ou editar um item da lista: item do jogo (com busca), moeda, preço máximo e os
    limites opcionais. Salvar deixa o item DESLIGADO (ligar é no cartão, com confirmação)."""

    def __init__(self, parent, catalogo: list[dict], item: ItemCompra | None):
        super().__init__(parent)
        self.setWindowTitle("Item da lista de compras")
        carregar_fontes()
        self.setStyleSheet(qss_dialogo())
        self.resize(560, 620)
        self.catalogo = sorted(catalogo, key=lambda i: str(i.get("nome") or ""))
        self.base = item
        self.item: ItemCompra | None = None
        lay = QVBoxLayout(self)
        lay.addWidget(_rot("Item", "cardTitle"))
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("buscar item do jogo…")
        lay.addWidget(self.busca)
        self.lista = QListWidget()
        self.lista.setMinimumHeight(170)
        lay.addWidget(self.lista)
        self.busca.textChanged.connect(self._filtrar)
        form = QFormLayout()
        self.moeda = QComboBox()
        self.moeda.addItems(["Ouro", "Gema"])
        self.preco = _spin(1, 2_000_000_000, 1)
        form.addRow("Moeda", self.moeda)
        form.addRow("Preço máximo por unidade", self.preco)
        lay.addLayout(form)
        lay.addWidget(_rot("Limites (opcionais)", "cardTitle"))
        g = QGridLayout()
        self.c_unid, self.s_unid = QCheckBox("Parar depois de comprar"), _spin(1, 10_000_000, 10, " unidades")
        self.c_gasto, self.s_gasto = QCheckBox("Parar depois de gastar"), _spin(1, 2_000_000_000, 10_000)
        self.c_dia, self.s_dia = QCheckBox("No máximo por dia"), _spin(1, 2_000_000_000, 10_000)
        for r, (c, s) in enumerate(((self.c_unid, self.s_unid), (self.c_gasto, self.s_gasto), (self.c_dia, self.s_dia))):
            g.addWidget(c, r, 0)
            g.addWidget(s, r, 1)
            s.setEnabled(False)
            c.toggled.connect(s.setEnabled)
            c.toggled.connect(self._resumo)
            s.valueChanged.connect(self._resumo)
        lay.addLayout(g)
        self.txt_limites = _rot("", "muted", wrap=True)
        lay.addWidget(self.txt_limites)
        self.erro = _rot("", None, f"color:{T['erro']}; font-weight:700;", wrap=True)
        lay.addWidget(self.erro)
        lay.addWidget(_rot("O item entra DESLIGADO. Para comprar, ligue no cartão dele.", "muted", wrap=True))
        base = QHBoxLayout()
        base.addStretch()
        c = Botao("Cancelar")
        c.clicked.connect(self.reject)
        s = Botao("Salvar")
        _ico(s, "salvar", "primary")
        s.setObjectName("primary")
        s.clicked.connect(self._salvar)
        base.addWidget(c)
        base.addWidget(s)
        lay.addLayout(base)
        self.moeda.currentIndexChanged.connect(self._resumo)
        self._filtrar("")
        if item:
            self.moeda.setCurrentIndex(0 if item.moeda == "gold" else 1)
            self.preco.setValue(item.preco_max)
            for valor, c, s in ((item.lim_unidades, self.c_unid, self.s_unid), (item.lim_gasto, self.c_gasto, self.s_gasto),
                                (item.lim_dia, self.c_dia, self.s_dia)):
                if valor:
                    c.setChecked(True)
                    s.setValue(valor)
        self._resumo()
        travar_roda(self)                 # a roda do mouse não muda preço nem limite sem querer

    def _filtrar(self, texto):
        self.lista.clear()
        t = (texto or "").strip().lower()
        for it in self.catalogo:
            nome = str(it.get("nome") or f"#{it.get('id')}")
            if t and t not in nome.lower():
                continue
            li = QListWidgetItem(f"{nome}  {it.get('categoria') or ''}")
            li.setData(Qt.UserRole, it)
            self.lista.addItem(li)
            if self.base and it.get("id") == self.base.item_id:
                li.setSelected(True)
                self.lista.setCurrentItem(li)

    def _resumo(self, *_):
        m = "ouro" if self.moeda.currentIndex() == 0 else "gema"
        for s in (self.s_gasto, self.s_dia):
            s.setSuffix(f" {m}")
        self.txt_limites.setText(self._montar(None).limites_txt())

    def _montar(self, item_do_jogo) -> ItemCompra:
        it = item_do_jogo or {"id": 1, "nome": "?"}
        return ItemCompra(item_id=int(it["id"]), item_nome=str(it.get("nome") or f"#{it['id']}"),
                          moeda="gold" if self.moeda.currentIndex() == 0 else "orb", preco_max=self.preco.value(),
                          lim_unidades=self.s_unid.value() if self.c_unid.isChecked() else 0,
                          lim_gasto=self.s_gasto.value() if self.c_gasto.isChecked() else 0,
                          lim_dia=self.s_dia.value() if self.c_dia.isChecked() else 0)

    def _salvar(self):
        li = self.lista.currentItem()
        item = li.data(Qt.UserRole) if li else None
        if not item:
            self.erro.setText("escolha o item na lista")
            return
        novo = self._montar(item)
        if self.base:
            # editar: mantém id e contadores; volta DESLIGADO (o que foi confirmado era o item antigo)
            b = self.base
            mesmo = b.item_id == novo.item_id and b.moeda == novo.moeda
            novo.id = b.id
            if mesmo:
                novo.comprado_total, novo.gasto_total = b.comprado_total, b.gasto_total
                novo.dia, novo.comprado_hoje, novo.gasto_hoje, novo.ultima_compra = (
                    b.dia, b.comprado_hoje, b.gasto_hoje, b.ultima_compra)
        try:
            validar_item(novo)
        except ErroItem as e:
            self.erro.setText(str(e))
            return
        self.item = novo
        self.accept()


# ============================================================ cartão de um item
class CartaoItem(Moldura):
    """Um item da lista: o que compra, o interruptor, os limites, o status e os contadores."""

    def __init__(self, painel, item: ItemCompra):
        super().__init__()
        self.setObjectName("card")
        self.painel, self.iid = painel, item.id
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(6)
        topo = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(0)
        self.nome = _rot("", "cardTitle")
        self.preco = _rot("", None, "font-size:13px; font-weight:700;")
        col.addWidget(self.nome)
        col.addWidget(self.preco)
        topo.addLayout(col, 1)
        self.b_editar = Botao("Editar")
        _ico(self.b_editar, "editar")
        self.b_editar.setObjectName("tool")
        self.b_editar.clicked.connect(lambda: painel.editar(self.iid))
        self.b_remover = Botao("Remover")
        _ico(self.b_remover, "excluir", "danger")
        self.b_remover.setObjectName("tool")
        self.b_remover.clicked.connect(lambda: painel.remover(self.iid))
        self.interruptor = Botao("")
        self.interruptor.setMinimumWidth(170)
        self.interruptor.setCursor(Qt.PointingHandCursor)
        self.interruptor.clicked.connect(lambda: painel.alternar(self.iid))
        for b in (self.b_editar, self.b_remover, self.interruptor):
            topo.addWidget(b, 0, Qt.AlignTop)
        v.addLayout(topo)
        self.limites = _rot("", "muted", wrap=True)
        v.addWidget(self.limites)
        self.status = _rot("", None, "font-size:14px; font-weight:800;", wrap=True)
        v.addWidget(self.status)
        self.contadores = _rot("", "muted", "font-size:12px;", wrap=True)
        v.addWidget(self.contadores)
        self._ligado = None

    def atualizar(self, item: ItemCompra, st: dict | None, conta_parada: str | None):
        m = NOME_MOEDA[item.moeda]
        self.nome.setText(f"{item.item_nome}   ({'Gema' if item.moeda == 'orb' else 'Ouro'})")
        self.preco.setText(f"Compra até {num(item.preco_max)} {m} cada")
        self.limites.setText(item.limites_txt())
        if self._ligado != item.ligado:
            self._ligado = item.ligado
            self.interruptor.setText(" Ligado" if item.ligado else " Desligado")
            self.interruptor.setObjectName("primary" if item.ligado else "")
            self.interruptor.setIcon(icone("comecar" if item.ligado else "parar",
                                           "escuro" if item.ligado else "claro"))
            self.interruptor.setIconSize(ICO_TAM)
            self.interruptor.setToolTip("Clique para desligar" if item.ligado else "Clique para ligar (pede confirmação)")
            self.interruptor.style().unpolish(self.interruptor)
            self.interruptor.style().polish(self.interruptor)
            self.b_editar.setEnabled(not item.ligado)
            self.b_editar.setToolTip("Desligue o item para editar" if item.ligado else "Mudar item, preço ou limites")
        # a frase do status: o que está fazendo agora (ou por que não está)
        if not item.ligado:
            txt = f"Desligado: {item.desligado_por}" if item.desligado_por else "Desligado"
            tipo = "parado" if item.desligado_por else "desligado"
        elif conta_parada:
            txt, tipo = f"Parado: {conta_parada}", "parado"
        elif st:
            txt, tipo = st["texto"], st["tipo"]
        else:
            txt, tipo = "Ligado: vai olhar a vitrine em instantes", "espera"
        self.status.setText(txt)
        cor = T[COR_STATUS[tipo]] if tipo in COR_STATUS else T["dim"]
        estilo = f"font-size:14px; font-weight:800; color:{cor};"
        if self.status.styleSheet() != estilo:
            self.status.setStyleSheet(estilo)
        u = item.ultima_compra
        ultima = (f"   Última compra: {time.strftime('%d/%m %H:%M', time.localtime(u['quando']))}, "
                  f"{u['qtd']} por {num(round(u['total'] / max(1, u['qtd'])))} {m} cada") if u else "   Nenhuma compra ainda."
        self.contadores.setText(f"Hoje: {num(item.comprado_hoje)} comprados, {num(item.gasto_hoje)} {m} gastos.   "
                                f"Total: {num(item.comprado_total)} comprados, {num(item.gasto_total)} {m} gastos.{ultima}")


# ============================================================ o painel
class RmtPanel(QScrollArea):
    """Os sinais levam a conta junto: o painel nunca mistura uma conta com outra."""
    parar_todos = Signal()         # desliga todas as compras, em todas as contas
    guia_visto = Signal()          # a pessoa já viu (ou dispensou) o guia

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        corpo = QWidget()
        self.setWidget(corpo)
        corpo.setStyleSheet(qss_campos())
        lay = QVBoxLayout(corpo)
        lay.setContentsMargins(4, 4, 8, 8)
        lay.setSpacing(10)
        self.conta = None
        self.worker = None
        self._guia = None
        self._cartoes: dict[str, CartaoItem] = {}
        self._estrutura = None

        topo = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(0)
        self._titulo = _rot("Mercado da Comunidade", "cardTitle")
        self._descricao = _rot("Compra itens sozinho para esta conta assim que o anúncio libera, sem abrir nada na tela. Mexe com Ouro "
                               "e Gema (que vale dinheiro de verdade).", "muted", "font-size:11px;", wrap=True)
        col.addWidget(self._titulo)
        col.addWidget(self._descricao)
        topo.addLayout(col, 1)
        self.b_guia = Botao("Guia")
        _ico(self.b_guia, "guia")
        self.b_guia.setObjectName("tool")
        self.b_guia.setToolTip("Mostra, passo a passo, para que serve cada parte do Mercado")
        self.b_guia.clicked.connect(self.abrir_guia)
        self.b_parar = Botao("Parar todas as compras")
        _ico(self.b_parar, "parar", "danger")
        self.b_parar.setObjectName("danger")
        self.b_parar.setToolTip("Desliga todos os itens da lista, em todas as contas")
        self.b_parar.clicked.connect(self.parar_todos.emit)
        for b in (self.b_guia, self.b_parar):
            b.setCursor(Qt.PointingHandCursor)
            topo.addWidget(b, 0, Qt.AlignTop)
        lay.addLayout(topo)

        # convite discreto na primeira vez (some ao clicar ou fechar, e não volta mais)
        self.convite = QWidget()
        cv = QHBoxLayout(self.convite)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.addWidget(_rot(CONVITE_MERCADO, "muted"))
        b_ver = Botao("Ver o guia")
        _ico(b_ver, "guia")
        b_ver.setObjectName("tool")
        b_ver.clicked.connect(self.abrir_guia)
        b_fechar = Botao("")
        b_fechar.setIcon(icone("excluir"))
        b_fechar.setIconSize(ICO_TAM)
        b_fechar.setObjectName("tool")
        b_fechar.setToolTip("Dispensar")
        b_fechar.clicked.connect(self._dispensar_convite)
        cv.addWidget(b_ver)
        cv.addWidget(b_fechar)
        cv.addStretch()
        self.convite.hide()
        lay.addWidget(self.convite)

        # saldo e a situação da conta
        c, cl = _card()
        self.card_saldo = c
        linha = QHBoxLayout()
        self._saldo_rot = _rot("Saldo", "statKey")
        self.saldo = _rot("", "statVal")
        sc = QVBoxLayout()
        sc.setSpacing(0)
        sc.addWidget(self._saldo_rot)
        sc.addWidget(self.saldo)
        linha.addLayout(sc)
        linha.addStretch()
        cl.addLayout(linha)
        self.situacao = _rot("", None, "font-size:13px; font-weight:700;", wrap=True)
        cl.addWidget(self.situacao)
        lay.addWidget(c)

        # a lista de compras
        c, cl = _card("Lista de compras")
        self.card_lista = c
        barra = QHBoxLayout()
        self.b_adicionar = Botao("Adicionar item")
        _ico(self.b_adicionar, "mais", "primary")
        self.b_adicionar.setObjectName("primary")
        self.b_adicionar.clicked.connect(lambda: self.editar(None))
        barra.addWidget(self.b_adicionar)
        barra.addStretch()
        cl.addLayout(barra)
        self.vazio = _rot("Nenhum item ainda. Clique em Adicionar item, escolha o item e o preço máximo.", "muted", wrap=True)
        cl.addWidget(self.vazio)
        self.caixa_itens = QVBoxLayout()
        self.caixa_itens.setSpacing(8)
        cl.addLayout(self.caixa_itens)
        lay.addWidget(c)

        # segurança e ritmo (valem para todos os itens da conta)
        c, cl = _card("Segurança e ritmo")
        self.card_seguranca = c
        g = QGridLayout()
        g.setHorizontalSpacing(16)
        # olhar mais que a retenção (2 min) faria perder anúncio: o teto é 100 s (a rotina também limita)
        self.intervalo = _spin(INTERVALO_MIN_S, 100, INTERVALO_PADRAO_S, " s", 5)
        self.bloquear = QCheckBox("Nunca comprar anúncio das minhas outras contas do PokeNexus")
        self.bloquear.setToolTip("Os Termos do PokeIdle permitem negociar entre as suas contas pelo Mercado; "
                                 "com isto ligado o Mercado nunca faz isso sozinho (evita pagar taxa à toa)")
        self.intervalo.setMaximumWidth(280)
        self._rot_intervalo = _rot("Olhar a vitrine a cada")
        g.addWidget(self._rot_intervalo, 0, 0)
        g.addWidget(self.intervalo, 0, 1)
        g.addWidget(_rot("Sem abrir nada na tela. Todo anúncio novo fica retido 2 min, então olhar a cada "
                         "minuto já pega todos antes de liberar.", "muted", "font-size:11px;", wrap=True), 1, 0, 1, 3)
        g.addWidget(self.bloquear, 2, 0, 1, 3)
        g.setColumnStretch(2, 1)
        cl.addLayout(g)
        cl.addWidget(_rot("Mudou, já vale (fica salvo no perfil desta conta).", "muted", "font-size:11px;"))
        self.intervalo.valueChanged.connect(self._salvar_ajustes)
        self.bloquear.toggled.connect(self._salvar_ajustes)
        lay.addWidget(c)
        lay.addStretch()
        travar_roda(corpo, self.verticalScrollBar())

    # ------------------------------------------------------------ guia
    def set_convite(self, mostrar: bool):
        """Convite "Primeira vez aqui?" (só até a pessoa abrir o guia ou dispensar)."""
        self.convite.setVisible(mostrar)

    def _dispensar_convite(self):
        self.convite.hide()
        self.guia_visto.emit()

    def alvos_guia(self) -> dict:
        """As partes do painel que cada passo do guia destaca (app/textos_guia.py)."""
        primeiro = next(iter(self._cartoes.values()), None)
        return {
            "topo": [self._titulo, self._descricao],
            "saldo": [self.card_saldo],
            "adicionar": [self.b_adicionar],
            "interruptor": [primeiro.interruptor] if primeiro else [self.b_adicionar],
            "limites": [primeiro.limites] if primeiro else [self.vazio],
            "status": [primeiro.status] if primeiro else [self.situacao],
            "contadores": [primeiro.contadores] if primeiro else [self.vazio],
            "seguranca": [self.card_seguranca],
            "parar": [self.b_parar],
            "guia": [self.b_guia],
        }

    def abrir_guia(self):
        """Abre o guia por cima do painel. Ele só explica: não clica nem muda nada."""
        if self._guia is not None:
            return
        if self.convite.isVisible():
            self.convite.hide()
        self.guia_visto.emit()
        self._guia = Guia(self, PASSOS_GUIA, self.alvos_guia())
        self._guia.fechado.connect(self._guia_fechou)
        self._guia.abrir()

    def _guia_fechou(self, _motivo):
        self._guia = None

    # ------------------------------------------------------------ desenho
    def render(self, conta: int, worker):
        """Atualiza a tela (chamado a cada atualização; só refaz os cartões quando a lista muda)."""
        mudou_conta = conta != self.conta
        self.conta, self.worker = conta, worker
        rot = worker.rmt
        v = rot.view()
        if mudou_conta:
            cfg = v["config"]
            self.intervalo.blockSignals(True)
            self.intervalo.setValue(cfg.intervalo_s if cfg.intervalo_s >= INTERVALO_MIN_S else INTERVALO_PADRAO_S)
            self.intervalo.blockSignals(False)
            self.bloquear.blockSignals(True)
            self.bloquear.setChecked(cfg.bloquear_proprias)
            self.bloquear.blockSignals(False)
        s = v["saldo"]
        self.saldo.setText(f"{num(s['gold'])} ouro  {num(s['orb'])} gema")
        parada = rot._conta_parada() if any(i.ligado for i in v["itens"]) else None
        if not v["conectada"]:
            sit, cor = "A conta não está conectada: inicie a conta para o Mercado poder comprar.", T["dim"]
        elif parada:
            sit, cor = f"Parado: {parada}. Os itens ligados voltam sozinhos quando a conta voltar.", T["erro"]
        elif any(i.ligado for i in v["itens"]):
            sit, cor = ("Compra marcada para a liberação de um anúncio" if v["ocupado"]
                        else "De olho: olha a vitrine sem abrir nada na tela"), T["ok"]
        else:
            sit, cor = "Nenhum item ligado.", T["dim"]
        self.situacao.setText(sit)
        estilo = f"font-size:13px; font-weight:700; color:{cor};"
        if self.situacao.styleSheet() != estilo:
            self.situacao.setStyleSheet(estilo)
        estrutura = (conta, tuple(i.id for i in v["itens"]))
        if estrutura != self._estrutura:
            self._estrutura = estrutura
            for c in self._cartoes.values():
                self.caixa_itens.removeWidget(c)
                c.deleteLater()
            self._cartoes = {}
            for i in v["itens"]:
                c = CartaoItem(self, i)
                self._cartoes[i.id] = c
                self.caixa_itens.addWidget(c)
        self.vazio.setVisible(not v["itens"])
        for i in v["itens"]:
            self._cartoes[i.id].atualizar(i, v["status"].get(i.id), parada if i.ligado else None)

    # ------------------------------------------------------------ ações (thread da tela)
    def _lista(self):
        return self.worker.rmt.lista if self.worker else None

    def _salvar_ajustes(self, *_):
        lv = self._lista()
        if not lv:
            return
        c = lv.config
        c.intervalo_s, c.bloquear_proprias = self.intervalo.value(), self.bloquear.isChecked()
        lv.salvar()

    def alternar(self, iid: str):
        lv = self._lista()
        i = lv and lv.item(iid)
        if not i:
            return
        rot = self.worker.rmt
        if i.ligado:
            rot.desligar_item(iid)
            self._estrutura = None
            return
        m = NOME_MOEDA[i.moeda]
        resumo = (f"Conta: {self.worker.acc.name}\nItem: {i.item_nome}\nMoeda: {'Gema' if i.moeda == 'orb' else 'Ouro'}\n"
                  f"Preço máximo: {num(i.preco_max)} {m} por unidade\n{i.limites_txt()}\n\n"
                  f"Compra todo anúncio até esse preço assim que ele liberar (no fim da retenção do jogo).\n")
        if i.sem_limite:
            resumo += "Sem limite: vai comprar sem parar até você desligar.\n"
        resumo += ("Fica ligado mesmo se você fechar e abrir o PokeNexus. Para parar, clique em Ligado (ou em Parar "
                   "todas as compras).")
        gema = i.moeda == "orb"
        if not perguntar(self, "Ligar a compra", resumo, sim="Ligar", nao="Cancelar", perigo=gema or i.sem_limite,
                         destaque="A Gema vale dinheiro de verdade (USDT)." if gema else "",
                         exige="Entendi que a Gema vale dinheiro de verdade" if gema else ""):
            return
        rot.ligar_item(iid)
        self._estrutura = None

    def editar(self, iid):
        lv = self._lista()
        if not lv:
            return
        g = self.worker.game
        catalogo = list((g.mercado_info.get("catalogo") if g else None) or [])
        if not catalogo:
            avisar(self, "Mercado", "Inicie a conta primeiro: a lista de itens do Mercado vem do próprio jogo "
                                    "quando a conta conecta.")
            return
        base = lv.item(iid) if iid else None
        if base and base.ligado:
            avisar(self, "Mercado", "Desligue o item antes de editar.")
            return
        d = CompraDialog(self, catalogo, base)
        if d.exec() and d.item:
            if base:
                lv.itens[lv.itens.index(base)] = d.item
            else:
                lv.itens.append(d.item)
            lv.salvar()
            self.worker.log(f"Mercado: {'editou' if base else 'adicionou'} {d.item.resumo()} ({d.item.limites_txt()})")
            self._estrutura = None

    def remover(self, iid: str):
        lv = self._lista()
        i = lv and lv.item(iid)
        if i and perguntar(self, "Remover item", f"Tirar {i.item_nome} da lista de compras?", sim="Remover",
                           nao="Cancelar", perigo=True):
            if i.ligado:
                self.worker.rmt.desligar_item(iid)
            lv.itens.remove(i)
            lv.salvar()
            self._estrutura = None

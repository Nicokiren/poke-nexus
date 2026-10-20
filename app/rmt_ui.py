"""Mercado da conta selecionada: a lista de compras (um cartão por item), o saldo, os ajustes e o guia.
Só desenha e edita a lista; quem compra é rmt/rotina.py (compra na liberação, sem abrir nada na tela).

Cada item: o item do jogo, a moeda, o preço máximo por unidade e um interruptor Ligado/Desligado.
Ligado, compra todo anúncio até esse preço assim que ele libera, sem fim, a não ser que um limite
opcional diga para parar. Ligar pede confirmação com o resumo (sem limite: "vai comprar sem parar";
Gema: dinheiro de verdade, com uma caixa para marcar).
"""
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QValidator
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QSizePolicy, QSpinBox,
                               QVBoxLayout, QWidget)

from app import conversor_gemas as cg
from app.config import MODO_LEVE
from app.dialogos import avisar, perguntar
from app.guia import Guia
from app.icones import TAM as ICO_TAM, icone, por_nome_do_botao
from app.molduras import Botao, Moldura
from app.tema import T, carregar_fontes, px, qss_campos, qss_dialogo
from app.textos_guia import CONVITE_MERCADO, MERCADO as PASSOS_GUIA
from app.widgets import PixelSprite, travar_roda
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


# ============================================================ calculadora Gemas ⇄ dólares
class _Numero(QValidator):
    """Só deixa digitar o que app/conversor_gemas.py aceita (o resto o campo simplesmente não aceita)."""

    def __init__(self, dolares: bool, parent=None):
        super().__init__(parent)
        self.dolares = dolares

    def validate(self, texto, pos):
        ok = cg.entrada_valida(texto, self.dolares)
        return (QValidator.Acceptable if ok else QValidator.Invalid), texto, pos


class _Mascote(PixelSprite):
    """O Meowth da calculadora: anima como os outros mascotes, mas só com o Mercado à vista (escondido,
    animar é trabalho à toa). No Modo Leve fica parado no 1º quadro (o PixelSprite já faz isso)."""

    def _aplicar_pausa(self):
        if self._movie and not MODO_LEVE:
            self._movie.setPaused(not self._active or PixelSprite._pausa_global or not self.isVisible())

    def showEvent(self, ev):
        super().showEvent(ev)
        self._aplicar_pausa()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._aplicar_pausa()


class Balao(QLabel):
    """Balão de fala do mascote, em pixel: corpo creme com contorno e um rabinho de degraus para a esquerda."""
    RABO = 8

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"color:{T['sobre_destaque']}; font-size:12px; font-weight:800; background:transparent;")
        self.setContentsMargins(self.RABO + 8, 3, 10, 5)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def paintEvent(self, ev):
        p = QPainter(self)
        w, h, r = self.width(), self.height(), self.RABO
        borda, miolo = QColor(T["filete"]), QColor(T["texto"])
        p.fillRect(r + 2, 0, w - r - 4, h, borda)          # corpo, com os cantos de pixel cortados
        p.fillRect(r, 2, w - r, h - 4, borda)
        p.fillRect(r + 2, 2, w - r - 4, h - 4, miolo)
        cy = h // 2 - 1                                      # o rabinho aponta para o Meowth
        p.fillRect(4, cy - 4, r - 2, 2, borda)
        p.fillRect(2, cy - 2, 2, 2, borda)
        p.fillRect(0, cy, 2, 2, borda)
        p.fillRect(2, cy + 2, 2, 2, borda)
        p.fillRect(4, cy + 4, r - 2, 2, borda)
        p.fillRect(4, cy - 2, r, 2, miolo)
        p.fillRect(2, cy, r + 2, 2, miolo)
        p.fillRect(4, cy + 2, r, 2, miolo)
        p.end()
        super().paintEvent(ev)


class CalculadoraGemas(Moldura):
    """Gemas ⇄ dólares pela taxa de referência do usuário (app/conversor_gemas.py, num lugar só).

    SÓ CALCULA: não compra, não vende, não liga item, não mexe em Gema, USDT, carteira ou Pix, não grava
    nada em disco e não acessa a internet. A única coisa que lê é o saldo de Gemas que o painel já mostra
    (ficha "Meu saldo"). Digitar num campo atualiza o outro; o botão de setas troca qual fica de entrada."""

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self._saldo: int | None = None
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(6)
        v.addWidget(_rot("Calculadora de Gemas", "cardTitle"))

        meio = QHBoxLayout()
        meio.setSpacing(10)
        self.mascote = _Mascote(52, 56)                      # Meowth, o Pokémon que vive atrás de moedas
        meio.addWidget(self.mascote, 0, Qt.AlignTop)        # ao lado do balão (o rabinho aponta para ele)
        col = QVBoxLayout()
        col.setSpacing(4)
        self.balao = Balao()
        col.addWidget(self.balao, 0, Qt.AlignLeft)
        self.campos = QHBoxLayout()
        self.campos.setSpacing(6)
        self.c_gemas, self.e_gemas = self._campo("Gemas", False)
        self.c_dolares, self.e_dolares = self._campo("Dólares (US$)", True)
        self.b_inverter = Botao("")
        self.b_inverter.setIcon(icone("inverter"))
        self.b_inverter.setIconSize(ICO_TAM)
        self.b_inverter.setObjectName("tool")
        self.b_inverter.setCursor(Qt.PointingHandCursor)
        self.b_inverter.setToolTip("Inverter: troca qual campo é a entrada")
        self.b_inverter.clicked.connect(self.inverter)
        self.campos.addWidget(self.c_gemas, 1)
        self.campos.addWidget(self.b_inverter, 0, Qt.AlignBottom)
        self.campos.addWidget(self.c_dolares, 1)
        col.addLayout(self.campos)
        meio.addLayout(col, 1)
        v.addLayout(meio)

        fichas = QHBoxLayout()
        fichas.setSpacing(6)
        for n in (100, 1000, 10_000):
            b = Botao(cg.formatar_gemas(n))
            b.setObjectName("tool")
            b.setToolTip(f"{cg.formatar_gemas(n)} Gemas")
            b.clicked.connect(lambda _=False, n=n: self.usar_gemas(n))
            fichas.addWidget(b)
        self.b_saldo = Botao("Meu saldo")
        self.b_saldo.setObjectName("tool")
        self.b_saldo.clicked.connect(lambda: self._saldo is not None and self.usar_gemas(self._saldo))
        fichas.addWidget(self.b_saldo)
        # a soma das Gemas das contas conectadas (pedido do usuário, 19/10/2026)
        self._todas: tuple[int, int] | None = None          # (soma, quantas contas)
        self.b_todas = Botao("Saldo de todas as contas")
        self.b_todas.setObjectName("tool")
        self.b_todas.clicked.connect(lambda: self._todas is not None and self.usar_gemas(self._todas[0]))
        fichas.addWidget(self.b_todas)
        fichas.addStretch()
        for b in (fichas.itemAt(i).widget() for i in range(fichas.count())):
            if b:
                b.setCursor(Qt.PointingHandCursor)
        v.addLayout(fichas)

        base = QHBoxLayout()
        base.addWidget(_rot(cg.taxa_txt(), None, f"color:{T['texto']}; font-size:12px; font-weight:800;"))
        base.addStretch()
        base.addWidget(_rot("Valor de referência. Não é cotação nem saque.", "muted", "font-size:11px;"))
        v.addLayout(base)
        self.set_saldo(None)
        self.set_saldo_todas([])
        self._calcular("gemas")

    def _campo(self, rotulo: str, dolares: bool):
        caixa = QWidget()
        cv = QVBoxLayout(caixa)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(2)
        cv.addWidget(_rot(rotulo, "muted", "font-size:11px; font-weight:700;"))
        e = QLineEdit()
        e.setAccessibleName(rotulo)                # leitores de tela (e a automação dos testes) acham pelo nome
        e.setValidator(_Numero(dolares, e))
        e.setPlaceholderText("0,00" if dolares else "0")
        e.setStyleSheet(px(30))                    # números na fonte de pixel (uma vez só, aqui)
        e.setMinimumWidth(110)
        e.setToolTip("Dólares, com vírgula (até 2 casas)" if dolares else "Gemas (números inteiros)")
        e.textEdited.connect(lambda _t, q="dolares" if dolares else "gemas": self._calcular(q))
        cv.addWidget(e)
        return caixa, e

    # ------------------------------------------------------------ a conta
    def _calcular(self, fonte: str):
        """`fonte` é o campo que a pessoa mexeu; só o texto do outro muda (nada de estilo novo)."""
        if fonte == "gemas":
            texto = self.e_gemas.text()
            d = cg.gemas_para_dolares(cg.ler_gemas(texto))
            self.e_dolares.setText(cg.formatar_dolares(d) if texto else "")
        else:
            texto = self.e_dolares.text()
            d = cg.ler_dolares(texto)
            self.e_gemas.setText(cg.formatar_gemas(cg.dolares_para_gemas(d)) if texto else "")
        self.balao.setText(cg.frase_do_mascote(d))

    def usar_gemas(self, gemas: int):
        self.e_gemas.setText(cg.formatar_gemas(max(0, int(gemas))))
        self._calcular("gemas")

    def inverter(self):
        """Troca os campos de lugar: o da esquerda vira a entrada (recebe o cursor). Os números ficam."""
        esq, dir_ = self.campos.itemAt(0).widget(), self.campos.itemAt(2).widget()
        self.campos.removeWidget(esq)
        self.campos.removeWidget(dir_)
        self.campos.insertWidget(0, dir_, 1)
        self.campos.addWidget(esq, 1)
        e = self.e_gemas if dir_ is self.c_gemas else self.e_dolares
        e.setFocus(Qt.OtherFocusReason)
        e.selectAll()

    def entrada(self) -> str:
        """Qual campo está à esquerda (a entrada): "gemas" ou "dolares"."""
        return "gemas" if self.campos.itemAt(0).widget() is self.c_gemas else "dolares"

    def set_saldo(self, gemas):
        """As Gemas da conta selecionada que o painel já mostra (None = sem conta conectada)."""
        gemas = None if gemas is None else int(gemas)
        if gemas == self._saldo and self.b_saldo.toolTip():
            return
        self._saldo = gemas
        self.b_saldo.setEnabled(gemas is not None)
        self.b_saldo.setToolTip("Conecte a conta para usar o saldo dela" if gemas is None
                                else f"Usa as Gemas desta conta ({cg.formatar_gemas(gemas)})")

    def set_saldo_todas(self, saldos):
        """As Gemas de cada conta (None = conta sem conexão). A ficha usa a soma das conectadas."""
        vals = [int(g) for g in saldos if g is not None]
        novo = (sum(vals), len(vals)) if vals else None
        if novo == self._todas and self.b_todas.toolTip():
            return
        self._todas = novo
        self.b_todas.setEnabled(novo is not None)
        if novo is None:
            dica = "Conecte uma conta para usar a soma das Gemas"
        else:
            quem = "da conta conectada" if novo[1] == 1 else f"das {novo[1]} contas conectadas"
            dica = f"Soma as Gemas {quem} ({cg.formatar_gemas(novo[0])})"
        self.b_todas.setToolTip(dica)


# ============================================================ o painel
class RmtPanel(QScrollArea):
    """Os sinais levam a conta junto: o painel nunca mistura uma conta com outra."""
    parar_todos = Signal()         # desliga todas as compras, em todas as contas
    guia_visto = Signal()          # a pessoa já viu (ou dispensou) o guia
    _calc_aberta = False           # calculadora aberta ou fechada: só na memória (não vai para o config.toml)
    saldos = None                  # () -> [Gemas de cada conta, None = sem conexão] (a janela principal passa)

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

        # a calculadora de Gemas, perto do Saldo (os dois falam de dinheiro). Começa recolhida (escolha do
        # usuário, 16/10/2026): o botão Calculadora no Saldo abre e fecha, e lembra só enquanto o programa
        # está aberto. Fechada, o Mercado fica como era.
        self.b_calc = Botao("Calculadora")
        _ico(self.b_calc, "inverter")
        self.b_calc.setObjectName("tool")
        self.b_calc.setCheckable(True)
        self.b_calc.setCursor(Qt.PointingHandCursor)
        self.b_calc.setToolTip("Mostra ou esconde a calculadora de Gemas")
        self.b_calc.toggled.connect(self._mostrar_calc)
        linha.addWidget(self.b_calc, 0, Qt.AlignTop)
        self.calc = CalculadoraGemas()
        self.calc.setMaximumWidth(640)                       # em tela larga os campos não esticam à toa
        self.calc.hide()
        lay.addWidget(self.calc, 0, Qt.AlignLeft)
        self.b_calc.setChecked(RmtPanel._calc_aberta)

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
            "calculadora": [self.calc] if self.calc.isVisible() else [self.b_calc],   # fechada: o botão dela
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

    def _mostrar_calc(self, aberta: bool):
        RmtPanel._calc_aberta = aberta
        self.calc.setVisible(aberta)

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
        self.calc.set_saldo(s["orb"] if v["conectada"] else None)
        if self.saldos is not None:
            self.calc.set_saldo_todas(self.saldos())
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

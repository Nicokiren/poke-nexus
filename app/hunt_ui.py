"""Painel "Hunts" do PokeNexus: a análise da conta selecionada (só desenha; a conta é do
hunts/analyzer.py e a matemática do hunts/calculator.py)."""
import math

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QImageReader, QPixmap, QRegion
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QStyle, QStyledItemDelegate, QStyleOptionButton, QStyleOptionViewItem,
                               QStylePainter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.molduras import Botao, Moldura
from app.icones import TAM as ICO_TAM, icone
from app.config import ASSETS_DIR
from app.tema import T, UI_DIR, moldura
from app.widgets import SPRITES, _alpha_bbox, pixel_pixmap, pokemon_path

YELLOW = T["destaque"]
COR_RISCO = {"alto": T["erro"], "medio": T["aviso"], "baixo": T["ok"]}
REGIAO = {"kanto": "Kanto", "johto": "Johto", "outland": "Outland", "orre": "Orre", "hoenn": "Hoenn",
          "sinnoh": "Sinnoh", "unova": "Unova", "kalos": "Kalos", "alola": "Alola", "galar": "Galar",
          "paldea": "Paldea"}
ORDENS = (("xp", "XP/h"), ("ouro", "Ouro/h"), ("kills", "Abates/h"), ("risco", "Risco"))
MAX_DEX_SPRITE = 386          # sprites que o PokeNexus tem (Gen 1–3)


def num(v) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    return f"{int(math.floor(v + 0.5)):,}".replace(",", ".")


def segundos(s) -> str:
    if s is None or not math.isfinite(s):
        return "—"
    if s < 1:
        return "<1 s"
    if s < 60:
        return f"{s:.1f} s".replace(".", ",")
    return f"{int(s // 60)} min {int(s % 60 + 0.5)} s"


def regiao(r) -> str:
    return REGIAO.get(r, (r or "").capitalize())


def _icone(dex, altura=28) -> QPixmap | None:
    """Primeiro quadro da sprite do pokémon, recortado e nítido (só Gen 1–3)."""
    if not isinstance(dex, int) or not 1 <= dex <= MAX_DEX_SPRITE:
        return None
    img = QImageReader(str(pokemon_path(dex))).read()
    if img.isNull():
        return None
    r = _alpha_bbox(img)
    if r:
        img = img.copy(r)
    f = max(1, altura // max(1, img.height())) if img.height() < altura else 0
    if f:
        img = img.scaled(img.width() * f, img.height() * f, Qt.KeepAspectRatio, Qt.FastTransformation)
    else:
        img = img.scaledToHeight(altura, Qt.FastTransformation)
    return QPixmap.fromImage(img)


def _rotulo(texto="", obj=None, estilo=None, wrap=False) -> QLabel:
    l = QLabel(texto)
    if obj:
        l.setObjectName(obj)
    if estilo:
        l.setStyleSheet(estilo)
    l.setWordWrap(wrap)
    return l


def _card() -> tuple[QFrame, QVBoxLayout]:
    f = Moldura()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(8)
    return f, lay


def _risco(linha) -> tuple[str, str]:
    from hunts.analyzer import nivel_de_risco
    return nivel_de_risco(linha)


ATIVO, SLUG = Qt.UserRole + 1, Qt.UserRole + 2


class _ModeloBotao(Botao):
    """Um botão que se pinta igual a qualquer outro (o mesmo `Botao.paintEvent`), mas aceita "mouse
    em cima" por fora (`hover`): escondido, o Qt nunca marca hover."""


class _BotaoCacar(QStyledItemDelegate):
    """O botão "Caçar" de cada linha do ranking, desenhado pelo mesmo estilo de um QPushButton
    de verdade (mesma folha de estilo, hover e clique), sem criar um widget por linha: o ranking
    pode ter centenas de hunts e era redesenhado a cada recálculo."""

    def __init__(self, tabela: QTableWidget, coluna: int, ao_clicar):
        super().__init__(tabela)
        self.t, self.col, self.ao_clicar = tabela, coluna, ao_clicar
        self.modelo = _ModeloBotao("Caçar", tabela)       # só a referência de estilo; nunca aparece
        self.modelo.setObjectName("tool")
        self.modelo.setStyleSheet("padding:2px 10px; margin:3px 6px;")
        self.modelo.setProperty("margem", (6, 3, 6, 3))      # a mesma margem do QSS acima
        self.modelo.hide()
        self.hover = self.apertado = -1
        self._cache: dict[tuple, QPixmap] = {}
        tabela.setMouseTracking(True)
        tabela.viewport().setMouseTracking(True)       # hover sem botão apertado
        tabela.viewport().installEventFilter(self)

    def paint(self, p, opt, idx):
        super().paint(p, opt, idx)                         # o fundo/linha da célula, como antes
        area = self._area(opt.rect, idx)
        ativo = bool(idx.data(ATIVO))
        estado = (ativo, ativo and idx.row() == self.hover, ativo and idx.row() == self.apertado)
        p.drawPixmap(area.topLeft(), self._imagem(estado, area.size(), p.device().devicePixelRatioF()))

    def _imagem(self, estado, tamanho, dpr) -> QPixmap:
        """O próprio QPushButton de referência pintado naquele estado (ativo, hover, apertado):
        o mesmo desenho do botão-widget que existia antes. Cada estado é pintado uma vez só."""
        chave = (estado, tamanho.width(), tamanho.height(), dpr)
        pix = self._cache.get(chave)
        if pix is None:
            b = self.modelo
            ativo, hover, apertado = estado
            b.setEnabled(ativo)
            b.hover = hover
            b.setDown(apertado)
            b.resize(tamanho)
            pix = QPixmap(tamanho * dpr)
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.transparent)
            b.render(pix, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
            self._cache[chave] = pix
        return pix

    def _area(self, celula, idx):
        """A mesma área que o Qt dava ao botão-widget da célula (descontado o padding do item)."""
        vo = QStyleOptionViewItem()
        vo.initFrom(self.t)
        vo.rect = celula
        self.initStyleOption(vo, idx)
        vo.showDecorationSelected = True
        return self.t.style().subElementRect(QStyle.SE_ItemViewItemText, vo, self.t)

    def _linha(self, pos) -> int:
        idx = self.t.indexAt(pos)
        if not idx.isValid() or idx.column() != self.col:
            return -1
        return idx.row() if self._area(self.t.visualRect(idx), idx).contains(pos) else -1

    def eventFilter(self, obj, ev):
        tipo = ev.type()
        if tipo == QEvent.MouseMove:
            r = self._linha(ev.position().toPoint())
            if r != self.hover:
                self.hover = r
                obj.setCursor(Qt.PointingHandCursor if r >= 0 else Qt.ArrowCursor)
                obj.update()
        elif tipo == QEvent.Leave:
            if self.hover >= 0 or self.apertado >= 0:
                self.hover = self.apertado = -1
                obj.unsetCursor()
                obj.update()
        elif tipo == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            r = self._linha(ev.position().toPoint())
            if r >= 0:
                self.apertado = r
                obj.update()
        elif tipo == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton and self.apertado >= 0:
            r, self.apertado = self._linha(ev.position().toPoint()), -1
            obj.update()
            it = self.t.item(r, self.col) if r >= 0 else None
            if it is not None and r == self.hover and it.data(ATIVO):
                self.ao_clicar(it.data(SLUG))
        return False


class HuntPanel(QScrollArea):
    pref = Signal(str, object)     # (chave, valor) — opções desta conta
    cacar = Signal(str)            # slug: "Caçar aqui"
    recalcular = Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        corpo = QWidget()
        self.setWidget(corpo)
        lay = QVBoxLayout(corpo)
        lay.setContentsMargins(4, 4, 8, 8)
        lay.setSpacing(10)
        self._ultimo = None            # (conta, versão) desenhada
        self._dex_pk = None

        # ---- cabeçalho
        topo = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(_rotulo("Hunt Analyzer", "cardTitle"))
        col.addWidget(_rotulo("Onde caçar com o pokémon em campo desta conta, calculado com os dados "
                              "e as fórmulas do jogo no ar", "muted", "font-size:11px;", wrap=True))
        topo.addLayout(col, 1)
        self.status = _rotulo("", "muted", "font-size:11px;")
        topo.addWidget(self.status)
        b = Botao(" Recalcular")
        b.setIcon(icone("recarregar"))
        b.setIconSize(ICO_TAM)
        b.setObjectName("tool")
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip("Recalcula agora (o cálculo já se refaz sozinho quando algo da conta muda)")
        b.clicked.connect(self.recalcular.emit)
        topo.addWidget(b)
        lay.addLayout(topo)

        # ---- pokémon em campo
        self.card_pk, cl = _card()
        linha = QHBoxLayout()
        linha.setSpacing(14)
        self.sprite_box = QLabel()
        self.sprite_box.setFixedSize(84, 84)
        self.sprite_box.setAlignment(Qt.AlignCenter)
        linha.addWidget(self.sprite_box)
        info = QVBoxLayout()
        info.setSpacing(3)
        self.pk_nome = _rotulo("", None, "font-size:18px; font-weight:900;")
        self.pk_meta = _rotulo("", "muted", "font-size:12px;", wrap=True)
        info.addWidget(self.pk_nome)
        info.addWidget(self.pk_meta)
        self.stats_lay = QHBoxLayout()
        self.stats_lay.setSpacing(6)
        self.stats_lbl = {}
        for k, rot in (("hp", "HP"), ("atk", "ATK"), ("def", "DEF"), ("spAtk", "SP.ATK"), ("spDef", "SP.DEF"),
                       ("speed", "SPD")):
            l = _rotulo("", None, f"background:{T['trilho']}; border:2px solid {T['filete']};"
                                  "padding:3px 7px; font-size:11px;")
            self.stats_lbl[k] = (rot, l)
            self.stats_lay.addWidget(l)
        self.stats_lay.addStretch()
        info.addLayout(self.stats_lay)
        self.bonus = _rotulo("", "muted", "font-size:11px;", wrap=True)
        info.addWidget(self.bonus)
        linha.addLayout(info, 1)
        cl.addLayout(linha)
        lay.addWidget(self.card_pk)

        # ---- opções
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        ctrl.addWidget(_rotulo("Ordenar por", "muted", "font-size:12px;"))
        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.b_ordem = {}
        for chave, texto in ORDENS:
            bt = Botao(texto)
            bt.setObjectName("tool")
            bt.setCheckable(True)
            bt.setCursor(Qt.PointingHandCursor)
            bt.clicked.connect(lambda _c=False, k=chave: self.pref.emit("ordem", k))
            self.grupo.addButton(bt)
            self.b_ordem[chave] = bt
            ctrl.addWidget(bt)
        ctrl.addSpacing(10)
        self.cb_liberadas = QCheckBox("Mostrar apenas hunts disponíveis")
        self.cb_liberadas.setToolTip("Desmarcado: mostra todas, inclusive as que exigem um nível de treinador maior")
        self.cb_liberadas.clicked.connect(lambda v: self.pref.emit("so_liberadas", bool(v)))
        self.cb_pocao = QCheckBox("Considerar poção automática")
        self.cb_pocao.setToolTip("Com a poção automática ligada, só morre quem leva um golpe maior que o HP inteiro")
        self.cb_pocao.clicked.connect(lambda v: self.pref.emit("com_pocao", bool(v)))
        ctrl.addWidget(self.cb_liberadas)
        ctrl.addWidget(self.cb_pocao)
        ctrl.addStretch()
        lay.addLayout(ctrl)
        self.atual = _rotulo("", None, "font-size:12px;")
        lay.addWidget(self.atual)

        # ---- melhor hunt
        self.card_top = Moldura()
        self.card_top.setObjectName("card")
        self.card_top.setProperty("moldura", "selecionado")
        self.card_top.setStyleSheet(f"QFrame#card {{ background:{T['sel_fundo']}; {moldura('selecionado')} }}")
        ct = QVBoxLayout(self.card_top)
        ct.setContentsMargins(16, 12, 16, 14)
        ct.setSpacing(8)
        cab = QHBoxLayout()
        coroa = QLabel()
        coroa.setPixmap(pixel_pixmap(UI_DIR / "ico_hunts_ouro.png", 2))
        cab.addWidget(coroa)
        tcol = QVBoxLayout()
        tcol.setSpacing(0)
        tcol.addWidget(_rotulo("Melhor hunt agora", "cardTitle"))
        self.top_nome = _rotulo("", None, "font-size:20px; font-weight:900;")
        self.top_sub = _rotulo("", "muted", "font-size:12px;")
        tcol.addWidget(self.top_nome)
        tcol.addWidget(self.top_sub)
        cab.addLayout(tcol, 1)
        self.b_cacar_top = Botao(" Caçar aqui")
        self.b_cacar_top.setIcon(icone("hunts", "escuro"))
        self.b_cacar_top.setIconSize(ICO_TAM)
        self.b_cacar_top.setObjectName("primary")
        self.b_cacar_top.setCursor(Qt.PointingHandCursor)
        self.b_cacar_top.clicked.connect(lambda: self._top and self.cacar.emit(self._top))
        cab.addWidget(self.b_cacar_top, 0, Qt.AlignTop)
        ct.addLayout(cab)
        grade = QGridLayout()
        grade.setHorizontalSpacing(22)
        grade.setVerticalSpacing(6)
        self.top_vals = {}
        for i, (k, rot) in enumerate((("xp_pk", "XP/H DO POKÉMON"), ("xp_tr", "XP/H DO TREINADOR"),
                                      ("ouro", "OURO/H"), ("kph", "ABATES/H"), ("ttk", "TEMPO P/ DERROTAR"),
                                      ("golpe", "GOLPE RECOMENDADO"))):
            c = QVBoxLayout()
            c.setSpacing(0)
            c.addWidget(_rotulo(rot, "statKey"))
            v = _rotulo("—", "statVal")
            c.addWidget(v)
            grade.addLayout(c, i // 3, i % 3)
            self.top_vals[k] = v
        ct.addLayout(grade)
        self.top_risco = _rotulo("", None, "font-size:13px; font-weight:700;", wrap=True)
        ct.addWidget(self.top_risco)
        sel = QHBoxLayout()
        sel.setSpacing(6)
        sel.addWidget(_rotulo("Selvagens:", "muted", "font-size:12px;"))
        self.top_selv = QHBoxLayout()
        self.top_selv.setSpacing(8)
        sel.addLayout(self.top_selv)
        sel.addStretch()
        ct.addLayout(sel)
        self.top_real = _rotulo("", "muted", "font-size:12px;", wrap=True)
        ct.addWidget(self.top_real)
        lay.addWidget(self.card_top)
        self._top = None

        # ---- ranking
        rk, rl = _card()
        rl.addWidget(_rotulo("RANKING DE HUNTS", "cardTitle"))
        self.tabela = QTableWidget(0, 9)
        self.tabela.setHorizontalHeaderLabels(["#", "Hunt", "XP/h", "Ouro/h", "Abates/h", "Mata em", "Risco",
                                               "Real", ""])
        t = self.tabela
        t.verticalHeader().setVisible(False)
        t.setShowGrid(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        t.setFocusPolicy(Qt.NoFocus)
        t.setWordWrap(False)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(8, QHeaderView.Fixed)     # o botão "Caçar"
        t.setColumnWidth(8, 86)
        t.setItemDelegateForColumn(8, _BotaoCacar(t, 8, self.cacar.emit))
        t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(t)
        self.rodape = _rotulo("", "muted", "font-size:11px;", wrap=True)
        rl.addWidget(self.rodape)
        lay.addWidget(rk)
        self.vazio = _rotulo("", None, f"font-size:14px; color:{T['dim']}; padding:30px;", wrap=True)
        self.vazio.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.vazio)
        lay.addStretch()
        self._mostrar(False)

    # ------------------------------------------------------------ desenho
    def _mostrar(self, tem: bool):
        for w in (self.card_pk, self.card_top, self.tabela.parentWidget(), self.atual):
            w.setVisible(tem)
        self.vazio.setVisible(not tem)

    def render(self, conta: int, nome_conta: str, v: dict):
        """Desenha a análise `v` (HuntAnalyzer.view) — só quando ela mudou."""
        st = v.get("status", "")
        self.status.setText("" if st == "ok" else st)
        prefs = v["prefs"]
        self.b_ordem[prefs["ordem"]].setChecked(True)
        self.cb_liberadas.setChecked(prefs["so_liberadas"])
        self.cb_pocao.setChecked(prefs["com_pocao"])
        chave = (conta, v.get("version"))
        if chave == self._ultimo:
            return
        self._ultimo = chave
        r = v.get("result")
        if not r:
            self._mostrar(False)
            self.vazio.setText(f"{nome_conta}: {st}" if st else f"{nome_conta}: sem dados ainda")
            return
        self._mostrar(True)
        self._pokemon(r)
        self._melhor(r)
        self._ranking(r)

    def _pokemon(self, r):
        pk, esp = r["pokemon"], r["especie"] or {}
        dex = pk.get("speciesId")
        if dex != self._dex_pk:
            self._dex_pk = dex
            pix = _icone(dex, 72)
            self.sprite_box.setPixmap(pix or pixel_pixmap(ASSETS_DIR / "marca" / "logo_1x.png", 4))
        nome = pk.get("nome") or esp.get("nome") or f"#{dex}"
        self.pk_nome.setText(f"{nome}  ·  Nv {num(pk.get('level'))}")
        q = pk.get("quality", pk.get("qualidade"))
        ivs = pk.get("ivs") or {}
        partes = [f"P{pk.get('potencia') or 1}"]
        if isinstance(q, (int, float)):
            partes.append(f"Q {q:.3f}".replace(".", ","))
        if ivs:
            partes.append(f"IV {sum(int(x or 0) for x in ivs.values())}")
        if pk.get("refino"):
            partes.append("refinado")
        if pk.get("tmElemental"):
            partes.append(f"TM {pk['tmElemental']}")
        if r.get("aoe"):
            a = r["aoe"]
            cal = f"calibrado em {a['calibrado_em']} hunt(s)" if a["calibrado_em"] else "padrão"
            partes.append(f"TM AoE ({a['alvos_por_golpe']:.1f} alvos/golpe, {cal})".replace(".", ","))
        tipos = " / ".join(t for t in (esp.get("type1"), esp.get("type2")) if t)
        self.pk_meta.setText("  ·  ".join(partes + ([tipos] if tipos else [])))
        for k, (rot, l) in self.stats_lbl.items():
            iv = ivs.get(k)
            l.setText(f"<b>{rot}</b> {num((pk.get('stats') or {}).get(k))}" + (f" <span style='color:{T["dim"]}'>IV {iv}</span>" if iv is not None else ""))
        b = r.get("bonus_xp") or {}
        itens = b.get("itens") or []
        if itens:
            fmt = lambda i: f"{i['nome']} " + (f"×{i['mult']:.2f}" if i["mult"] >= 2 else f"+{(i['mult'] - 1) * 100:.1f}%")
            total = (f"×{b['pokemon']:.2f}" if abs(b["pokemon"] - b["treinador"]) < 1e-6
                     else f"pokémon ×{b['pokemon']:.2f} · treinador ×{b['treinador']:.2f}")
            self.bonus.setText(("Bônus de XP: " + " · ".join(fmt(i) for i in itens) + f"  =  {total}").replace(".", ","))
        else:
            self.bonus.setText("Bônus de XP: nenhum ativo")

    def _melhor(self, r):
        top = r.get("melhor")
        atual = r.get("atual")
        self.atual.setText(f"Hunt atual: <b>{atual['nome']}</b> ({regiao(atual['regiao'])} · Nv {num(atual['nivel'])})"
                           if atual else "Hunt atual: nenhuma (a conta não está numa hunt)")
        self.card_top.setVisible(bool(top))
        self._top = top["slug"] if top else None
        if not top:
            return
        self.top_nome.setText(top["nome"] + ("   ◉ atual" if atual and atual["slug"] == top["slug"] else ""))
        self.top_sub.setText(f"{regiao(top['regiao'])} · Nv {num(top['nivel'])}"
                             + ("" if top["liberada"] else " · 🔒 nível de treinador insuficiente"))
        self.b_cacar_top.setEnabled(top["liberada"] and not (atual and atual["slug"] == top["slug"]))
        v = self.top_vals
        v["xp_pk"].setText(num(top["xp_pokemon_h"]))
        v["xp_tr"].setText(num(top["xp_treinador_h"]))
        v["ouro"].setText(num(top["ouro_h"]))
        v["kph"].setText(num(top["kph"]) + (" (AoE)" if top.get("aoe") else ""))
        v["ttk"].setText(segundos(top["ttk"]))
        g = top.get("melhor_golpe")
        v["golpe"].setText(f"{g['nome']} ×{top['efetividade']:.2f}".replace(".", ",") if g else "—")
        nivel, texto = _risco(top)
        pior = f" · pior golpe recebido: {num(top['hit_pior'])} de {num(top['hp_pk'])} HP" if "hit_pior" in top else ""
        self.top_risco.setText(f"Risco: {texto}{pior}")
        self.top_risco.setStyleSheet(f"font-size:13px; font-weight:700; color:{COR_RISCO[nivel]};")
        while self.top_selv.count():
            it = self.top_selv.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for pid, nome in zip(top["especies"], top["selvagens"]):
            ic = _icone(pid, 26)
            if ic:
                l = QLabel()
                l.setPixmap(ic)
                self.top_selv.addWidget(l)
            self.top_selv.addWidget(_rotulo(nome, None, "font-size:12px; font-weight:700;"))
        real = r.get("real") if atual and atual["slug"] == top["slug"] else None
        self.top_real.setText(self._texto_real(top, real))

    @staticmethod
    def _texto_real(linha, real) -> str:
        partes = []
        if real:
            partes.append(f"Desempenho real nesta caçada: {num(real['kph'])} abates/h, {num(real['xp_h'])} XP/h do "
                          f"treinador em {segundos(real['seg'])}")
        if linha.get("kph_medido"):
            partes.append(f"Histórico medido com este pokémon aqui: {num(linha['kph_medido'])} abates/h")
        if not partes:
            return "Estimativa (onda cheia). Desempenho real: aparece depois de caçar aqui com este pokémon."
        return "Estimativa (onda cheia) acima.  " + "  ·  ".join(partes) + "  (referência; não muda o ranking)"

    def _ranking(self, r):
        linhas = r["linhas"]
        atual = r.get("atual_slug")
        real = r.get("real")
        t = self.tabela
        t.setUpdatesEnabled(False)
        # Colunas "do tamanho do conteúdo" ficam paradas enquanto a tabela é preenchida e se
        # ajustam uma vez no fim (o Qt reajustaria a cada célula: centenas de hunts = segundos).
        hh = t.horizontalHeader()
        modos = [hh.sectionResizeMode(c) for c in range(t.columnCount())]
        for c, modo in enumerate(modos):
            if modo == QHeaderView.ResizeToContents:
                hh.setSectionResizeMode(c, QHeaderView.Fixed)
        t.clearContents()
        t.setRowCount(len(linhas))
        cinza, fundo_atual = QColor(T["apagado"]), QColor(T["sel_fundo"])
        for i, l in enumerate(linhas):
            nivel, texto = _risco(l)
            eh_atual = l["slug"] == atual
            hunt = f"{'◉ ' if eh_atual else ''}{l['nome']}   {regiao(l['regiao'])} · Nv {num(l['nivel'])}" \
                   f"{'' if l['liberada'] else '  🔒'}"
            if l["inviavel"]:
                vals = [str(i + 1), hunt, "—", "—", "—", "—", "não derrota o selvagem", "—"]
            else:
                medido = real["kph"] if eh_atual and real else l.get("kph_medido")
                vals = [str(i + 1), hunt, num(l["xp_pokemon_h"]), num(l["ouro_h"]),
                        ("≈AoE " if l.get("aoe") else "") + num(l["kph"]), segundos(l["ttk"]),
                        texto.split(" — ")[0] + (" · 1 golpe" if l["um_hit"] else
                                                 f" · {math.floor(l['hit_pct'] * 100 + 0.5)}%"),
                        f"{num(medido)}/h" if medido else "—"]
            g = l.get("melhor_golpe")
            dica = (f"Selvagens: {', '.join(l['selvagens'])}\nGolpe recomendado: {g['nome']} ×{l['efetividade']:.2f}\n"
                    f"XP/h do treinador: {num(l['xp_treinador_h'])}\nRisco: {texto}"
                    + ("" if l.get("geo_medida") else "\nGeometria padrão (≈): ainda sem onda cheia medida aqui")
                    if g else texto)
            for c, txt in enumerate(vals):
                it = QTableWidgetItem(txt)
                it.setToolTip(dica)
                if c >= 2:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 6:
                    it.setForeground(QColor(COR_RISCO[nivel]))
                elif not l["liberada"]:
                    it.setForeground(cinza)
                if eh_atual:
                    it.setBackground(fundo_atual)
                    if c == 1:
                        f = it.font(); f.setBold(True); it.setFont(f)
                t.setItem(i, c, it)
            bt = QTableWidgetItem()
            bt.setData(ATIVO, l["liberada"] and not l["inviavel"] and not eh_atual)
            bt.setData(SLUG, l["slug"])
            t.setItem(i, 8, bt)
            t.setRowHeight(i, 32)
        for c, modo in enumerate(modos):
            hh.setSectionResizeMode(c, modo)
        t.setFixedHeight(t.horizontalHeader().height() + 32 * len(linhas) + 4)
        t.setUpdatesEnabled(True)
        aoe = r.get("aoe")
        self.rodape.setText(
            f"Dados do jogo v{r.get('versao_jogo') or '?'} · {len(linhas)} de {r['total']} hunts · cálculo em "
            f"{r['ms']} ms · ranking com ondas cheias, igual para todas as hunts (a atual não ganha vantagem) · "
            f"geometria medida em {r.get('hunts_medidas', 0)} hunt(s) — ≈ = padrão"
            + (f" · TM AoE: {aoe['alvos_por_golpe']:.1f} alvos/golpe".replace(".", ",") if aoe else "")
            + " · Real = abates/h medidos (referência)")

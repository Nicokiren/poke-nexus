"""Guia passo a passo por cima de uma tela (tutorial): escurece o resto, destaca a parte explicada com
uma moldura dourada e mostra uma caixa com o texto, Voltar, Próximo e "Pular guia".

Só explica: a camada fica por cima e não deixa clicar no painel enquanto está aberta, não mexe no
layout e não muda nada da tela. Não tem timer nem animação, e só existe enquanto o guia está aberto
(fechou = apagada).

Uso:
    Guia(painel, passos, alvos).abrir()
`passos`: [{"alvo": nome | None, "titulo": str, "texto": str}] (app/textos_guia.py)
`alvos`: {nome: widget ou [widgets]} (o destaque cobre todos juntos)
"""
from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.icones import TAM as ICO_TAM, icone
from app.molduras import Botao, Moldura
from app.tema import T

LARGURA_CAIXA = 380
FOLGA = 12                  # entre o destaque e a caixa
MARGEM = 8                  # a caixa nunca encosta na borda


class Guia(QWidget):
    fechado = Signal(str)       # "fim" | "pulou"

    def __init__(self, painel: QWidget, passos: list[dict], alvos: dict):
        super().__init__(painel)
        self.painel, self.passos, self.alvos = painel, passos, alvos
        self.i = 0
        self.destaque = QRect()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.StrongFocus)
        self.caixa = self._montar_caixa()
        painel.installEventFilter(self)
        if isinstance(painel, QAbstractScrollArea):
            painel.verticalScrollBar().valueChanged.connect(self._reposicionar)

    # ------------------------------------------------------------ caixa
    def _montar_caixa(self) -> Moldura:
        c = Moldura(self)
        c.setObjectName("card")
        c.setFixedWidth(LARGURA_CAIXA)
        v = QVBoxLayout(c)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(6)
        topo = QHBoxLayout()
        self.titulo = QLabel()
        self.titulo.setObjectName("cardTitle")
        self.titulo.setWordWrap(True)
        topo.addWidget(self.titulo, 1)
        self.b_pular = Botao(" Pular guia")
        self.b_pular.setObjectName("tool")
        self.b_pular.setIcon(icone("excluir"))
        self.b_pular.setIconSize(ICO_TAM)
        self.b_pular.setToolTip("Fecha o guia (Esc)")
        self.b_pular.clicked.connect(lambda: self.fechar("pulou"))
        topo.addWidget(self.b_pular, 0, Qt.AlignTop)
        v.addLayout(topo)
        self.texto = QLabel()
        self.texto.setWordWrap(True)
        self.texto.setTextFormat(Qt.PlainText)
        v.addWidget(self.texto)
        base = QHBoxLayout()
        self.contador = QLabel()
        self.contador.setObjectName("muted")
        base.addWidget(self.contador)
        base.addStretch()
        self.b_voltar = Botao(" Voltar")
        self.b_voltar.setObjectName("tool")
        self.b_voltar.setIcon(icone("mostrar"))    # setas para a esquerda
        self.b_voltar.setIconSize(ICO_TAM)
        self.b_voltar.clicked.connect(self.voltar)
        self.b_proximo = Botao(" Próximo")
        self.b_proximo.setObjectName("primary")
        self.b_proximo.clicked.connect(self.avancar)
        for b in (self.b_pular, self.b_voltar, self.b_proximo):
            b.setFocusPolicy(Qt.NoFocus)       # o teclado fica com o guia (Esc, Enter, setas)
            b.setCursor(Qt.PointingHandCursor)
        base.addWidget(self.b_voltar)
        base.addWidget(self.b_proximo)
        v.addLayout(base)
        return c

    # ------------------------------------------------------------ navegação
    def abrir(self):
        self.setGeometry(self.painel.rect())
        self.show()
        self.raise_()
        self.setFocus(Qt.OtherFocusReason)
        self._mostrar()
        return self

    def avancar(self):
        if self.i >= len(self.passos) - 1:
            return self.fechar("fim")
        self.i += 1
        self._mostrar()

    def voltar(self):
        if self.i > 0:
            self.i -= 1
            self._mostrar()

    def fechar(self, motivo: str = "pulou"):
        if getattr(self, "_fechou", False):
            return
        self._fechou = True
        self.painel.removeEventFilter(self)
        if isinstance(self.painel, QAbstractScrollArea):
            try:
                self.painel.verticalScrollBar().valueChanged.disconnect(self._reposicionar)
            except (RuntimeError, TypeError):
                pass
        self.fechado.emit(motivo)
        self.close()          # WA_DeleteOnClose: some de vez

    def _mostrar(self):
        p = self.passos[self.i]
        n = len(self.passos)
        self.titulo.setText(p["titulo"])
        self.texto.setText(p["texto"])
        self.contador.setText(f"Passo {self.i + 1} de {n}")
        self.b_voltar.setEnabled(self.i > 0)
        ultimo = self.i == n - 1
        self.b_proximo.setText(" Entendi" if ultimo else " Próximo")
        self.b_proximo.setIcon(icone("comecar", "escuro"))
        self.b_proximo.setIconSize(ICO_TAM)
        widgets = self._widgets(p.get("alvo"))
        if widgets and isinstance(self.painel, QAbstractScrollArea) and hasattr(self.painel, "ensureWidgetVisible"):
            self.painel.ensureWidgetVisible(widgets[0], 20, 24)     # rola até a parte, se preciso
        self._reposicionar()

    def _widgets(self, nome) -> list[QWidget]:
        if not nome:
            return []
        w = self.alvos.get(nome)
        lista = w if isinstance(w, (list, tuple)) else [w]
        return [x for x in lista if x is not None and x.isVisible()]

    # ------------------------------------------------------------ geometria
    def _area_visivel(self) -> QRect:
        if isinstance(self.painel, QAbstractScrollArea):
            vp = self.painel.viewport()
            return QRect(vp.mapTo(self.painel, QPoint(0, 0)), vp.size())
        return self.rect()

    def _reposicionar(self, *_):
        self.setGeometry(self.painel.rect())
        visivel = self._area_visivel()
        r = QRect()
        for w in self._widgets(self.passos[self.i].get("alvo")):
            r = r.united(QRect(w.mapTo(self.painel, QPoint(0, 0)), w.size()))
        self.destaque = r.adjusted(-6, -6, 6, 6).intersected(visivel) if not r.isNull() else QRect()
        # altura certa para o texto com quebra de linha (o adjustSize sozinho cortava a última linha)
        self.caixa.resize(LARGURA_CAIXA, self.caixa.layout().totalHeightForWidth(LARGURA_CAIXA))
        self.caixa.move(self._lugar_da_caixa(self.caixa.size(), self.destaque, self.rect()))
        self.update()

    @staticmethod
    def _lugar_da_caixa(tam, alvo: QRect, area: QRect) -> QPoint:
        """Perto da parte destacada, sem cobrir ela e sem sair da área. Tenta embaixo, em cima, à
        direita e à esquerda; se nada couber inteiro, fica no canto que menos cobre."""
        a = area.adjusted(MARGEM, MARGEM, -MARGEM, -MARGEM)
        w, h = tam.width(), tam.height()

        def preso(x, y):
            return QPoint(max(a.left(), min(x, a.right() - w + 1)), max(a.top(), min(y, a.bottom() - h + 1)))

        if alvo.isNull():
            return preso(a.center().x() - w // 2, a.center().y() - h // 2)
        tentativas = [
            preso(alvo.left(), alvo.bottom() + FOLGA),
            preso(alvo.left(), alvo.top() - FOLGA - h),
            preso(alvo.right() + FOLGA, alvo.top()),
            preso(alvo.left() - FOLGA - w, alvo.top()),
        ]
        for pt in tentativas:
            if not QRect(pt, tam).intersects(alvo):
                return pt
        cantos = [preso(a.right(), a.bottom()), preso(a.left(), a.bottom()), preso(a.right(), a.top()),
                  preso(a.left(), a.top())]

        def cobre(pt):
            i = QRect(pt, tam).intersected(alvo)
            return i.width() * i.height()
        return min(cantos, key=cobre)

    # ------------------------------------------------------------ desenho e eventos
    def paintEvent(self, _ev):
        p = QPainter(self)
        sombra = QColor(T["fundo"])
        sombra.setAlpha(170)
        r, toda = self.destaque, self.rect()
        if r.isNull():
            p.fillRect(toda, sombra)
            return
        # o escuro em volta (4 retângulos), a parte explicada fica clara
        p.fillRect(QRect(toda.left(), toda.top(), toda.width(), r.top() - toda.top()), sombra)
        p.fillRect(QRect(toda.left(), r.bottom() + 1, toda.width(), toda.bottom() - r.bottom()), sombra)
        p.fillRect(QRect(toda.left(), r.top(), r.left() - toda.left(), r.height()), sombra)
        p.fillRect(QRect(r.right() + 1, r.top(), toda.right() - r.right(), r.height()), sombra)
        p.setPen(QPen(QColor(T["filete"]), 2))
        p.drawRect(r.adjusted(-2, -2, 2, 2))
        p.setPen(QPen(QColor(T["destaque"]), 3))
        p.drawRect(r)

    def keyPressEvent(self, ev):
        k = ev.key()
        if k == Qt.Key_Escape:
            self.fechar("pulou")
        elif k in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Right):
            self.avancar()
        elif k == Qt.Key_Left:
            self.voltar()
        else:
            ev.accept()       # nenhuma outra tecla passa para o painel enquanto o guia está aberto

    def mousePressEvent(self, ev):
        ev.accept()           # clicar fora da caixa não faz nada (nem atravessa para o painel)

    def wheelEvent(self, ev):
        if isinstance(self.painel, QAbstractScrollArea):     # a roda ainda rola o painel
            QApplication.sendEvent(self.painel.verticalScrollBar(), ev)
        ev.accept()

    def eventFilter(self, obj, ev):
        if obj is self.painel:
            if ev.type() == QEvent.Resize:
                self._reposicionar()
            elif ev.type() == QEvent.Hide:
                self.fechar("pulou")       # trocou de tela: o guia fecha junto
        return False

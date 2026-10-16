"""Avisos e perguntas no tema do PokeNexus (no lugar das janelas QMessageBox do Windows).

Mesmo comportamento das janelas de antes: `perguntar` só devolve True se a pessoa escolher "Sim"
(fechar no X ou apertar Esc conta como "Não"), e `avisar` só mostra a mensagem e espera o OK. Os
botões ficam em português (as do Windows apareciam como "Yes"/"No", porque o pacote não leva as
traduções do Qt).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout

from app.icones import status_png
from app.molduras import Botao
from app.tema import T, carregar_fontes, qss_dialogo

# ícone (de status) por tipo de mensagem
_ICONE = {"pergunta": "AGUARDANDO", "info": "FARMING", "aviso": "BATALHA", "erro": "ERRO"}


class Dialogo(QDialog):
    def __init__(self, parent, titulo: str, texto: str, tipo: str = "info",
                 botoes=(("OK", "primary", True),), destaque: str = "", exige: str = ""):
        super().__init__(parent)
        carregar_fontes()
        self.setWindowTitle(titulo)
        self.setStyleSheet(qss_dialogo())
        self.setMinimumWidth(380)
        self.setMaximumWidth(640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)
        topo = QHBoxLayout()
        topo.setSpacing(12)
        ic = QLabel()
        pix = QPixmap(status_png(_ICONE.get(tipo, "FARMING")))
        ic.setPixmap(pix.scaled(pix.width() * 2, pix.height() * 2, Qt.KeepAspectRatio, Qt.FastTransformation))
        ic.setAlignment(Qt.AlignTop)
        topo.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(4)
        t = QLabel(titulo)
        t.setObjectName("cardTitle")
        col.addWidget(t)
        msg = QLabel(texto)
        msg.setWordWrap(True)
        msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
        col.addWidget(msg)
        if destaque:          # aviso que não pode passar batido (ex.: Gema = dinheiro de verdade)
            d = QLabel(destaque)
            d.setWordWrap(True)
            d.setStyleSheet(f"color:{T['erro']}; font-weight:800; font-size:14px;")
            col.addWidget(d)
        self.marcar = None
        if exige:             # caixa que a pessoa tem de marcar para o "Sim" funcionar
            self.marcar = QCheckBox(exige)
            self.marcar.setStyleSheet(f"color:{T['texto']}; font-size:13px; font-weight:700;")
            col.addWidget(self.marcar)
        topo.addLayout(col, 1)
        lay.addLayout(topo)
        base = QHBoxLayout()
        base.addStretch()
        self.resposta = False
        padrao = None
        for rotulo, estilo, valor in botoes:
            b = Botao(rotulo)
            if estilo:
                b.setObjectName(estilo)
            b.setMinimumWidth(96)
            b.setAutoDefault(False)          # o botão com foco não vira o "Enter" sozinho
            b.clicked.connect(lambda _=False, v=valor: self._fim(v))
            base.addWidget(b)
            if valor is False or len(botoes) == 1:
                padrao = b                   # numa pergunta, Enter = "Não" (como antes)
            if valor is True and self.marcar is not None:
                b.setEnabled(False)
                self.marcar.toggled.connect(b.setEnabled)
        lay.addLayout(base)
        if padrao is not None:
            padrao.setDefault(True)
            padrao.setFocus()

    def _fim(self, valor: bool):
        self.resposta = valor
        self.accept()


def perguntar(parent, titulo: str, texto: str, sim: str = "Sim", nao: str = "Não",
              perigo: bool = False, destaque: str = "", exige: str = "") -> bool:
    """Pergunta de sim/não. True só com "Sim"; fechar, Esc ou "Não" = False. `exige`: uma caixa que
    tem de estar marcada para o "Sim" funcionar."""
    d = Dialogo(parent, titulo, texto, "pergunta",
                ((sim, "danger" if perigo else "primary", True), (nao, None, False)), destaque, exige)
    d.exec()
    return d.resposta


def avisar(parent, titulo: str, texto: str, tipo: str = "info") -> None:
    """Mensagem com um OK (tipo: info, aviso ou erro)."""
    Dialogo(parent, titulo, texto, tipo).exec()

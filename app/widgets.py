"""Widgets visuais: sprites em pixel art nítidas, selo de status e fundo de tábuas."""
import math
import weakref
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QImage, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QGraphicsColorizeEffect, QLabel,
                               QWidget)

from app.config import ASSETS_DIR, MODO_LEVE
from app.icones import status_png
from app.tema import T, px, rgba, status_cor, status_nome

SPRITES = ASSETS_DIR / "sprites"


def status_color(status: str) -> str:
    return status_cor(status)


class _SemRoda(QObject):
    def __init__(self, dono, barra):
        super().__init__(dono)
        self.barra = barra

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel:
            if self.barra is not None:
                QApplication.sendEvent(self.barra, ev)     # rola a janela, como em qualquer outro lugar
            return True
        return False


def travar_roda(container: QWidget, barra=None):
    """A roda do mouse NÃO muda números nem listas de escolha dentro de `container` (rola `barra`, se
    houver). Rolando a janela, o cursor passava pelas caixas e ia mudando valores sem ninguém ver —
    foi assim que "Contas no programa" caiu de 4 para 1. Para mudar: clicar e digitar ou usar as setas."""
    filtro = _SemRoda(container, barra)
    for w in container.findChildren(QAbstractSpinBox) + container.findChildren(QComboBox):
        w.setFocusPolicy(Qt.StrongFocus)
        w.installEventFilter(filtro)


def pokemon_path(dex: int) -> Path:
    p = SPRITES / "pokemon" / f"{dex}.gif"
    return p if p.exists() else SPRITES / "pokemon" / "25.gif"


def pixel_pixmap(path: Path, factor: int) -> QPixmap:
    """PNG pequeno ampliado por um fator inteiro, sem suavização."""
    img = QImage(str(path))
    if img.isNull():
        return QPixmap()
    return QPixmap.fromImage(img.scaled(img.width() * factor, img.height() * factor,
                                        Qt.IgnoreAspectRatio, Qt.FastTransformation))


def _alpha_bbox(img: QImage) -> QRect | None:
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h, stride = img.width(), img.height(), img.bytesPerLine()
    data = bytes(img.constBits())
    xs, ys = [], []
    for y in range(h):
        row = data[y * stride: y * stride + w * 4]
        alphas = row[3::4]
        if any(a > 16 for a in alphas):
            ys.append(y)
            first = next(i for i, a in enumerate(alphas) if a > 16)
            last = w - 1 - next(i for i, a in enumerate(reversed(alphas)) if a > 16)
            xs += [first, last]
    if not ys:
        return None
    return QRect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


class PixelSprite(QLabel):
    """GIF animado de Pokémon, recortado no desenho e ampliado só em fatores
    inteiros (vizinho mais próximo) para manter o pixel nítido."""

    _crop_cache: dict[str, QRect] = {}
    # Quadros já recortados e ampliados, por (arquivo, tamanho): cada quadro é preparado uma vez
    # e reaproveitado em todas as voltas da animação (e por todos os widgets do mesmo tamanho).
    _frames: dict[tuple, dict[int, QPixmap]] = {}
    _todos = weakref.WeakSet()
    _pausa_global = False          # app minimizado: nenhuma animação roda

    def __init__(self, dex: int, box: int, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(box, box)
        self._box = box
        self._movie: QMovie | None = None
        self._active = True
        self._key = None
        PixelSprite._todos.add(self)
        self._grey = QGraphicsColorizeEffect(self)
        self._grey.setColor(QColor(T["sprite_cinza"]))
        self._grey.setStrength(1.0)
        self._grey.setEnabled(False)
        self.setGraphicsEffect(self._grey)
        self.set_dex(dex)

    def set_dex(self, dex: int):
        if self._movie:
            self._movie.stop()
            self._movie.deleteLater()
        path = pokemon_path(dex)
        self._movie = QMovie(str(path), parent=self)
        if not self._movie.isValid():
            return
        key = str(path)
        if key not in self._crop_cache:
            self._crop_cache[key] = self._union_crop()
        self._crop = self._crop_cache[key]
        side = max(self._crop.width(), self._crop.height())
        self._factor = max(1, self._box // side) if side <= self._box else 1 / math.ceil(side / self._box)
        self._key = (key, self._box)
        if MODO_LEVE:
            # Modo Leve: o 1º quadro, parado (mesmo recorte e tamanho); a animação nem começa.
            self._movie.jumpToFrame(0)
            self._render(0)
            return
        self._movie.frameChanged.connect(self._render)
        self._movie.start()
        self._aplicar_pausa()

    def _union_crop(self) -> QRect:
        m = self._movie
        full = QRect(0, 0, 96, 96)
        union = None
        for i in range(max(1, m.frameCount())):
            m.jumpToFrame(i)
            img = m.currentImage()
            full = img.rect()
            r = _alpha_bbox(img)
            if r:
                union = r if union is None else union.united(r)
        m.jumpToFrame(0)
        union = union or full
        side = max(union.width(), union.height())
        c = union.center()
        sq = QRect(c.x() - side // 2, c.y() - side // 2, side, side)
        return sq.intersected(full)

    def _render(self, n=None):
        quadros = self._frames.setdefault(self._key, {})
        n = self._movie.currentFrameNumber() if n is None else n
        pix = quadros.get(n)
        if pix is None:
            img = self._movie.currentImage()
            if img.isNull():
                return
            img = img.copy(self._crop)
            f = self._factor
            img = img.scaled(max(1, int(img.width() * f)), max(1, int(img.height() * f)),
                             Qt.IgnoreAspectRatio, Qt.FastTransformation)
            pix = quadros[n] = QPixmap.fromImage(img)
        self.setPixmap(pix)

    def _aplicar_pausa(self):
        if self._movie and not MODO_LEVE:
            self._movie.setPaused(not self._active or PixelSprite._pausa_global)

    def set_active(self, active: bool):
        """Ativo = animando e colorido. Inativo = parado e acinzentado."""
        if active == self._active and self._movie and (MODO_LEVE or self._movie.state() != QMovie.NotRunning):
            return
        self._active = active
        self._aplicar_pausa()
        self._grey.setEnabled(not active)

    @classmethod
    def pausar_todas(cls, pausar: bool):
        """Com a janela minimizada nenhuma sprite precisa animar."""
        cls._pausa_global = pausar
        for s in list(cls._todos):
            s._aplicar_pausa()


class StatusPill(QLabel):
    """Selo colorido do status. Pisca de leve em BATALHA/INICIANDO."""

    def __init__(self, big=False, parent=None):
        super().__init__(parent)
        self._big = big
        self._status = ""
        self._blink = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.set_status("OFFLINE")

    def set_status(self, status: str):
        if status == self._status:
            return
        self._status = status
        if status in ("BATALHA", "INICIANDO") and not MODO_LEVE:      # Modo Leve: cor fixa
            self._timer.start(550)
        else:
            self._timer.stop()
            self._blink = False
        self._paint()

    def _tick(self):
        if not self.isVisible() or PixelSprite._pausa_global:
            return                     # piscar escondido ou minimizado é trabalho à toa
        self._blink = not self._blink
        self._paint()

    _estilos: dict[tuple, str] = {}

    def _paint(self):
        # ícone de pixel + nome: o status nunca depende só da cor
        self.setText(f'<img src="{status_png(self._status)}" width="20" height="20" style="vertical-align:middle">'
                     f'&nbsp;{status_nome(self._status, curto=not self._big)}')
        chave = (self._status, self._blink, self._big)
        estilo = self._estilos.get(chave)
        if estilo is None:
            cor = status_color(self._status)
            alfa = 70 if self._blink else 36
            pad = "1px 10px 2px 10px" if self._big else "0px 6px 1px 6px"
            estilo = self._estilos[chave] = (
                f"color:{cor}; background:{rgba(cor, alfa)}; border:2px solid {T['filete']};"
                f"border-bottom-color:{rgba(cor, 150)}; padding:{pad}; {px(30 if self._big else 20)}")
        self.setStyleSheet(estilo)


class CheckerBackground(QWidget):
    """Fundo da janela: tábuas de madeira escura, bem discretas (a "base do treinador")."""

    _ladrilho: QPixmap | None = None

    def paintEvent(self, ev):
        if MODO_LEVE:                      # Modo Leve: cor lisa
            QPainter(self).fillRect(ev.rect(), QColor(T["fundo"]))
            return
        # Um ladrilho pintado uma vez e repetido pelo pincel (nada é redesenhado a cada animação):
        # tábuas de 32 px com uma linha de 2 px e as emendas desencontradas.
        if CheckerBackground._ladrilho is None:
            t = QPixmap(96, 64)
            t.fill(QColor(T["fundo"]))
            pt = QPainter(t)
            veio = QColor(T["fundo_veio"])
            for y in (30, 62):
                pt.fillRect(0, y, 96, 2, veio)
            pt.fillRect(40, 0, 2, 30, veio)
            pt.fillRect(84, 32, 2, 30, veio)
            pt.end()
            CheckerBackground._ladrilho = t
        p = QPainter(self)
        p.fillRect(ev.rect(), QBrush(CheckerBackground._ladrilho))

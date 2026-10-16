"""Molduras de pixel pintadas por nós, a partir de uma imagem já pronta no tamanho do widget.

O mesmo desenho do `border-image` da folha de estilo, mas muito mais barato: o Qt recortava as 9
partes da moldura e esticava o miolo a CADA pintura (medido: repintar a janela 7,7 ms com
`border-image` × 3,2 ms sem). Aqui a moldura é montada uma vez por tamanho e estado e depois é só
copiada. A folha de estilo continua definindo as larguras da borda e os espaçamentos (o conteúdo fica
no mesmo lugar); só não desenha mais a borda.

- `Moldura`: QFrame dos painéis ("card") e das fichas das contas ("tab").
- `Botao`: QPushButton de todo o programa.
"""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QPushButton, QStyle, QStyleOptionButton, QStylePainter

from app.tema import BORDA, T, UI_DIR

E, C, B = BORDA                 # esquerda/direita, cima, baixo (as mesmas do QSS)
_fontes: dict[str, QImage] = {}
_cache: dict[tuple, QPixmap] = {}
_CACHE_MAX = 600


def _fonte(nome: str) -> QImage:
    img = _fontes.get(nome)
    if img is None:
        img = _fontes[nome] = QImage(str(UI_DIR / f"moldura_{nome}.png")).convertToFormat(
            QImage.Format_ARGB32_Premultiplied)
    return img


def pixmap(nome: str, w: int, h: int, dpr: float = 1.0, canto: str | None = None) -> QPixmap:
    """A moldura `nome` montada em w×h (9 partes: cantos copiados, bordas e miolo esticados sem
    suavização, como o `border-image ... stretch`). `canto`: cor que aparece nos pixels de canto (no
    `border-image` eles mostravam o fundo do widget)."""
    chave = (nome, w, h, dpr, canto)
    pix = _cache.get(chave)
    if pix is not None:
        return pix
    if len(_cache) > _CACHE_MAX:
        _cache.clear()
    src = _fonte(nome)
    sw, sh = src.width(), src.height()
    W, H = max(1, round(w * dpr)), max(1, round(h * dpr))
    e, c, b = round(E * dpr), round(C * dpr), round(B * dpr)
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(canto) if canto else Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.SmoothPixmapTransform, False)
    xs = [(0, e, 0, E), (e, W - 2 * e, E, sw - 2 * E), (W - e, e, sw - E, E)]
    ys = [(0, c, 0, C), (c, H - c - b, C, sh - C - B), (H - b, b, sh - B, B)]
    for (dx, dw, sx, swp) in xs:
        for (dy, dh, sy, shp) in ys:
            if dw > 0 and dh > 0:
                p.drawImage(QRect(dx, dy, dw, dh), src, QRect(sx, sy, swp, shp))
    p.end()
    if canto:    # nos cantos de pixel (transparentes na imagem) aparece a cor de fundo
        cor = QColor(canto)
        for (x, y), (sx, sy) in (((0, 0), (0, 0)), ((W - 1, 0), (sw - 1, 0)),
                                 ((0, H - 1), (0, sh - 1)), ((W - 1, H - 1), (sw - 1, sh - 1))):
            if src.pixelColor(sx, sy).alpha() == 0:
                img.setPixelColor(x, y, cor)
    pix = QPixmap.fromImage(img)
    pix.setDevicePixelRatio(dpr)
    _cache[chave] = pix
    return pix


class Moldura(QFrame):
    """Painel ("card") ou ficha de conta ("tab"). O estado vem das mesmas propriedades do QSS."""

    def moldura_atual(self) -> str:
        fixa = self.property("moldura")
        if fixa:
            return str(fixa)
        if self.objectName() == "tab":
            # mesma prioridade das regras do QSS: desligada > selecionada > mouse em cima > normal
            if self.property("disabledacc"):
                return "desligado"
            if self.property("selected"):
                return "selecionado"
            if self.underMouse():
                return "painel_hover"
        return "painel"

    def paintEvent(self, _ev):
        if self.objectName() not in ("card", "tab"):
            return super().paintEvent(_ev)
        p = QPainter(self)
        p.drawPixmap(0, 0, pixmap(self.moldura_atual(), self.width(), self.height(), self.devicePixelRatioF()))


def nome_botao(objeto: str, estado) -> str:
    """Qual moldura o QSS dava ao botão (mesma prioridade das regras de tema.qss)."""
    ligado = bool(estado & QStyle.State_Enabled)
    hover = bool(estado & QStyle.State_MouseOver)
    apertado = bool(estado & QStyle.State_Sunken)
    if objeto == "primary":
        if not ligado:
            return "botao_desligado"
        return "botao_principal_apertado" if apertado else "botao_principal_hover" if hover else "botao_principal"
    if objeto == "danger":
        if not ligado:
            return "botao_desligado"
        return "botao_perigo_hover" if hover else "botao_perigo"
    if estado & QStyle.State_On:
        return "botao_ligado"
    if not ligado:
        return "botao_desligado"
    return "botao_apertado" if apertado else "botao_hover" if hover else "botao"


class Botao(QPushButton):
    """QPushButton com a moldura de pixel pronta; o texto e o ícone o Qt desenha como sempre."""
    hover = False            # o modelo do ranking (escondido) marca "mouse em cima" por fora

    def paintEvent(self, _ev):
        p = QStylePainter(self)
        o = QStyleOptionButton()
        self.initStyleOption(o)
        if self.hover:
            o.state |= QStyle.State_MouseOver
        m = self.property("margem") or (0, 0, 0, 0)          # margem do QSS (esq, cima, dir, baixo)
        r = self.rect().adjusted(m[0], m[1], -m[2], -m[3])
        if r.width() > 0 and r.height() > 0:
            p.drawPixmap(r.topLeft(), pixmap(nome_botao(self.objectName(), o.state), r.width(), r.height(),
                                             self.devicePixelRatioF(), T["painel_alto"]))
        # o texto/ícone vão na área de conteúdo (sem borda e padding), como o Qt faz no CE_PushButton
        o.rect = self.style().subElementRect(QStyle.SE_PushButtonContents, o, self)
        p.drawControl(QStyle.CE_PushButtonLabel, o)

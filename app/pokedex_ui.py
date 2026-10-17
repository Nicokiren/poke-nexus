"""A Pokédex do PokeNexus na tela: abre na área do jogo, como o Hunts (as páginas seguem rodando por trás).

SÓ MOSTRA: não captura, não clica no jogo, não abre tela do jogo, não troca de hunt e não manda nada ao
servidor. Quem entra e o que cada conta já capturou: game/pokedex.py. Sem animação nenhuma.

Leve: a grade é um QListView com um delegate que pinta pixmaps já prontos (nada de um widget por pokémon).
Cada sprite é lido do disco uma vez, no primeiro desenho da célula (só as que aparecem); a silhueta sai do
próprio sprite (CompositionMode_SourceIn) e fica na memória. Trocar de filtro não relê nada do disco.
"""
import json
import time

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListView, QProgressBar, QSizePolicy, QStyle, QStyledItemDelegate, QVBoxLayout,
                               QWidget)

from app import tema
from app.config import ASSETS_DIR, DATA_DIR, SPRITES_POKEMON
from app.molduras import Botao, Moldura
from app.tema import T, px
from app.widgets import _alpha_bbox
from game import pokedex as P

CACHE_CATALOGO = DATA_DIR / "pokedex_especies.json"     # para abrir sem internet
BOLA = ASSETS_DIR / "sprites" / "ui" / "bola_capturado.png"
CATALOGO_VELHO_S = 24 * 3600                              # pede um novo à página de dados só depois disso
NOVO_S = 24 * 3600                                        # o selo "Novo"
CELULA = QSize(88, 104)
CAIXA_SPRITE = 56


def _data(t: float | None) -> str:
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(t)) if t else ""


# ============================================================ dados (sem tela)
class PokedexDados:
    """O lado sem tela. Vive o tempo todo, mas só faz uma coisa barata: quando a Pokédex do jogo de uma conta
    muda (`game.dex_seq`), junta as espécies capturadas e grava as novas em profiles/conta_XX/pokedex.json.
    A tela (PokedexPanel) só nasce quando a pessoa abre a Pokédex."""

    def __init__(self, manager):
        self.m = manager
        self.contas = [P.PokedexConta(w.acc.profile_dir / "pokedex.json") for w in manager.workers]
        self._visto = [None] * len(self.contas)
        self.inventario: list[set[int]] = [set() for _ in self.contas]   # o que está no inventário agora
        self.sprites = P.numeros_dos_sprites(SPRITES_POKEMON)
        self.especies: dict | None = None
        self.versao = None
        self._cache_em = 0.0
        self._pedido = None

    def observar(self) -> dict[int, list[int]]:
        """{conta: [espécies novas]} desde a última olhada. Só faz a conta quando a Pokédex do jogo ou o
        inventário da conta mudou (o inventário conta sempre, pedido do usuário em 17/10/2026: pokémon que
        chegou por evolução ou troca, sem captura, também aparece)."""
        novos = {}
        for i, w in enumerate(self.m.workers):
            g = w.game
            if g is None or not g.welcomed:
                continue
            colecao = frozenset(n for n in (P.chave_pokedex(p.get("speciesId")) for p in list(g.pokemons.values()))
                                if n is not None)
            marca = (id(g), g.dex_seq, colecao)
            if marca == self._visto[i]:
                continue
            self._visto[i] = marca
            self.inventario[i] = set(colecao)
            dex = dict(g.dex)                                   # cópia: o loop das contas mexe nele
            pegos = P.capturados(dex, colecao, list(g.dex_capturas))
            n = self.contas[i].atualizar(g.eu.get("id"), pegos)
            if n:
                novos[i] = n
        return novos

    # ------------------------------------------------------------ catálogo (nomes e tipos)
    def atualizar_catalogo(self) -> bool:
        """O catálogo que o Hunt Analyzer já tem na memória; senão o cache em disco. Pede um novo à página de
        dados do jogo (sem conta, hunts/game_data.py) só sem cache ou com o cache de mais de 1 dia. True = mudou."""
        mudou = False
        cat = self.m.hunt_data.catalogo
        if cat and cat.get("versao") != self.versao:
            self.especies = {int(pid): {"nome": e.get("nome"), "type1": e.get("type1"), "type2": e.get("type2")}
                             for pid, e in (cat.get("especies") or {}).items() if 1 <= int(pid) <= P.NACIONAL_MAX}
            self.versao, self._cache_em = cat.get("versao"), time.time()
            self._gravar_cache()
            mudou = True
        elif self.especies is None:
            mudou = self._ler_cache()
        if self._pedido is None and (self.especies is None or time.time() - self._cache_em > CATALOGO_VELHO_S):
            self._pedido = self.m.pokedex_catalogo()            # roda no loop das contas; a tela não espera
        return mudou

    def _ler_cache(self) -> bool:
        try:
            d = json.loads(CACHE_CATALOGO.read_text(encoding="utf-8"))
            self.especies = {int(k): v for k, v in d["especies"].items()}
            self.versao, self._cache_em = d.get("versao"), float(d.get("em") or 0)
            return True
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return False

    def _gravar_cache(self):
        so = {str(n): e for n, e in (self.especies or {}).items() if n in self.sprites}
        try:
            tmp = CACHE_CATALOGO.with_suffix(".json.tmp")
            tmp.write_text(json.dumps({"versao": self.versao, "em": self._cache_em, "especies": so},
                                      ensure_ascii=False), encoding="utf-8")
            tmp.replace(CACHE_CATALOGO)
        except OSError:
            pass

    def lista(self) -> list[dict]:
        return P.montar_lista(self.sprites, self.especies)


# ============================================================ sprites prontos
class Sprites:
    """O 1º quadro de cada sprite (lido do disco uma vez, recortado no desenho) e as versões prontas para
    pintar, colorida e silhueta, por escala. Nenhum arquivo novo: a silhueta sai do próprio sprite."""

    def __init__(self, cor_silhueta: str):
        self.cor = QColor(cor_silhueta)
        self._base: dict[int, QImage] = {}
        self._pix: dict[tuple, QPixmap] = {}

    def limpar(self):
        self._base.clear()
        self._pix.clear()

    def _imagem(self, dex: int) -> QImage:
        img = self._base.get(dex)
        if img is None:
            img = QImageReader(str(SPRITES_POKEMON / f"{dex}.gif")).read()
            if not img.isNull():
                img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
                r = _alpha_bbox(img)
                if r:
                    img = img.copy(r)
            self._base[dex] = img
        return img

    def _silhueta(self, img: QImage) -> QImage:
        """O próprio sprite pintado de preto onde ele não é transparente."""
        out = img.copy()
        p = QPainter(out)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)
        p.fillRect(out.rect(), self.cor)
        p.end()
        return out

    def pixmap(self, dex: int, pego: bool, caixa: int = CAIXA_SPRITE) -> QPixmap:
        chave = (dex, pego, caixa)
        pix = self._pix.get(chave)
        if pix is None:
            img = self._imagem(dex)
            if img.isNull():
                pix = QPixmap()
            else:
                img = img if pego else self._silhueta(img)
                lado = max(img.width(), img.height())
                f = max(1, caixa // lado) if lado <= caixa else 0     # só fatores inteiros (pixel nítido)
                if f:
                    img = img.scaled(img.width() * f, img.height() * f, Qt.IgnoreAspectRatio, Qt.FastTransformation)
                else:
                    img = img.scaled(caixa, caixa, Qt.KeepAspectRatio, Qt.FastTransformation)
                pix = QPixmap.fromImage(img)
            self._pix[chave] = pix
        return pix


# ============================================================ a grade
class ModeloDex(QAbstractListModel):
    """As células à vista (depois dos filtros). `pegos`: {número: {"quando", "donos", "desde"}}."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.linhas: list[dict] = []
        self.pegos: dict[int, dict] = {}
        self.todas = False
        self._linha: dict[int, int] = {}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.linhas)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        e = self.linhas[index.row()]
        if role == Qt.UserRole:
            return e
        if role == Qt.ToolTipRole:
            return self.dica(e)
        return None

    def mostrar(self, linhas: list[dict]):
        self.beginResetModel()
        self.linhas = linhas
        self._linha = {e["dex"]: i for i, e in enumerate(linhas)}
        self.endResetModel()

    def mudou(self, dex: int):
        i = self._linha.get(dex)
        if i is not None:
            ix = self.index(i)
            self.dataChanged.emit(ix, ix)

    def dica(self, e: dict) -> str:
        num = f"#{e['dex']:03d}"
        p = self.pegos.get(e["dex"])
        if not p:
            return f"{num}\nAinda não capturado"
        linhas = [f"{num} {e['nome']}".strip()]
        if e["tipos"]:
            linhas.append(" / ".join(e["tipos"]))
        linhas.append(f"Primeira captura: {_data(p['quando'])}" if p["quando"]
                      else f"Capturado antes de {_data(p.get('desde'))[:10]}" if p.get("desde") else "Capturado")
        if p.get("inv"):
            linhas.append("No inventário")
        if self.todas:
            linhas.append("Conta: " + ", ".join(p["donos"]) if len(p["donos"]) == 1 else "Contas: " + ", ".join(p["donos"]))
        return "\n".join(linhas)


class PintorDex(QStyledItemDelegate):
    """Pinta uma célula: o número (#025, fonte de pixel), o sprite (ou a silhueta) e o nome (ou "???")."""

    def __init__(self, modelo: ModeloDex, sprites: Sprites, cores: dict, parent=None):
        super().__init__(parent)
        self.modelo, self.sprites, self.c = modelo, sprites, {k: QColor(v) for k, v in cores.items()}
        self.f_num = QFont(tema.PIXEL)
        self.f_num.setPixelSize(20)
        self.f_nome = QFont(tema.TEXTO)
        self.f_nome.setPixelSize(11)
        self.f_nome.setWeight(QFont.Bold)
        self.f_selo = QFont(tema.TEXTO)
        self.f_selo.setPixelSize(9)
        self.f_selo.setWeight(QFont.ExtraBold)
        # a Pokébola só nas células capturadas (escolha do usuário, 17/10/2026; desenho do pacote pokesprite)
        bola = QImage(str(BOLA))
        r = _alpha_bbox(bola) if not bola.isNull() else None
        self.bola = QPixmap.fromImage(bola.copy(r) if r else bola)

    def sizeHint(self, *_):
        return CELULA

    def paint(self, p: QPainter, opt, index):
        e = index.data(Qt.UserRole)
        info = self.modelo.pegos.get(e["dex"])
        pego, c = info is not None, self.c
        r = opt.rect.adjusted(3, 3, -3, -3)
        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        hover = bool(opt.state & QStyle.State_MouseOver)
        p.fillRect(r, c["borda_hover"] if hover else c["borda"])          # moldura de 2 px, cantos de pixel
        p.fillRect(r.adjusted(2, 2, -2, -2), c["fundo_pego"] if pego else c["fundo"])
        for x, y in ((r.left(), r.top()), (r.right(), r.top()), (r.left(), r.bottom()), (r.right(), r.bottom())):
            p.fillRect(x, y, 1, 1, c["vao"])
        p.setFont(self.f_num)
        p.setPen(c["num_pego"] if pego else c["num"])
        p.drawText(QRect(r.left() + 6, r.top() + 2, r.width() - 12, 20), Qt.AlignLeft | Qt.AlignVCenter, f"#{e['dex']:03d}")
        pix = self.sprites.pixmap(e["dex"], pego)
        if not pix.isNull():
            area = QRect(r.left(), r.top() + 20, r.width(), CAIXA_SPRITE + 4)
            p.drawPixmap(area.center().x() - pix.width() // 2 + 1, area.center().y() - pix.height() // 2 + 1, pix)
        p.setFont(self.f_nome)
        p.setPen(c["nome"] if pego else c["fraco"])
        nome = (e["nome"] or f"#{e['dex']:03d}") if pego else "???"
        nome = p.fontMetrics().elidedText(nome, Qt.ElideRight, r.width() - 8)
        p.drawText(QRect(r.left() + 4, r.bottom() - 20, r.width() - 8, 16), Qt.AlignHCenter | Qt.AlignVCenter, nome)
        if pego and not self.bola.isNull():
            p.drawPixmap(r.right() - 4 - self.bola.width() + 1, r.top() + 6, self.bola)
        if pego and info["quando"] and time.time() - info["quando"] < NOVO_S:
            p.setFont(self.f_selo)
            larg = p.fontMetrics().horizontalAdvance("Novo") + 8
            s = QRect(r.left() + 5, r.top() + 23, larg, 13)      # embaixo do número
            p.fillRect(s, c["selo"])
            p.setPen(c["sobre_selo"])
            p.drawText(s, Qt.AlignCenter, "Novo")
        p.restore()


# O aparelho, com a tela de LCD clara (escolha do usuário, 17/10/2026): a silhueta é preta pura.
CORES = {"fundo": T["tela_dex"], "fundo_pego": T["tela_dex"], "borda": T["tela_dex_borda"],
         "borda_hover": T["sobre_destaque"], "vao": T["tela_dex"], "num": T["tela_dex_fraco"],
         "num_pego": T["sobre_destaque"], "nome": T["sobre_destaque"], "fraco": T["tela_dex_fraco"],
         "selo": T["destaque"], "sobre_selo": T["sobre_destaque"], "silhueta": T["filete"]}


def bola(arquivo, fator: int = 1) -> QPixmap:
    """Uma Pokébola do pacote pokesprite (assets/sprites/ui), recortada no desenho e ampliada sem borrar."""
    img = QImage(str(ASSETS_DIR / "sprites" / "ui" / arquivo))
    r = _alpha_bbox(img) if not img.isNull() else None
    img = img.copy(r) if r else img
    return QPixmap.fromImage(img.scaled(img.width() * fator, img.height() * fator, Qt.IgnoreAspectRatio,
                                        Qt.FastTransformation))


class Lente(QLabel):
    """A Ultra Ball no alto da Pokédex (escolha do usuário, 17/10/2026: no lugar da lente desenhada)."""

    def __init__(self):
        super().__init__()
        self.setPixmap(bola("bola_pokedex.png", 3))


# ============================================================ o painel
class PokedexPanel(QWidget):
    """A Pokédex de uma conta (a selecionada) ou de todas juntas, com cara de aparelho: a lente e as luzinhas no
    alto, a telinha do pokémon em que o mouse está e a grade numa tela de LCD."""

    def __init__(self, dados: PokedexDados, nomes):
        super().__init__()
        self.dados, self.nomes = dados, nomes        # nomes(): os nomes das contas do PokeNexus
        self.conta = 0
        self.todas = False
        self.regiao = None
        self.sprites = Sprites(CORES["silhueta"])
        # O modelo é filho do painel: o Qt o apaga depois da grade que o usa (sem dono, o Python podia apagá-lo
        # antes, ao fechar o programa). As imagens saem da memória antes do Qt fechar.
        self.modelo = ModeloDex(self)
        QApplication.instance().aboutToQuit.connect(self.sprites.limpar)
        self._lista: list[dict] = []
        self._detalhe = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8)

        topo = Moldura()
        topo.setObjectName("card")
        tv = QVBoxLayout(topo)
        tv.setContentsMargins(14, 10, 14, 12)
        tv.setSpacing(8)
        l1 = QHBoxLayout()
        l1.addWidget(Lente(), 0, Qt.AlignVCenter)
        l1.addSpacing(6)
        titulo = QLabel("Pokédex")
        titulo.setStyleSheet(px(30) + f" color:{T['destaque']};")
        l1.addWidget(titulo)
        self.rot_conta = QLabel("")
        self.rot_conta.setObjectName("statTxt")
        l1.addWidget(self.rot_conta)
        l1.addStretch()
        self.b_conta = Botao("Esta conta")
        self.b_todas = Botao("Todas as contas")
        for b, todas in ((self.b_conta, False), (self.b_todas, True)):
            b.setObjectName("tool")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=todas: self.set_todas(t))
            l1.addWidget(b)
        self.b_conta.setToolTip("Só a conta selecionada")
        self.b_todas.setToolTip("As 4 contas juntas: conta se qualquer uma tiver capturado")
        tv.addLayout(l1)
        l2 = QHBoxLayout()
        l2.setSpacing(10)
        self.barra = QProgressBar()
        self.barra.setTextVisible(True)
        self.barra.setFormat("%v de %m")
        l2.addWidget(self.barra, 1)
        self.pct = QLabel("")
        self.pct.setStyleSheet(px(20) + f" color:{T['destaque']};")
        self.pct.setMinimumWidth(52)
        l2.addWidget(self.pct)
        self.fichas = {}
        for nome, _a, _b in P.REGIOES:
            f = QLabel("")
            f.setObjectName("counter")
            self.fichas[nome] = f
            l2.addWidget(f)
        tv.addLayout(l2)
        l3 = QHBoxLayout()
        l3.setSpacing(6)
        self.b_reg = {}
        for nome in (None,) + tuple(r[0] for r in P.REGIOES):
            b = Botao(nome or "Todas")
            b.setObjectName("tool")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=nome: self.set_regiao(n))
            self.b_reg[nome] = b
            l3.addWidget(b)
        l3.addSpacing(8)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar número, ou nome dos já capturados")
        self.busca.setClearButtonEnabled(True)
        self.busca.setAccessibleName("Buscar na Pokédex")
        self.busca.textChanged.connect(lambda _t: self._filtrar())
        l3.addWidget(self.busca, 1)
        self.so_faltam = QCheckBox("Mostrar só os que faltam")
        self.so_faltam.toggled.connect(lambda _on: self._filtrar())
        l3.addWidget(self.so_faltam)
        tv.addLayout(l3)
        lay.addWidget(topo)

        self.grade = QListView()
        self.grade.setObjectName("gradeDexTela")
        self.grade.setViewMode(QListView.IconMode)
        self.grade.setFlow(QListView.LeftToRight)
        self.grade.setWrapping(True)
        self.grade.setResizeMode(QListView.Adjust)
        self.grade.setMovement(QListView.Static)
        self.grade.setUniformItemSizes(True)
        self.grade.setGridSize(CELULA)
        self.grade.setSelectionMode(QAbstractItemView.NoSelection)
        self.grade.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grade.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.grade.verticalScrollBar().setSingleStep(24)
        self.grade.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grade.setFocusPolicy(Qt.NoFocus)
        self.grade.setMouseTracking(True)
        self.grade.setModel(self.modelo)
        self.grade.setItemDelegate(PintorDex(self.modelo, self.sprites, CORES, self.grade))
        self.vazio = QLabel("Nada encontrado.", self.grade.viewport())
        self.vazio.setStyleSheet(f"color:{T['sobre_destaque']};")
        self.vazio.hide()
        corpo = QHBoxLayout()
        corpo.setSpacing(8)
        corpo.addWidget(self._montar_detalhe())
        self.grade.entered.connect(self._mostrar_detalhe)
        moldura = Moldura()
        moldura.setObjectName("card")
        mv = QVBoxLayout(moldura)
        mv.setContentsMargins(12, 10, 12, 12)
        mv.addWidget(self.grade)
        corpo.addWidget(moldura, 1)
        lay.addLayout(corpo, 1)
        self.b_reg[None].setChecked(True)
        self.b_conta.setChecked(True)
        self.recarregar()

    # ------------------------------------------------------------ a telinha do pokémon em que o mouse está
    def _montar_detalhe(self) -> QWidget:
        caixa = Moldura()
        caixa.setObjectName("card")
        caixa.setFixedWidth(220)
        v = QVBoxLayout(caixa)
        v.setContentsMargins(12, 10, 12, 12)
        tela = QFrame()
        tela.setObjectName("telaDex")
        tv = QVBoxLayout(tela)
        tv.setContentsMargins(10, 8, 10, 10)
        tv.setSpacing(2)
        self.d_num = QLabel("")
        self.d_num.setStyleSheet(px(30))
        self.d_sprite = QLabel()
        self.d_sprite.setAlignment(Qt.AlignCenter)
        # cabe o 2×? senão o tamanho normal (tela baixa, 125%): nada passa por cima do nome
        self.d_sprite.setMinimumHeight(CAIXA_SPRITE + 4)
        self.d_sprite.setMaximumHeight(CAIXA_SPRITE * 2 + 16)
        self.d_sprite.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.d_nome = QLabel("")
        self.d_nome.setStyleSheet(px(20))
        self.d_info = QLabel("")
        self.d_info.setWordWrap(True)
        self.d_info.setStyleSheet(f"font-size:11px; color:{T['tela_dex_fraco']};")
        for w in (self.d_num, self.d_sprite, self.d_nome, self.d_info):
            tv.addWidget(w)
        tv.addStretch()
        v.addWidget(tela, 1)
        dica = QLabel("Passe o mouse num pokémon.")
        dica.setObjectName("muted")
        dica.setStyleSheet("font-size:11px;")
        dica.setWordWrap(True)
        v.addWidget(dica)
        return caixa

    def _mostrar_detalhe(self, index):
        if not index.isValid():
            return
        self._detalhar(index.data(Qt.UserRole))

    def _detalhar(self, e: dict | None):
        self._detalhe = e
        if e is None:
            return
        info = self.modelo.pegos.get(e["dex"])
        self.d_num.setText(f"#{e['dex']:03d}")
        caixa = CAIXA_SPRITE * 2 if self.d_sprite.height() >= CAIXA_SPRITE * 2 + 8 else CAIXA_SPRITE
        self.d_sprite.setPixmap(self.sprites.pixmap(e["dex"], info is not None, caixa))
        self.d_nome.setText((e["nome"] or "") if info else "???")
        self.d_info.setText(self.modelo.dica(e).split("\n", 1)[1] if info else "Ainda não capturado")

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._detalhar(self._detalhe)            # a telinha pode ter mudado de altura

    # ------------------------------------------------------------ o que mostrar
    def mostrar(self, conta: int):
        """A conta selecionada mudou (Ctrl+1…4, clique na aba)."""
        self.conta = conta
        if not self.todas:
            self._pegos()

    def set_todas(self, todas: bool):
        self.todas = todas
        self.b_conta.setChecked(not todas)
        self.b_todas.setChecked(todas)
        self._pegos()

    def set_regiao(self, nome):
        self.regiao = nome
        for n, b in self.b_reg.items():
            b.setChecked(n == nome)
        self._filtrar()

    def recarregar(self):
        """A lista inteira (abriu, ou o catálogo do jogo chegou)."""
        self.dados.atualizar_catalogo()
        self._lista = self.dados.lista()
        self._pegos()

    def capturou(self, novos: dict[int, list[int]]):
        """Capturas novas: atualiza só aquelas células e os números."""
        if not novos or not (self.todas or self.conta in novos):
            return
        antes = set(self.modelo.pegos)
        self._pegos(refiltrar=self.so_faltam.isChecked())
        for n in set(self.modelo.pegos) - antes:
            self.modelo.mudou(n)

    def _pegos(self, refiltrar: bool = True):
        nomes = self.nomes()
        if self.todas:
            por = {nomes[i]: c.atual() for i, c in enumerate(self.dados.contas)}
            desde = min((c.desde() for c in self.dados.contas if c.desde()), default=None)
            inv = set().union(*self.dados.inventario)
            pegos = {n: {**e, "desde": desde, "inv": n in inv} for n, e in P.juntar(por).items()}
            self.rot_conta.setText("Todas as contas")
        else:
            c, inv = self.dados.contas[self.conta], self.dados.inventario[self.conta]
            pegos = {n: {"quando": q, "donos": [nomes[self.conta]], "desde": c.desde(), "inv": n in inv}
                     for n, q in c.atual().items()}
            self.rot_conta.setText(nomes[self.conta])
        self.modelo.pegos, self.modelo.todas = pegos, self.todas
        pr = P.progresso(self._lista, set(pegos))
        feito, total = pr["total"]
        self.barra.setMaximum(max(1, total))
        self.barra.setValue(feito)
        self.pct.setText(f"{(100 * feito // total) if total else 0}%")
        for nome, f in self.fichas.items():
            f.setText(f"{nome} {pr[nome][0]}/{pr[nome][1]}")
        if refiltrar:
            self._filtrar()
        else:
            self.grade.viewport().update()

    def _filtrar(self):
        q = self.busca.text().strip().lower().lstrip("#")
        so_faltam = self.so_faltam.isChecked()
        pegos = self.modelo.pegos
        linhas = []
        for e in self._lista:
            if self.regiao and e["regiao"] != self.regiao:
                continue
            if so_faltam and e["dex"] in pegos:
                continue
            if q:
                if q.isdigit():
                    if int(q) != e["dex"] and not f"{e['dex']:03d}".startswith(q):
                        continue
                elif not (e["dex"] in pegos and q in (e["nome"] or "").lower()):
                    continue                 # o nome só acha quem já foi capturado (sem estragar a surpresa)
            linhas.append(e)
        self.modelo.mostrar(linhas)
        self.vazio.setVisible(not linhas)
        if not linhas:
            self.vazio.adjustSize()
            self.vazio.move(QPoint(16, 16))

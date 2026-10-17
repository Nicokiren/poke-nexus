"""Tema "Base do Treinador": as cores, as fontes e a folha de estilo do PokeNexus, num lugar só.

A ideia: o PokeNexus é a base do treinador, com molduras de madeira escura como as do próprio PokeIdle
(`estilo.css` do jogo), para o app e o jogo parecerem uma coisa só. Nenhuma outra parte do código tem
cor fixa: tudo vem daqui (`T[...]`). Contraste de leitura conferido (WCAG AA) em
`docs/visual/V6_RELATORIO.md`.
"""
from PySide6.QtGui import QFontDatabase

from app.config import ASSETS_DIR

FONTES_DIR = ASSETS_DIR / "fonts"
UI_DIR = ASSETS_DIR / "ui"

# ------------------------------------------------------------------- cores
T = {
    # fundo e painéis (ameixa quase preto, como o vão escuro do jogo)
    "fundo": "#1A1016",
    "fundo_veio": "#1D1219",          # linha das tábuas do fundo
    "painel": "#2A1A22",
    "painel_alto": "#3A2430",         # hover, item em foco
    "campo": "#22151C",               # campos de texto, listas, log
    "trilho": "#1E1219",              # trilho das barras, "buracos" (como o --barra-vazia do jogo)
    # madeira das molduras
    "moldura": "#8C4A3E",
    "moldura_luz": "#C9785C",
    "moldura_esc": "#5A2A2E",
    "filete": "#2B0C14",
    # texto
    "texto": "#F6E9DC",               # creme
    "dim": "#C9AFA4",                 # secundário (8,0:1 sobre o painel)
    "apagado": "#8A7480",             # desligado
    "sobre_madeira": "#FFF6EF",
    # destaque (ouro, como o --ouro do jogo)
    "destaque": "#E8B04A",
    "destaque_luz": "#FFE3A0",
    "destaque_esc": "#9A6A1C",
    "sobre_destaque": "#2B1608",
    "sel_fundo": "#3A2A16",           # linha/aba selecionada
    # outros
    "foco": "#3CCFC0",
    "perigo": "#C8473B",
    "erro": "#F0705F",
    "aviso": "#F0A03C",
    "ok": "#6FD08A",
    "info": "#6FC0F0",
    "xp": "#6FC0F0",
    "chao": "#3E6B34",                # chão de grama do palco do mascote
    "chao_luz": "#5E9A4C",
    "sprite_cinza": "#6E5A64",        # mascote de conta parada
    # a tela de LCD da Pokédex (app/pokedex_ui.py; texto escuro 11,3:1, fraco 5,3:1, silhueta 11,8:1)
    "tela_dex": "#CDD5B3",
    "tela_dex_borda": "#98A47F",
    "tela_dex_fraco": "#4A5436",      # texto secundário na tela
    # só nas molduras dos botões (ferramentas/arte/gerar_ui.py)
    "botao_hover": "#4A2E3B",
    "destaque_hover": "#F2C25E",
    "perigo_luz": "#E07062",
    "perigo_esc": "#7A2418",
}

# Status: os nomes internos não mudam (código, log, config); só o texto e a cor mostrados.
STATUS_COR = {
    "FARMING": "#6FD08A",
    "BATALHA": "#F0A03C",
    "AGUARDANDO": "#6FC0F0",
    "INICIANDO": "#6FC0F0",
    "PAUSADO": "#C77BE0",
    "MANUAL": "#3CCFC0",
    "ERRO": "#F0705F",
    "SESSÃO EXPIRADA": "#FFB4A0",
    "OFFLINE": "#A8979D",
}
STATUS_NOME = {
    "FARMING": "Caçando",
    "BATALHA": "Em batalha",
    "AGUARDANDO": "Aguardando",
    "INICIANDO": "Iniciando",
    "PAUSADO": "Pausado",
    "MANUAL": "Você no controle",
    "ERRO": "Erro",
    "SESSÃO EXPIRADA": "Faça login",
    "OFFLINE": "Parado",
}
STATUS_CURTO = {"MANUAL": "No controle", "SESSÃO EXPIRADA": "Login"}   # nas fichas pequenas


def status_cor(status: str) -> str:
    return STATUS_COR.get(status, STATUS_COR["OFFLINE"])


def status_nome(status: str, curto: bool = False) -> str:
    if curto and status in STATUS_CURTO:
        return STATUS_CURTO[status]
    return STATUS_NOME.get(status, status.capitalize())


def rgba(cor: str, alfa: int) -> str:
    """Cor com transparência para o QSS (no Qt, "#RRGGBBAA" seria lido como #AARRGGBB)."""
    c = cor.lstrip("#")
    return f"rgba({int(c[0:2], 16)},{int(c[2:4], 16)},{int(c[4:6], 16)},{alfa})"


# ------------------------------------------------------------------- fontes
# Jersey 10 (pixel, títulos/números/botões) só nos tamanhos da grade dela, 20/30/40 px, e peso único.
# Nunito (textos). As duas são SIL OFL e vão junto do programa (assets/fonts, com a licença).
PIXEL = "Jersey 10"
TEXTO = "Nunito"
_fontes_ok = False


def carregar_fontes() -> bool:
    """Registra as fontes do pacote. Chamar depois de criar o QApplication."""
    global _fontes_ok, PIXEL, TEXTO
    if _fontes_ok:
        return True
    achou = {}
    for arq in ("Jersey10-Regular.ttf", "Nunito-Variavel.ttf"):
        fid = QFontDatabase.addApplicationFont(str(FONTES_DIR / arq))
        if fid >= 0:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                achou[arq] = fams[0]
    PIXEL = achou.get("Jersey10-Regular.ttf", "Segoe UI")
    TEXTO = achou.get("Nunito-Variavel.ttf", "Segoe UI")
    _fontes_ok = len(achou) == 2
    return _fontes_ok


def px(tamanho: int = 20) -> str:
    """Trecho de QSS para a fonte de pixel. Só 20, 30 ou 40 px (a grade da Jersey 10)."""
    tamanho = min((20, 30, 40), key=lambda t: abs(t - tamanho))
    return f'font-family: "{PIXEL}"; font-size: {tamanho}px; font-weight: 400;'


def _url(nome: str) -> str:
    return (UI_DIR / nome).as_posix()


BORDA = (4, 4, 6)              # largura da moldura: esquerda/direita, cima, baixo (px)
# True = o Qt desenha a moldura com `border-image` (o jeito antigo, lento; só para comparar nos testes).
# False = a folha de estilo só reserva a largura da borda e quem desenha é app/molduras.py (Moldura,
# Botao), com a moldura já pronta em memória: o mesmo desenho, bem mais barato a cada pintura.
MOLDURA_QSS = False


def moldura(nome: str = "painel") -> str:
    """Moldura de pixel (9-slice) desenhada por `ferramentas/arte/gerar_ui.py`."""
    e, c, b = BORDA
    if MOLDURA_QSS:
        return (f'border-image: url("{_url("moldura_" + nome + ".png")}") {c} {e} {b} {e} stretch; '
                f'border-width: {c}px {e}px {b}px {e}px;')
    return f"border-style: solid; border-color: transparent; border-width: {c}px {e}px {b}px {e}px;"


# ------------------------------------------------------------------- folhas de estilo
def qss() -> str:
    """Folha de estilo da janela principal (e do que nasce dentro dela)."""
    t = T
    return f"""
* {{ font-family: "{TEXTO}", "Segoe UI", sans-serif; color: {t['texto']}; font-size: 13px; }}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{ background: {t['painel_alto']}; color: {t['texto']}; border: 2px solid {t['filete']};
            padding: 4px 6px; }}

QFrame#card {{ background: {t['painel']}; {moldura('painel')} }}
QLabel#cardTitle {{ {px(20)} color: {t['destaque']}; }}
QLabel#muted {{ color: {t['dim']}; }}
QLabel#statKey {{ color: {t['dim']}; font-size: 11px; }}
QLabel#statVal {{ {px(30)} color: {t['texto']}; }}
QLabel#heroName {{ {px(40)} color: {t['texto']}; }}
QLabel#gameTitle {{ {px(20)} color: {t['texto']}; }}
QLabel#statTxt {{ color: {t['texto']}; font-size: 12px; font-weight: 700; }}
QLabel#brand {{ {px(30)} color: {t['destaque']}; }}
QLabel#brandSub {{ color: {t['dim']}; font-size: 12px; }}
QLabel#counter {{ {px(20)} background: {t['trilho']}; border: 2px solid {t['filete']}; padding: 2px 10px; }}
QLabel#atalho {{ color: {t['apagado']}; font-size: 11px; }}

QPushButton {{ {px(20)} color: {t['texto']}; background: {t['painel_alto']}; padding: 0px 10px;
               min-height: 24px; {moldura('botao')} }}
QPushButton:hover {{ {moldura('botao_hover')} }}
QPushButton:pressed {{ {moldura('botao_apertado')} padding-top: 2px; }}
QPushButton:disabled {{ color: {t['apagado']}; {moldura('botao_desligado')} }}
QPushButton:checked {{ color: {t['destaque']}; {moldura('botao_ligado')} }}
QPushButton#primary {{ color: {t['sobre_destaque']}; {moldura('botao_principal')} }}
QPushButton#primary:hover {{ {moldura('botao_principal_hover')} }}
QPushButton#primary:pressed {{ {moldura('botao_principal_apertado')} padding-top: 2px; }}
QPushButton#primary:disabled {{ color: {t['apagado']}; {moldura('botao_desligado')} }}
QPushButton#danger {{ {moldura('botao_perigo')} }}
QPushButton#danger:hover {{ {moldura('botao_perigo_hover')} }}
QPushButton#danger:disabled {{ color: {t['apagado']}; {moldura('botao_desligado')} }}
QPushButton#tool {{ padding: 0px 8px; min-width: 20px; }}
QPushButton::menu-indicator {{ width: 0; }}

QMenu {{ background: {t['painel']}; border: 2px solid {t['filete']}; padding: 4px; }}
QMenu::item {{ padding: 6px 16px; }}
QMenu::item:selected {{ background: {t['sel_fundo']}; color: {t['destaque']}; }}

QFrame#tab {{ background: {t['painel']}; {moldura('painel')} }}
QFrame#tab:hover {{ {moldura('painel_hover')} }}
QFrame#tab[selected="true"] {{ background: {t['sel_fundo']}; {moldura('selecionado')} }}
QFrame#tab[disabledacc="true"] {{ background: {t['trilho']}; {moldura('desligado')} }}
QLabel#tabName {{ {px(20)} color: {t['texto']}; }}
QLabel#tabTitle {{ {px(20)} color: {t['destaque']}; }}

QFrame#cell {{ background: {t['trilho']}; border: 2px solid {t['filete']}; }}
QFrame#cell[grid="true"] {{ background: {t['trilho']}; border: 2px solid {t['moldura_esc']}; }}
QFrame#cell[selected="true"] {{ border: 2px solid {t['destaque']}; }}
QFrame#cellHeader {{ background: {t['painel']}; border: none; border-bottom: 2px solid {t['filete']}; }}
QLabel#cellName {{ {px(20)} color: {t['texto']}; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {t['moldura_esc']}; }}
QTableWidget {{ background: transparent; border: none; gridline-color: transparent;
                selection-background-color: {t['sel_fundo']}; selection-color: {t['texto']}; }}
QTableWidget::item {{ padding: 2px 6px; border-bottom: 1px solid {t['trilho']}; }}
QHeaderView {{ background: transparent; border: none; }}
QTableCornerButton::section {{ background: transparent; border: none; }}
QHeaderView::section {{ background: {t['painel']}; color: {t['dim']}; border: none;
                        border-bottom: 2px solid {t['filete']}; padding: 5px; font-size: 11px; font-weight: 700; }}
QPlainTextEdit {{ background: {t['campo']}; border: 2px solid {t['filete']};
                  font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; padding: 6px; }}
QCheckBox {{ color: {t['dim']}; font-size: 12px; spacing: 6px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; image: url("{_url('caixa_off.png')}"); }}
QCheckBox::indicator:checked {{ image: url("{_url('caixa_on.png')}"); }}
QCheckBox::indicator:disabled {{ image: url("{_url('caixa_desligada.png')}"); }}
QScrollBar:vertical {{ background: {t['trilho']}; width: 10px; border-left: 2px solid {t['filete']}; }}
QScrollBar::handle:vertical {{ background: {t['moldura']}; border-top: 2px solid {t['moldura_luz']};
                               border-bottom: 2px solid {t['moldura_esc']}; min-height: 30px; }}
QScrollBar:horizontal {{ background: {t['trilho']}; height: 10px; border-top: 2px solid {t['filete']}; }}
QScrollBar::handle:horizontal {{ background: {t['moldura']}; border-left: 2px solid {t['moldura_luz']};
                                 border-right: 2px solid {t['moldura_esc']}; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QProgressBar {{ background: {t['trilho']}; border: 2px solid {t['filete']}; min-height: 18px;
                color: {t['texto']}; font-size: 12px; font-weight: 700; text-align: center; }}
QProgressBar::chunk {{ background: {t['moldura_esc']}; }}
QListView#gradeDexTela {{ background: {t['tela_dex']}; border: 2px solid {t['filete']}; }}
QFrame#telaDex {{ background: {t['tela_dex']}; border: 2px solid {t['filete']}; }}
QFrame#telaDex QLabel {{ color: {t['sobre_destaque']}; }}
""" + qss_campos()


def qss_campos() -> str:
    """Campos de texto, números, listas e atalhos (janela principal e diálogos)."""
    t = T
    return f"""
QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit, QComboBox {{ background: {t['campo']};
    border: 2px solid {t['filete']}; border-bottom-color: {t['moldura_esc']}; padding: 3px 8px;
    color: {t['texto']}; min-height: 20px; selection-background-color: {t['sel_fundo']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QKeySequenceEdit:focus, QComboBox:focus {{
    border-color: {t['foco']}; }}
QComboBox QAbstractItemView {{ background: {t['painel']}; border: 2px solid {t['filete']};
    selection-background-color: {t['sel_fundo']}; selection-color: {t['destaque']}; }}
QListWidget {{ background: {t['campo']}; border: 2px solid {t['filete']}; }}
QListWidget::item:selected {{ background: {t['sel_fundo']}; color: {t['destaque']}; }}
*[erro="true"] {{ border: 2px solid {t['erro']}; }}
"""


def qss_dialogo() -> str:
    """Janelas à parte (Configurações, regra do RMT, avisos): fundo + tudo da principal."""
    return f"QDialog {{ background: {T['fundo']}; }}" + qss()

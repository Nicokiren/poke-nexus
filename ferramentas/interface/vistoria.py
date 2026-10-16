"""Vistoria da interface: abre o PokeNexus de verdade (a mesma janela, as mesmas páginas) e, para cada
cenário, tira um print da janela e mede o que a página do jogo recebe (px CSS, zoom, layout de celular)
e, na página de teste do Market, se o botão de compra dos cartões aparece.

Nada é gravado no config.toml (as trocas de ficha, layout e zoom são só na memória), a pasta de dados é
temporária e NENHUMA conta é tocada: as páginas mostram a tela de login do jogo (--pagina jogo) ou a
página de teste do Market (--pagina mercado, ver mercado_teste.py). Não precisa de login.

    .venv\\Scripts\\python.exe ferramentas\\interface\\vistoria.py --escala 1.25 --leve 1 --saida <pasta>

A escala do Windows é simulada com QT_SCALE_FACTOR (os px lógicos do Qt mudam como numa tela a 125%).
Cada cenário: tamanho da área da janela (px lógicos), visão, ficha, registro, zoom, área.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
import mercado_teste  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--escala", type=float, default=1.0, help="escala do Windows simulada (QT_SCALE_FACTOR)")
ap.add_argument("--leve", type=int, default=0)
ap.add_argument("--semgpu", type=int, default=0, help="Modo Leve como num PC sem placa de vídeo")
ap.add_argument("--pagina", default="mercado", choices=["mercado", "jogo"])
ap.add_argument("--versao", default="1.300.2")
ap.add_argument("--cenarios", default="", help="arquivo JSON com a lista de cenários (padrão: os da escala)")
ap.add_argument("--saida", required=True)
ap.add_argument("--prefixo", default="")
ap.add_argument("--tela", default="secundaria", choices=["principal", "secundaria"])
ap.add_argument("--espera", type=float, default=2.5, help="segundos depois de aplicar cada cenário")
ap.add_argument("--sem-correcao", action="store_true", help="desliga o zoom do Market (para o print de antes)")
A = ap.parse_args()
SAIDA = Path(A.saida)
SAIDA.mkdir(parents=True, exist_ok=True)

TMP = Path(tempfile.mkdtemp(prefix="pn_vist_"))
os.environ["POKENEXUS_DATA"] = str(TMP)
if A.escala != 1.0:
    os.environ["QT_SCALE_FACTOR"] = str(A.escala)
os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
os.environ.pop("QT_QUICK_BACKEND", None)

import app.config as C  # noqa: E402
C.MODO_LEVE = bool(A.leve)
import browser.web_host as WH  # noqa: E402
if A.semgpu:
    WH.tem_gpu = lambda: False
PORT = WH.setup_environment()

from PySide6.QtCore import QTimer, QUrl, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.gui as G  # noqa: E402

web = WH.WebHost(PORT)
m = G.Manager(cfg, contas, web)             # sem m.start(): nenhuma conta conecta
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
telas = QGuiApplication.screens()
tela = QGuiApplication.primaryScreen()
if A.tela == "secundaria":
    tela = next((t for t in telas if t is not QGuiApplication.primaryScreen()), tela)
GEO = tela.geometry()
win.move(GEO.x(), GEO.y())
win.show()
if A.sem_correcao and hasattr(win.game, "_market_timer"):
    win.game._market_timer.stop()

if A.pagina == "mercado":
    URL = QUrl.fromLocalFile(str(mercado_teste.preparar(A.versao, TMP / "mercado"))).toString()
else:
    URL = "https://pokeidle.io/app"


def esperar(seg: float):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


for a in contas:
    web.open(a.index, str(a.profile_dir / "web"), URL, cfg["janela"]["zoom"])
esperar(8 if A.pagina == "jogo" else 3)


def medir(view) -> dict:
    res = {}
    view.page().runJavaScript(mercado_teste.MEDIR_JS, 0, lambda v: res.setdefault("v", v))
    fim = time.monotonic() + 5
    while "v" not in res and time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)
    try:
        return json.loads(res.get("v") or "{}")
    except (TypeError, ValueError):
        return {}


def aplicar(c: dict):
    DIALOGO.clear()
    win.setFixedSize(c["w"], c["h"])
    qapp.processEvents()
    win._painel_conta(c.get("ficha", True), salvar=False)
    win.b_bottom.setChecked(c.get("registro", False))
    visao = c.get("visao", "uma")
    if visao == "uma":
        win.select(c.get("conta", 3))
        if "zoom" in c:
            g = win.game
            g.zoom[g.current] = c["zoom"]
            g.host.relayout()
            g.update_info(m.snapshot()[g.current])
    else:
        win._trocar_layout_todas("celulares" if visao == "celulares" else "grade", salvar=False)
        win.view_all()
    area = c.get("area", "jogo")
    if area in ("jogo", "hunts"):
        win.game.set_hunts(area == "hunts")
    elif area in ("rmt", "guia"):
        if win.game.area != "rmt":
            win._alternar_rmt()
        if area == "guia":
            esperar(0.5)
            win.game.rmt_panel.abrir_guia()
    esperar(c.get("espera", A.espera))
    if area in ("f1", "ajustes", "perguntar"):
        # Janelas modais: o print é da própria janela, tirado com ela aberta, e ela é fechada sem resposta.
        def tirar():
            d = QApplication.activeModalWidget()
            if d is None:                      # ainda não abriu: tenta de novo (senão o exec() trava)
                QTimer.singleShot(300, tirar)
                return
            if d is not None:
                d.grab().save(str(SAIDA / f"{A.prefixo}{c['nome']}_janela.png"))
                DIALOGO["tam"] = [d.width(), d.height()]
                fg, av = d.frameGeometry(), d.screen().availableGeometry()
                DIALOGO["moldura"] = [fg.x(), fg.y(), fg.width(), fg.height()]
                DIALOGO["tela_util"] = [av.x(), av.y(), av.width(), av.height()]
                DIALOGO["cabe_na_tela"] = av.contains(fg)
                d.reject()
        DIALOGO.clear()
        QTimer.singleShot(1200, tirar)
        if area == "f1":
            win._ajuda()
        elif area == "ajustes":
            win.open_settings()
        else:
            G.perguntar(win, "Parar tudo?", "As 4 contas conectadas param de caçar agora. Dá para "
                        "começar de novo quando quiser.", sim="Parar", nao="Cancelar", perigo=True)
        esperar(0.3)


DIALOGO = {}


def cenarios_padrao() -> list:
    e = A.escala
    # Área da janela maximizada (sem a barra de título, ~31 px lógicos) e sem a barra de tarefas (48 px).
    telas = {"1366x768": (1366, 768), "1600x900": (1600, 900), "1920x1080": (1920, 1080), "2560x1440": (2560, 1440)}
    r = []
    for nome, (tw, th) in telas.items():
        w, h = round(tw / e), round(th / e) - 48 - 31
        for ficha in (True, False):
            r.append({"nome": f"{nome}_uma_ficha{int(ficha)}", "w": w, "h": max(h, 600), "ficha": ficha,
                      "visao": "uma", "zoom": 1.0})
    r.append({"nome": "minimo_uma", "w": 760, "h": 600, "visao": "uma", "zoom": 1.0})
    # O resto da matriz: cada valor de cada eixo pelo menos uma vez, mais as combinações de tela pequena.
    extras = {
        "1920x1080": ["zoom50", "zoom80", "zoom150", "zoom200", "grade", "celulares", "registro", "hunts", "rmt",
                      "guia", "f1", "ajustes", "perguntar"],
        "1366x768": ["grade", "celulares", "registro", "hunts", "rmt", "guia", "ajustes", "f1"],
        "minimo": ["grade", "celulares", "registro", "hunts", "rmt", "guia", "ajustes"],
    }
    for nome, lista in extras.items():
        if nome == "minimo":
            w, h = 760, 600
        else:
            tw, th = telas[nome]
            w, h = round(tw / e), max(600, round(th / e) - 48 - 31)
        for x in lista:
            c = {"nome": f"{nome}_{x}", "w": w, "h": h, "visao": "uma", "zoom": 1.0}
            if x.startswith("zoom"):
                c["zoom"] = int(x[4:]) / 100
            elif x in ("grade", "celulares"):
                c["visao"] = x
                c.pop("zoom")
            elif x == "registro":
                c["registro"] = True
            else:
                c["area"] = x
            r.append(c)
    return r


CEN = json.loads(Path(A.cenarios).read_text(encoding="utf-8")) if A.cenarios else cenarios_padrao()
resultado = {"escala": A.escala, "leve": A.leve, "semgpu": A.semgpu, "desenho_leve": WH.DESENHO_LEVE,
             "pagina": A.pagina, "tela": [GEO.width(), GEO.height()], "cenarios": []}
for c in CEN:
    aplicar(c)
    g = win.game
    reg = {"cenario": c, "janela": [win.width(), win.height()]}
    vistas = []
    for cell in g.cells:
        if cell.view is None or not cell.isVisible():
            continue
        v = cell.view
        reg_v = {"conta": cell.index + 1, "zoom": round(v.zoomFactor(), 3),
                 "quadro_px_logicos": [v.width(), v.height()],
                 "quadro_px_fisicos": [round(v.width() * v.devicePixelRatioF()), round(v.height() * v.devicePixelRatioF())]}
        reg_v.update(medir(v))
        vistas.append(reg_v)
    reg["paginas"] = vistas
    if DIALOGO:
        reg["dialogo"] = dict(DIALOGO)
    reg["area_jogo_px"] = [g.host.width(), g.host.height()]
    png = SAIDA / f"{A.prefixo}{c['nome']}.png"
    win.grab().save(str(png))
    reg["print"] = png.name
    resultado["cenarios"].append(reg)
    p0 = vistas[0] if vistas else {}
    print(c["nome"], "janela", reg["janela"], "pagina css", p0.get("iw"), "x", p0.get("ih"), "zoom", p0.get("zoom"),
          "modal", (p0.get("modal") or {}).get("h"), "cortados", p0.get("cortados"), flush=True)

(SAIDA / f"{A.prefixo}medidas.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False), encoding="utf-8")
win.timer.stop()
web.close_all()
esperar(0.5)
os._exit(0)

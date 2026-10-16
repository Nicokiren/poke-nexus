"""Vistoria das telas do jogo que só existem com login, numa conta REAL. SÓ com a autorização do usuário.

    .venv\\Scripts\\python.exe ferramentas\\interface\\conta_real.py --autorizado --conta 4 --saida <pasta>

O que faz: abre o PokeNexus (a mesma janela) com uma pasta de dados temporária e só a página da conta pedida,
usando o perfil web dela (o login fica com o navegador; este script não lê cookies nem tokens). Nenhum worker
é iniciado: nada de farm, nada de Mercado (RMT), nenhuma automação. Os únicos cliques são para ABRIR e FECHAR
telas: os botões do menu do jogo (`button[data-modal]`, Mochila), as categorias e as abas do Market. Nunca
clica dentro de um cartão (comprar, vender), nem em Shop/RMT/Diamantes/Gema.

Para cada tela: print da janela e medidas (página em px CSS, modal, e o que está cortado sem rolagem).
"""
import argparse
import json
import os
import subprocess
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
ap.add_argument("--autorizado", action="store_true")
ap.add_argument("--conta", type=int, required=True)
ap.add_argument("--saida", required=True)
ap.add_argument("--escala", type=float, default=1.0)
ap.add_argument("--leve", type=int, default=1)
ap.add_argument("--w", type=int, default=1920)
ap.add_argument("--h", type=int, default=1001)
ap.add_argument("--prefixo", default="")
ap.add_argument("--ficha", type=int, default=1)
ap.add_argument("--telas", default="market,bolsa,pokedex,mapa,ranking,ginasios,pokepedia")
A = ap.parse_args()
if not A.autorizado:
    sys.exit("Conta real só com a autorização do usuário: use --autorizado.")
lista = subprocess.run(["tasklist", "/FI", "IMAGENAME eq PokeNexus.exe"], capture_output=True, text=True).stdout
if "PokeNexus.exe" in lista:
    sys.exit("O PokeNexus do usuário está aberto: a mesma conta em dois lugares derruba a sessão.")
PERFIL_REAL = Path(os.environ["LOCALAPPDATA"]) / "PokeNexus" / "profiles" / f"conta_{A.conta:02d}" / "web"
if not PERFIL_REAL.is_dir():
    sys.exit(f"perfil não encontrado: {PERFIL_REAL}")
SAIDA = Path(A.saida)
SAIDA.mkdir(parents=True, exist_ok=True)

TMP = Path(tempfile.mkdtemp(prefix="pn_real_"))
os.environ["POKENEXUS_DATA"] = str(TMP)
if A.escala != 1.0:
    os.environ["QT_SCALE_FACTOR"] = str(A.escala)
os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
import app.config as C  # noqa: E402
C.MODO_LEVE = bool(A.leve)
import browser.web_host as WH  # noqa: E402
PORT = WH.setup_environment()
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.gui as G  # noqa: E402

web = WH.WebHost(PORT)
m = G.Manager(cfg, contas, web)             # sem m.start(): nenhum worker, nenhuma automação
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
tela = next((t for t in QGuiApplication.screens() if t is not QGuiApplication.primaryScreen()),
            QGuiApplication.primaryScreen())
win.move(tela.geometry().x(), tela.geometry().y())
win.setFixedSize(A.w, A.h)
win.show()
I = A.conta - 1
LOG = []


def esperar(seg: float):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


def js(codigo: str, espera=8.0):
    res = {}
    win.game.view(I).page().runJavaScript(codigo, 0, lambda v: res.setdefault("v", v))
    fim = time.monotonic() + espera
    while "v" not in res and time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)
    return res.get("v")


# Só leitura: o que está cortado SEM rolagem dentro do modal aberto (conteúdo maior que a caixa e
# `overflow` que não rola), mais as medidas do Market (mercado_teste.MEDIR_JS).
CORTES_JS = r"""(() => {
  const fundo = document.getElementById('modal');
  if (!fundo || fundo.classList.contains('hidden')) return JSON.stringify({aberto: false});
  const cx = fundo.querySelector('.modal-caixa'), b = cx.getBoundingClientRect();
  const cortes = [];
  for (const el of cx.querySelectorAll('*')) {
    if (!el.offsetParent || el.clientHeight < 20) continue;
    const oy = getComputedStyle(el).overflowY;
    if ((oy === 'hidden' || oy === 'clip') && el.scrollHeight > el.clientHeight + 4)
      cortes.push({cls: (el.className && el.className.baseVal === undefined ? el.className : '').slice(0, 50),
                   h: el.clientHeight, conteudo: el.scrollHeight});
  }
  return JSON.stringify({aberto: true, modal: cx.dataset.modal, ih: innerHeight, iw: innerWidth,
                         mobile: document.documentElement.classList.contains('mobile'),
                         caixa: [Math.round(b.top), Math.round(b.bottom), Math.round(b.height)],
                         fora_da_tela: b.bottom > innerHeight + 1 || b.top < -1,
                         cortes: cortes.slice(0, 12), n_cortes: cortes.length});
})()"""


def registrar(nome: str, extra: dict | None = None):
    esperar(0.3)
    r = {"nome": nome, "zoom": round(win.game.view(I).zoomFactor(), 3), "rotulo_zoom": win.game.zoom_lbl.text()}
    try:
        r["cortes"] = json.loads(js(CORTES_JS) or "{}")
        r["market"] = json.loads(js(mercado_teste.MEDIR_JS) or "{}")
    except (TypeError, ValueError):
        pass
    if extra:
        r.update(extra)
    win.grab().save(str(SAIDA / f"{A.prefixo}{nome}.png"))
    LOG.append(r)
    mk = r.get("market") or {}
    print(nome, "zoom", r["zoom"], "pagina", mk.get("iw"), "x", mk.get("ih"), "modal", (mk.get("modal") or {}).get("h"),
          "cartoes sem botao", mk.get("cortados"), "cortes", (r.get("cortes") or {}).get("n_cortes"), flush=True)


def clicar(seletor: str) -> bool:
    """Clica num botão de NAVEGAÇÃO do jogo (abrir/fechar tela, aba, categoria)."""
    return js(f"(() => {{ const b = document.querySelector({json.dumps(seletor)});"
              f" if (!b) return false; b.click(); return true; }})()") is True


def fechar_modal():
    clicar("#modal:not(.hidden) #modal-fechar")
    esperar(1.5)


try:
    web.open(I, str(PERFIL_REAL), "https://pokeidle.io/app", 1.0)
    esperar(2)
    win._painel_conta(bool(A.ficha), salvar=False)
    win.select(I)
    # espera o jogo (logado) montar o menu
    pronto = False
    for _ in range(90):
        esperar(1)
        # o jogo à vista (`#app` sem `hidden`, o mesmo teste do game/selectors.py); no layout de celular o
        # botão do Market fica dentro do "Menu", mas o clique de abrir é o mesmo
        if js("(() => { const a = document.getElementById('app'); return !!(a && !a.classList.contains('hidden')"
              " && document.querySelector('button[data-modal=\"market\"]')); })()") is True:
            pronto = True
            break
    if not pronto:
        registrar("00_sem_jogo")
        raise SystemExit("o jogo não montou o menu (sessão expirada ou tela de login?): nada foi feito")
    esperar(4)
    # Os avisos do próprio jogo que abrem sozinhos por cima de tudo (Discord, novidades): só o × / OK
    # de fechar, nunca o "não mostrar novamente" nem o link.
    for _ in range(3):
        clicar("#discord-popup:not(.hidden) #discord-popup-fechar")
        js("(() => { const b = document.getElementById('aviso-jogo-ok'); if (b && b.offsetParent) b.click(); })()")
        esperar(1.5)
    registrar("00_jogo")
    telas = A.telas.split(",")
    if "market" in telas:
        win.game._market_timer.stop()                     # ANTES: sem o zoom do Market
        clicar('button[data-modal="market"]')
        esperar(3)
        registrar("01_market_antes")
        win.game._market_timer.start(800)                 # DEPOIS: com o zoom do Market
        esperar(3)
        registrar("02_market_depois")
        cats = js("JSON.stringify([...document.querySelectorAll('#mk-corpo .mk-cat')].map(b => b.textContent.trim()))")
        for k, nome in enumerate(json.loads(cats or "[]")):
            clicar(f"#mk-corpo .mk-lado .mk-cat:nth-of-type({k + 1})")
            esperar(2.5)
            registrar(f"03_market_cat{k + 1}", {"categoria": nome})
        clicar("#mk-corpo .mk-lado .mk-cat:nth-of-type(1)")
        esperar(1)
        # a aba de VENDA só é olhada (nenhum botão dentro dela é tocado)
        clicar('#mk-modos .cmp-op:not(.on)')
        esperar(3)
        registrar("04_market_venda")
        clicar('#mk-modos .cmp-op:not(.on)')
        esperar(1.5)
        # Grade e Celulares com o Market aberto
        win._trocar_layout_todas("grade", salvar=False)
        win.view_all()
        esperar(3)
        registrar("05_market_grade")
        win._trocar_layout_todas("celulares", salvar=False)
        esperar(3)
        registrar("06_market_celulares")
        win._trocar_layout_todas("grade", salvar=False)
        win.select(I)
        esperar(3)
        registrar("07_market_volta_uma")
        fechar_modal()
        esperar(2)
        registrar("08_market_fechado")
    for nome in telas:
        if nome == "market":
            continue
        sel = "#btn-bolsa" if nome == "bolsa" else f'button[data-modal="{nome}"]'
        if not clicar(sel):
            LOG.append({"nome": f"10_{nome}", "erro": "botão não encontrado"})
            continue
        esperar(3)
        registrar(f"10_{nome}")
        fechar_modal()
    registrar("99_fim")
finally:
    (SAIDA / f"{A.prefixo}medidas.json").write_text(json.dumps(LOG, indent=1, ensure_ascii=False), encoding="utf-8")
    try:
        js("(() => { const f = document.querySelector('#modal:not(.hidden) #modal-fechar'); if (f) f.click(); })()", 2)
    except Exception:
        pass
    win.timer.stop()
    web.close_all()
    esperar(1.5)
    os._exit(0)

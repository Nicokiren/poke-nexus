"""Teste de tela do erro de rede, do contador do topo e do DNS seguro (docs/rede/RELATORIO.md).

    .venv\\Scripts\\python.exe ferramentas\\rede\\tela_erro.py --saida <arquivo.json> --prints <pasta>
        [--sem-dns] [--netlog <arquivo.json>]

Abre o PokeNexus de verdade com uma pasta de dados TEMPORÁRIA (as contas ficam na tela de login: nenhuma conta
real é tocada) e inicia as 4 contas.
  --sem-dns   simula o defeito do amigo SÓ neste processo: o Chromium do programa recebe
              --host-resolver-rules="MAP pokeidle.io ~NOTFOUND" (o pokeidle.io "não existe"). A rede do PC não
              é tocada. Confere a frase em português, o código na dica, o log com o texto original, o contador
              "0/4 jogando" e que o limite de contas continua valendo.
  --netlog    grava o registro de rede do Chromium (--log-net-log) para conferir as consultas de DNS seguro.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
ap.add_argument("--saida", required=True)
ap.add_argument("--prints", required=True)
ap.add_argument("--sem-dns", action="store_true")
ap.add_argument("--netlog", default="")
A = ap.parse_args()
sys.path.insert(0, A.raiz)
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_rede_")
flags = []
if A.sem_dns:
    flags.append('--host-resolver-rules="MAP pokeidle.io ~NOTFOUND"')
if A.netlog:
    flags += [f"--log-net-log={A.netlog}", "--net-log-capture-mode=Default"]     # caminho sem espaços
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)
PRINTS = Path(A.prints)
PRINTS.mkdir(parents=True, exist_ok=True)

import app.config as C  # noqa: E402
import browser.web_host as WH  # noqa: E402
porta = WH.setup_environment()
from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolTip  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
import app.gui as G  # noqa: E402

web = WH.WebHost(porta)
m = G.Manager(cfg, contas, web)
m.start()
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
win.setFixedSize(1600, 1000)
win.move(0, 0)
win.show()
R = {"dns_seguro_ligado": getattr(WH, "DNS_SEGURO", None),"flags": os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")}


def esperar(seg):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


def esperar_ate(cond, seg):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        if cond():
            return True
        esperar(0.2)
    return False


def print_dica(widget, nome):
    """Mostra a dica (tooltip) do widget e monta o print com a janela + o balão da dica, os dois desenhados pelo
    próprio Qt (widget.grab). Nada da tela do PC entra no print (outras janelas por cima ficariam na foto)."""
    centro = widget.mapToGlobal(widget.rect().center())
    QToolTip.showText(centro, widget.toolTip(), widget)
    esperar(0.8)
    balao = next((w for w in QApplication.topLevelWidgets()
                   if w.isVisible() and w.metaObject().className() == "QTipLabel"), None)
    foto = win.grab()
    if balao is not None:
        p = QPainter(foto)
        p.drawPixmap(win.mapFromGlobal(balao.pos()), balao.grab())
        p.end()
    perto = win.mapFromGlobal(centro)
    x, y = max(0, perto.x() - 420), max(0, perto.y() - 120)
    foto.copy(x, y, 840, 280).save(str(PRINTS / nome))
    QToolTip.hideText()
    esperar(0.3)


def ler(prefixo):
    s = m.snapshot()
    win.select(0)
    esperar(1.2)
    ph = win.game.cells[0].placeholder
    R[prefixo] = {
        "status": [x["status"] for x in s], "detail_original": [x["detail"] for x in s],
        "placeholder_texto": ph.text.text(), "placeholder_dica": ph.text.toolTip(),
        "placeholder_visivel": ph.isVisible(),
        "ficha_texto": win.side.detail.text(), "ficha_dica": win.side.detail.toolTip(),
        "contador": win.counter.text(), "contador_dica": win.counter.toolTip(),
        "iniciadas_manager": m.connected_count(),
    }
    win.grab().save(str(PRINTS / f"{prefixo}_janela.png"))
    print_dica(win.counter, f"{prefixo}_dica_contador.png")
    if ph.isVisible() and ph.text.toolTip():
        print_dica(ph.text, f"{prefixo}_dica_erro.png")


m.start_all()
if A.sem_dns:
    # espera as 4 contas caírem no erro de rede (a 1ª tentativa leva alguns segundos)
    R["todas_em_erro"] = esperar_ate(lambda: all(x["status"] == "ERRO" for x in m.snapshot()), 60)
    ler("erro_dns")
    linhas = []
    for arq in C.LOGS_DIR.glob("*.log"):
        linhas += arq.read_text(encoding="utf-8").splitlines()
    R["log_com_codigo"] = [l for l in linhas if "ERR_NAME_NOT_RESOLVED" in l][:4]
    R["log_com_frase_traduzida"] = [l for l in linhas if "Não consegui" in l]

    def foto_f1():
        d = QApplication.activeModalWidget()
        if d is None:
            QTimer.singleShot(200, foto_f1)
            return
        d.grab().save(str(PRINTS / "f1_ajuda.png"))
        d.reject()
    QTimer.singleShot(500, foto_f1)
    win._ajuda()
    # o limite de contas não mudou: com 0 jogando, as 4 iniciadas continuam contando
    cfg["max_simultaneas"] = 3                       # como em Ajustes (vale na hora)
    m.stop_account(3)
    esperar(3)
    R["limite_3_quarta_recusada"] = m.start_account(3)
    cfg["max_simultaneas"] = 4
    R["limite_4_quarta_aceita"] = m.start_account(3)
    esperar(1)
    R["iniciadas_depois"] = m.connected_count()
    # uma 5ª conta não existe: o config com 5 contas abre só 4
    t = Path(tempfile.mkdtemp(prefix="pn_cfg5_")) / "config.toml"
    t.write_text("quantidade_contas = 5\nmax_simultaneas = 5\n"
                 + "".join(f'[[contas]]\nnome = "T{i}"\n' for i in range(1, 6)), encoding="utf-8")
    cfg5, contas5 = C.load_config(t)
    R["config_5_contas"] = {"contas": len(contas5), "max_simultaneas": cfg5["max_simultaneas"]}
else:
    # DNS normal: as contas abrem na tela de login do jogo, como antes
    t0 = time.monotonic()
    R["paginas_abertas"] = esperar_ate(lambda: all(web.view(i) is not None for i in range(4)), 60)
    R["todas_no_login"] = esperar_ate(lambda: all(x["status"] == "SESSÃO EXPIRADA" for x in m.snapshot()), 90)
    R["segundos_ate_o_login"] = round(time.monotonic() - t0, 1)
    esperar(5)
    R["urls"] = [web.view(i).url().toString() if web.view(i) else None for i in range(4)]
    ler("dns_normal")
    # a página de dados do Hunt Analyzer e da Pokédex (perfil anônimo) também abre
    fut = m.pokedex_catalogo()
    esperar_ate(fut.done, 120)
    try:
        cat = fut.result(0)
        R["pagina_de_dados"] = {"versao_do_jogo": cat.get("versao"), "especies": len(cat.get("especies") or {})}
    except Exception as e:
        R["pagina_de_dados"] = {"erro": str(e)}

Path(A.saida).write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(R, indent=1, ensure_ascii=False), flush=True)
win.close()           # fecha como o X da janela
esperar(4)
os._exit(0)

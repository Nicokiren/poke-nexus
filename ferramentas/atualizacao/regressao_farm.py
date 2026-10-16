"""Teste 7 (regressão): o farm das contas continua com o aviso de atualização aberto e durante o download.

    set POKENEXUS_ATUALIZACAO_URL=http://127.0.0.1:8766/maior8766/latest   (servidor falso lento)
    .venv\\Scripts\\python.exe ferramentas\\atualizacao\\regressao_farm.py --saida <pasta>

Janela de verdade, pasta de dados temporária, as 4 contas iniciadas (ficam na tela de login: nenhuma conta
real). Mostra a faixa e abre o MESMO diálogo de download do botão Atualizar (o instalador vem do servidor
falso). A cada 1 s mede: a idade do `heartbeat` de cada conta (o mesmo sinal do vigia de travamento, que
reinicia a conta acima de WATCHDOG_SEGUNDOS) e o atraso da thread da tela. O fim do fluxo (fechar e
instalar) não roda aqui.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
ap = argparse.ArgumentParser()
ap.add_argument("--saida", required=True)
A = ap.parse_args()
SAIDA = Path(A.saida)
SAIDA.mkdir(parents=True, exist_ok=True)
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_atu_7_")

from browser.web_host import WebHost, setup_environment  # noqa: E402
porta = setup_environment()
from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
qapp = QApplication(sys.argv)
import app.config as C  # noqa: E402
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.atualizacao as AT  # noqa: E402
import app.gui as G  # noqa: E402
from app.manager import WATCHDOG_SEGUNDOS  # noqa: E402

web = WebHost(porta)
m = G.Manager(cfg, contas, web)
m.start()
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
win.setFixedSize(1920, 1001)
win.show()


def esperar(s):
    fim = time.monotonic() + s
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


AMOSTRAS = []
_ult = [time.monotonic()]


def amostrar(fase):
    agora = time.monotonic()
    atraso_tela = (agora - _ult[0] - 1.0) * 1000
    _ult[0] = agora
    idades = [round(agora - w.heartbeat, 2) if w.running else None for w in m.workers]
    AMOSTRAS.append({"fase": fase(), "idades_heartbeat_s": idades, "atraso_tela_ms": round(atraso_tela, 1),
                     "status": [s["status"] for s in m.snapshot()]})


FASE = ["contas iniciando"]
relogio = QTimer()
relogio.timeout.connect(lambda: amostrar(lambda: FASE[0]))
relogio.start(1000)

m.start_all()
esperar(15)
FASE[0] = "faixa aberta"
info = AT.Consulta(AT.URL_TESTE).buscar()
win.atualizacao.faixa.mostrar(info)
esperar(10)
win.grab().save(str(SAIDA / "7a_faixa_com_4_contas.png"))
FASE[0] = "baixando"
destino = Path(tempfile.mkdtemp(prefix="pn_atu_7_dl_")) / info["setup_nome"]
d = AT.DialogoDownload(win, info, destino)
QTimer.singleShot(8000, lambda: (win.grab().save(str(SAIDA / "7b_baixando_janela.png")),
                                 d.grab().save(str(SAIDA / "7b_baixando_dialogo.png"))))
t0 = time.monotonic()
d.exec()
dur = time.monotonic() - t0
FASE[0] = "depois do download"
esperar(5)
relogio.stop()

baixando = [a for a in AMOSTRAS if a["fase"] in ("faixa aberta", "baixando")]
idades = [x for a in baixando for x in a["idades_heartbeat_s"] if x is not None]
resumo = {
    "download_s": round(dur, 1), "download_erro": d.erro, "sha_ok": d.esperado == d.obtido and bool(d.esperado),
    "contas_rodando": sum(1 for w in m.workers if w.running),
    "heartbeat_idade_max_s": max(idades) if idades else None, "watchdog_reinicia_acima_de_s": WATCHDOG_SEGUNDOS,
    "atraso_tela_max_ms": max(a["atraso_tela_ms"] for a in baixando) if baixando else None,
    "amostras": len(AMOSTRAS),
}
(SAIDA / "7_medidas.json").write_text(json.dumps({"resumo": resumo, "amostras": AMOSTRAS}, indent=1,
                                                 ensure_ascii=False), encoding="utf-8")
print(json.dumps(resumo, ensure_ascii=False), flush=True)
destino.unlink(missing_ok=True)
win.close()
esperar(3)
os._exit(0)

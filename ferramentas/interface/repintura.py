"""Quanto tempo leva repintar a janela inteira do PokeNexus (a mesma conta do `app/molduras.py`).

    .venv\\Scripts\\python.exe ferramentas\\interface\\repintura.py [--raiz <cópia do projeto>] [--leve 1]

`--raiz` permite medir o código de ANTES (ex.: `git archive HEAD` descompactado numa pasta temporária) com
o mesmo script. Janela de verdade, 1920×1001, pasta de dados temporária, nenhuma conta aberta (só os
widgets do programa). Imprime a mediana e o p90 de 200 repinturas, depois de 30 de aquecimento.
"""
import argparse
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
ap.add_argument("--leve", type=int, default=1)
ap.add_argument("--n", type=int, default=200)
A = ap.parse_args()
sys.path.insert(0, A.raiz)
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_rep_")

import app.config as C  # noqa: E402
C.MODO_LEVE = bool(A.leve)
import browser.web_host as WH  # noqa: E402
porta = WH.setup_environment()
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.gui as G  # noqa: E402

web = WH.WebHost(porta)
m = G.Manager(cfg, contas, web)
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
win.setFixedSize(1920, 1001)
win.show()
fim = time.monotonic() + 2
while time.monotonic() < fim:
    qapp.processEvents()
    time.sleep(0.01)
win.timer.stop()
tempos = []
for k in range(30 + A.n):
    t = time.perf_counter()
    win.repaint()
    dt = (time.perf_counter() - t) * 1000
    if k >= 30:
        tempos.append(dt)
    qapp.processEvents()
tempos.sort()
print(f"raiz={A.raiz} leve={A.leve} mediana={statistics.median(tempos):.2f} ms "
      f"p90={tempos[int(len(tempos) * 0.9)]:.2f} ms n={len(tempos)}", flush=True)
web.close_all()
os._exit(0)

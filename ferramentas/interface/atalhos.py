"""Teste de comportamento (Fase 5): o programa responde igual antes × depois de uma mudança de interface.

    .venv\\Scripts\\python.exe ferramentas\\interface\\atalhos.py --saida <arquivo.json> [--raiz <cópia do projeto>]

Abre o PokeNexus de verdade com uma pasta de dados TEMPORÁRIA, inicia as 4 contas (ficam na tela de login:
nenhuma conta real é tocada) e aperta, pelos próprios atalhos da janela: Ctrl+1…4, Ctrl+0, grade/celulares,
Ctrl+H, Ctrl+M, Ctrl+, (Ajustes), F1, F8, Ctrl+B e "Parar tudo" (respondendo Parar). Depois de cada um anota
o estado da janela (conta selecionada, modo, área, painel, diálogo aberto) e o estado das contas. Rodar no
código de antes (`--raiz`) e no de depois e comparar os dois JSON.
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
A = ap.parse_args()
sys.path.insert(0, A.raiz)
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_atal_")

import app.config as C  # noqa: E402
import browser.web_host as WH  # noqa: E402
porta = WH.setup_environment()
from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtGui import QShortcut  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.gui as G  # noqa: E402

web = WH.WebHost(porta)
m = G.Manager(cfg, contas, web)
m.start()
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
win.setFixedSize(1600, 1000)
win.show()


def esperar(seg):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


atalhos = {sc.key().toString(): sc for sc in win.findChildren(QShortcut)}
DIALOGOS = []


def fechar_dialogo(resposta: str | None = None):
    def tirar():
        d = QApplication.activeModalWidget()
        if d is None:
            QTimer.singleShot(200, tirar)
            return
        DIALOGOS.append(d.windowTitle())
        if resposta:
            for b in d.findChildren(QPushButton):
                if b.text().strip() == resposta:
                    b.click()
                    return
        d.reject()
    QTimer.singleShot(300, tirar)


def estado(acao: str) -> dict:
    esperar(1.5)
    s = m.snapshot()
    return {"acao": acao, "selecionada": win.selected, "ver_todas": win.grid_mode,
            "layout_todas": win.game.host.layout_todas, "area": win.game.area,
            "ficha_visivel": win.side.isVisible(), "dialogos": list(DIALOGOS),
            "contas": [(x["running"], x["mode"], x["status"]) for x in s]}


LOG = []
m.start_all()
esperar(10)
LOG.append(estado("começar tudo"))
for k in (2, 3, 4, 1):
    atalhos[f"Ctrl+{k}"].activated.emit()
    LOG.append(estado(f"Ctrl+{k}"))
atalhos["Ctrl+0"].activated.emit()
LOG.append(estado("Ctrl+0"))
win.game.b_cel.click()
LOG.append(estado("Celulares"))
win.game.b_grade.click()
LOG.append(estado("Grade"))
atalhos["Ctrl+1"].activated.emit()
for k in ("Ctrl+H", "Ctrl+H", "Ctrl+M", "Ctrl+M", "Ctrl+B", "Ctrl+B", "F8", "F8"):
    atalhos[k].activated.emit()
    LOG.append(estado(k))
fechar_dialogo()
atalhos["Ctrl+,"].activated.emit()
LOG.append(estado("Ctrl+,"))
fechar_dialogo()
atalhos["F1"].activated.emit()
LOG.append(estado("F1"))
fechar_dialogo("Parar")
win._stop_all()
esperar(4)
LOG.append(estado("Parar tudo"))
Path(A.saida).write_text(json.dumps(LOG, indent=1, ensure_ascii=False), encoding="utf-8")
print("ok", len(LOG), "passos", flush=True)
# fecha como o X da janela (closeEvent: para o relógio, as contas e as páginas), com o laço do Qt rodando
win.close()
esperar(3)
os._exit(0)

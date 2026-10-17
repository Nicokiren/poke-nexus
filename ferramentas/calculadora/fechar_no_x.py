"""Abre o PokeNexus pelo main.py de verdade (pasta de dados temporária: as contas abrem na tela de login),
vai ao Mercado, abre e usa a calculadora e fecha pelo X (o mesmo caminho da pessoa). O código de saída do
processo é o do programa: 0 = fechou limpo.

    .venv\\Scripts\\python.exe ferramentas\\calculadora\\fechar_no_x.py [--raiz <cópia do projeto>]
"""
import os
import sys
import tempfile

raiz = sys.argv[sys.argv.index("--raiz") + 1] if "--raiz" in sys.argv else os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.abspath(raiz))
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_x_")
sys.argv = [sys.argv[0]]

import main as M  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
import app.gui as G  # noqa: E402

_orig = G.MainWindow.showMaximized


def roteiro(win):
    win._alternar_rmt()                                   # Ctrl+M: o Mercado
    rp = win.game.rmt_panel
    if getattr(rp, "b_calc", None) is not None:
        rp.b_calc.click()                                 # abre a calculadora
        QTest.keyClicks(rp.calc.e_gemas, "1000")
        rp.calc.b_inverter.click()
        QTest.keyClicks(rp.calc.e_dolares, "5")
    print("roteiro feito, fechando no X", flush=True)
    QTimer.singleShot(1500, win.close)


def mostrar(self):
    _orig(self)
    QTimer.singleShot(5000, lambda: roteiro(self))


G.MainWindow.showMaximized = mostrar
codigo = M.main()
print("app.exec() devolveu", codigo, flush=True)
sys.exit(codigo)

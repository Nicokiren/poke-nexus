"""Abre o PokeNexus pelo main.py de verdade (pasta de dados temporária: as contas abrem na tela de login), abre a
Pokédex, rola, filtra, troca de conta e de modo, volta ao jogo e fecha pelo X (o caminho da pessoa). O código de
saída do processo é o do programa: 0 = fechou limpo.

    .venv\\Scripts\\python.exe ferramentas\\pokedex\\fechar_no_x.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_x_")
sys.argv = [sys.argv[0]]

import main as M  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
import app.gui as G  # noqa: E402

_orig = G.MainWindow.showMaximized


def roteiro(win):
    win._alternar_pokedex()
    p = win.game.pokedex_panel
    barra = p.grade.verticalScrollBar()
    for v in range(0, barra.maximum() + 200, 200):
        barra.setValue(v)
    p.set_regiao("Hoenn")
    p.busca.setText("25")
    p.so_faltam.setChecked(True)
    p.set_todas(True)
    win.select(1)
    p.set_todas(False)
    win._alternar_pokedex()                      # volta ao jogo
    win._alternar_pokedex()                      # e abre de novo
    print("roteiro feito, fechando no X", flush=True)
    QTimer.singleShot(1500, win.close)


def mostrar(self):
    _orig(self)
    QTimer.singleShot(5000, lambda: roteiro(self))


G.MainWindow.showMaximized = mostrar
codigo = M.main()
print("app.exec() devolveu", codigo, flush=True)
sys.exit(codigo)

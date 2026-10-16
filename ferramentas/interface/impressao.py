"""Impressão digital do comportamento do PokeNexus (prova de que uma mudança de interface não mexeu em nada
que o programa FAZ). Só lê: nada do app é mudado e nenhuma conta é tocada (pasta de dados temporária).

    .venv\\Scripts\\python.exe ferramentas\\interface\\impressao.py --saida docs\\visual\\interface_1300\\linha_de_base

Gera na pasta de saída:
  hashes.json      SHA-256 de todos os arquivos do repositório (fora .venv, build, dist, docs e caches)
  ligacoes.json    leitura do código (AST) de app/*.py: cada `.connect(...)`, cada `button(...)`/`Botao(...)`
                   com o método que ele chama, cada `addAction` de menu e a lista de atalhos. Sem número de
                   linha, para comparar antes × depois mesmo com linhas que mudaram de lugar.
  widgets.json     a janela de verdade montada (offscreen): cada botão (nome do objeto, texto, dica,
                   quantos métodos ligados ao clique) e cada atalho de teclado.
"""
import argparse
import ast
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
FORA = {".venv", "build", "dist", "dist_novo", "docs", "__pycache__", ".git", "profiles", "logs", ".claude"}

ap = argparse.ArgumentParser()
ap.add_argument("--saida", required=True)
A = ap.parse_args()
SAIDA = Path(A.saida)
SAIDA.mkdir(parents=True, exist_ok=True)


def hashes() -> dict:
    r = {}
    for p in sorted(RAIZ.rglob("*")):
        rel = p.relative_to(RAIZ)
        if p.is_dir() or any(part in FORA for part in rel.parts) or p.suffix in (".pyc",):
            continue
        r[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return r


class Ligacoes(ast.NodeVisitor):
    def __init__(self, arq: str, fonte: str):
        self.arq, self.fonte, self.pilha, self.itens = arq, fonte, [], []

    def _onde(self):
        return ".".join(self.pilha) or "<módulo>"

    def visit_ClassDef(self, n):
        self.pilha.append(n.name)
        self.generic_visit(n)
        self.pilha.pop()

    visit_FunctionDef = visit_ClassDef

    def _src(self, n):
        return " ".join((ast.get_source_segment(self.fonte, n) or "").split())

    def visit_Call(self, n):
        f = n.func
        nome = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
        if nome == "connect" and isinstance(f, ast.Attribute):
            self.itens.append({"tipo": "connect", "onde": self._onde(), "sinal": self._src(f.value),
                               "metodo": [self._src(a) for a in n.args]})
        elif nome in ("button", "Botao"):
            kw = {k.arg: self._src(k.value) for k in n.keywords}
            pos = [self._src(a) for a in n.args]
            slot = kw.get("slot") or (pos[3] if nome == "button" and len(pos) > 3 else None)
            self.itens.append({"tipo": nome, "onde": self._onde(), "texto": pos[0] if pos else kw.get("text"),
                               "obj": kw.get("obj") or (pos[1] if len(pos) > 1 else None), "metodo": slot})
        elif nome == "addAction":
            self.itens.append({"tipo": "addAction", "onde": self._onde(), "args": [self._src(a) for a in n.args]})
        elif nome in ("QShortcut",):
            self.itens.append({"tipo": "QShortcut", "onde": self._onde(), "args": [self._src(a) for a in n.args]})
        self.generic_visit(n)

    def visit_Assign(self, n):
        # a lista de atalhos (`pares = [...]` em MainWindow._shortcuts)
        if any(isinstance(t, ast.Name) and t.id == "pares" for t in n.targets):
            self.itens.append({"tipo": "atalhos", "onde": self._onde(), "pares": self._src(n.value)})
        self.generic_visit(n)

    def visit_AugAssign(self, n):
        if isinstance(n.target, ast.Name) and n.target.id == "pares":
            self.itens.append({"tipo": "atalhos+", "onde": self._onde(), "pares": self._src(n.value)})
        self.generic_visit(n)


def ligacoes() -> list:
    todos = []
    for p in sorted((RAIZ / "app").glob("*.py")):
        fonte = p.read_text(encoding="utf-8")
        v = Ligacoes(p.name, fonte)
        v.visit(ast.parse(fonte))
        for it in v.itens:
            it["arquivo"] = p.name
        todos += v.itens
    return sorted(todos, key=lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True))


def widgets() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="pn_imp_"))
    os.environ["POKENEXUS_DATA"] = str(tmp)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from browser.web_host import WebHost, setup_environment
    porta = setup_environment()
    from PySide6.QtCore import SIGNAL
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import QAbstractButton, QApplication
    qapp = QApplication(sys.argv)
    import app.config as C
    C.prepare_data_dir()
    cfg, contas = C.load_config()
    cfg["iniciar_contas_ao_abrir"] = False
    import app.gui as G
    web = WebHost(porta)
    m = G.Manager(cfg, contas, web)          # sem m.start(): nada conecta
    win = G.MainWindow(m, web)
    win.resize(1600, 1000)
    win.show()
    qapp.processEvents()

    def botoes(raiz, nome):
        r = []
        for b in raiz.findChildren(QAbstractButton):
            r.append({"tela": nome, "classe": type(b).__name__, "obj": b.objectName(), "texto": b.text().strip(),
                      "dica": b.toolTip(), "checavel": b.isCheckable(),
                      "ligados_clicked": b.receivers(SIGNAL("clicked(bool)")) + b.receivers(SIGNAL("clicked()")),
                      "ligados_toggled": b.receivers(SIGNAL("toggled(bool)"))})
        return sorted(r, key=lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True))

    r = {"janela": botoes(win, "janela")}
    r["atalhos"] = sorted(sc.key().toString() for sc in win.findChildren(QShortcut))
    dlg = G.SettingsDialog(win, cfg, m.accounts)
    r["ajustes"] = botoes(dlg, "ajustes")
    dlg.deleteLater()
    win.timer.stop()
    web.close_all()
    qapp.processEvents()
    return r


(SAIDA / "hashes.json").write_text(json.dumps(hashes(), indent=1, ensure_ascii=False), encoding="utf-8")
(SAIDA / "ligacoes.json").write_text(json.dumps(ligacoes(), indent=1, ensure_ascii=False), encoding="utf-8")
(SAIDA / "widgets.json").write_text(json.dumps(widgets(), indent=1, ensure_ascii=False), encoding="utf-8")
print("ok", SAIDA)
os._exit(0)

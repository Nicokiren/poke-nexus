"""Pokédex na janela de verdade: prints, testes da tela e medidas. Pasta de dados temporária e NENHUMA conta
conecta (sem m.start()): cada conta recebe um "jogo" falso, só na memória deste teste, com a Pokédex e a coleção
montadas aqui (nada de dados de conta real). Nada sai para a internet.

    .venv\\Scripts\\python.exe ferramentas\\pokedex\\tela.py --modo prints --estilo escuro --saida <pasta>
    .venv\\Scripts\\python.exe ferramentas\\pokedex\\tela.py --modo testes --saida <pasta>
    .venv\\Scripts\\python.exe ferramentas\\pokedex\\tela.py --modo medidas --saida <pasta>
    .venv\\Scripts\\python.exe ferramentas\\pokedex\\tela.py --modo topo --saida <pasta> [--raiz <código de antes>]

--catalogo: pasta com os assets/creatures*.json públicos do jogo (nomes e tipos); sem ela, nomes falsos.
"""
import argparse
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--modo", required=True, choices=["prints", "testes", "medidas", "topo"])
ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
ap.add_argument("--estilo", default="escuro", choices=["escuro", "tela"])
ap.add_argument("--catalogo", default="")
ap.add_argument("--escala", type=float, default=1.0)
ap.add_argument("--leve", type=int, default=0)
ap.add_argument("--offscreen", action="store_true")
ap.add_argument("--saida", required=True)
ap.add_argument("--prefixo", default="")
A = ap.parse_args()
SAIDA = Path(A.saida)
SAIDA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, A.raiz)
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_dex_tela_")
if A.escala != 1.0:
    os.environ["QT_SCALE_FACTOR"] = str(A.escala)
if A.offscreen:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

import app.config as C  # noqa: E402
C.MODO_LEVE = bool(A.leve)
import browser.web_host as WH  # noqa: E402
PORT = WH.setup_environment()
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.gui as G  # noqa: E402

TEM_DEX = hasattr(G, "PokedexPanel")
if TEM_DEX and hasattr(G.PokedexPanel, "ESTILO"):      # só existia durante a escolha das duas propostas
    G.PokedexPanel.ESTILO = A.estilo
web = WH.WebHost(PORT)
m = G.Manager(cfg, contas, web)
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
tela = QGuiApplication.primaryScreen()
if not A.offscreen:
    tela = next((t for t in QGuiApplication.screens() if t is not QGuiApplication.primaryScreen()), tela)
win.move(tela.geometry().topLeft())
win.show()


def esperar(seg: float):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


def tamanho(nome: str):
    if nome == "minimo":
        return 760, 600
    tw, th = {"1366x768": (1366, 768), "1920x1080": (1920, 1080)}[nome]
    return round(tw / A.escala), round(th / A.escala) - 48 - 31


def foto(nome: str, alvo=None):
    esperar(0.4)
    (alvo or win).grab().save(str(SAIDA / f"{A.prefixo}{nome}.png"))


# ------------------------------------------------------------ catálogo (público) e contas falsas
def catalogo_publico() -> dict:
    if not A.catalogo:
        return {n: {"nome": f"Pokémon {n}", "type1": "NORMAL", "type2": None} for n in range(1, 1026)}
    out = {}
    for arq in ("assets_creatures.json", "assets_creatures-novos.json"):
        for c in json.loads((Path(A.catalogo) / arq).read_text(encoding="utf-8"))["creatures"]:
            out[c["pokeId"]] = {"pokeId": c["pokeId"], "nome": c["name"], "type1": c.get("type1"), "type2": c.get("type2")}
    return out


if TEM_DEX:
    m.hunt_data.catalogo = {"versao": "teste", "especies": catalogo_publico()}


class JogoFalso:
    """Só o que a tela lê do jogo. A Pokédex e a coleção são inventadas aqui."""

    def __init__(self, ident, pegos, inventario=()):
        self.eu = {"id": ident, "nick": f"teste{ident}", "gold": 0, "orbs": 0}
        self.dex = {str(n): {"k": 3, "c": 1} for n in pegos}
        self.dex_seq = 1
        self.dex_capturas = []
        self.pokemons = {k: {"id": k, "speciesId": n} for k, n in enumerate(inventario)}
        self.welcomed, self.ws_open, self.error_key, self.hunt_slug, self.nick = True, True, None, None, f"teste{ident}"
        self.mercado_info = {}

    def hunt_name(self, s):
        return s

    def capturar(self, n):
        self.dex[str(n)] = {"k": 1, "c": 1}
        self.dex_capturas.append(n)
        self.dex_seq += 1


rnd = random.Random(42)
PEGOS = {
    0: sorted(set(range(1, 152, 1)) - set(rnd.sample(range(1, 152), 45)) | set(rnd.sample(range(152, 387), 60))),
    1: [],                                                       # conta vazia
    2: sorted(rnd.sample(range(1, 387), 25)),
    3: sorted(rnd.sample(range(252, 387), 40)),
}
INVENTARIO = {0: [133, 13258], 1: [], 2: [6], 3: []}           # 133 e 258 (Orre): só no inventário
for i, w in enumerate(m.workers):
    w.game = JogoFalso(100 + i, PEGOS[i], INVENTARIO[i])
if TEM_DEX:
    win.pokedex.observar()                                       # 1ª olhada: "já estava capturado"


def abrir(conta=0):
    win.select(conta)
    if win.game.area != "pokedex":
        win._alternar_pokedex()
    esperar(0.5)
    return win.game.pokedex_panel


# ============================================================ prints
def prints():
    m.workers[0].game.capturar(4)
    m.workers[0].game.capturar(9)
    win._pokedex_olhou = 0
    win.refresh()                                                 # 4 e 9: capturas novas (selo "Novo")
    for tel in ("1366x768", "1920x1080"):
        win.setFixedSize(*tamanho(tel))
        p = abrir(0)
        p.set_todas(False)
        p.set_regiao(None)
        p.busca.clear()
        p.so_faltam.setChecked(False)
        p.grade.verticalScrollBar().setValue(0)
        if hasattr(p, "d_num"):
            p._mostrar_detalhe(p.modelo.index(5))
        foto(f"{tel}_conta1")
        win.select(1)
        foto(f"{tel}_conta_vazia")
        win.select(0)
        p.set_todas(True)
        foto(f"{tel}_todas")
        p.set_todas(False)
        p.set_regiao("Johto")
        p.so_faltam.setChecked(True)
        foto(f"{tel}_johto_faltam")
        p.set_regiao(None)
        p.so_faltam.setChecked(False)
    img = win.game.pokedex_panel.grade.grab().toImage()
    img = img.copy(0, 0, min(img.width(), 460), min(img.height(), 230))
    img.scaled(img.width() * 2, img.height() * 2, Qt.IgnoreAspectRatio, Qt.FastTransformation).save(
        str(SAIDA / f"{A.prefixo}celulas_2x.png"))


# ============================================================ topo (antes × depois)
def topo():
    for tel in ("1366x768", "minimo"):
        win.setFixedSize(*tamanho(tel))
        esperar(0.6)
        h = win.header
        r = h.geometry()
        for k in range(h.count()):
            it = h.itemAt(k)
            if it.layout():
                r = r.united(it.layout().geometry())
        img = win.grab().copy(0, 0, win.width(), r.bottom() + 16)
        img.save(str(SAIDA / f"{A.prefixo}topo_{tel}.png"))
        # nada cortado: cada botão/rótulo do topo cabe inteiro e não encosta em outro
        ws = [w for w in win.findChildren(QLabel) + win.findChildren(G.Botao)
              if w.isVisible() and w.mapTo(win, QPoint(0, 0)).y() < r.bottom() + 4]
        caixas = [(w, w.geometry().translated(w.parentWidget().mapTo(win, QPoint(0, 0)))) for w in ws]
        corte = [type(w).__name__ + ":" + (w.text() if hasattr(w, "text") else "") for w, g in caixas
                 if w.sizeHint().width() > w.width() + 1 or g.right() > win.width()]
        sobre = [(a.text(), b.text()) for i, (a, ga) in enumerate(caixas) for b, gb in caixas[i + 1:]
                 if ga.intersects(gb) and not (a.isAncestorOf(b) or b.isAncestorOf(a))
                 and hasattr(a, "text") and hasattr(b, "text") and a.text() and b.text()]
        print(json.dumps({"tela": tel, "janela": [win.width(), win.height()], "cortados": corte, "sobrepostos": sobre,
                          "ordem": [w.text().strip() for w, _g in sorted(caixas, key=lambda c: c[1].x())
                                    if hasattr(w, "text") and w.text().strip() and _g.y() < 80 and _g.x() > 300]},
                         ensure_ascii=False), flush=True)


# ============================================================ testes
falhas = []


def confere(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"{'ok   ' if ok else 'FALHA'} {nome}: {obtido!r}" + ("" if ok else f" (esperado {esperado!r})"), flush=True)
    if not ok:
        falhas.append(nome)


def mostrados(p):
    return [e["dex"] for e in p.modelo.linhas]


def testes():
    win.setFixedSize(*tamanho("1366x768"))
    confere("antes de abrir: a tela não existe", win.game.pokedex_panel, None)
    p = abrir(0)
    confere("abriu na área do jogo", (win.game.area, win.b_pokedex.isChecked(), win.game.b_jogo.isChecked()), ("pokedex", True, False))
    confere("385 na lista (sprites ∩ jogo)", len(p._lista), 385)
    confere("Unown fora", 201 in [e["dex"] for e in p._lista], False)
    pegos0 = (set(PEGOS[0]) | {133, 258}) - {201}              # o Unown não está na lista (sem sprite)
    confere("conta 1: total = Pokédex do jogo + inventário", p.barra.value(), len(pegos0 & set(e["dex"] for e in p._lista)))
    confere("barra de", p.barra.maximum(), 385)
    confere("fichas por região", [f.text() for f in p.fichas.values()],
            [f"Kanto {len([n for n in pegos0 if n <= 151])}/151", f"Johto {len([n for n in pegos0 if 152 <= n <= 251])}/99",
             f"Hoenn {len([n for n in pegos0 if 252 <= n <= 386])}/135"])
    confere("só no inventário conta (133) e Orre do inventário vira a base (13258 -> 258)",
            (133 in p.modelo.pegos, 258 in p.modelo.pegos), (True, True))
    confere("dica: no inventário", "No inventário" in p.modelo.dica(next(e for e in p._lista if e["dex"] == 133)), True)
    # os 4 filtros
    for nome, (a, b, n) in {"Kanto": (1, 151, 151), "Johto": (152, 251, 99), "Hoenn": (252, 386, 135)}.items():
        p.set_regiao(nome)
        d = mostrados(p)
        confere(f"filtro {nome}", (len(d), min(d), max(d)), (n, a, b))
    p.set_regiao(None)
    confere("filtro Todas", len(mostrados(p)), 385)
    # busca: número acha qualquer um; nome só os capturados
    p.busca.setText("25")
    confere("busca número 25", mostrados(p)[:1], [25])
    p.busca.setText("#006")
    confere("busca #006", mostrados(p), [6])
    nao = next(e for e in p._lista if e["dex"] not in p.modelo.pegos and e["nome"])
    sim = next(e for e in p._lista if e["dex"] in p.modelo.pegos and e["nome"])
    p.busca.setText(nao["nome"])
    confere(f"nome de quem falta ({nao['nome']}) não aparece", nao["dex"] in mostrados(p), False)
    p.busca.setText(sim["nome"].lower())
    confere(f"nome de capturado ({sim['nome']}) aparece", sim["dex"] in mostrados(p), True)
    p.busca.setText("zzzz")
    confere("busca sem resultado: aviso", (mostrados(p), p.vazio.isVisible()), ([], True))
    p.busca.clear()
    p.so_faltam.setChecked(True)
    confere("só os que faltam", all(n not in p.modelo.pegos for n in mostrados(p)) and len(mostrados(p)) == 385 - p.barra.value(), True)
    p.so_faltam.setChecked(False)
    # trocar de conta com a Pokédex aberta (Ctrl+2) e a conta vazia
    win.activateWindow()
    esperar(0.2)
    QTest.keyClick(win, Qt.Key_2, Qt.ControlModifier)
    esperar(0.3)
    confere("Ctrl+2: conta vazia", (win.selected, p.barra.value(), p.rot_conta.text(), win.game.area), (1, 0, "Conta 2", "pokedex"))
    confere("vazia: tudo ???", p.modelo.dica(p.modelo.linhas[0]), "#001\nAinda não capturado")
    QTest.keyClick(win, Qt.Key_1, Qt.ControlModifier)
    esperar(0.3)
    # Todas as contas
    p.set_todas(True)
    todas = set().union(*[set(v) for v in PEGOS.values()], {133, 258, 6})
    confere("Todas as contas: junta as 4", p.barra.value(), len(todas & set(e["dex"] for e in p._lista)))
    dono = next(n for n in PEGOS[2] if n not in PEGOS[0] and n not in PEGOS[3] and n != 6)
    confere("Todas: o dono na dica", p.modelo.dica(next(e for e in p._lista if e["dex"] == dono)).splitlines()[-1], "Conta: Conta 3")
    p.set_todas(False)
    # captura nova: só a célula e os números; selo Novo
    antes = p.barra.value()
    alvo = next(e["dex"] for e in p._lista if e["dex"] not in p.modelo.pegos)
    m.workers[0].game.capturar(alvo)
    win._pokedex_olhou = 0
    win.refresh()
    confere("captura nova: +1", p.barra.value(), antes + 1)
    info = p.modelo.pegos.get(alvo) or {}
    confere("selo Novo (capturado agora)", bool(info.get("quando")) and time.time() - info["quando"] < 60, True)
    confere("dica: data da primeira captura", "Primeira captura:" in p.modelo.dica(next(e for e in p._lista if e["dex"] == alvo)), True)
    confere("salvo no perfil da conta", str(alvo) in json.loads((m.workers[0].acc.profile_dir / "pokedex.json").read_text())["contas"]["100"]["capturados"], True)
    pular = os.environ.get("PN_PULAR", "")
    if "teclas" in pular:
        print("\nTUDO OK (parcial)", flush=True)
        return
    # atalhos que já existiam, com a Pokédex aberta
    QTest.keyClick(win, Qt.Key_H, Qt.ControlModifier)
    esperar(0.3)
    confere("Ctrl+H: Hunts", (win.game.area, win.b_pokedex.isChecked()), ("hunts", False))
    QTest.keyClick(win, Qt.Key_D, Qt.ControlModifier)
    esperar(0.3)
    confere("Ctrl+D: Pokédex", win.game.area, "pokedex")
    QTest.keyClick(win, Qt.Key_M, Qt.ControlModifier)
    esperar(0.3)
    confere("Ctrl+M: Mercado", win.game.area, "rmt")
    QTest.keyClick(win, Qt.Key_D, Qt.ControlModifier)
    esperar(0.3)
    QTest.keyClick(win, Qt.Key_0, Qt.ControlModifier)
    esperar(0.3)
    confere("Ctrl+0: todas as contas", (win.grid_mode, win.game.area), (True, "pokedex"))
    QTest.keyClick(win, Qt.Key_D, Qt.ControlModifier)
    esperar(0.3)
    confere("Ctrl+D de novo: volta ao jogo", (win.game.area, win.b_pokedex.isChecked()), ("jogo", False))
    win.b_pokedex.click()
    esperar(0.3)
    win.game.b_jogo.click()
    esperar(0.3)
    confere("botão Jogo volta para o jogo", (win.game.area, win.b_pokedex.isChecked()), ("jogo", False))
    if "f1" in pular:
        print("\nTUDO OK (parcial)", flush=True)
        return
    # F1 lista o atalho novo; Ajustes tem o atalho
    textos = {}
    from PySide6.QtCore import QTimer

    def pegar():
        d = QApplication.activeModalWidget()
        if d is None:
            QTimer.singleShot(200, pegar)
            return
        textos["f1"] = " ".join(l.text() for l in d.findChildren(QLabel))
        d.reject()
    QTimer.singleShot(300, pegar)
    win._ajuda()
    confere("F1 lista Ctrl+D", "Ctrl+D: jogo ou Pokédex" in textos.get("f1", ""), True)
    dlg = G.SettingsDialog(win, cfg, m.accounts)
    confere("Ajustes: atalho da Pokédex", dlg.w_atalhos["pokedex"].keySequence().toString(), "Ctrl+D")
    v, _c = dlg.valores()
    confere("Ajustes: grava o atalho", v[("atalhos", "pokedex")], "Ctrl+D")
    dlg.deleteLater()
    # sem animação e sem widget por pokémon
    confere("nenhum widget por pokémon", len(p.findChildren(QLabel)) < 40, True)
    confere("nenhum PixelSprite na Pokédex", len(p.findChildren(G.PixelSprite)), 0)
    print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}", flush=True)
    (SAIDA / f"{A.prefixo}testes.json").write_text(json.dumps({"falhas": falhas}), encoding="utf-8")


# ============================================================ medidas
def medidas():
    from browser.proc_mem import memoria_privada_mb
    win.setFixedSize(*tamanho("1920x1080"))
    win.select(0)
    esperar(1.0)
    res = {"memoria_antes_mb": round(memoria_privada_mb(os.getpid()) or 0, 1)}
    t = time.perf_counter()
    win._alternar_pokedex()
    p = win.game.pokedex_panel
    p.grade.repaint()
    res["abrir_ms"] = round((time.perf_counter() - t) * 1000, 1)
    esperar(0.5)
    barra = p.grade.verticalScrollBar()
    tempos = []
    for v in range(0, barra.maximum() + 40, 40):          # rola a grade inteira, 40 px por vez
        t = time.perf_counter()
        barra.setValue(v)
        p.grade.viewport().repaint()
        tempos.append((time.perf_counter() - t) * 1000)
    tempos.sort()
    res["rolar"] = {"passos": len(tempos), "mediana_ms": round(tempos[len(tempos) // 2], 2), "pior_ms": round(tempos[-1], 2)}
    for nome in ("Kanto", "Johto", None):
        t = time.perf_counter()
        p.set_regiao(nome)
        p.grade.repaint()
        res[f"filtro_{nome or 'Todas'}_ms"] = round((time.perf_counter() - t) * 1000, 1)
    esperar(0.5)
    res["memoria_aberta_mb"] = round(memoria_privada_mb(os.getpid()) or 0, 1)
    res["memoria_a_mais_mb"] = round(res["memoria_aberta_mb"] - res["memoria_antes_mb"], 1)
    res["sprites_lidos"] = len(p.sprites._base)
    print(json.dumps(res), flush=True)
    (SAIDA / f"{A.prefixo}medidas.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


{"prints": prints, "testes": testes, "medidas": medidas, "topo": topo}[A.modo]()
win.close()
esperar(0.5)
sys.exit(1 if falhas else 0)

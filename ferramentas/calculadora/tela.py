"""Calculadora de Gemas no Mercado: prints, testes da tela e regressão do Mercado, na janela de verdade.

Pasta de dados temporária e NENHUMA conta conecta (sem m.start()): o saldo e o catálogo são falsos, só
na memória deste teste. Nada é comprado e nada sai para a internet.

    .venv\\Scripts\\python.exe ferramentas\\calculadora\\tela.py --modo prints --layout lado --saida <pasta>
    .venv\\Scripts\\python.exe ferramentas\\calculadora\\tela.py --modo testes --saida <pasta>
    .venv\\Scripts\\python.exe ferramentas\\calculadora\\tela.py --modo regressao --saida <pasta> [--raiz <cópia de antes>]

--raiz: roda o MESMO roteiro num outro código (ex.: `git archive HEAD` descompactado), para comparar antes
× depois. --escala simula a escala do Windows (QT_SCALE_FACTOR). --offscreen: sem janela.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--modo", required=True, choices=["prints", "testes", "regressao", "guia", "repintura"])
ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
ap.add_argument("--layout", default="lado", choices=["lado", "recolhida"])
ap.add_argument("--escala", type=float, default=1.0)
ap.add_argument("--leve", type=int, default=0)
ap.add_argument("--offscreen", action="store_true")
ap.add_argument("--saida", required=True)
ap.add_argument("--prefixo", default="")
A = ap.parse_args()
SAIDA = Path(A.saida)
SAIDA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, A.raiz)

os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_calc_")
if A.escala != 1.0:
    os.environ["QT_SCALE_FACTOR"] = str(A.escala)
if A.offscreen:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

import app.config as C  # noqa: E402
C.MODO_LEVE = bool(A.leve)
import browser.web_host as WH  # noqa: E402
PORT = WH.setup_environment()
from PySide6.QtCore import QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication, QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QPushButton  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
cfg["iniciar_contas_ao_abrir"] = False
import app.gui as G  # noqa: E402
import app.rmt_ui as R  # noqa: E402
from rmt.compras import ItemCompra  # noqa: E402

TEM_CALC = hasattr(R, "CalculadoraGemas")
if TEM_CALC and hasattr(R.RmtPanel, "LAYOUT_CALC"):      # só existia durante a escolha das duas propostas
    R.RmtPanel.LAYOUT_CALC = A.layout

web = WH.WebHost(PORT)
m = G.Manager(cfg, contas, web)             # sem m.start(): nenhuma conta conecta
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
tela = QGuiApplication.primaryScreen()
if not A.offscreen:
    tela = next((t for t in QGuiApplication.screens() if t is not QGuiApplication.primaryScreen()), tela)
win.move(tela.geometry().topLeft())
win.show()
rp = win.game.rmt_panel


def esperar(seg: float):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.01)


def tamanho(nome: str):
    tw, th = {"1366x768": (1366, 768), "1920x1080": (1920, 1080)}[nome]
    # área da janela maximizada: sem a barra de título (~31 px) e sem a barra de tarefas (48 px)
    return round(tw / A.escala), round(th / A.escala) - 48 - 31


# ------------------------------------------------------------ o que o painel recebe (falso)
SALDO = {"conectada": True, "gold": 48_210, "orb": 12_345}


def view_falso(w):
    orig = w.rmt.view

    def view():
        v = orig()
        v["conectada"] = SALDO["conectada"]
        v["saldo"] = {"gold": SALDO["gold"] if SALDO["conectada"] else None,
                      "orb": SALDO["orb"] if SALDO["conectada"] else None}
        return v
    return view


for w in m.workers:
    w.rmt.view = view_falso(w)


def itens_de_exemplo(w):
    w.rmt.lista.itens[:] = [
        ItemCompra(item_id=4, item_nome="Ultra Ball", moeda="gold", preco_max=100, lim_unidades=10),
        ItemCompra(item_id=50, item_nome="Rare Candy", moeda="orb", preco_max=3, lim_dia=30),
    ]


def abrir_mercado(conta=0):
    win.select(conta)
    if win.game.area != "rmt":
        win._alternar_rmt()
    rp.render(win.selected, m.workers[win.selected])
    esperar(0.4)


def foto(nome: str, alvo=None):
    esperar(0.5)
    (alvo or win).grab().save(str(SAIDA / f"{A.prefixo}{nome}.png"))


def medidas() -> dict:
    vp = rp.viewport()
    y_lista = rp.card_lista.mapTo(vp, QPoint(0, 0)).y()
    primeiro = next(iter(rp._cartoes.values()), None)
    r = {"janela": [win.width(), win.height()], "painel": [vp.width(), vp.height()], "y_lista": y_lista,
         "titulo_lista_visivel": 0 <= y_lista and y_lista + 30 <= vp.height()}
    if primeiro:
        y1 = primeiro.mapTo(vp, QPoint(0, 0)).y()
        r["primeiro_item_inteiro"] = y1 + primeiro.height() <= vp.height()
        r["y_fim_primeiro_item"] = y1 + primeiro.height()
    if TEM_CALC:
        c = rp.calc
        r["calc"] = {"visivel": c.isVisible(), "tam": [c.width(), c.height()]}
    return r


# ============================================================ prints
def prints():
    res = {}
    itens_de_exemplo(m.workers[0])
    for tel in ("1366x768", "1920x1080"):
        win.setFixedSize(*tamanho(tel))
        abrir_mercado(0)
        rp.verticalScrollBar().setValue(0)
        if TEM_CALC:
            rp.calc.usar_gemas(1000)
            if rp.b_calc is not None:
                rp.b_calc.setChecked(False)
                esperar(0.2)
                foto(f"{tel}_fechada")
                res[f"{tel}_fechada"] = medidas()
                rp.b_calc.setChecked(True)
        esperar(0.2)
        foto(tel)
        res[tel] = medidas()
        if TEM_CALC:
            # a calculadora sozinha, ampliada 2× sem suavizar (para ver o pixel)
            img = rp.calc.grab().toImage()
            img = img.scaled(img.width() * 2, img.height() * 2, Qt.IgnoreAspectRatio, Qt.FastTransformation)
            img.save(str(SAIDA / f"{A.prefixo}{tel}_calc_2x.png"))
    (SAIDA / f"{A.prefixo}medidas.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False), flush=True)


# ============================================================ testes da calculadora
falhas = []


def confere(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"{'ok   ' if ok else 'FALHA'} {nome}: {obtido!r}" + ("" if ok else f" (esperado {esperado!r})"), flush=True)
    if not ok:
        falhas.append(nome)


def digitar(campo, texto):
    campo.setFocus()
    campo.selectAll()
    QTest.keyClick(campo, Qt.Key_Delete)
    QTest.keyClicks(campo, texto)
    qapp.processEvents()


def roda(widget, n=6):
    """A roda do mouse em cima do widget, de verdade (o evento passa pelo mesmo caminho do mouse)."""
    meio = QPointF(widget.width() / 2, widget.height() / 2)
    glob = QPointF(widget.mapToGlobal(meio.toPoint()))
    for _ in range(n):
        for d in (120, -120):
            ev = QWheelEvent(meio, glob, QPoint(0, 0), QPoint(0, d), Qt.NoButton, Qt.NoModifier,
                             Qt.NoScrollPhase, False)
            QApplication.sendEvent(widget, ev)
    qapp.processEvents()


def testes():
    win.setFixedSize(*tamanho("1366x768"))
    abrir_mercado(0)
    c = rp.calc
    if rp.b_calc is not None:
        rp.b_calc.setChecked(True)
    eg, ed = c.e_gemas, c.e_dolares
    # digitar nos dois campos
    digitar(eg, "1000")
    confere("Gemas 1000 -> US$", ed.text(), "9,00")
    confere("balão em US$ 9,00", c.balao.text(), "Dá um lanche")
    digitar(ed, "1,00")
    confere("US$ 1,00 -> Gemas", eg.text(), "111")
    digitar(ed, "10")
    confere("US$ 10 -> Gemas", eg.text(), "1.111")
    digitar(eg, "1")
    confere("1 Gema -> US$ (3 casas)", ed.text(), "0,009")
    # texto inválido: o campo simplesmente não aceita
    digitar(eg, "abc-1e,5")
    confere("Gemas com letras, sinal e vírgula", eg.text(), "15")
    digitar(ed, "-9,005x")
    confere("US$ com sinal e 3 casas", ed.text(), "9,00")
    confere("US$ 9,00 -> Gemas", eg.text(), "1.000")
    digitar(ed, "2,5")
    confere("vírgula com 1 casa", eg.text(), "277")
    # campo vazio = 0 (o outro fica vazio, mostrando o 0 de exemplo)
    digitar(eg, "")
    confere("Gemas vazio -> US$ vazio", ed.text(), "")
    confere("balão com zero", c.balao.text(), "Quanto vale? Digite aí!")
    # 9 dígitos no máximo
    digitar(eg, "1234567890")
    confere("Gemas param em 9 dígitos", eg.text(), "123456789")
    confere("123.456.789 Gemas -> US$", ed.text(), "1.111.111,10")
    digitar(ed, "12345678,99")
    confere("US$ param em 9 dígitos", ed.text(), "12345678,9")
    confere("US$ 12.345.678,90 -> Gemas", eg.text(), "1.371.742.100")
    # inverter
    confere("entrada no começo", c.entrada(), "gemas")
    numeros = (eg.text(), ed.text())
    c.b_inverter.click()
    qapp.processEvents()
    confere("inverter: entrada", c.entrada(), "dolares")
    confere("inverter: cursor no campo de dólares", QApplication.focusWidget() is ed, True)
    confere("inverter não muda os números", (eg.text(), ed.text()), numeros)
    foto("teste_invertida", c)
    c.b_inverter.click()
    qapp.processEvents()
    confere("inverter de novo: entrada", c.entrada(), "gemas")
    # as fichas
    fichas = {b.text(): b for b in c.findChildren(QPushButton)}
    for txt, us in (("100", "0,900"), ("1.000", "9,00"), ("10.000", "90,00")):
        fichas[txt].click()
        qapp.processEvents()
        confere(f"ficha {txt}", (eg.text(), ed.text()), (txt, us))
    # Meu saldo: com e sem conta
    SALDO["conectada"] = True
    rp.render(win.selected, m.workers[win.selected])
    confere("Meu saldo ligado com conta", fichas["Meu saldo"].isEnabled(), True)
    fichas["Meu saldo"].click()
    qapp.processEvents()
    confere("Meu saldo (12.345 Gemas)", (eg.text(), ed.text()), ("12.345", "111,10"))
    foto("teste_meu_saldo", c)
    SALDO["conectada"] = False
    rp.render(win.selected, m.workers[win.selected])
    confere("Meu saldo apagado sem conta", fichas["Meu saldo"].isEnabled(), False)
    confere("dica sem conta", "onecte a conta" in fichas["Meu saldo"].toolTip(), True)
    foto("teste_sem_conta", c)
    SALDO["conectada"] = True
    rp.render(win.selected, m.workers[win.selected])
    # Saldo de todas as contas (a soma das conectadas)
    if "Saldo de todas as contas" in fichas:
        bt = fichas["Saldo de todas as contas"]
        confere("todas: sem conta conectada, apagada", (bt.isEnabled(), "Conecte uma conta" in bt.toolTip()), (False, True))
        real = rp.saldos
        for saldos, ligada, dica, campos in (
                ([12_345, None, 1_000, 500], True, "Soma as Gemas das 3 contas conectadas (13.845)", ("13.845", "124,60")),
                ([None, 777, None, None], True, "Soma as Gemas da conta conectada (777)", ("777", "6,99")),
                ([0, 0, None, None], True, "Soma as Gemas das 2 contas conectadas (0)", ("0", "0,00")),
                ([400_000_000, 300_000_000, 200_000_000, 150_000_000], True,
                 "Soma as Gemas das 4 contas conectadas (1.050.000.000)", ("1.050.000.000", "9.450.000,00")),
                ([None, None, None, None], False, "Conecte uma conta para usar a soma das Gemas", None)):
            rp.saldos = lambda s=saldos: s
            rp.render(win.selected, m.workers[win.selected])
            confere(f"todas {saldos}: ligada e dica", (bt.isEnabled(), bt.toolTip()), (ligada, dica))
            if campos:
                bt.click()
                qapp.processEvents()
                confere(f"todas {saldos}: campos", (eg.text(), ed.text()), campos)
        # o caminho de verdade da janela principal: as Gemas que cada conta conectada já recebeu do jogo
        from types import SimpleNamespace as NS
        rp.saldos = real
        guardados = [w.game for w in m.workers]
        jogos = [NS(welcomed=True, eu={"orbs": 1_500}), NS(welcomed=False, eu={"orbs": 9_999}),
                 NS(welcomed=True, eu={"orbs": 2_500.0}), NS(welcomed=True, eu={})]
        for w, j in zip(m.workers, jogos):
            w.game = j
        confere("janela: lê só as conectadas (sem saldo ainda = fora)", real(), [1_500, None, 2_500.0, None])
        for w, j in zip(m.workers, guardados):
            w.game = j
        rp.calc.set_saldo_todas([1_500, None, 2_500.0, None])
        bt.click()
        qapp.processEvents()
        confere("janela: soma 1.500 + 2.500", eg.text(), "4.000")
        rp.render(win.selected, m.workers[win.selected])
    # roda do mouse em cima dos campos e das fichas: nenhum valor muda
    digitar(eg, "1000")
    antes = (eg.text(), ed.text())
    for wdg in (eg, ed, c.b_inverter, fichas["100"]):
        roda(wdg)
    confere("roda do mouse não muda valor", (eg.text(), ed.text()), antes)
    # o balão nas faixas certas
    for g, frase in ((111, "Trocado de bolso"), (112, "Trocado de bolso"), (113, "Dá um lanche"),
                     (1111, "Dá um lanche"), (1112, "Dá um lanche"), (1113, "Agora sim, miau!"),
                     (11_112, "Agora sim, miau!"), (11_113, "Isso é muita moeda!")):
        digitar(eg, str(g))
        confere(f"balão em {g} Gemas (US$ {ed.text()})", c.balao.text(), frase)
    # regras do tema: só Botao, cartão Moldura, sem emoji
    botoes = c.findChildren(QAbstractButton)
    confere("todo botão é Botao", sorted({type(b).__name__ for b in botoes}), ["Botao"])
    confere("cartão é Moldura 'card'", (type(c).__mro__[1].__name__, c.objectName()), ("Moldura", "card"))
    textos = [b.text() for b in botoes] + [l.text() for l in c.findChildren(QLabel)]
    confere("sem emoji", [t for t in textos if any(ord(ch) > 0x2600 for ch in t)], [])
    # o mascote: Meowth, parado no Modo Leve, pausado com o Mercado escondido
    confere("mascote", Path(c.mascote._key[0]).name, "52.gif")
    if C.MODO_LEVE:
        confere("Modo Leve: sprite parado", c.mascote._movie.state().name, "NotRunning")
    else:
        confere("anima com o Mercado à vista", c.mascote._movie.state().name, "Running")
        win._alternar_rmt()            # volta para o jogo: o Mercado some
        esperar(0.3)
        confere("pausa com o Mercado escondido", c.mascote._movie.state().name, "Paused")
        win._alternar_rmt()
        esperar(0.3)
        confere("volta a animar", c.mascote._movie.state().name, "Running")
    # nada no disco
    lista_arq = m.workers[0].acc.profile_dir / "rmt_compras.json"
    confere("a calculadora não grava nada", lista_arq.exists(), False)
    print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}", flush=True)
    (SAIDA / f"{A.prefixo}testes.json").write_text(json.dumps({"falhas": falhas, "leve": A.leve}), encoding="utf-8")


# ============================================================ regressão do Mercado (antes × depois)
CATALOGO = [{"id": 4, "nome": "Ultra Ball", "categoria": "bolas"}, {"id": 50, "nome": "Rare Candy", "categoria": "itens"},
            {"id": 7, "nome": "Potion", "categoria": "cura"}]


class JogoFalso:
    """Só o que a tela lê do jogo: o catálogo do Mercado. Não conectado (welcomed False)."""
    def __init__(self, i):
        self.mercado_info = {"catalogo": CATALOGO}
        self.eu, self.nick, self.welcomed, self.ws_open, self.error_key = {}, f"teste{i}", False, False, None
        self.hunt_slug = None

    def hunt_name(self, s):
        return s


def texto_do_painel() -> list:
    """Tudo que o Mercado mostra (rótulos e botões), em ordem de cima para baixo, FORA a calculadora."""
    fora = set(rp.calc.findChildren(QLabel) + rp.calc.findChildren(QAbstractButton)) if TEM_CALC else set()
    if TEM_CALC and rp.b_calc is not None:
        fora.add(rp.b_calc)
    itens = []
    for w in rp.widget().findChildren(QLabel) + rp.widget().findChildren(QAbstractButton):
        if w in fora or not w.isVisible() or isinstance(w, R.Balao if TEM_CALC else type(None)):
            continue
        p = w.mapTo(rp.widget(), QPoint(0, 0))
        itens.append((p.y(), p.x(), type(w).__name__, w.text().strip(), w.toolTip(), w.isEnabled()))
    itens.sort()
    # posição relativa: só a ordem (a calculadora empurra tudo para baixo igual)
    return [list(i[2:]) for i in itens]


def ordem_dos_cartoes() -> list:
    nomes = {"saldo": rp.card_saldo, "lista": rp.card_lista, "seguranca": rp.card_seguranca}
    return sorted(nomes, key=lambda n: nomes[n].mapTo(rp.widget(), QPoint(0, 0)).y())


def modal(acao, timeout=4.0):
    """Roda `acao` com a janela modal aberta (QTimer), como uma pessoa clicando nela."""
    def tentar(fim=time.monotonic() + timeout):
        d = QApplication.activeModalWidget()
        if d is None:
            if time.monotonic() < fim:
                QTimer.singleShot(100, lambda: tentar(fim))
            return
        acao(d)
    QTimer.singleShot(200, tentar)


def clicar_botao(d, texto):
    for b in d.findChildren(QAbstractButton):
        if b.text().strip() == texto:
            b.click()
            return True
    return False


def regressao():
    reg = {"tem_calculadora": TEM_CALC, "passos": []}
    for i, w in enumerate(m.workers):
        w.game = JogoFalso(i)
    SALDO["conectada"] = False
    win.setFixedSize(*tamanho("1920x1080"))
    abrir_mercado(0)
    if TEM_CALC and rp.b_calc is not None:
        rp.b_calc.setChecked(True)
    if TEM_CALC:
        rp.calc.usar_gemas(1000)          # calculadora aberta e usada durante tudo

    def passo(nome):
        rp._estrutura = None
        rp.render(win.selected, m.workers[win.selected])
        esperar(0.3)
        lv = m.workers[win.selected].rmt.lista
        reg["passos"].append({"passo": nome, "conta": win.selected, "area": win.game.area,
                              "ordem": ordem_dos_cartoes(), "tela": texto_do_painel(),
                              "lista": [{k: v for k, v in it.__dict__.items() if k not in ("id", "criado_em")}
                                        for it in lv.itens]})

    passo("inicio")

    # adicionar um item (desligado)
    def preencher(d, nome="Rare Candy", preco=7):
        for k in range(d.lista.count()):
            if d.lista.item(k).text().startswith(nome):
                d.lista.setCurrentRow(k)
        d.moeda.setCurrentIndex(0)
        d.preco.setValue(preco)
        d.c_unid.setChecked(True)
        d.s_unid.setValue(5)
        d.findChildren(QAbstractButton)  # noqa
        clicar_botao(d, "Salvar")
    modal(preencher)
    rp.editar(None)
    passo("adicionou")
    iid = m.workers[0].rmt.lista.itens[0].id
    modal(lambda d: preencher(d, "Potion", 12))
    rp.editar(iid)
    passo("editou")
    # ligar (com a confirmação) e Parar todas as compras
    modal(lambda d: clicar_botao(d, "Ligar"))
    rp.alternar(iid)
    passo("ligou")
    rp.b_parar.click()
    passo("parar_todas")
    # o guia inteiro
    rp.abrir_guia()
    esperar(0.3)
    g = rp._guia
    titulos = []
    while g is not None and rp._guia is not None:
        titulos.append({"titulo": g.titulo.text(), "texto": g.texto.text(),
                        "destaque": [g.destaque.width() > 0, g.destaque.height() > 0]})
        g.avancar()
        esperar(0.15)
    reg["guia"] = titulos
    passo("guia_fechado")
    # trocar de conta pelo teclado (Ctrl+1..4) e Ctrl+M
    win.activateWindow()
    win.raise_()
    esperar(0.3)
    for k, tecla in enumerate((Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_1)):
        QTest.keyClick(win, tecla, Qt.ControlModifier)
        esperar(0.3)
        passo(f"ctrl+{(k + 1) % 4 + 1}")
    QTest.keyClick(win, Qt.Key_M, Qt.ControlModifier)
    esperar(0.3)
    reg["passos"].append({"passo": "ctrl+m (volta ao jogo)", "area": win.game.area})
    QTest.keyClick(win, Qt.Key_M, Qt.ControlModifier)
    esperar(0.3)
    passo("ctrl+m (volta ao Mercado)")
    # remover (com a confirmação)
    modal(lambda d: clicar_botao(d, "Remover"))
    rp.remover(iid)
    passo("removeu")
    (SAIDA / f"{A.prefixo}regressao.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
    print("passos:", [p["passo"] for p in reg["passos"]], "guia:", len(reg["guia"]), flush=True)


# ============================================================ o passo do guia
def guia():
    win.setFixedSize(*tamanho("1366x768"))
    itens_de_exemplo(m.workers[0])
    abrir_mercado(0)
    if TEM_CALC and rp.b_calc is not None:
        rp.b_calc.setChecked(True)
    rp.calc.usar_gemas(1000)
    rp.abrir_guia()
    esperar(0.3)
    while rp._guia is not None and rp._guia.titulo.text() != "Calculadora de Gemas":
        rp._guia.avancar()
        esperar(0.1)
    foto("guia_calculadora")
    rp._guia.fechar()


# ============================================================ repintura (a mesma conta do app/molduras.py)
def repintura():
    import statistics
    win.setFixedSize(*tamanho("1920x1080"))
    itens_de_exemplo(m.workers[0])
    abrir_mercado(0)
    if TEM_CALC:
        rp.b_calc.setChecked(True)
        rp.calc.usar_gemas(1000)
    esperar(1.0)
    win.timer.stop()
    res = {}
    for nome, alvo in (("mercado", rp), ("janela", win)):
        tempos = []
        for k in range(30 + 200):
            t = time.perf_counter()
            alvo.repaint()
            if k >= 30:
                tempos.append((time.perf_counter() - t) * 1000)
            qapp.processEvents()
        tempos.sort()
        res[nome] = {"mediana_ms": round(statistics.median(tempos), 2), "p90_ms": round(tempos[int(len(tempos) * 0.9)], 2)}
    res["calculadora_aberta"] = TEM_CALC
    print(json.dumps(res), flush=True)
    (SAIDA / f"{A.prefixo}repintura.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


{"prints": prints, "testes": testes, "regressao": regressao, "guia": guia, "repintura": repintura}[A.modo]()
# Sai pelo caminho do programa (X + fim normal do Python). os._exit aqui dava, às vezes, "access violation"
# no encerramento (PySide6 6.12 com botões ligados, também sem a calculadora); o fechar no X não dá.
win.close()
esperar(0.5)
sys.exit(1 if falhas else 0)

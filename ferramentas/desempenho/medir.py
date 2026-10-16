"""Mede o PokeNexus num modo (normal, Leve ou um candidato), num perfil de máquina e nos cenários C1 a C4.

Abre o PokeNexus de verdade (a mesma janela, as mesmas páginas) DENTRO deste processo. Nada do app é
mudado em disco: o modo e os flags do navegador são trocados só na memória deste teste.

    .venv\\Scripts\\python.exe ferramentas\\desempenho\\medir.py --modo leve --perfil P3 --rodada 2

Páginas:
  --pagina carga   (padrão) as 4 contas mostram ferramentas/desempenho/carga.html, uma cena de canvas
                   2D parecida com a do jogo. Pasta de dados temporária, nenhuma conta é tocada.
  --pagina jogo    o PokeIdle de verdade. Com a pasta temporária, as contas ficam na tela de login.
  --dados reais    as contas reais (farm de verdade). SÓ com a autorização do usuário (--autorizado) e
                   com o PokeNexus dele fechado. Nada é salvo no config.toml dele.

Perfis: P1 forte (sem limite); P2 sem GPU (Chromium com --disable-gpu e Qt com o desenho por software
do Windows); P3 fraco (P2 + PokeNexus e todos os QtWebEngineProcess presos a 2 núcleos lógicos).

Saída: um JSON por rodada em --saida (padrão docs/desempenho/dados).
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
import sistema as S  # noqa: E402

BASE = ("--disable-background-timer-throttling --disable-renderer-backgrounding "
        "--disable-backgrounding-occluded-windows --disable-features=IntensiveWakeUpThrottling")
# Cada modo: flags do Chromium e se a interface fica no Modo Leve (MODO_LEVE das telas).
MODOS = {
    "normal": {"flags": BASE, "ui_leve": False},
    # o Leve de verdade do app (browser/web_host.py decide os flags pela placa de vídeo)
    "leve": {"flags": None, "ui_leve": True},
    # o Leve de antes do 2.0, para comparar
    "leve_antigo": {"flags": BASE + " --disable-gpu --force-prefers-reduced-motion", "ui_leve": True},
}
# Candidatos do Leve 2.0 (ver docs/desempenho/PLANO.md); `candidatos.py` pode acrescentar mais.
try:
    from candidatos import CANDIDATOS  # noqa: E402
    MODOS.update(CANDIDATOS)
except ImportError:
    pass

ap = argparse.ArgumentParser()
ap.add_argument("--modo", default="normal", choices=sorted(MODOS))
ap.add_argument("--perfil", default="P1", choices=["P1", "P2", "P3"])
ap.add_argument("--pagina", default="carga", choices=["carga", "jogo"])
ap.add_argument("--dados", default="temp", choices=["temp", "reais"])
ap.add_argument("--autorizado", action="store_true", help="o usuário autorizou usar as contas reais")
ap.add_argument("--cenarios", default="C1,C2,C3,C4")
ap.add_argument("--segundos", type=int, default=180, help="duração de cada cenário")
ap.add_argument("--aquecimento", type=int, default=60, help="descartado antes do 1º cenário")
ap.add_argument("--assentar", type=int, default=15, help="descartado depois de trocar de cenário")
ap.add_argument("--rodada", type=int, default=1)
ap.add_argument("--tela", default="secundaria", choices=["principal", "secundaria"])
ap.add_argument("--saida", default=str(RAIZ / "docs" / "desempenho" / "dados"))
ap.add_argument("--depurar", type=int, default=0, help="mostra onde cada thread está a cada N s")
A = ap.parse_args()
MODO = MODOS[A.modo]
if A.depurar:
    import faulthandler
    faulthandler.dump_traceback_later(A.depurar, repeat=True)

if A.dados == "reais":
    if not A.autorizado:
        sys.exit("Contas reais só com a autorização do usuário: use --autorizado.")
    if any(n.lower().startswith("pokenexus") for _p, (_pai, n) in S.processos().items()):
        sys.exit("O PokeNexus do usuário está aberto: a mesma conta em dois lugares derruba a sessão.")
    if A.pagina != "jogo":
        sys.exit("Com --dados reais use --pagina jogo.")
    TMP = None
else:
    TMP = Path(tempfile.mkdtemp(prefix="pn_med_"))
    os.environ["POKENEXUS_DATA"] = str(TMP)
    cfg_txt = (RAIZ / "config.toml").read_text(encoding="utf-8")
    cfg_txt = cfg_txt.replace("iniciar_contas_ao_abrir = true", "iniciar_contas_ao_abrir = false")
    (TMP / "config.toml").write_text(cfg_txt, encoding="utf-8")

# ------------------------------------------------------------------ modo e perfil (só na memória)
import app.config as C  # noqa: E402
C.MODO_LEVE = MODO["ui_leve"]
import browser.web_host as WH  # noqa: E402
os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
os.environ.pop("QT_QUICK_BACKEND", None)
sem_gpu = A.perfil in ("P2", "P3")
if sem_gpu:
    os.environ["QSG_RHI_PREFER_SOFTWARE_RENDERER"] = "1"     # o Qt também fica sem a placa
    WH.tem_gpu = lambda: False                               # o app enxerga um PC sem placa
if MODO["flags"] is not None:                                # modos fixos: flags trocados só aqui
    C.MODO_LEVE = False                                      # (o web_host não mexe nos flags)
    WH.CHROMIUM_FLAGS = MODO["flags"] + (" --disable-gpu" if sem_gpu and "--disable-gpu" not in MODO["flags"] else "")
PORT = WH.setup_environment()
C.MODO_LEVE = MODO["ui_leve"]
flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
for k, v in (MODO.get("env") or {}).items():
    os.environ[k] = v

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, accounts = C.load_config()
for a in accounts:
    a.profile_dir.mkdir(parents=True, exist_ok=True)
import app.gui as G  # noqa: E402
for p in MODO.get("patches", []):          # ajustes de um candidato aplicados no código, só neste teste
    p(G)
from browser.cdp import list_targets  # noqa: E402
import websockets  # noqa: E402

web = WH.WebHost(PORT)
m = G.Manager(cfg, accounts, web)
m.start()
# conta reconexões e erros do log (o log continua igual)
EVENTOS = {"reconexoes": 0, "erros": 0, "sessao": 0}
_log_orig = m._log
def _log(i, msg):
    low = msg.lower()
    if "reconect" in low or "conexão perdida" in low:
        EVENTOS["reconexoes"] += 1
    if "erro" in low or "travado" in low:
        EVENTOS["erros"] += 1
    if "expirad" in low:
        EVENTOS["sessao"] += 1
    _log_orig(i, msg)
m._log = _log
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
telas = QGuiApplication.screens()
tela = QGuiApplication.primaryScreen()
if A.tela == "secundaria":
    tela = next((t for t in telas if t is not QGuiApplication.primaryScreen()), tela)
geo = tela.geometry()
win.setGeometry(geo.x(), geo.y(), 1920, 1040)
win.show()


# ------------------------------------------------------------------ utilidades
def pct(v, p):
    if not v:
        return None
    v = sorted(v)
    return round(v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))], 2)


def resumo_quadros(iv: list[float], dur: float) -> dict:
    if not iv:
        return {"n": 0}
    return {"n": len(iv), "qps": round(len(iv) / dur, 1), "p50_ms": pct(iv, 50), "p95_ms": pct(iv, 95),
            "p99_ms": pct(iv, 99), "max_ms": round(max(iv), 1),
            "acima_33ms": round(sum(1 for x in iv if x > 33.4) / len(iv), 4)}


def esperar(seg: float):
    fim = time.monotonic() + seg
    while time.monotonic() < fim:
        qapp.processEvents()
        time.sleep(0.005)


# ------------------------------------------------------------------ quadros mostrados (Qt)
class Pinturas(QObject):
    """Conta as pinturas do widget interno de cada página: é o quadro que aparece na tela."""

    def __init__(self):
        super().__init__()
        self.t: dict[int, list[float]] = {}
        self.ligados = set()

    def ligar(self):
        for c in win.game.cells:
            v = c.view
            if v is None:
                continue
            for w in v.findChildren(QWidget):
                if w.metaObject().className() == "QQuickWidget" and id(w) not in self.ligados:
                    w.setProperty("pn_conta", c.index)
                    w.installEventFilter(self)
                    self.ligados.add(id(w))

    def eventFilter(self, o, e):
        if e.type() == QEvent.Paint:
            self.t.setdefault(int(o.property("pn_conta")), []).append(time.perf_counter())
        return False

    def zerar(self):
        self.t = {}

    def ler(self, dur):
        por = {}
        todos = []
        for i, ts in sorted(self.t.items()):
            iv = [(b - a) * 1000 for a, b in zip(ts, ts[1:])]
            por[i] = resumo_quadros(iv, dur)
            todos += iv
        return {"todas": resumo_quadros(todos, dur), "por_conta": por}


pint = Pinturas()


# ------------------------------------------------------------------ folga da thread da interface
class Folga:
    def __init__(self):
        self.iv = []
        self.ult = None
        self.tm = QTimer()
        self.tm.setTimerType(Qt.PreciseTimer)
        self.tm.timeout.connect(self._tick)
        self.tm.start(16)

    def _tick(self):
        t = time.perf_counter()
        if self.ult is not None:
            self.iv.append(max(0.0, (t - self.ult) * 1000 - 16))
        self.ult = t

    def ler(self):
        r = {"n": len(self.iv), "p50_ms": pct(self.iv, 50), "p95_ms": pct(self.iv, 95),
             "max_ms": round(max(self.iv), 1) if self.iv else None}
        self.iv = []
        return r


folga = Folga()


# ------------------------------------------------------------------ CPU, memória, GPU (thread)
class Amostrador(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.pid = os.getpid()
        self.amostras = []          # (t, {pid: (cpu_s, mem_mb)}, gpu)
        self.gpu = S.ContadoresGpu()
        self.parar = False
        self.mascara = 0b11 if A.perfil == "P3" else None
        self.presos = set()

    def run(self):
        while not self.parar:
            t = time.monotonic()
            pids = S.arvore(self.pid)
            if self.mascara:
                for p in pids:
                    if p not in self.presos and S.afinidade(p, self.mascara):
                        self.presos.add(p)
            leitura = {p: S.cpu_e_memoria(p) for p in pids}
            self.amostras.append((t, {p: v for p, v in leitura.items() if v}, self.gpu.amostra(set(pids))))
            time.sleep(max(0.0, 1.0 - (time.monotonic() - t)))

    def janela(self, t0, t1, tipos):
        a = [x for x in self.amostras if t0 <= x[0] <= t1]
        if len(a) < 3:
            return {}
        uso, por_tipo_cpu, mem_tot, mem_tipo = [], {}, [], {}
        for (ta, da, _g), (tb, db, _g2) in zip(a, a[1:]):
            dt = tb - ta
            tot = 0.0
            for p, (cb, _mb) in db.items():
                ca = da.get(p, (cb, 0))[0] if p in da else 0.0
                if p not in da:
                    continue
                d = max(0.0, cb - ca)
                tot += d
                tp = tipos.get(p, "principal" if p == self.pid else "outro")
                por_tipo_cpu[tp] = por_tipo_cpu.get(tp, 0.0) + d
            uso.append(tot / dt / S.NCPU * 100)
        dur = a[-1][0] - a[0][0]
        for _t, d, _g in a:
            mem_tot.append(sum(v[1] for v in d.values()))
            for p, (_c, mb) in d.items():
                tp = tipos.get(p, "principal" if p == self.pid else "outro")
                mem_tipo.setdefault(tp, []).append(mb)
        gpus = [g for _t, _d, g in a if g]
        out = {
            "cpu_media_pct": round(sum(uso) / len(uso), 2), "cpu_p95_pct": pct(uso, 95),
            "cpu_nucleos": round(sum(uso) / len(uso) * S.NCPU / 100, 3),
            "cpu_por_tipo_pct": {k: round(v / dur / S.NCPU * 100, 2) for k, v in sorted(por_tipo_cpu.items())},
            "ram_media_mb": round(sum(mem_tot) / len(mem_tot), 1), "ram_max_mb": round(max(mem_tot), 1),
            "ram_por_tipo_mb": {k: round(sum(v) / len(a), 1) for k, v in sorted(mem_tipo.items())},
            "processos": len(a[-1][1]),
        }
        if gpus:
            out["gpu_3d_pct"] = round(sum(g["uso_3d"] for g in gpus) / len(gpus), 2)
            out["gpu_total_pct"] = round(sum(g["uso_total"] for g in gpus) / len(gpus), 2)
            out["gpu_mem_mb"] = round(sum(g["mem_mb"] for g in gpus) / len(gpus), 1)
        return out


amost = Amostrador()
amost.start()


# ------------------------------------------------------------------ páginas (DevTools, mundo isolado)
JS = (AQUI / "medidor.js").read_text(encoding="utf-8")
JS_LER = """(() => { const m = globalThis.__pnMed; if (!m) return null;
  const r = {raf: m.raf, ent: m.ent, et: m.et, loaf: m.loaf, rec: m.rec, vis: document.visibilityState,
             w: innerWidth, h: innerHeight, url: location.href.slice(0, 80)};
  m.raf = []; m.ent = []; m.et = []; m.loaf = []; m.rec = 0; return r; })()"""


class Medidor:
    """Uma conexão própria do DevTools por página (as dos workers continuam iguais)."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.pags: dict[str, dict] = {}       # target id -> {ws, ctx, ...}
        self.dados: dict[str, dict] = {}


        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    def rodar(self, coro, timeout=60):
        # O DevTools do Qt responde na thread da tela: esperar parado aqui travaria tudo.
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        fim = time.monotonic() + timeout
        while not fut.done() and time.monotonic() < fim:
            qapp.processEvents()
            time.sleep(0.002)
        return fut.result(0)

    async def _cmd(self, p, metodo, params=None):
        p["id"] += 1
        i = p["id"]
        fut = self.loop.create_future()
        p["pend"][i] = fut
        await p["ws"].send(json.dumps({"id": i, "method": metodo, "params": params or {}}))
        return await asyncio.wait_for(fut, 15)

    async def _ler_ws(self, tid, p):
        try:
            async for raw in p["ws"]:
                msg = json.loads(raw)
                if "id" in msg and msg["id"] in p["pend"]:
                    f = p["pend"].pop(msg["id"])
                    if not f.done():
                        f.set_result(msg)
                elif msg.get("method") in ("Runtime.executionContextsCleared", "Page.frameNavigated"):
                    p["ctx"] = None
        except Exception:
            pass
        finally:
            self.pags.pop(tid, None)

    async def _instalar(self, p):
        arv = await self._cmd(p, "Page.getFrameTree")
        fid = arv["result"]["frameTree"]["frame"]["id"]
        r = await self._cmd(p, "Page.createIsolatedWorld", {"frameId": fid, "worldName": "pn_medidor"})
        p["ctx"] = r["result"]["executionContextId"]
        await self._cmd(p, "Runtime.evaluate", {"expression": JS, "contextId": p["ctx"], "returnByValue": True})

    async def conectar(self):
        alvos = await self.loop.run_in_executor(None, list_targets, PORT)
        for t in alvos:
            if t.get("type") != "page" or t["id"] in self.pags or not t.get("webSocketDebuggerUrl"):
                continue
            if t.get("url", "").startswith(("about:blank#pokeidle-dados", "devtools")):
                continue
            try:
                ws = await websockets.connect(t["webSocketDebuggerUrl"], max_size=None, ping_interval=None)
            except Exception:
                continue
            p = {"ws": ws, "id": 0, "pend": {}, "ctx": None}
            self.pags[t["id"]] = p
            asyncio.ensure_future(self._ler_ws(t["id"], p))
            try:
                await self._cmd(p, "Page.enable")
            except Exception:
                pass

    async def coletar(self):
        await self.conectar()
        for tid, p in list(self.pags.items()):
            try:
                if p["ctx"] is None:
                    await self._instalar(p)
                r = await self._cmd(p, "Runtime.evaluate", {"expression": JS_LER, "contextId": p["ctx"],
                                                            "returnByValue": True})
                v = (r.get("result") or {}).get("result", {}).get("value")
                if r.get("error") or v is None:
                    p["ctx"] = None
                    continue
                d = self.dados.setdefault(tid, {"raf": [], "ent": [], "et": [], "loaf": [], "vis": set(), "rec": 0})
                d["rec"] += v.get("rec") or 0
                for k in ("raf", "ent", "et", "loaf"):
                    d[k] += v[k]
                d["vis"].add(v["vis"])
                d["tam"] = (v["w"], v["h"])
            except Exception:
                p["ctx"] = None

    async def teclar(self):
        """Uma tecla F24 em cada página à vista (nenhuma página usa essa tecla)."""
        for p in list(self.pags.values()):
            if p["ctx"] is None:
                continue
            try:
                for tipo in ("rawKeyDown", "keyUp"):
                    await self._cmd(p, "Input.dispatchKeyEvent", {"type": tipo, "key": "F24", "code": "F24",
                                                                  "windowsVirtualKeyCode": 135})
            except Exception:
                pass

    def zerar(self):
        self.rodar(self.coletar())
        self.dados = {}

    def ler(self, dur):
        self.rodar(self.coletar())
        vis = {k: d for k, d in self.dados.items() if "visible" in d["vis"] and d["raf"]}
        todos_raf = [x for d in vis.values() for x in d["raf"]]
        ent = [x for d in vis.values() for x in d["ent"]]
        et = [x for d in vis.values() for x in d["et"]]
        loaf = [x for d in vis.values() for x in d["loaf"]]
        # Event Timing só registra eventos de 16 ms ou mais: os que faltam ficaram abaixo disso (conta 16).
        env = sum(d["rec"] for d in vis.values())
        et_todos = et + [16.0] * max(0, env - len(et))
        return {
            "paginas_visiveis": len(vis),
            "raf": resumo_quadros(todos_raf, dur),
            "raf_por_pagina": [resumo_quadros(d["raf"], dur) | {"tam": d.get("tam")} for d in vis.values()],
            "entrada": {"n": len(ent), "p50_ms": pct(ent, 50), "p95_ms": pct(ent, 95),
                        "max_ms": round(max(ent), 1) if ent else None},
            "event_timing": {"teclas": env, "acima_16ms": len(et), "p50_ms": pct(et_todos, 50),
                             "p95_ms": pct(et_todos, 95), "max_ms": max(et_todos) if et_todos else None},
            "quadros_longos": {"n": len(loaf), "por_min": round(len(loaf) / dur * 60, 1),
                               "p95_ms": pct(loaf, 95)},
        }


med = Medidor()


# ------------------------------------------------------------------ cenários
def cenario(nome):
    if win.isMinimized():
        win.showNormal()
        win.setGeometry(geo.x(), geo.y(), 1920, 1040)
    if nome == "C1":
        win.select(0)
    elif nome in ("C2", "C3"):
        win._trocar_layout_todas("grade" if nome == "C2" else "celulares", salvar=False)
        win.view_all()
    elif nome == "C4":
        win.showMinimized()


def repintura_ms():
    """Repintar a interface inteira (como o bench_final): mediana de 15 vezes."""
    ts = []
    alvo = win.centralWidget()
    for _ in range(15):
        t = time.perf_counter()
        alvo.repaint()
        ts.append(time.perf_counter() - t)
        qapp.processEvents()
    return round(sorted(ts)[len(ts) // 2] * 1000, 2)


def troca_ms():
    """Tempo da interface para trocar de conta e ir para Todas as contas (só a parte do Qt)."""
    ts = []
    for passo in (lambda: win.select(1), lambda: win.select(2), lambda: win.view_all(), lambda: win.select(0)):
        t = time.perf_counter()
        passo()
        qapp.processEvents()
        ts.append(time.perf_counter() - t)
    return round(sorted(ts)[len(ts) // 2] * 1000, 2)


def farm():
    return {s["index"]: {"batalhas": s["battles"], "tempo": s["elapsed"], "xp": s["xp_gained"]}
            for s in m.snapshot()}


def abrir_paginas():
    if A.dados == "reais" or A.pagina == "jogo":
        m.start_all()
        return
    url = QUrl.fromLocalFile(str(AQUI / "carga.html")).toString()
    for a in accounts:
        web.open(a.index, str(a.profile_dir / "web"), f"{url}?conta={a.index + 1}", cfg["janela"]["zoom"])


def principal():
    resultado = {
        "quando": datetime.now().isoformat(timespec="seconds"), "modo": A.modo, "perfil": A.perfil,
        "pagina": A.pagina, "dados": A.dados, "rodada": A.rodada, "flags": flags,
        "ui_leve": MODO["ui_leve"], "env": {k: os.environ.get(k) for k in ("QSG_RHI_PREFER_SOFTWARE_RENDERER", "QT_QUICK_BACKEND")},
        "tela": {"nome": tela.name(), "hz": tela.refreshRate(), "dpr": tela.devicePixelRatio(),
                 "geo": [geo.width(), geo.height()]},
        "janela": [win.width(), win.height()], "segundos": A.segundos, "cenarios": {},
    }
    abrir_paginas()
    esperar(A.aquecimento)
    cache_tipos = {}
    for nome in A.cenarios.split(","):
        cenario(nome)
        esperar(A.assentar)
        pint.ligar()
        cache_tipos.update(S.tipos(S.arvore(os.getpid())))
        for c in win.game.cells:                       # os renderers são "pagina"
            try:
                pid = c.view.page().renderProcessPid() if c.view else 0
            except RuntimeError:
                pid = 0
            if pid:
                cache_tipos[pid] = "pagina"
        pint.zerar(); folga.ler(); med.zerar()
        f0 = farm()
        t0 = time.monotonic()
        prox_tecla = t0 + 1
        while time.monotonic() - t0 < A.segundos:
            esperar(0.25)
            if time.monotonic() >= prox_tecla and nome != "C4":
                med.rodar(med.teclar())
                prox_tecla += 2
        t1 = time.monotonic()
        dur = t1 - t0
        f1 = farm()
        r = {"duracao_s": round(dur, 1), "quadros_mostrados": pint.ler(dur), "folga_qt": folga.ler()}
        r |= {"pagina": med.ler(dur)}
        r["recursos"] = amost.janela(t0, t1, cache_tipos)
        if nome != "C4":
            r["repintura_janela_ms"] = repintura_ms()
        if nome == "C1":
            r["troca_de_tela_ms"] = troca_ms()
        if A.dados == "reais":
            r["farm"] = {i: {"batalhas": f1[i]["batalhas"] - f0[i]["batalhas"],
                             "batalhas_h": round((f1[i]["batalhas"] - f0[i]["batalhas"]) / dur * 3600, 1)}
                         for i in f1}
        r["eventos_log"] = dict(EVENTOS)
        resultado["cenarios"][nome] = r
        print(f"[{A.modo} {A.perfil} r{A.rodada}] {nome}: quadros {r['quadros_mostrados']['todas'].get('qps')} q/s "
              f"p95 {r['quadros_mostrados']['todas'].get('p95_ms')} ms, entrada p95 "
              f"{r['pagina']['event_timing']['p95_ms']} ms, CPU {r['recursos'].get('cpu_media_pct')}%, "
              f"RAM {r['recursos'].get('ram_media_mb')} MB", flush=True)
    resultado["afinidade_aplicada"] = len(amost.presos)
    saida = Path(A.saida)
    saida.mkdir(parents=True, exist_ok=True)
    arq = saida / f"{A.pagina}_{A.dados}_{A.perfil}_{A.modo}_r{A.rodada}_{datetime.now():%Y%m%d_%H%M%S}.json"
    arq.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado:", arq, flush=True)
    amost.parar = True
    win.close()
    qapp.quit()


QTimer.singleShot(1500, principal)
qapp.exec()
if TMP:
    for _ in range(10):
        try:
            shutil.rmtree(TMP)
            break
        except OSError:
            time.sleep(1)

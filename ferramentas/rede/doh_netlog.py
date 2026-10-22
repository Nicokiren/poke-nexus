"""Prova pelo registro de rede do Chromium (--log-net-log) que o navegador embutido usa o DNS seguro.

    .venv\\Scripts\\python.exe ferramentas\\rede\\doh_netlog.py --netlog <arquivo.json> [--so-seguro]
    .venv\\Scripts\\python.exe ferramentas\\rede\\doh_netlog.py --ler <arquivo.json>

Abre o PokeIdle numa página anônima (sem login, nada gravado) e, 12 s depois, outra página num nome novo
(example.com), para ver a consulta feita depois que o Chromium testou os servidores (ele testa ~5 s depois de
abrir; antes disso usa o DNS do Windows).
  --so-seguro  só para este teste: troca o modo por "SecureOnly" (sem volta para o DNS do Windows). Se a página
               abre assim, o DNS seguro sozinho resolve o PokeIdle.
  --ler        conta, no registro, os pedidos ao DNS seguro por nome.
"""
import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--netlog", default="")
ap.add_argument("--so-seguro", action="store_true")
ap.add_argument("--ler", default="")
A = ap.parse_args()


def ler(arq: str) -> dict:
    # Lido linha a linha: o Chromium grava um evento por linha, e o fim do arquivo pode vir cortado ou com
    # pedaços fora de ordem quando o processo fecha. Linha que não fecha como JSON é deixada de lado.
    linhas = Path(arq).read_text(encoding="utf-8", errors="replace").replace("\x00", "").splitlines()
    d = {"constants": json.loads(linhas[0].rstrip().rstrip(",") + "}")["constants"], "events": []}
    for ln in linhas[1:]:
        ln = ln.strip().rstrip(",")
        if ln.startswith('{"') and ln.endswith("}"):
            try:
                d["events"].append(json.loads(ln))
            except ValueError:
                pass
    tipos = {v: k for k, v in d["constants"]["logEventTypes"].items()}
    modos = {v: k for k, v in d["constants"].get("secureDnsMode", {}).items()}
    doh = collections.Counter()
    jobs = []
    servidores = None
    for e in d["events"]:
        t, p = tipos.get(e["type"]), e.get("params") or {}
        if t == "DOH_URL_REQUEST":
            doh[p.get("hostname")] += 1
        elif t == "HOST_RESOLVER_MANAGER_JOB" and p.get("host"):
            jobs.append((p["host"], modos.get(p.get("secure_dns_mode"), p.get("secure_dns_mode"))))
        elif t == "DNS_CONFIG_CHANGED":
            servidores = [s["template"] for s in (p.get("doh_config") or {}).get("servers", [])]
    return {"servidores_doh": servidores, "pedidos_doh_por_nome": dict(doh),
            "consultas": [f"{h} ({m})" for h, m in jobs if "wpad" not in h]}


if A.ler:
    print(json.dumps(ler(A.ler), indent=1, ensure_ascii=False))
    sys.exit(0)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"--log-net-log={A.netlog} --net-log-capture-mode=Default"   # sem espaços
import browser.web_host as WH  # noqa: E402
from PySide6.QtWebEngineCore import QWebEngineGlobalSettings as G, QWebEnginePage, QWebEngineProfile  # noqa: E402

if A.so_seguro:
    def so_seguro():
        modo = G.DnsMode()
        modo.secureMode = G.SecureDnsMode.SecureOnly
        modo.serverTemplates = WH.DNS_SERVIDORES
        return bool(G.setDnsMode(modo))
    WH.configurar_dns = so_seguro
WH.setup_environment()
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
qapp = QApplication(sys.argv)
perfil = QWebEngineProfile()                       # anônimo, em memória
R = {"dns_seguro_ligado": WH.DNS_SEGURO, "modo": "SecureOnly" if A.so_seguro else "SecureWithFallback"}


def abrir(url: str, seg: float) -> bool:
    pg = QWebEnginePage(perfil)
    fim = {}
    pg.loadFinished.connect(lambda ok: fim.setdefault("ok", ok))
    pg.load(QUrl(url))
    t = time.monotonic() + seg
    while "ok" not in fim and time.monotonic() < t:
        qapp.processEvents()
        time.sleep(0.01)
    return bool(fim.get("ok"))


R["pokeidle_abriu"] = abrir("https://pokeidle.io/app", 40)
t = time.monotonic() + 12
while time.monotonic() < t:
    qapp.processEvents()
    time.sleep(0.01)
R["example_abriu"] = abrir("https://example.com/", 30)
print(json.dumps(R, ensure_ascii=False), flush=True)
os._exit(0)

"""O caso do amigo, de ponta a ponta: o DNS do Windows não acha o pokeidle.io, mas a internet funciona.

    .venv\\Scripts\\python.exe ferramentas\\rede\\dns_quebrado.py --saida <arquivo.json> [--raiz <cópia do projeto>]

Só DENTRO deste processo de teste: troca, na tabela de importação do Qt6WebEngineCore.dll, o `getaddrinfo` do
Windows (o "DNS do sistema" do Chromium) por um que responde "nome não encontrado" para *pokeidle.io e chama
o verdadeiro para o resto. A rede do PC, o DNS, o arquivo hosts e o firewall não são tocados. Abre o PokeNexus
com uma pasta de dados TEMPORÁRIA (contas na tela de login: nenhuma conta real é tocada), inicia as 4 contas e
anota, por 90 s, o status de cada uma. Com o DNS seguro as contas chegam à tela de login do jogo; sem ele
(--raiz com o código de antes) ficam no erro.
"""
import argparse
import ctypes
import json
import os
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
ap.add_argument("--saida", required=True)
ap.add_argument("--segundos", type=float, default=90)
ap.add_argument("--controle", action="store_true", help="o gancho fica, mas não recusa nada (mede o custo dele)")
A = ap.parse_args()
sys.path.insert(0, A.raiz)
os.environ["POKENEXUS_DATA"] = tempfile.mkdtemp(prefix="pn_dnsq_")
os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)

import app.config as C  # noqa: E402
import browser.web_host as WH  # noqa: E402
porta = WH.setup_environment()
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

# ----------------------------------------------------------------- o "DNS do Windows quebrado"
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetModuleHandleW.restype = ctypes.c_void_p
k32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
k32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
ws2 = ctypes.WinDLL("ws2_32")
GAI = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p)
verdadeiro = GAI(("getaddrinfo", ws2))
CHAMADAS = {"recusadas": 0, "passaram": 0}


def falso(no, servico, dicas, resultado):
    if not A.controle and no and no.lower().rstrip(b".").endswith(b"pokeidle.io"):
        CHAMADAS["recusadas"] += 1
        return 11001                      # WSAHOST_NOT_FOUND: o que um DNS que não acha o nome devolve
    CHAMADAS["passaram"] += 1
    return verdadeiro(no, servico, dicas, resultado)


GANCHO = GAI(falso)                       # guardado em variável global: não pode ser coletado


def u32(a):
    return ctypes.c_uint32.from_address(a).value


def u64(a):
    return ctypes.c_uint64.from_address(a).value


def trocar_iat(modulo: str, dll: str, funcao: str, novo) -> list[str]:
    base = k32.GetModuleHandleW(modulo)
    assert base, f"{modulo} não carregado"
    opt = base + u32(base + 0x3C) + 24             # cabeçalho opcional (PE32+)
    feitos = []

    def trocar(slot):
        velho = wintypes.DWORD()
        k32.VirtualProtect(slot, 8, 0x04, ctypes.byref(velho))    # PAGE_READWRITE
        ctypes.c_uint64.from_address(slot).value = ctypes.cast(novo, ctypes.c_void_p).value
        k32.VirtualProtect(slot, 8, velho.value, ctypes.byref(velho))

    def procurar(nomes_rva, iat_rva, tipo):
        i = 0
        while True:
            ent = u64(base + nomes_rva + 8 * i)
            if ent == 0:
                return
            if not ent & (1 << 63) and ctypes.string_at(base + (ent & 0x7FFFFFFF) + 2) == funcao.encode():
                trocar(base + iat_rva + 8 * i)
                feitos.append(tipo)
            i += 1

    imp = u32(opt + 112 + 8 * 1)                   # importações normais
    d = base + imp
    while imp and u32(d + 12):
        if ctypes.string_at(base + u32(d + 12)).decode().lower() == dll:
            procurar(u32(d) or u32(d + 16), u32(d + 16), "normal")
        d += 20
    dly = u32(opt + 112 + 8 * 13)                  # importações atrasadas (delay-load)
    d = base + dly
    while dly and u32(d + 4):
        if ctypes.string_at(base + u32(d + 4)).decode().lower() == dll:
            procurar(u32(d + 16), u32(d + 12), "atrasada")
        d += 32
    return feitos


R = {"troca": trocar_iat("Qt6WebEngineCore.dll", "ws2_32.dll", "getaddrinfo", GANCHO),
     "dns_seguro_ligado": getattr(WH, "DNS_SEGURO", None), "raiz": A.raiz}

# ----------------------------------------------------------------- o programa
qapp = QApplication(sys.argv)
C.prepare_data_dir()
cfg, contas = C.load_config()
import app.gui as G  # noqa: E402

web = WH.WebHost(porta)
m = G.Manager(cfg, contas, web)
m.start()
win = G.MainWindow(m, web)
win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
win.setFixedSize(1600, 1000)
win.show()

linha = []
t0 = time.monotonic()
m.start_all()
ultimo = None
while time.monotonic() - t0 < A.segundos:
    qapp.processEvents()
    time.sleep(0.05)
    st = tuple(x["status"] for x in m.snapshot())
    if st != ultimo:
        linha.append([round(time.monotonic() - t0, 1), list(st)])
        ultimo = st
    if all(s == "SESSÃO EXPIRADA" for s in st):
        break
R["linha_do_tempo"] = linha
R["todas_no_login"] = all(s == "SESSÃO EXPIRADA" for s in ultimo)
R["segundos"] = round(time.monotonic() - t0, 1)
R["getaddrinfo"] = dict(CHAMADAS)
R["contador"] = win.counter.text()
R["detail_final"] = [x["detail"] for x in m.snapshot()]
Path(A.saida).write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(R, indent=1, ensure_ascii=False), flush=True)
os._exit(0)

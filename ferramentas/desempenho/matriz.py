"""Roda medir.py para cada rodada x perfil x modo, um de cada vez, intercalando os modos (assim um
aquecimento do PC ou um programa aberto no meio não favorece um modo só).

    .venv\\Scripts\\python.exe ferramentas\\desempenho\\matriz.py --modos normal,leve --perfis P1,P2,P3 --rodadas 3

O que vier depois de "--" vai direto para medir.py (ex.: -- --segundos 60 --pagina jogo).
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
args, resto = sys.argv[1:], []
if "--" in args:
    i = args.index("--")
    args, resto = args[:i], args[i + 1:]
ap = argparse.ArgumentParser()
ap.add_argument("--modos", default="normal,leve")
ap.add_argument("--perfis", default="P1,P2,P3")
ap.add_argument("--rodadas", type=int, default=3)
ap.add_argument("--primeira", type=int, default=1, help="número da primeira rodada")
A = ap.parse_args(args)

combos = [(r, p, m) for r in range(A.primeira, A.primeira + A.rodadas)
          for p in A.perfis.split(",") for m in A.modos.split(",")]
print(f"{datetime.now():%H:%M:%S} {len(combos)} medições", flush=True)
for n, (r, p, m) in enumerate(combos, 1):
    t = time.monotonic()
    cmd = [sys.executable, "-u", str(AQUI / "medir.py"), "--modo", m, "--perfil", p, "--rodada", str(r), *resto]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    linhas = [l for l in proc.stdout.splitlines() if l.startswith(("[", "gravado"))]
    print(f"{datetime.now():%H:%M:%S} ({n}/{len(combos)}) {m} {p} r{r}: saiu {proc.returncode} em "
          f"{time.monotonic() - t:.0f} s", flush=True)
    for l in linhas:
        print("   ", l, flush=True)
    if proc.returncode != 0:
        print("   ERRO:", "\n".join(proc.stderr.splitlines()[-15:]), flush=True)
    time.sleep(5)          # os processos do Chromium terminam de sair
print(f"{datetime.now():%H:%M:%S} fim", flush=True)

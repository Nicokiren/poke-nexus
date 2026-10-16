"""A página de teste do Market (mercado_teste.py) num NAVEGADOR COMUM (Microsoft Edge, sem nada do
PokeNexus), em vários tamanhos de página. Serve para saber se o corte é do jogo ou do PokeNexus.

    .venv\\Scripts\\python.exe ferramentas\\interface\\navegador_comum.py --saida <pasta> 1531x763 1920x947

Para cada tamanho: um print (Edge sem janela, --headless) e as medidas do modal (o mesmo MEDIR_JS da
vistoria). Pasta e perfil do Edge temporários; nenhuma conta, nenhum login.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import mercado_teste

EDGE = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"

ap = argparse.ArgumentParser()
ap.add_argument("--saida", required=True)
ap.add_argument("--versao", default="1.300.2")
ap.add_argument("tamanhos", nargs="+")
A = ap.parse_args()
SAIDA = Path(A.saida).resolve()
SAIDA.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="pn_nav_"))
html = mercado_teste.preparar(A.versao, tmp / "mercado")
# A mesma página, com a medida escrita no fim (depois de medir: não muda o que foi medido).
medir = html.with_name("market_medir.html")
medir.write_text(html.read_text(encoding="utf-8").replace(
    "</body>", f"<script>addEventListener('load', () => setTimeout(() => {{ const p = document.createElement('pre');"
               f" p.id = 'medida'; p.textContent = {mercado_teste.MEDIR_JS};"
               " p.style.display = 'none'; document.body.append(p); }, 300));</script></body>"),
    encoding="utf-8")


def edge(w: int, h: int, *extra) -> str:
    return subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           f"--user-data-dir={tmp / 'perfil'}", f"--window-size={w},{h}",
                           "--virtual-time-budget=3000", *extra], capture_output=True, timeout=60, text=True,
                          encoding="utf-8").stdout


res = {}
try:
    for t in A.tamanhos:
        w, h = (int(x) for x in t.lower().split("x"))
        # `--dump-dom` desconta uma moldura da janela; `--screenshot` não (o print sai com a página do tamanho
        # pedido). O tamanho pedido é o da PÁGINA.
        m = re.search(r'<pre id="medida"[^>]*>(.*?)</pre>', edge(w + 24, h + 92, "--dump-dom", medir.as_uri()), re.S)
        res[t] = json.loads(m.group(1).replace("&quot;", '"')) if m else None
        edge(w, h, f"--screenshot={SAIDA / f'edge_{w}x{h}.png'}", html.as_uri())
        r = res[t] or {}
        print(t, "pagina", r.get("iw"), "x", r.get("ih"), "modal", (r.get("modal") or {}).get("h"),
              "cortados", r.get("cortados"), flush=True)
finally:
    (SAIDA / "edge_medidas.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)

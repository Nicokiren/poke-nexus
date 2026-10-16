"""Junta as rodadas gravadas por medir.py: mediana e faixa (mín–máx) por perfil, cenário e modo.

    .venv\\Scripts\\python.exe ferramentas\\desempenho\\resumo.py [pasta] [--pagina carga] [--dados temp]
                                                               [--modos normal,leve] [--md saida.md]
"""
import argparse
import json
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("pasta", nargs="?", default=str(RAIZ / "docs" / "desempenho" / "dados"))
ap.add_argument("--pagina", default="carga")
ap.add_argument("--dados", default="temp")
ap.add_argument("--modos", default="")
ap.add_argument("--perfis", default="")
ap.add_argument("--md", default="")
A = ap.parse_args()

# (rótulo, caminho no JSON do cenário, casas, menor é melhor?)
METRICAS = [
    ("Quadros/s", ("quadros_mostrados", "todas", "qps"), 1),
    ("Quadro p95 (ms)", ("quadros_mostrados", "todas", "p95_ms"), 1),
    ("Quadros >33 ms", ("quadros_mostrados", "todas", "acima_33ms"), 4),
    ("Entrada p95 (ms)", ("pagina", "event_timing", "p95_ms"), 0),
    ("rAF p95 (ms)", ("pagina", "raf", "p95_ms"), 1),
    ("Folga Qt p95 (ms)", ("folga_qt", "p95_ms"), 1),
    ("CPU média (%)", ("recursos", "cpu_media_pct"), 2),
    ("CPU p95 (%)", ("recursos", "cpu_p95_pct"), 2),
    ("RAM (MB)", ("recursos", "ram_media_mb"), 0),
    ("GPU 3D (%)", ("recursos", "gpu_3d_pct"), 1),
    ("GPU mem (MB)", ("recursos", "gpu_mem_mb"), 0),
    ("Batalhas/h", ("farm_total",), 0),
]


def pegar(d, caminho):
    if caminho == ("farm_total",):
        f = d.get("farm")
        return sum(v["batalhas_h"] for v in f.values()) if f else None
    for k in caminho:
        if not isinstance(d, dict) or d.get(k) is None:
            return None
        d = d[k]
    return d


rodadas = []
for arq in sorted(Path(A.pasta).glob("*.json")):
    try:
        j = json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        continue
    if j.get("pagina") != A.pagina or j.get("dados") != A.dados:
        continue
    if A.modos and j["modo"] not in A.modos.split(","):
        continue
    if A.perfis and j["perfil"] not in A.perfis.split(","):
        continue
    rodadas.append(j)

grupos: dict[tuple, list] = {}
for j in rodadas:
    for cen, d in j["cenarios"].items():
        grupos.setdefault((j["perfil"], cen, j["modo"]), []).append(d)


def fmt(vals, casas):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "–"
    med = statistics.median(vals)
    f = (lambda x: f"{x:.{casas}f}".replace(".", ","))
    if len(vals) == 1:
        return f(med)
    return f"{f(med)} ({f(min(vals))}–{f(max(vals))})"


ordem_modos = (A.modos.split(",") if A.modos else
               sorted({k[2] for k in grupos}, key=lambda m: (m != "normal", m != "leve", m)))
linhas = ["| Perfil | Cenário | Modo | n | " + " | ".join(m[0] for m in METRICAS) + " |",
          "|" + "---|" * (4 + len(METRICAS))]
resumo = {}
for perfil in sorted({k[0] for k in grupos}):
    for cen in sorted({k[1] for k in grupos if k[0] == perfil}):
        for modo in ordem_modos:
            ds = grupos.get((perfil, cen, modo))
            if not ds:
                continue
            cel = [fmt([pegar(d, m[1]) for d in ds], m[2]) for m in METRICAS]
            linhas.append(f"| {perfil} | {cen} | {modo} | {len(ds)} | " + " | ".join(cel) + " |")
            resumo[f"{perfil}/{cen}/{modo}"] = {
                m[0]: statistics.median(v) if (v := [x for d in ds if (x := pegar(d, m[1])) is not None]) else None
                for m in METRICAS}
texto = "\n".join(linhas)
print(texto)
if A.md:
    Path(A.md).write_text(texto + "\n", encoding="utf-8")
    Path(A.md).with_suffix(".json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")

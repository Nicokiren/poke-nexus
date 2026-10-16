"""Servidor FALSO de Releases do GitHub, só para testar o aviso de atualização sem publicar nada.

    .venv\\Scripts\\python.exe ferramentas\\atualizacao\\servidor_falso.py --pasta <pasta> --porta 8765 [--kbps 20000]

Na pasta:
  <cenário>/latest           a resposta da API (o JSON de uma Release, ou qualquer texto para testar erro)
  arquivos/<nome>            os arquivos da Release (instalador, SHA256SUMS.txt)

O programa de teste aponta para ele com POKENEXUS_ATUALIZACAO_URL=http://127.0.0.1:8765/<cenário>/latest.
Responde com ETag e 304 (If-None-Match), como o GitHub. Cada pedido sai numa linha (para o relatório).
`--kbps` limita a velocidade dos .exe (para ver a barra de progresso e testar o farm durante o download).
`montar_release(...)` monta o JSON de um cenário.
"""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def montar_release(pasta: Path, cenario: str, versao: str, porta: int, setup: str | None, notas: list[str]):
    """Escreve <pasta>/<cenário>/latest com uma Release no formato da API do GitHub."""
    base = f"http://127.0.0.1:{porta}/arquivos"
    assets = [{"name": "SHA256SUMS.txt", "browser_download_url": f"{base}/SHA256SUMS.txt"}]
    if setup:
        assets.append({"name": setup, "browser_download_url": f"{base}/{setup}"})
    d = pasta / cenario
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest").write_text(json.dumps({
        "tag_name": f"v{versao}", "name": f"PokeNexus {versao}", "html_url": f"http://127.0.0.1:{porta}/{cenario}",
        "body": "\n".join(f"- {n}" for n in notas), "assets": assets}, ensure_ascii=False, indent=1), encoding="utf-8")


class Pedido(SimpleHTTPRequestHandler):
    kbps = 0

    def log_message(self, fmt, *args):
        print(f"[{datetime.now():%H:%M:%S}] {self.client_address[0]} {fmt % args}", flush=True)

    def do_GET(self):
        alvo = Path(self.translate_path(self.path))
        if self.path.endswith("/latest") and alvo.is_file():
            corpo = alvo.read_bytes()
            etag = '"' + hashlib.sha1(corpo).hexdigest() + '"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("ETag", etag)
            self.end_headers()
            self.wfile.write(corpo)
            return
        if self.kbps and alvo.suffix == ".exe" and alvo.is_file():
            tam = alvo.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(tam))
            self.end_headers()
            passo = max(64 * 1024, self.kbps * 1024 // 10)
            with open(alvo, "rb") as f:
                try:
                    while bloco := f.read(passo):
                        self.wfile.write(bloco)
                        time.sleep(len(bloco) / (self.kbps * 1024))
                except (ConnectionError, OSError):
                    pass                      # o cliente cancelou
            return
        super().do_GET()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--kbps", type=int, default=0)
    a = ap.parse_args()
    Pedido.kbps = a.kbps
    servidor = ThreadingHTTPServer(("127.0.0.1", a.porta), lambda *x: Pedido(*x, directory=a.pasta))
    print(f"servidor falso em http://127.0.0.1:{a.porta}/ servindo {a.pasta}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)

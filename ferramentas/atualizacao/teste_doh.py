"""Teste da volta pelo DNS seguro do aviso de atualização (app/atualizacao.py, `_abrir`). Usa a internet
(GitHub e Cloudflare), sem login e sem mexer na rede do PC: o "DNS do Windows quebrado" é simulado só
dentro deste processo, trocando socket.getaddrinfo por um que não acha nenhum nome.

    .venv\\Scripts\\python.exe ferramentas\\atualizacao\\teste_doh.py

Sai com código 1 se algum caso falhar.
"""
import ipaddress
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import atualizacao as at  # noqa: E402

falhas = []


def confere(nome, ok, extra=""):
    print(f"{'ok   ' if ok else 'FALHA'} {nome}" + (f": {extra}" if extra else ""))
    if not ok:
        falhas.append(nome)


def eh_ip(h) -> bool:
    try:
        ipaddress.ip_address(h if isinstance(h, str) else h.decode())
        return True
    except ValueError:
        return False


# 1. a pergunta ao DNS seguro
ips = at.resolver_doh("api.github.com")
confere("resolver_doh(api.github.com) devolve IPv4", bool(ips) and all(eh_ip(i) for i in ips), ", ".join(ips))
originais = at.URLS_DOH
for base in originais:
    at.URLS_DOH = (base,)
    ips_um = at.resolver_doh("api.github.com")
    confere(f"servidor {base} sozinho", bool(ips_um), ", ".join(ips_um))
at.URLS_DOH = ("https://127.0.0.1:9/dns-query",) + originais     # o primeiro recusa a conexão
confere("primeiro servidor fora do ar: usa o seguinte", bool(at.resolver_doh("api.github.com")))
at.URLS_DOH = originais
try:
    at.resolver_doh("nao-existe-nunca.invalid")
    confere("nome inexistente dá erro", False)
except OSError as e:
    confere("nome inexistente dá erro", True, str(e))

# 2. com o DNS "quebrado" (só neste processo)
original = socket.getaddrinfo
nomes_recusados = []


def sem_dns(host, *a, **k):
    if not eh_ip(host):
        nomes_recusados.append(host)
        raise socket.gaierror(11001, "getaddrinfo failed")
    return original(host, *a, **k)


socket.getaddrinfo = sem_dns
try:
    try:
        urllib.request.urlopen(at.URL_RELEASES, timeout=10)
        confere("sem a volta, o pedido falha (a simulação vale)", False)
    except urllib.error.URLError as e:
        confere("sem a volta, o pedido falha (a simulação vale)", isinstance(e.reason, socket.gaierror), str(e.reason))

    info = at.Consulta(at.URL_RELEASES).buscar()
    confere("Consulta da Release funciona pela volta", bool(info.get("versao")), f"v{info.get('versao')}")

    with tempfile.TemporaryDirectory() as d:
        destino = Path(d) / "SHA256SUMS.txt"
        at.baixar(info["sums_url"], destino)        # github.com redireciona para o servidor de arquivos
        texto = destino.read_text(encoding="utf-8")
        confere("download com redirecionamento funciona pela volta",
                at.sha256_esperado(texto, info["setup_nome"]) is not None, f"{destino.stat().st_size} bytes")

    try:
        at.Consulta("https://api.github.com/repos/PauloAfonsoGR/repo-que-nao-existe-xyz/releases/latest").buscar()
        confere("erro HTTP continua erro HTTP", False)
    except at.ErroAtualizacao as e:
        confere("erro HTTP continua erro HTTP", "HTTP 404" in str(e), str(e))
    confere("o DNS do Windows foi tentado antes", "api.github.com" in nomes_recusados, ", ".join(sorted(set(nomes_recusados))))
finally:
    socket.getaddrinfo = original

# 3. com o DNS normal nada muda (não passa pela volta)
usou = []
_orig_resolver = at.resolver_doh
at.resolver_doh = lambda *a, **k: usou.append(a) or _orig_resolver(*a, **k)
info2 = at.Consulta(at.URL_RELEASES).buscar()
at.resolver_doh = _orig_resolver
confere("DNS normal: não usa o DNS seguro", bool(info2.get("versao")) and not usou)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)

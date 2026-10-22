"""Teste da tradução dos erros de rede para a tela (app/erros_rede.py). Sem Qt, sem rede.

    .venv\\Scripts\\python.exe ferramentas\\rede\\teste_erros.py

Sai com código 1 se algum caso falhar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import erros_rede as er  # noqa: E402

falhas = []


def confere(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"{'ok   ' if ok else 'FALHA'} {nome}: {obtido!r}" + ("" if ok else f" (esperado {esperado!r})"))
    if not ok:
        falhas.append(nome)


DNS = ("Não consegui achar o endereço do PokeIdle. Teste o site no navegador; se abrir lá, troque o DNS do "
       "Windows (veja F1).")
PROXY = "Um proxy do Windows está bloqueando a conexão."
CERT = "A conexão segura com o PokeIdle falhou (data e hora do PC certas?)."

# o texto que o worker grava hoje (CdpPage.goto + _curto)
confere("DNS (texto do worker)", er.traduzir("falha ao abrir https://pokeidle.io/app: net::ERR_NAME_NOT_RESOLVED"),
        (DNS, "Código: ERR_NAME_NOT_RESOLVED"))
confere("DNS sem net::", er.traduzir("ERR_NAME_NOT_RESOLVED"), (DNS, "Código: ERR_NAME_NOT_RESOLVED"))
confere("DNS dentro de parênteses", er.traduzir("repetindo verificação (net::ERR_NAME_NOT_RESOLVED)")[0], DNS)
confere("sem internet", er.traduzir("falha ao abrir x: net::ERR_INTERNET_DISCONNECTED"),
        ("Sem internet.", "Código: ERR_INTERNET_DISCONNECTED"))
for c in ("ERR_CONNECTION_TIMED_OUT", "ERR_CONNECTION_RESET", "ERR_CONNECTION_REFUSED", "ERR_ADDRESS_UNREACHABLE"):
    confere(c, er.traduzir(f"falha ao abrir x: net::{c}"), (er.GENERICO, f"Código: {c}"))
for c in ("ERR_PROXY_CONNECTION_FAILED", "ERR_PROXY_AUTH_UNSUPPORTED", "ERR_PROXY_CERTIFICATE_INVALID"):
    confere(c, er.traduzir(f"net::{c}")[0], PROXY)
for c in ("ERR_CERT_DATE_INVALID", "ERR_CERT_AUTHORITY_INVALID", "ERR_CERT_COMMON_NAME_INVALID"):
    confere(c, er.traduzir(f"net::{c}")[0], CERT)
confere("outro código: frase genérica, código na dica", er.traduzir("falha ao abrir x: net::ERR_SSL_PROTOCOL_ERROR"),
        (er.GENERICO, "Código: ERR_SSL_PROTOCOL_ERROR"))
confere("ERR_ABORTED também", er.traduzir("net::ERR_ABORTED"), (er.GENERICO, "Código: ERR_ABORTED"))

# textos que não são erro de rede passam iguais e sem dica
for t in ("abrindo o PokeIdle", "faça login: botão 'Login' do programa", "sem internet ou PokeIdle fora do ar",
          "servidor recusou: limite de contas conectadas nesta rede", "", "ERRO", "a página da conta foi fechada"):
    confere(f"sem código: {t!r}", er.traduzir(t), (t, ""))
confere("codigo() sem código", er.codigo("FERRO_X"), None)
confere("codigo() com código", er.codigo("x net::ERR_CERT_REVOKED y"), "ERR_CERT_REVOKED")

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)

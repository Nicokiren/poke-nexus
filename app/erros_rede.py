"""Erros de rede do navegador embutido (Chromium) em português, só para a TELA.

O worker guarda o texto técnico (ex.: "falha ao abrir https://pokeidle.io/app: net::ERR_NAME_NOT_RESOLVED")
e é esse texto que vai para o log, sem mudança. A tela mostra a frase de `traduzir` e o código original fica
na dica (tooltip). Sem Qt: o teste fica em ferramentas/rede/teste_erros.py.
"""
import re

_CODIGO = re.compile(r"\b(?:net::)?(ERR_[A-Z0-9_]+)\b")

GENERICO = "Não consegui falar com o PokeIdle. Pode ser a internet ou o site fora do ar."
_FRASES = {
    "ERR_NAME_NOT_RESOLVED": "Não consegui achar o endereço do PokeIdle. Teste o site no navegador; se abrir "
                             "lá, troque o DNS do Windows (veja F1).",
    "ERR_INTERNET_DISCONNECTED": "Sem internet.",
    "ERR_CONNECTION_TIMED_OUT": GENERICO,
    "ERR_CONNECTION_RESET": GENERICO,
    "ERR_CONNECTION_REFUSED": GENERICO,
    "ERR_ADDRESS_UNREACHABLE": GENERICO,
}
# famílias inteiras de códigos (ERR_PROXY_CONNECTION_FAILED, ERR_CERT_DATE_INVALID...)
_PREFIXOS = (
    ("ERR_PROXY_", "Um proxy do Windows está bloqueando a conexão."),
    ("ERR_CERT_", "A conexão segura com o PokeIdle falhou (data e hora do PC certas?)."),
)


def codigo(texto: str) -> str | None:
    """O código do Chromium dentro do texto ("ERR_NAME_NOT_RESOLVED"), ou None se não houver."""
    m = _CODIGO.search(texto or "")
    return m.group(1) if m else None


def traduzir(texto: str) -> tuple[str, str]:
    """(frase para a tela, dica com o código original). Texto sem código de rede volta igual, sem dica."""
    c = codigo(texto)
    if c is None:
        return texto, ""
    frase = _FRASES.get(c)
    if frase is None:
        frase = next((f for p, f in _PREFIXOS if c.startswith(p)), GENERICO)
    return frase, f"Código: {c}"

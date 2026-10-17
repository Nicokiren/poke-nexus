"""Teste da conta da calculadora de Gemas (app/conversor_gemas.py). Sem Qt, sem rede.

    .venv\\Scripts\\python.exe ferramentas\\calculadora\\teste_conta.py

Sai com código 1 se algum caso falhar.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import conversor_gemas as cg  # noqa: E402

falhas = []


def confere(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"{'ok   ' if ok else 'FALHA'} {nome}: {obtido!r}" + ("" if ok else f" (esperado {esperado!r})"))
    if not ok:
        falhas.append(nome)


def dol(gemas: int) -> str:
    return "US$ " + cg.formatar_dolares(cg.gemas_para_dolares(gemas))


# a tabela do pedido
confere("1.000 Gemas", dol(1000), "US$ 9,00")
confere("1 Gema", dol(1), "US$ 0,009")
confere("0 Gemas", dol(0), "US$ 0,00")
confere("111 Gemas", dol(111), "US$ 0,999")
confere("112 Gemas", dol(112), "US$ 1,00")
confere("112 Gemas (exato)", cg.gemas_para_dolares(112), Decimal("1.008"))
confere("1.234.567 Gemas", dol(1_234_567), "US$ 11.111,10")
for d, g in (("9.00", 1000), ("1.00", 111), ("10.00", 1111), ("0.01", 1), ("0.00", 0)):
    confere(f"US$ {d}", cg.dolares_para_gemas(Decimal(d)), g)

# o tipo: Decimal, nunca float
confere("tipo Gemas -> US$", type(cg.gemas_para_dolares(7)).__name__, "Decimal")
confere("tipo US$ -> Gemas", type(cg.dolares_para_gemas(Decimal("7"))).__name__, "int")

# ida e volta nunca dá mais Gemas que o começo (com o valor exato e com o que aparece na tela)
pior = None
for g in list(range(0, 5000)) + [99_999, 123_456, 999_999_999]:
    d = cg.gemas_para_dolares(g)
    volta = cg.dolares_para_gemas(d)
    volta_tela = cg.dolares_para_gemas(cg.ler_dolares(cg.formatar_dolares(d)))
    if volta > g or volta_tela > g:
        pior = (g, volta, volta_tela)
        break
confere("ida e volta nunca ganha Gema (5.003 valores)", pior, None)

# a taxa num lugar só
confere("linha da taxa", cg.taxa_txt(), "1.000 Gemas = US$ 9,00")
confere("constantes", (cg.GEMAS_REF, cg.CENTAVOS_REF), (1000, 900))

# o que a pessoa digita
for texto, dolares, esperado in (
        ("1000", False, True), ("1.000", False, True), ("", False, True), ("-5", False, False),
        ("1,5", False, False), ("abc", False, False), ("123456789", False, True), ("1234567890", False, False),
        ("9,00", True, True), ("9,", True, True), ("9,005", True, False), ("9,0,0", True, False),
        ("1.234,56", True, True), ("-1", True, False), ("1e5", True, False), ("1234567,89", True, True),
        ("12345678,90", True, False), (" 9", True, False)):
    confere(f"aceita {texto!r} ({'US$' if dolares else 'Gemas'})", cg.entrada_valida(texto, dolares), esperado)
confere("ler '' Gemas", cg.ler_gemas(""), 0)
confere("ler '1.000' Gemas", cg.ler_gemas("1.000"), 1000)
confere("ler '' US$", cg.ler_dolares(""), Decimal(0))
confere("ler ',' US$", cg.ler_dolares(","), Decimal(0))
confere("ler '1.234,5' US$", cg.ler_dolares("1.234,5"), Decimal("1234.5"))
confere("ler '0,009' US$ (o resultado da tela)", cg.ler_dolares("0,009"), Decimal("0.009"))
for n in (-1,):
    try:
        cg.gemas_para_dolares(n)
        confere("negativo recusado", False, True)
    except ValueError:
        confere("negativo recusado", True, True)

# a fala do mascote nas faixas
for valor, frase in (("0", "Quanto vale? Digite aí!"), ("0.009", "Trocado de bolso"), ("1", "Trocado de bolso"),
                     ("1.008", "Trocado de bolso"), ("1.01", "Dá um lanche"), ("10", "Dá um lanche"),
                     ("10.01", "Agora sim, miau!"), ("100", "Agora sim, miau!"), ("100.01", "Isso é muita moeda!"),
                     ("8999999.99", "Isso é muita moeda!")):
    confere(f"frase em US$ {valor}", cg.frase_do_mascote(Decimal(valor)), frase)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)

"""A conta da calculadora do Mercado: Gemas ⇄ dólares, com Decimal (nunca float).

Só conta: sem Qt, sem rede e sem disco (testável sozinho: ferramentas/calculadora/teste_conta.py). A
taxa é a de referência do usuário, NÃO o preço que o jogo manda (welcome.economia).
"""
import re
from decimal import ROUND_DOWN, Decimal

from app.textos_guia import FRASES_MEOWTH

# Taxa de referência dada pelo usuário em 16/10/2026: 1.000 Gemas = US$ 9,00.
# Mudou a taxa? Mude só estas duas linhas (o resto do programa lê daqui).
GEMAS_REF = 1000
CENTAVOS_REF = 900

MAX_DIGITOS = 9            # nos dois campos da calculadora
_CENTAVO = Decimal("0.01")
_MILESIMO = Decimal("0.001")


def gemas_para_dolares(gemas: int) -> Decimal:
    """Valor exato: 1 Gema = US$ 0,009."""
    gemas = int(gemas)
    if gemas < 0:
        raise ValueError("Gemas negativas")
    return Decimal(gemas) * CENTAVOS_REF / (GEMAS_REF * 100)


def dolares_para_gemas(dolares: Decimal) -> int:
    """Arredonda para BAIXO: com US$ 1,00 você consegue 111 Gemas, não 111,11 (frações de centavo caem)."""
    dolares = Decimal(dolares)
    if dolares < 0:
        raise ValueError("dólares negativos")
    centavos = int((dolares * 100).to_integral_value(rounding=ROUND_DOWN))
    return centavos * GEMAS_REF // CENTAVOS_REF


# ------------------------------------------------------------ formato brasileiro
def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def formatar_gemas(gemas: int) -> str:
    """1000 -> '1.000'."""
    return _milhar(int(gemas))


def formatar_dolares(dolares: Decimal) -> str:
    """Sem o 'US$': 9 -> '9,00'; abaixo de US$ 1,00, 3 casas ('0,009') para não virar '0,00'.
    Corta (não arredonda para cima): 1,008 -> '1,00'."""
    d = Decimal(dolares)
    pequeno = 0 < d < 1
    q = d.quantize(_MILESIMO if pequeno else _CENTAVO, rounding=ROUND_DOWN)
    inteiro, _, frac = f"{q:f}".partition(".")
    return f"{_milhar(int(inteiro))},{frac}"


def taxa_txt() -> str:
    """A linha fixa embaixo da calculadora: '1.000 Gemas = US$ 9,00'."""
    return f"{formatar_gemas(GEMAS_REF)} Gemas = US$ {formatar_dolares(gemas_para_dolares(GEMAS_REF))}"


# ------------------------------------------------------------ o que a pessoa digita
_RE_GEMAS = re.compile(r"[0-9.]*")
_RE_DOLARES = re.compile(r"[0-9.]*(,[0-9]{0,2})?")


def entrada_valida(texto: str, dolares: bool) -> bool:
    """Só números (Gemas inteiras; dólares com vírgula e até 2 casas), sem sinal, até 9 dígitos. O ponto
    é separador de milhar (o resultado aparece com ele) e é ignorado na conta."""
    if not (_RE_DOLARES if dolares else _RE_GEMAS).fullmatch(texto or ""):
        return False
    return sum(c.isdigit() for c in texto) <= MAX_DIGITOS


def ler_gemas(texto: str) -> int:
    """'1.000' -> 1000; vazio -> 0."""
    digitos = (texto or "").replace(".", "")
    return int(digitos) if digitos else 0


def ler_dolares(texto: str) -> Decimal:
    """'1.234,5' -> Decimal('1234.5'); vazio ou ',' -> 0."""
    t = (texto or "").replace(".", "").replace(",", ".")
    return Decimal(t) if t.strip(".") else Decimal(0)


def frase_do_mascote(dolares: Decimal) -> str:
    """A fala do Meowth para o valor em dólares (as frases e as faixas ficam em app/textos_guia.py).
    Usa o valor como aparece na tela (de US$ 1 para cima, cortado no centavo), para a frase bater com o
    número: 112 Gemas = US$ 1,008, que aparece como US$ 1,00, ainda é "até US$ 1"."""
    d = Decimal(dolares)
    if d >= 1:
        d = d.quantize(_CENTAVO, rounding=ROUND_DOWN)
    for teto, frase in FRASES_MEOWTH:
        if teto is None or d <= teto:
            return frase
    return FRASES_MEOWTH[-1][1]

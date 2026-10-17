"""Ícones de pixel do PokeNexus (arte própria), 10×10, como grades de letras.

'o' = contorno, 'i' = corpo, 'l' = brilho, '.' = transparente. As cores vêm do tema na hora de gerar
(gerar_ui.py), em variantes: clara (botões comuns), escura (sobre o ouro), perigo e ouro.
"""

ACOES = {
    "jogo": """
..........
.oooooooo.
oiiiiiiiio
oiloiiiloi
oioooiolii
oiloiiiloi
oiiiiiiiio
.oiioooiio
..oo...oo.
..........""",
    "hunts": """
...oooo...
..oiiiio..
.oio..oio.
.oi.ll.io.
.oi.lo.io.
.oio..oio.
..oiiiio..
...oooo...
..........
..........""",
    "rmt": """
...oooo...
....oo....
..oiiiio..
.oiillilo.
.oiliiiio.
.oiiliiio.
.oiillilo.
..oiiiio..
...oooo...
..........""",
    "config": """
...o..o...
..oiooio..
.oiiiiiio.
oiio..oiio
.oio.loio.
.oio..oio.
oiio..oiio
.oiiiiiio.
..oiooio..
...o..o...""",
    "todas": """
oooo.oooo.
oilo.oilo.
oiio.oiio.
oooo.oooo.
..........
oooo.oooo.
oilo.oilo.
oiio.oiio.
oooo.oooo.
..........""",
    "celulares": """
.oooo.oooo
.olio.olio
.oiio.oiio
.oiio.oiio
.oiio.oiio
.oiio.oiio
.oiio.oiio
.oioo.oioo
.oooo.oooo
..........""",
    "comecar": """
.oo.......
.olo......
.oilo.....
.oiilo....
.oiiilo...
.oiiio....
.oiio.....
.oio......
.oo.......
..........""",
    "parar": """
..........
.oooooooo.
.olllllio.
.oliiiiio.
.oliiiiio.
.oliiiiio.
.oliiiiio.
.oiiiiiio.
.oooooooo.
..........""",
    "pausar": """
..........
.ooo..ooo.
.oli..oli.
.oii..oii.
.oii..oii.
.oii..oii.
.oii..oii.
.oii..oii.
.ooo..ooo.
..........""",
    "mao": """
...o.o....
..olololo.
..oiioioio
..oiiiiiio
.ooiiiiiio
oiiiiiiio.
oiiiiiiio.
.oiiiiiio.
..oiiiio..
...oooo...""",
    "chave": """
..........
.oooo.....
olllio....
oioolioooo
oioolilili
olllio.o.o
.oooo.....
..........
..........
..........""",
    "recarregar": """
...ooooo..
..oiiiiio.
.oio...oo.
.oi..oooo.
.oi...oio.
.oi....o..
.oio...o..
..oiiiio..
...oooo...
..........""",
    "reiniciar": """
....oo....
.oo.oo.oo.
oio.oo.oio
oi..oo..io
oi..oo..io
oi......io
oio....oio
.oiiiiiio.
..oooooo..
..........""",
    "recolher": """
..........
.oo..oo...
.olo.olo..
..olo.olo.
...olo.olo
..olo.olo.
.olo.olo..
.oo..oo...
..........
..........""",
    "log": """
.oooooooo.
.olllllio.
.oiooooio.
.oiiiiiio.
.oiooooio.
.oiiiiiio.
.oioooiio.
.oiiiiiio.
.oooooooo.
..........""",
    "mais": """
...oooo...
...oiio...
ooooiioooo
oiiiiiiiio
oiiiiiiiio
ooooiioooo
...oiio...
...oooo...
..........
..........""",
    "menos": """
..........
..........
..........
oooooooooo
oiiiiiiiio
oiiiiiiiio
oooooooooo
..........
..........
..........""",
    "salvar": """
...oooo...
...oiio...
...oiio...
.oooiiooo.
..oiiiio..
...oiio...
o...oo...o
oo......oo
oiooooooio
oooooooooo""",
    "pasta": """
..........
oooo......
oiiioooooo
oiiiiiiiio
oooooooooo
oiiiiiiiio
oiiiiiiiio
oiiiiiiiio
oooooooooo
..........""",
    "copiar": """
oooooo....
oiiiio....
oi.oooooo.
oi.oiiiio.
oi.oiiiio.
ooooiiiio.
...oiiiio.
...oiiiio.
...oooooo.
..........""",
    "editar": """
.......oo.
......olio
.....oiio.
....oiio..
...oiio...
..oiio....
.oiio.....
oolo......
ooo.......
..........""",
    "excluir": """
oo......oo
oio....oio
.oio..oio.
..oiooio..
...oiio...
...oiio...
..oiooio..
.oio..oio.
oio....oio
oo......oo""",
}
ACOES["guia"] = """
..oooooo..
.oiiiiiio.
.oioooiio.
.ooo.oiio.
....oiio..
...oiio...
...oooo...
...oiio...
...oooo...
.........."""
ACOES["mostrar"] ="\n".join(linha[::-1] for linha in ACOES["recolher"].split("\n"))
# duas setas, uma para cada lado (inverter a conta da calculadora do Mercado)
ACOES["inverter"] = """
.....oo...
oooooolo..
oiiiiiiio.
oooooolo..
.....oo...
...oo.....
..oioooooo
.oiiiiiiio
..oioooooo
...oo....."""

# o aparelho da Pokédex (desenho próprio): a lente grande, uma luzinha e a tela
ACOES["pokedex"] = """
.oooooooo.
oiiiiiiiio
oiooooiiio
oiolloilio
oiolloiiio
oiooooiiio
oiiiiiiiio
oillllllio
oiiiiiiiio
.oooooooo."""

# Ícones de status (cada um pintado com a cor do status).
STATUS = {
    "FARMING": """
.....oo...
....oiio..
...oiliio.
..oiliiio.
.oiliiio..
.oiliio...
.oiiio....
oooo......
o.........
..........""",
    "BATALHA": """
o.......o.
olo...olo.
.olo.olo..
..olilo...
...oio....
..olilo...
.olo.olo..
ooo...ooo.
oo.....oo.
..........""",
    "AGUARDANDO": """
oooooooo..
.oiiiio...
..olio....
...oo.....
...oo.....
..oiio....
.oiliio...
oooooooo..
..........
..........""",
    "PAUSADO": """
..........
.ooo.ooo..
.oio.oio..
.oio.oio..
.oio.oio..
.oio.oio..
.ooo.ooo..
..........
..........
..........""",
    "MANUAL": """
...o.o....
..olololo.
..oiioioio
..oiiiiiio
.ooiiiiiio
oiiiiiiio.
oiiiiiiio.
.oiiiiiio.
..oooooo..
..........""",
    "ERRO": """
...oooo...
..oiiiio..
.oiiooiio.
.oiiooiio.
.oiiooiio.
.oiiiiiio.
.oiiooiio.
..oiiiio..
...oooo...
..........""",
    "SESSÃO EXPIRADA": """
.oooo.....
olllio....
oioolioooo
oioolilili
olllio.o.o
.oooo.....
..........
..........
..........
..........""",
    "OFFLINE": """
...ooo....
..oiio....
.oiio.....
.oio......
.oio......
.oiio...o.
..oiiooio.
...oiiio..
....ooo...
..........""",
}
STATUS["INICIANDO"] = STATUS["AGUARDANDO"]

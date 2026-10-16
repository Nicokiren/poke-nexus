"""Desenha, pixel a pixel, as molduras (9-slice) e as caixas de seleção do tema em assets/ui/.

Arte própria do PokeNexus, feita só com o QImage do PySide6 e as cores de app/tema.py. Rodar de novo
depois de mudar uma cor do tema:

    .venv\\Scripts\\python.exe ferramentas\\arte\\gerar_ui.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from PySide6.QtGui import QColor, QImage  # noqa: E402

from app.tema import T, UI_DIR  # noqa: E402

# Bordas do 9-slice (iguais às de tema.moldura): esquerda/direita 4, cima 4, baixo 6.
E, C, B = 4, 4, 6
L, A = E * 2 + 4, C + B + 4      # 12 × 14


def _img(w, h):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    return img


def moldura(corpo, luz, lado, sombra, contorno=T["filete"], apertado=False) -> QImage:
    """Contorno de 2 px, bisel claro em cima (2 px), lados de madeira (2 px) e o "degrau" escuro
    embaixo (4 px), como as molduras do jogo. Apertado: o bisel inverte e o degrau some."""
    img = _img(L, A)
    c = {k: QColor(v) for k, v in dict(corpo=corpo, luz=luz, lado=lado, sombra=sombra,
                                         contorno=contorno).items()}
    for y in range(A):
        for x in range(L):
            if x < 2 or x >= L - 2 or y < 2 or y >= A - 2:
                cor = c["contorno"]
            elif apertado:
                cor = c["sombra"] if y < 4 else (c["lado"] if x < 4 or x >= L - 4 else c["corpo"])
            elif y < 4:
                cor = c["luz"]
            elif y >= A - 6:
                cor = c["sombra"]
            elif x < 4 or x >= L - 4:
                cor = c["lado"]
            else:
                cor = c["corpo"]
            img.setPixelColor(x, y, cor)
    for x, y in ((0, 0), (L - 1, 0), (0, A - 1), (L - 1, A - 1)):   # cantos de pixel
        img.setPixelColor(x, y, QColor(0, 0, 0, 0))
    return img


def caixa(fundo, borda, marca=None, brilho=None) -> QImage:
    """Caixa de seleção 16×16; com `marca`, um "v" de pixel."""
    img = _img(16, 16)
    for y in range(1, 15):
        for x in range(1, 15):
            dentro = 2 < x < 13 and 2 < y < 13
            img.setPixelColor(x, y, QColor(fundo if dentro else borda))
    for x in range(1, 15):
        img.setPixelColor(x, 1, QColor(T["filete"]))
        img.setPixelColor(x, 14, QColor(T["filete"]))
        img.setPixelColor(1, x, QColor(T["filete"]))
        img.setPixelColor(14, x, QColor(T["filete"]))
    if brilho:
        for x in range(3, 13):
            img.setPixelColor(x, 3, QColor(brilho))
    if marca:
        for x, y in ((4, 8), (5, 9), (6, 10), (7, 9), (8, 8), (9, 7), (10, 6), (11, 5),
                     (4, 7), (5, 8), (6, 9), (7, 8), (8, 7), (9, 6), (10, 5), (11, 4)):
            img.setPixelColor(x, y, QColor(marca))
    return img


def bitmap(mapa: str, cores: dict, escala: int = 2) -> QImage:
    """Desenha uma grade de letras (ferramentas/arte/icones.py) ampliada sem suavização."""
    linhas = [l for l in mapa.strip("\n").split("\n")]
    assert all(len(l) == len(linhas[0]) for l in linhas), mapa
    img = _img(len(linhas[0]) * escala, len(linhas) * escala)
    for y, l in enumerate(linhas):
        for x, ch in enumerate(l):
            if ch == ".":
                continue
            cor = QColor(cores[ch])
            for dy in range(escala):
                for dx in range(escala):
                    img.setPixelColor(x * escala + dx, y * escala + dy, cor)
    return img


def icones():
    from icones import ACOES, STATUS
    t = T
    variantes = {   # nome: (corpo, brilho, contorno)
        "claro": (t["texto"], t["destaque_luz"], t["filete"]),
        "escuro": (t["sobre_destaque"], t["destaque_esc"], t["sobre_destaque"]),
        "perigo": (t["perigo_luz"], t["sobre_madeira"], t["filete"]),
        "ouro": (t["destaque"], t["destaque_luz"], t["filete"]),
        "apagado": (t["apagado"], t["apagado"], t["filete"]),
    }
    n = 0
    for nome, mapa in ACOES.items():
        for var, (corpo, brilho, contorno) in variantes.items():
            bitmap(mapa, {"o": contorno, "i": corpo, "l": brilho}).save(str(UI_DIR / f"ico_{nome}_{var}.png"))
            n += 1
    from app.tema import STATUS_COR
    for st, mapa in STATUS.items():
        nome = st.lower().replace("ã", "a").replace(" ", "_")
        bitmap(mapa, {"o": t["filete"], "i": STATUS_COR[st], "l": "#FFFFFF"}).save(str(UI_DIR / f"st_{nome}.png"))
        n += 1
    return n


def main():
    UI_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).parent))
    print(f"{icones()} ícones em {UI_DIR}")
    t = T
    pecas = {
        "moldura_painel": moldura(t["painel"], t["moldura_luz"], t["moldura"], t["moldura_esc"]),
        "moldura_painel_hover": moldura(t["painel_alto"], t["moldura_luz"], t["moldura"], t["moldura_esc"]),
        "moldura_selecionado": moldura(t["sel_fundo"], t["destaque_luz"], t["destaque"], t["destaque_esc"]),
        "moldura_desligado": moldura(t["trilho"], t["moldura_esc"], t["moldura_esc"], t["filete"]),
        "moldura_botao": moldura(t["painel_alto"], t["moldura_luz"], t["moldura"], t["moldura_esc"]),
        "moldura_botao_hover": moldura(t["botao_hover"], t["destaque_luz"], t["destaque_esc"], t["moldura_esc"]),
        "moldura_botao_apertado": moldura(t["painel"], t["moldura_luz"], t["moldura"], t["filete"], apertado=True),
        "moldura_botao_desligado": moldura(t["painel"], t["moldura_esc"], t["moldura_esc"], t["filete"]),
        "moldura_botao_ligado": moldura(t["sel_fundo"], t["destaque_luz"], t["destaque"], t["destaque_esc"],
                                        apertado=True),
        "moldura_botao_principal": moldura(t["destaque"], t["destaque_luz"], t["destaque"], t["destaque_esc"]),
        "moldura_botao_principal_hover": moldura(t["destaque_hover"], t["destaque_luz"], t["destaque_hover"],
                                                 t["destaque_esc"]),
        "moldura_botao_principal_apertado": moldura(t["destaque"], t["destaque_luz"], t["destaque"],
                                                    t["destaque_esc"], apertado=True),
        "moldura_botao_perigo": moldura(t["painel_alto"], t["perigo_luz"], t["perigo"], t["perigo_esc"]),
        "moldura_botao_perigo_hover": moldura(t["botao_hover"], t["perigo_luz"], t["perigo"], t["perigo_esc"]),
        "caixa_off": caixa(t["campo"], t["moldura_esc"]),
        "caixa_on": caixa(t["destaque"], t["destaque_esc"], marca=t["sobre_destaque"], brilho=t["destaque_luz"]),
        "caixa_desligada": caixa(t["trilho"], t["filete"]),
    }
    for nome, img in pecas.items():
        img.save(str(UI_DIR / f"{nome}.png"))
    print(f"{len(pecas)} peças em {UI_DIR}")


if __name__ == "__main__":
    main()

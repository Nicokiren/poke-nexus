"""Logo e ícone do programa (arte própria): o mascote "Broto", 16×16, ampliado só em fatores inteiros.

    .venv\\Scripts\\python.exe ferramentas\\arte\\gerar_marca.py

Gera assets/marca/logo_{1,2,3,4}x.png e assets/pokenexus.ico (16, 32, 48 e 256 px, cada tamanho
desenhado em pixels inteiros, para o ícone não ficar borrado na barra de tarefas).
"""
import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402

from app.config import ASSETS_DIR  # noqa: E402
from gerar_ui import bitmap  # noqa: E402

# Broto: uma criatura-broto original (verde, com uma folha na cabeça).
BROTO = """
.......oo.......
......ohgo......
.....ohgGo......
......oGo.......
....oooGooo.....
...ogggggggo....
..ogghggggggo...
.oghgggggggggo..
.oggwkggggwkgo..
.ogggwgggggwgo..
.oggggppgggggo..
.ogggggggggggo..
..oGggggggggGo..
...oGGGGGGGGo...
....oooooooo....
................"""
CORES = {"o": "#2B0C14", "g": "#5DB860", "G": "#3E8A44", "h": "#9BE07A", "w": "#FFFFFF", "k": "#1A1016",
         "p": "#F2A6C8"}


def png(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def ico(imagens: list[QImage]) -> bytes:
    """Arquivo .ico com várias imagens PNG (formato aceito pelo Windows desde o Vista)."""
    dados = [png(i) for i in imagens]
    cab = struct.pack("<HHH", 0, 1, len(imagens))
    pos = 6 + 16 * len(imagens)
    dirs = b""
    for img, d in zip(imagens, dados):
        w, h = img.width(), img.height()
        dirs += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(d), pos)
        pos += len(d)
    return cab + dirs + b"".join(dados)


def main():
    marca = ASSETS_DIR / "marca"
    marca.mkdir(parents=True, exist_ok=True)
    for f in (1, 2, 3, 4):
        bitmap(BROTO, CORES, f).save(str(marca / f"logo_{f}x.png"))
    # O ícone do programa (assets/pokenexus.ico) é a Poké Ball: escolha do usuário. Para gerar um .ico
    # com o Broto: ico([bitmap(BROTO, CORES, f) for f in (1, 2, 3, 16)]).
    print("logo em", marca)


if __name__ == "__main__":
    main()

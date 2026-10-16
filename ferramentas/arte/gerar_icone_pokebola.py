"""Ícone do programa = a Poké Ball (escolha do usuário), com TODOS os tamanhos que o Windows usa.

O .ico antigo só tinha a imagem de 256 px; a pasta e a barra de tarefas usam 16/24/32/48 px. Aqui:
- 24 e 48 px: a sprite de pixel (assets/sprites/ui/poke_ball.png, 24×24) em 1× e 2×, nítida;
- 16 e 32 px: reduzidas da imagem de 256 px do ícone antigo;
- 256 px: a do ícone antigo.

    .venv\\Scripts\\python.exe ferramentas\\arte\\gerar_icone_pokebola.py <ico_antigo_256.ico>
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QImage, QImageReader  # noqa: E402

from app.config import ASSETS_DIR  # noqa: E402
from gerar_marca import ico  # noqa: E402


def main(origem: Path):
    r = QImageReader(str(origem))
    grande = r.read().convertToFormat(QImage.Format_ARGB32)
    assert not grande.isNull() and grande.width() == 256, (origem, grande.size())
    sprite = QImage(str(ASSETS_DIR / "sprites" / "ui" / "poke_ball.png")).convertToFormat(QImage.Format_ARGB32)
    reduzir = lambda n: grande.scaled(n, n, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    ampliar = lambda f: sprite.scaled(sprite.width() * f, sprite.height() * f, Qt.KeepAspectRatio,
                                      Qt.FastTransformation)
    imagens = [reduzir(16), ampliar(1), reduzir(32), ampliar(2), grande]       # 16, 24, 32, 48, 256
    (ASSETS_DIR / "pokenexus.ico").write_bytes(ico(imagens))
    print("pokenexus.ico:", [f"{i.width()}x{i.height()}" for i in imagens])


if __name__ == "__main__":
    main(Path(sys.argv[1]))

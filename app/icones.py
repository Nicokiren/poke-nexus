"""Ícones de pixel do PokeNexus (arte própria, gerada por ferramentas/arte/gerar_ui.py em assets/ui).

Variantes: "claro" (botões comuns), "escuro" (sobre o botão dourado), "perigo", "ouro" e "apagado".
"""
from functools import lru_cache

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap

from app.tema import UI_DIR

TAM = QSize(20, 20)          # os desenhos são 10×10 ampliados 2×


@lru_cache(maxsize=None)
def icone(nome: str, variante: str = "claro") -> QIcon:
    ic = QIcon()
    p = UI_DIR / f"ico_{nome}_{variante}.png"
    if p.is_file():
        ic.addPixmap(QPixmap(str(p)), QIcon.Normal)
        apagado = UI_DIR / f"ico_{nome}_apagado.png"
        if apagado.is_file():
            ic.addPixmap(QPixmap(str(apagado)), QIcon.Disabled)
    return ic


def status_png(status: str) -> str:
    """Caminho do ícone de um status (para usar em texto rico: <img src=...>)."""
    nome = status.lower().replace("ã", "a").replace(" ", "_")
    p = UI_DIR / f"st_{nome}.png"
    return (p if p.is_file() else UI_DIR / "st_offline.png").as_posix()


def por_nome_do_botao(obj: str | None) -> str:
    """Variante certa do ícone para o estilo do botão."""
    return {"primary": "escuro", "danger": "perigo"}.get(obj or "", "claro")

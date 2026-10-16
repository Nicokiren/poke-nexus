"""Mercado 2.0: a "lista de compras" de UMA conta (profiles/conta_XX/rmt_compras.json).

Cada item da lista: o item do jogo, a moeda, o preço máximo por unidade (obrigatório) e um interruptor
Ligado/Desligado. Ligado, o PokeNexus compra o item sempre que houver anúncio até esse preço, sem fim,
a não ser que um limite opcional (unidades, gasto total, gasto por dia) diga para parar.

As regras antigas (rmt_regras.json) são convertidas na primeira vez: as de compra viram itens da
lista, DESLIGADOS; as de venda ficam guardadas em "vendas_guardadas", desligadas (a venda não está
nesta versão). O arquivo antigo não é apagado.
"""
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from rmt.regras import INTERVALO_MIN_S, MOEDAS, NOME_MOEDA


def hoje() -> str:
    return time.strftime("%Y-%m-%d")


@dataclass
class ItemCompra:
    item_id: int
    item_nome: str
    moeda: str                        # gold | orb
    preco_max: int                    # por unidade (obrigatório, >= 1)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    ligado: bool = False
    # limites opcionais (0 = sem esse limite)
    lim_unidades: int = 0             # parar depois de comprar X unidades (no total)
    lim_gasto: int = 0                # parar depois de gastar X (no total, na moeda do item)
    lim_dia: int = 0                  # no máximo X por dia (na moeda do item)
    # contadores (só compras de verdade)
    comprado_total: int = 0
    gasto_total: int = 0
    dia: str = ""
    comprado_hoje: int = 0
    gasto_hoje: int = 0
    ultima_compra: dict | None = None  # {"quando", "qtd", "preco", "total"}
    desligado_por: str = ""           # por que desligou sozinho (vazio = foi a pessoa)
    criado_em: float = field(default_factory=time.time)

    @property
    def sem_limite(self) -> bool:
        return not (self.lim_unidades or self.lim_gasto or self.lim_dia)

    def virar_dia(self):
        """Zera os contadores de hoje quando o dia muda."""
        d = hoje()
        if self.dia != d:
            self.dia, self.comprado_hoje, self.gasto_hoje = d, 0, 0

    def registrar_compra(self, qtd: int, preco: int, total: int):
        self.virar_dia()
        self.comprado_total += qtd
        self.gasto_total += total
        self.comprado_hoje += qtd
        self.gasto_hoje += total
        self.ultima_compra = {"quando": time.time(), "qtd": qtd, "preco": preco, "total": total}

    def resumo(self) -> str:
        return f"{self.item_nome} até {self.preco_max} {NOME_MOEDA[self.moeda]} cada"

    def limites_txt(self) -> str:
        if self.sem_limite:
            return "Sem limite: compra sempre que achar até esse preço."
        m = NOME_MOEDA[self.moeda]
        partes = []
        if self.lim_unidades:
            partes.append(f"até {self.lim_unidades} unidades")
        if self.lim_gasto:
            partes.append(f"até gastar {self.lim_gasto} {m}")
        if self.lim_dia:
            partes.append(f"no máximo {self.lim_dia} {m} por dia")
        return "Limites: " + ", ".join(partes) + "."


@dataclass
class ConfigMercado:
    """Valem para todos os itens da conta."""
    intervalo_s: int = 60             # olha a vitrine de cada item a cada X s (rmt/rotina.py limita)
    queda_max_pct: int = 30           # não usado desde a compra na liberação (fica para compatibilidade)
    bloquear_proprias: bool = True    # nunca comprar anúncio das outras contas do PokeNexus


class ErroItem(ValueError):
    def __init__(self, campo: str, msg: str):
        super().__init__(msg)
        self.campo = campo


def validar_item(i: ItemCompra) -> None:
    if not isinstance(i.item_id, int) or i.item_id <= 0 or not i.item_nome:
        raise ErroItem("item", "escolha o item na lista")
    if i.moeda not in MOEDAS:
        raise ErroItem("moeda", "moeda inválida")
    if not isinstance(i.preco_max, int) or i.preco_max < 1:
        raise ErroItem("preco_max", "diga o preço máximo por unidade (1 ou mais)")
    for k in ("lim_unidades", "lim_gasto", "lim_dia"):
        v = getattr(i, k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise ErroItem(k, "use um número inteiro, 0 = sem limite")


class Lista:
    """Lista de compras + ajustes + extrato de UMA conta."""

    def __init__(self, profile_dir: Path):
        self.dir = profile_dir
        self.arq = profile_dir / "rmt_compras.json"
        self.arq_antigo = profile_dir / "rmt_regras.json"
        self.arq_extrato = profile_dir / "rmt_extrato.jsonl"
        self.config = ConfigMercado()
        self.itens: list[ItemCompra] = []
        self.vendas_guardadas: list[dict] = []
        self.carregar()

    def carregar(self):
        if not self.arq.exists() and self.arq_antigo.exists():
            self._migrar()
            return
        try:
            d = json.loads(self.arq.read_text(encoding="utf-8"))
        except Exception:
            return
        self.config = ConfigMercado(**{k: v for k, v in (d.get("config") or {}).items()
                                       if k in ConfigMercado.__dataclass_fields__})
        self.itens = []
        for x in d.get("itens") or []:
            try:
                self.itens.append(ItemCompra(**{k: v for k, v in x.items() if k in ItemCompra.__dataclass_fields__}))
            except TypeError:
                continue
        self.vendas_guardadas = list(d.get("vendas_guardadas") or [])

    def _migrar(self):
        """rmt_regras.json (Mercado antigo) -> lista de compras. Tudo entra DESLIGADO."""
        try:
            d = json.loads(self.arq_antigo.read_text(encoding="utf-8"))
        except Exception:
            return
        cfg = d.get("config") or {}
        self.config = ConfigMercado(intervalo_s=max(INTERVALO_MIN_S, int(cfg.get("intervalo_s", 60))),
                                    queda_max_pct=int(cfg.get("queda_max_pct", 30)),
                                    bloquear_proprias=bool(cfg.get("bloquear_proprias", True)))
        for r in d.get("regras") or []:
            if r.get("acao") != "comprar":
                self.vendas_guardadas.append({**r, "ligada": False})
                continue
            moeda = r.get("moeda", "gold")
            dia = int(cfg.get("gasto_dia_orb" if moeda == "orb" else "gasto_dia_gold") or 0)
            try:
                self.itens.append(ItemCompra(
                    item_id=int(r["item_id"]), item_nome=str(r["item_nome"]), moeda=moeda,
                    preco_max=max(1, int(r.get("preco_max") or 1)), ligado=False,
                    lim_unidades=int(r.get("qtd_total") or 0), lim_gasto=int(r.get("gasto_max") or 0), lim_dia=dia,
                    comprado_total=int(r.get("comprado") or 0)))
            except (KeyError, ValueError, TypeError):
                continue
        self.salvar()

    def salvar(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.arq.with_suffix(".tmp")
        tmp.write_text(json.dumps({"versao": 2, "config": asdict(self.config),
                                   "itens": [asdict(i) for i in self.itens],
                                   "vendas_guardadas": self.vendas_guardadas}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self.arq)

    def item(self, iid: str) -> ItemCompra | None:
        return next((i for i in self.itens if i.id == iid), None)

    def registrar(self, **linha):
        """Uma linha no extrato da conta (só compras de verdade)."""
        linha = {"quando": time.time(), **linha}
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.arq_extrato, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")

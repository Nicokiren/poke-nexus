"""Regras do RMT de UMA conta, salvas no perfil dela (profiles/conta_XX/rmt_regras.json).

Toda regra nova nasce em SIMULAÇÃO: mostra o que faria, sem comprar nem anunciar nada. Sair da
simulação é uma escolha explícita do usuário, confirmada na tela com o resumo da regra.
"""
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

ACOES = ("comprar", "vender")
MOEDAS = ("gold", "orb")                  # os ids que o jogo usa: Ouro (Coins) e Gema
NOME_MOEDA = {"gold": "ouro", "orb": "gema"}
MODOS_VENDA = ("fixo", "acompanhar")
INTERVALO_MIN_S = 0                       # 0 = sem espera extra (ainda é uma ação por vez, por volta do laço)


class ErroRegra(ValueError):
    def __init__(self, campo: str, msg: str):
        super().__init__(msg)
        self.campo = campo


@dataclass
class Regra:
    item_id: int
    item_nome: str
    acao: str                     # comprar | vender
    moeda: str                    # gold | orb
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    ligada: bool = False
    simulacao: bool = True
    # comprar
    preco_max: int = 0            # por unidade
    qtd_total: int = 0            # meta de compra desta regra
    qtd_por_compra: int = 1
    gasto_max: int = 0            # teto desta regra (na moeda dela); 0 = só o limite do dia
    comprado: int = 0             # progresso da meta (só compras reais contam)
    # vender
    modo: str = "fixo"            # fixo | acompanhar
    preco: int = 0                # fixo: o preço; acompanhar: o preço quando ninguém mais vende
    piso: int = 0                 # acompanhar: nunca abaixo disso
    passo: int = 1                # acompanhar: quanto abaixo do menor preço dos outros
    qtd_anunciar: int = 1
    manter_estoque: int = 0       # nunca vender abaixo disso
    dias: int = 0                 # dias do anúncio (0 = o padrão que o jogo oferecer)
    ajustes_max_hora: int = 4
    criada_em: float = field(default_factory=time.time)

    def resumo(self) -> str:
        m = NOME_MOEDA[self.moeda]
        if self.acao == "comprar":
            return (f"comprar até {self.qtd_total}× {self.item_nome} por no máximo {self.preco_max} {m}/un"
                    f" ({self.qtd_por_compra} por vez" + (f", gasto máximo {self.gasto_max} {m}" if self.gasto_max else "")
                    + ")")
        if self.modo == "fixo":
            return f"vender {self.qtd_anunciar}× {self.item_nome} por {self.preco} {m}/un (manter {self.manter_estoque})"
        return (f"vender {self.qtd_anunciar}× {self.item_nome} {self.passo} abaixo do menor preço, nunca abaixo de "
                f"{self.piso} {m}/un (manter {self.manter_estoque})")


@dataclass
class ConfigRmt:
    """Limites da conta inteira (valem para todas as regras dela)."""
    gasto_dia_gold: int = 0       # 0 = a conta não compra nada com essa moeda
    gasto_dia_orb: int = 0
    intervalo_s: int = 60         # entre duas ações (mínimo INTERVALO_MIN_S)
    queda_max_pct: int = 30       # o menor preço caiu mais que isso de uma vez = pausa e avisa
    bloquear_proprias: bool = True  # nunca comprar anúncio das outras contas do PokeNexus

    def gasto_dia(self, moeda: str) -> int:
        return self.gasto_dia_orb if moeda == "orb" else self.gasto_dia_gold


def validar(r: Regra, preco_min: dict | None = None) -> None:
    """preco_min: {"gold": n, "orb": n} do jogo (o mínimo que o mercado aceita)."""
    pm = preco_min or {"gold": 1, "orb": 1}
    if r.acao not in ACOES:
        raise ErroRegra("acao", "ação inválida")
    if r.moeda not in MOEDAS:
        raise ErroRegra("moeda", "moeda inválida")
    if not isinstance(r.item_id, int) or r.item_id <= 0 or not r.item_nome:
        raise ErroRegra("item", "escolha o item na lista")
    inteiros = ("preco_max", "qtd_total", "qtd_por_compra", "gasto_max", "preco", "piso", "passo",
                "qtd_anunciar", "manter_estoque", "dias", "ajustes_max_hora")
    for k in inteiros:
        v = getattr(r, k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise ErroRegra(k, "precisa ser um número inteiro, zero ou maior")
    if r.acao == "comprar":
        if r.preco_max < 1:
            raise ErroRegra("preco_max", "diga o preço máximo por unidade")
        if r.qtd_total < 1 or r.qtd_por_compra < 1:
            raise ErroRegra("qtd_total", "diga quantas unidades comprar")
        if r.qtd_por_compra > r.qtd_total:
            raise ErroRegra("qtd_por_compra", "não pode passar da quantidade total")
    else:
        if r.modo not in MODOS_VENDA:
            raise ErroRegra("modo", "modo de venda inválido")
        alvo = r.preco if r.modo == "fixo" else r.piso
        nome = "preco" if r.modo == "fixo" else "piso"
        if alvo < pm[r.moeda]:
            raise ErroRegra(nome, f"o mercado só aceita a partir de {pm[r.moeda]} por unidade nessa moeda")
        if r.modo == "acompanhar" and r.passo < 1:
            raise ErroRegra("passo", "use pelo menos 1")
        if r.modo == "acompanhar" and r.preco < r.piso:
            raise ErroRegra("preco", "o preço sem concorrência não pode ser menor que o piso")
        if r.qtd_anunciar < 1:
            raise ErroRegra("qtd_anunciar", "diga quantas unidades anunciar")
        if r.ajustes_max_hora < 1:
            raise ErroRegra("ajustes_max_hora", "use pelo menos 1 ajuste por hora")


class Livro:
    """Regras + limites + extrato de UMA conta (arquivos no perfil dela)."""

    def __init__(self, profile_dir: Path):
        self.dir = profile_dir
        self.arq = profile_dir / "rmt_regras.json"
        self.arq_extrato = profile_dir / "rmt_extrato.jsonl"
        self.config = ConfigRmt()
        self.regras: list[Regra] = []
        self.carregar()

    def carregar(self):
        try:
            d = json.loads(self.arq.read_text(encoding="utf-8"))
        except Exception:
            return
        self.config = ConfigRmt(**{k: v for k, v in (d.get("config") or {}).items()
                                   if k in ConfigRmt.__dataclass_fields__})
        self.regras = []
        for x in d.get("regras") or []:
            try:
                self.regras.append(Regra(**{k: v for k, v in x.items() if k in Regra.__dataclass_fields__}))
            except TypeError:
                continue

    def salvar(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.arq.with_suffix(".tmp")
        tmp.write_text(json.dumps({"versao": 1, "config": asdict(self.config),
                                   "regras": [asdict(r) for r in self.regras]}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self.arq)

    def regra(self, rid: str) -> Regra | None:
        return next((r for r in self.regras if r.id == rid), None)

    # ------------------------------------------------------------ extrato
    def registrar(self, **linha):
        linha = {"quando": time.time(), **linha}
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.arq_extrato, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return linha

    def extrato(self, desde: float = 0.0) -> list[dict]:
        try:
            linhas = self.arq_extrato.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for l in linhas:
            try:
                x = json.loads(l)
            except ValueError:
                continue
            if x.get("quando", 0) >= desde:
                out.append(x)
        return out

    def gasto_hoje(self, moeda: str) -> int:
        """Soma das compras REAIS de hoje (dia local) nessa moeda."""
        inicio = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
        return sum(int(x.get("total") or 0) for x in self.extrato(inicio)
                   if x.get("acao") == "comprou" and x.get("moeda") == moeda)

"""Comissão do Mercado da Comunidade: a mesma conta de `shared/taxa-mercado.mjs` do jogo.

Os números (faixas da gema, alíquota plana, taxa do ouro) não ficam fixos aqui: chegam da versão
no ar — as constantes do módulo, lidas pela ponte, e `economia.taxaMercadoGoldPct` do welcome —
e o teste de equivalência roda as funções do próprio módulo contra estas. Os valores abaixo são
só a rede de baixo enquanto a ponte não respondeu (e o RMT não age sem ela, ver `Taxas.pronta`).
"""
import math
from dataclasses import dataclass, field

INF = math.inf


@dataclass
class Taxas:
    faixas_orb: list = field(default_factory=lambda: [(500, 1300), (5000, 1000), (INF, 750)])  # (até, bp)
    taxa_orb_plana: float = 0.15
    taxa_gold: float = 0.15
    preco_min_orb: int = 2
    preco_min_gold: int = 2
    pronta: bool = False          # True só depois de ler os números do jogo no ar
    versao: str | None = None

    @classmethod
    def do_jogo(cls, modulo: dict, economia: dict | None, versao=None) -> "Taxas":
        """modulo: {FAIXAS_ORB: [{ate, bp}], TAXA_ORB_PLANA, TAXA_GOLD, PRECO_MIN_ORB, PRECO_MIN_GOLD}
        (de taxa-mercado.mjs); economia: estado.economia do welcome (taxa do ouro que vale)."""
        faixas = [((INF if f.get("ate") in (None, "Infinity") else float(f["ate"])), int(f["bp"]))
                  for f in modulo["FAIXAS_ORB"]]
        gold = modulo["TAXA_GOLD"]
        pct = (economia or {}).get("taxaMercadoGoldPct")
        if isinstance(pct, (int, float)) and math.isfinite(pct):
            gold = pct / 100
        return cls(faixas_orb=faixas, taxa_orb_plana=float(modulo["TAXA_ORB_PLANA"]), taxa_gold=float(gold),
                   preco_min_orb=int(modulo["PRECO_MIN_ORB"]), preco_min_gold=int(modulo["PRECO_MIN_GOLD"]),
                   pronta=True, versao=versao)

    # ------------------------------------------------------------ as contas do jogo
    @staticmethod
    def _faixa_por_tipo(tipo) -> bool:
        return tipo == "pokemon"

    def taxa_orb(self, total, tipo="item") -> int:
        """taxaOrbDaVenda: comissão em gemas inteiras (arredonda para cima uma vez, no fim)."""
        t = math.floor(float(total or 0))
        if t <= 0:
            return 0
        if not self._faixa_por_tipo(tipo):
            return min(t, math.ceil((t * round(self.taxa_orb_plana * 10_000)) / 10_000))
        piso = 0
        bp = 0
        for ate, faixa_bp in self.faixas_orb:
            teto = min(t, ate)
            if teto <= piso:
                break
            bp += (teto - piso) * faixa_bp
            piso = teto
        return min(t, math.ceil(bp / 10_000))

    def liquido(self, preco: int, qtd: int, moeda: str, tipo="item") -> int:
        """totalLiquidoMercado: o que o vendedor recebe por `qtd` a `preco` (por unidade)."""
        total = qtd * preco
        if moeda == "orb":
            t = math.floor(total)
            return 0 if t <= 0 else t - self.taxa_orb(t, tipo)
        return math.floor(total * (1 - self.taxa_gold))

    def preco_min(self, moeda: str) -> int:
        return self.preco_min_orb if moeda == "orb" else self.preco_min_gold

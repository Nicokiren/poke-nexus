"""Hunt Analyzer de UMA conta: junta os dados da conta, a ponte com o jogo e o motor.

Cada conta tem o seu analisador (pokémon, bônus, hunts liberadas, opções e medição próprios).
O cálculo só roda quando muda algo que entra nele (a "assinatura") e fora da thread da tela.
"""
import asyncio
import json
import math
import time
from pathlib import Path

from hunts import calculator
from hunts.measure import HuntMeasure, chave_do_pokemon

ORDENS = ("xp", "ouro", "kills", "risco")
PREFS_PADRAO = {"ordem": "xp", "so_liberadas": True, "com_pocao": True}


def nivel_de_risco(l: dict) -> tuple[str, str]:
    """(nível, texto) do risco, pelas mesmas faixas do /hunt: morte em 1 golpe ou ≥ 0,5
    morte/h = Alto; pior golpe ≥ 50% do HP = Médio; senão Baixo."""
    if l.get("inviavel"):
        return "alto", "não derrota o selvagem"
    pct = math.floor(l["hit_pct"] * 100 + 0.5)
    if l["um_hit"]:
        return "alto", "Alto — pode morrer em 1 golpe"
    if l["mortes_h"] >= 0.5:
        return "alto", f"Alto — ~{l['mortes_h']:.1f} mortes/h".replace(".", ",")
    if pct >= 50:
        return "medio", f"Médio — pior golpe tira {pct}% do HP"
    return "baixo", f"Baixo — pior golpe tira {pct}% do HP"


def _chave_ordem(ordem):
    if ordem == "ouro":
        return lambda l: (-l["ouro_h"], l["nivel"])
    if ordem == "kills":
        return lambda l: (-l["kph"], l["nivel"])
    if ordem == "risco":
        # menos arriscada primeiro; empate → mais XP
        return lambda l: (l["inviavel"], l["um_hit"], l["mortes_h"], round(l["hit_pct"], 3), -l["xp_pokemon_h"])
    return lambda l: (-l["xp_pokemon_h"], l["nivel"])


def recomendar_hunt_automatica(resultado: dict | None, atual_slug: str | None,
                               ganho_minimo_pct: float = 10) -> dict | None:
    """Escolhe uma melhora conservadora para o farm automático.

    Só considera áreas liberadas, viáveis e sem risco alto. Uma hunt atual segura
    só é trocada quando a estimativa de XP/h melhora pelo percentual configurado;
    isso evita ficar saltando entre áreas por pequenas oscilações da medição.
    """
    if not resultado:
        return None
    candidatas = [l for l in resultado.get("todas", [])
                  if l.get("liberada") and not l.get("inviavel")
                  and nivel_de_risco(l)[0] != "alto" and float(l.get("xp_pokemon_h") or 0) > 0]
    if not candidatas:
        return None
    melhor = max(candidatas, key=lambda l: (float(l.get("xp_pokemon_h") or 0), -int(l.get("nivel") or 0)))
    if melhor.get("slug") == atual_slug:
        return None
    atual = next((l for l in resultado.get("todas", []) if l.get("slug") == atual_slug), None)
    if atual and not atual.get("inviavel") and nivel_de_risco(atual)[0] != "alto":
        xp_atual = float(atual.get("xp_pokemon_h") or 0)
        minimo = xp_atual * (1 + max(0, float(ganho_minimo_pct)) / 100)
        if xp_atual > 0 and float(melhor.get("xp_pokemon_h") or 0) < minimo:
            return None
    return melhor


class HuntAnalyzer:
    def __init__(self, profile_dir: Path, data):
        self.data = data                       # GameData compartilhado (só catálogo do jogo)
        self._prefs_file = profile_dir / "hunt_prefs.json"
        self.prefs = {**PREFS_PADRAO, **self._ler_prefs()}
        self.measure = HuntMeasure(profile_dir / "hunt_medicoes.json")
        self.result: dict | None = None        # última análise (sem ordenação de tela)
        self.version = 0                       # muda quando há resultado novo para a tela
        self.status = "aguardando a conta conectar"
        self.busy = False
        self._sig = None
        # A geometria medida muda a cada onda cheia; ela entra no cálculo no máximo a cada 5 min.
        self._medida_vista = self.measure.versao
        self._medida_em = 0.0

    # ------------------------------------------------------------ opções
    def _ler_prefs(self) -> dict:
        try:
            p = json.loads(self._prefs_file.read_text(encoding="utf-8"))
            return {k: v for k, v in p.items() if k in PREFS_PADRAO}
        except Exception:
            return {}

    def set_pref(self, chave: str, valor):
        if chave not in PREFS_PADRAO or (chave == "ordem" and valor not in ORDENS):
            return
        self.prefs[chave] = valor
        try:
            self._prefs_file.parent.mkdir(parents=True, exist_ok=True)
            self._prefs_file.write_text(json.dumps(self.prefs), encoding="utf-8")
        except OSError:
            pass
        self.version += 1                      # ordenação/filtro mudam a tela na hora

    # ------------------------------------------------------------ assinatura
    @staticmethod
    def _sig_bonus(eu: dict) -> str:
        loja = eu.get("loja") or {}
        partes = {k: eu.get(k) for k in ("level", "guildBonusPct", "twitch", "kick", "evento")}
        partes["guild"] = (eu.get("guild") or {}).get("boostAte")
        partes["loja"] = {k: loja.get(k) for k in ("vipAte", "boosts", "atrasados")}
        return json.dumps(partes, sort_keys=True, default=str)

    def _assinatura(self, game, pk, catalogo) -> tuple:
        if self.measure.versao != self._medida_vista and time.monotonic() - self._medida_em > 300:
            self._medida_vista, self._medida_em = self.measure.versao, time.monotonic()
        return (
            pk.get("id"), pk.get("speciesId"), pk.get("level"), pk.get("tmElemental"),
            str(pk.get("tmAoe")), json.dumps(pk.get("stats"), sort_keys=True), json.dumps(pk.get("ivs"), sort_keys=True),
            pk.get("maxHp"), self._sig_bonus(game.eu), game.welcome_seq, catalogo.get("versao"),
            self.prefs["com_pocao"], self._medida_vista,
            int(time.time() // 300),           # bônus que vencem com o tempo: no máximo 5 min velhos
        )

    # ------------------------------------------------------------ análise
    async def refresh(self, game, force=False):
        """Recalcula se algo que entra no cálculo mudou. Chamado pela tela enquanto a aba
        Hunts desta conta está aberta."""
        if self.busy:
            return
        if game is None or not game.welcomed:
            self.status = "a conta precisa estar iniciada e conectada ao jogo"
            return
        pk = game.active_pokemon
        if not pk:
            self.status = "coloque um pokémon em campo no jogo"
            return
        if not pk.get("stats"):
            self.status = "o jogo não mandou os stats deste pokémon"
            return
        self.busy = True
        try:
            catalogo = await self.data.garantir()
            sig = self._assinatura(game, pk, catalogo)
            if sig == self._sig and not force:
                return
            self.status = "calculando…"
            w = game.welcome_data
            hunts = w.get("hunts") or []
            eu = game.eu
            payload = {
                "hunts": hunts, "tabelaTipos": w.get("tabelaTipos") or {},
                "ampliacaoHunt": w.get("ampliacaoHunt"), "tiposBoost": w.get("tiposBoost") or [],
                "eu": {k: eu.get(k) for k in ("loja", "guildBonusPct", "guild", "level")},
                "pk": {k: pk.get(k) for k in ("speciesId", "level", "ivs", "tmElemental")},
            }
            prep = await self.data.preparar(payload)
            especie = prep.get("especie") or catalogo["especies"].get(pk.get("speciesId"))
            if not especie or prep.get("golpes") is None:
                self.status = f"espécie {pk.get('speciesId')} não está no catálogo do jogo"
                return
            ef_tab = prep["ef"]

            def ef(a, d1, d2):
                return ef_tab.get(f"{a}|{d1}|{d2 or ''}", 1)

            preco = dict(catalogo["precoItem"])
            for i in w.get("itensNossos") or []:
                if i.get("name") and float(i.get("npcPrice") or 0) > 0:
                    preco[i["name"]] = float(i["npcPrice"])
            chave_pk = chave_do_pokemon(pk)
            ctx = {
                "especies": catalogo["especies"], "hunts": hunts,
                "consts": {"multHpSelvagem": w.get("multHpSelvagem"), "multDanoSelvagem": w.get("multDanoSelvagem")},
                "ef": ef, "recompensa": prep["recompensa"], "preco_item": preco, "eu": eu,
                "geo": self.measure.da_hunt,
                "ritmo": (lambda slug: self.measure.ritmo_medido(slug, chave_pk)) if chave_pk else None,
                "bonus_base": prep["bonusBase"], "tipos_boost": w.get("tiposBoost") or [],
                "vip_mult": catalogo["vipMultXp"],
            }
            opcoes = {"com_pocao": self.prefs["com_pocao"], "so_liberadas": False, "ordem": "xp"}
            loop = asyncio.get_running_loop()
            r = await loop.run_in_executor(None, calculator.analisar, pk, especie, prep["golpes"], ctx, opcoes)
            r["versao_jogo"] = catalogo.get("versao")
            r["hunts_medidas"] = self.measure.hunts_medidas()
            self.result = r
            self._sig = sig
            self.version += 1
            self.status = "ok"
        except Exception as e:
            self.status = f"não consegui calcular: {str(e).splitlines()[0][:160] if str(e) else type(e).__name__}"
        finally:
            self.busy = False

    # ------------------------------------------------------------ para a tela
    def view(self, game) -> dict:
        """O que a tela mostra: filtro e ordenação das opções, hunt atual e desempenho real."""
        r = self.result
        out = {"status": self.status, "prefs": dict(self.prefs), "version": self.version, "result": None}
        if not r:
            return out
        linhas = list(r["todas"])
        if self.prefs["so_liberadas"]:
            linhas = [l for l in linhas if l["liberada"]]
        linhas.sort(key=_chave_ordem(self.prefs["ordem"]))
        atual = game.hunt_slug if game else None
        real = self.measure.ritmo_sessao()
        out["result"] = {
            **{k: r[k] for k in ("pokemon", "especie", "golpes", "aoe", "bonus_xp", "total", "ms",
                                 "versao_jogo", "hunts_medidas")},
            "linhas": linhas,
            "melhor": next((l for l in sorted(linhas, key=_chave_ordem("xp" if self.prefs["ordem"] == "risco"
                                                                      else self.prefs["ordem"]))
                            if not l["inviavel"]), None),
            "atual": next((l for l in r["todas"] if l["slug"] == atual), None),
            "atual_slug": atual,
            "real": real if real and real["slug"] == atual else None,
        }
        return out

"""Geometria das hunts e ritmo real, medidos enquanto UMA conta caça.

Reprodução da medição da extensão "/hunt for PokeIdle" (src/geo.js):

GEOMETRIA (entra no cálculo): no instante em que uma ONDA CHEIA nasce, guarda a distância (em
tiles) do pokémon até cada selvagem novo — a "fila de chegada" que o motor usa nos abates/h. Só
conta onda cheia (pelo menos 80% dos pontos de spawn da hunt nascendo juntos).

RITMO (só referência): os abates/h de verdade por hunt e por pokémon. NÃO muda o ranking.

Os dados vêm das mensagens `campo.init` / `campo` do WebSocket do jogo (só leitura) e ficam
no perfil da conta (profiles/conta_XX/hunt_medicoes.json) — nunca misturados entre contas.
"""
import json
import math
import time
from pathlib import Path

MAX_AMOSTRAS = 6
JANELA_ONDA_S = 4.0       # selvagens que nascem dentro disto são a mesma onda
FRACAO_CHEIA = 0.8
MIN_ONDA = 6
MAX_SPAWNS = 16
MIN_RITMO_S = 600         # ritmo medido só vale com 10+ min acumulados


def _nao_selvagem(m: dict) -> bool:
    """Boneco de XP Share, pet em treino, NPCs e treinadores não são selvagens."""
    return bool(m.get("bn") or "ti" in m or m.get("cura") or m.get("tm") or m.get("depot") or m.get("tr"))


def chave_do_pokemon(pk: dict | None) -> str | None:
    """O ritmo é guardado por pokémon e por com/sem disco AoE."""
    if not pk or not pk.get("id"):
        return None
    aoe = pk.get("tmAoe", pk.get("tm_aoe"))
    return f"{pk['id']}{':aoe' if aoe is True or aoe == 'true' or aoe == 1 else ''}"


class HuntMeasure:
    def __init__(self, arquivo: Path):
        self.arquivo = arquivo
        self.banco = self._ler()
        self.pontos: dict[str, int] = {}
        self.sessao = None
        self.pk_chave = None
        self.versao = 0              # muda quando a geometria medida muda (invalida o cache)
        self._sujo_em = None

    # ------------------------------------------------------------ disco
    def _ler(self) -> dict:
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
            return dados if isinstance(dados.get("hunts"), dict) else {"hunts": {}}
        except Exception:
            return {"hunts": {}}

    def _marcar(self):
        self._sujo_em = self._sujo_em or time.monotonic()

    def gravar_se_preciso(self, forcar=False):
        if self._sujo_em and (forcar or time.monotonic() - self._sujo_em > 2):
            self._sujo_em = None
            try:
                self.arquivo.parent.mkdir(parents=True, exist_ok=True)
                self.arquivo.write_text(json.dumps(self.banco), encoding="utf-8")
            except OSError:
                pass

    # ------------------------------------------------------------ eventos do jogo
    def on_welcome(self, hunts: list):
        for h in hunts or []:
            total = sum(float(e.get("pontos") or 0) for e in h.get("especies") or [])
            if h.get("slug") and total:
                self.pontos[h["slug"]] = min(MAX_SPAWNS, math.floor(total + 0.5))

    def _onda_cheia(self, slug):
        return max(MIN_ONDA, math.ceil(FRACAO_CHEIA * self.pontos.get(slug, 15)))

    def on_pokemon_ativo(self, pk: dict | None):
        chave = chave_do_pokemon(pk)
        if chave != self.pk_chave:
            self.fechar_sessao()
            self.pk_chave = chave

    def on_campo_init(self, m: dict):
        self.fechar_sessao()
        if not m.get("slug") or m.get("centro") or m.get("pvp") or m.get("casa") is not None:
            return
        # A entrada NÃO é medida: o herói está na porta do mapa e a onda pode estar pela metade.
        s = {"slug": m["slug"], "pk": self.pk_chave, "inicio": time.monotonic(), "abates": 0, "xp": 0,
             "slots": {}, "heroi": None, "onda": None}
        heroi = m.get("heroi") or {}
        if heroi.get("c") is not None:
            s["heroi"] = (heroi["c"], heroi["r"])
        for x in m.get("mobs") or []:
            if not _nao_selvagem(x):
                s["slots"][x.get("s")] = not x.get("x")
        self.sessao = s

    def on_campo(self, m: dict):
        s = self.sessao
        if not s:
            return
        self._expirar_onda()
        heroi = m.get("heroi") or {}
        if heroi.get("c") is not None:
            s["heroi"] = (heroi["c"], heroi["r"])
        for x in m.get("mobs") or []:
            if _nao_selvagem(x):
                continue
            slot = x.get("s")
            conhecido = slot in s["slots"]
            vivo_antes = s["slots"].get(slot)
            if x.get("x"):
                if vivo_antes:
                    s["abates"] += 1
                s["slots"][slot] = False
            elif not conhecido or (vivo_antes is False and x.get("x") is False):
                s["slots"][slot] = True        # slot novo, ou corpo que voltou: selvagem nascendo
                self._nasceu(s, x)
        for slot in m.get("fora") or []:
            s["slots"].pop(slot, None)

    def on_xp(self, xp: float):
        """XP de treinador de um abate (dos eventos de batalha), para o XP/h real da caçada."""
        if self.sessao:
            self.sessao["xp"] += xp or 0

    def tick(self):
        """Chamado periodicamente: fecha a onda que passou da janela e grava no disco."""
        self._expirar_onda()
        self.gravar_se_preciso()

    # ------------------------------------------------------------ ondas e sessões
    def _nasceu(self, s, x):
        if not s["heroi"] or x.get("c") is None or x.get("r") is None:
            return
        if not s["onda"]:
            s["onda"] = {"inicio": time.monotonic(), "dists": []}
        d = math.hypot(x["c"] - s["heroi"][0], x["r"] - s["heroi"][1])
        s["onda"]["dists"].append(math.floor(d * 10 + 0.5) / 10)

    def _expirar_onda(self):
        s = self.sessao
        if s and s["onda"] and time.monotonic() - s["onda"]["inicio"] >= JANELA_ONDA_S:
            self._fechar_onda(s)

    def _fechar_onda(self, s):
        onda, s["onda"] = s["onda"], None
        if not onda or len(onda["dists"]) < self._onda_cheia(s["slug"]):
            return                                         # onda parcial: não conta
        h = self.banco["hunts"].setdefault(s["slug"], {})
        h["amostras"] = (h.get("amostras", []) + [sorted(onda["dists"])])[-MAX_AMOSTRAS:]
        h["medidoEm"] = int(time.time() * 1000)
        self.versao += 1
        self._marcar()

    def fechar_sessao(self):
        s, self.sessao = self.sessao, None
        if not s:
            return
        if s["onda"]:
            self._fechar_onda(s)
        seg = time.monotonic() - s["inicio"]
        if seg >= 60 and s["abates"] > 0:
            h = self.banco["hunts"].setdefault(s["slug"], {})
            r = h.setdefault("ritmo", {}).setdefault(s["pk"] or "?", {"abates": 0, "seg": 0})
            r["abates"] += s["abates"]
            r["seg"] += seg
            self.versao += 1
            self._marcar()
        self.gravar_se_preciso(forcar=True)

    # ------------------------------------------------------------ leitura
    def da_hunt(self, slug):
        todas = [d for a in (self.banco["hunts"].get(slug) or {}).get("amostras", []) for d in a]
        return {"dists": sorted(todas)} if todas else None

    def ritmo_medido(self, slug, chave):
        """Abates/h medidos com este pokémon nesta hunt (só com 10+ min). Só referência."""
        r = ((self.banco["hunts"].get(slug) or {}).get("ritmo") or {}).get(chave)
        if r and r["seg"] >= MIN_RITMO_S:
            return r["abates"] * 3600 / r["seg"]
        return None

    def ritmo_sessao(self):
        """O ritmo da caçada em andamento (abates/h), para o "desempenho real" da hunt atual."""
        s = self.sessao
        if not s:
            return None
        seg = time.monotonic() - s["inicio"]
        horas = max(seg, 60) / 3600          # piso de 1 minuto, como o ritmo da sessão do jogo
        return {"slug": s["slug"], "abates": s["abates"], "seg": seg,
                "kph": s["abates"] / horas, "xp_h": s["xp"] / horas}

    def hunts_medidas(self):
        return sum(1 for h in self.banco["hunts"].values() if h.get("amostras"))

"""A Pokédex do PokeNexus: quem entra e o que cada conta já capturou. Sem Qt (testável sozinho).

Quem entra (docs/pokedex/RECONHECIMENTO.md): os sprites do PokeNexus ∩ as espécies BASE do jogo no ar
(pokeId nacional, 1 a 1025), montado na hora. Capturado: a Pokédex do próprio jogo, `c > 0` (o mesmo
critério das abas da Pokédex do jogo), o evento de batalha `capturado` e o INVENTÁRIO da conta (`pokemons`, com o
Depot): pokémon que chegou por evolução ou troca também conta (pedido do usuário, 17/10/2026), então o total pode
passar o da aba do jogo. Mega e Forma seguem o jogo: têm entrada própria lá e não marcam a espécie base
(escolha do usuário, 17/10/2026).

A Pokédex SÓ LÊ: nada aqui fala com o jogo.
"""
import json
import time
from pathlib import Path

REGIOES = (("Kanto", 1, 151), ("Johto", 152, 251), ("Hoenn", 252, 386))
NACIONAL_MAX = 1025

# shared/outland.mjs do jogo
_OUTLAND_MIN, _OUTLAND_MAX = 2001, 2059                  # [min, max)
_OUTLAND_LEGADO_MIN, _OUTLAND_LEGADO_MAX = 10501, 10548  # [min, max)

TIPOS = {"NORMAL": "Normal", "FIRE": "Fogo", "WATER": "Água", "GRASS": "Planta", "ELECTRIC": "Elétrico",
         "ICE": "Gelo", "FIGHTING": "Lutador", "POISON": "Venenoso", "GROUND": "Terra", "FLYING": "Voador",
         "PSYCHIC": "Psíquico", "BUG": "Inseto", "ROCK": "Pedra", "GHOST": "Fantasma", "DRAGON": "Dragão",
         "DARK": "Sombrio", "STEEL": "Aço", "FAIRY": "Fada"}


def chave_pokedex(poke_id) -> int | None:
    """A chave que o jogo grava na Pokédex (shared/pokedex.mjs `chavePokedex` + `dexDe`): o número nacional
    (os clones 13xxx viram a base: 13252 -> 252), o #2001… do Outland, ou o próprio número (Mega, Forma)."""
    try:
        i = int(poke_id)
    except (TypeError, ValueError):
        return None
    if i < 1:
        return None
    if _OUTLAND_LEGADO_MIN <= i < _OUTLAND_LEGADO_MAX:
        return i - (_OUTLAND_LEGADO_MIN - _OUTLAND_MIN)
    if _OUTLAND_MIN <= i < _OUTLAND_MAX or i < 1000:
        return i
    if i >= 13000:
        return i % 1000
    return i


def regiao(dex: int) -> str | None:
    return next((nome for nome, a, b in REGIOES if a <= dex <= b), None)


def numeros_dos_sprites(pasta: Path) -> set[int]:
    """Os pokémon que o PokeNexus tem desenho (assets/sprites/pokemon/<número>.gif)."""
    return {int(p.stem) for p in Path(pasta).glob("*.gif") if p.stem.isdigit()}


def montar_lista(sprites: set[int], especies: dict | None) -> list[dict]:
    """Sprites ∩ espécies base do jogo, em ordem de número: [{dex, nome, tipos, regiao}].

    `especies`: {pokeId: {"nome", "type1", "type2"}} (o catálogo da versão no ar, hunts/game_data.py, ou o
    cache dele). Formas, Megas, Outland e clones ficam de fora: só pokeId nacional. Sem catálogo (primeira
    vez e sem internet), entram os sprites, sem nome, até o catálogo chegar."""
    base = {}
    for pid, e in (especies or {}).items():
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            continue
        if 1 <= pid <= NACIONAL_MAX:
            base[pid] = e
    numeros = sorted(sprites & set(base)) if base else sorted(sprites)
    lista = []
    for n in numeros:
        e = base.get(n) or {}
        tipos = [TIPOS.get(t, str(t).capitalize()) for t in (e.get("type1"), e.get("type2")) if t]
        lista.append({"dex": n, "nome": e.get("nome") or "", "tipos": tipos, "regiao": regiao(n)})
    return lista


def capturados(dex_jogo: dict | None, especies_da_colecao=(), capturas=()) -> set[int]:
    """As chaves que a conta já capturou. `dex_jogo` = a Pokédex do jogo {chave: {k, c, ...}}: soma as
    entradas da mesma chave (o jogo também soma, `normalizarEntradasPokedex`) e vale `c > 0`. Reforço: as
    espécies da coleção (`pokemons[].speciesId`) e as do evento `capturado`."""
    soma: dict[int, float] = {}
    for k, v in (dex_jogo or {}).items():
        n = chave_pokedex(k)
        if n is None or not isinstance(v, dict):
            continue
        try:
            soma[n] = soma.get(n, 0) + float(v.get("c") or 0)
        except (TypeError, ValueError):
            continue
    out = {n for n, c in soma.items() if c > 0}
    for sid in list(especies_da_colecao) + list(capturas):
        n = chave_pokedex(sid)
        if n is not None:
            out.add(n)
    return out


def progresso(lista: list[dict], pegos: set[int]) -> dict:
    """{"total": (pegos, de), "Kanto": (pegos, de), ...} só com quem está na lista."""
    out = {"total": (sum(1 for e in lista if e["dex"] in pegos), len(lista))}
    for nome, a, b in REGIOES:
        da = [e for e in lista if a <= e["dex"] <= b]
        out[nome] = (sum(1 for e in da if e["dex"] in pegos), len(da))
    return out


class PokedexConta:
    """O que UMA conta do PokeNexus já capturou, guardado em profiles/conta_XX/pokedex.json para a Pokédex
    abrir com a conta parada. Separado por conta do jogo (o id dela): se outra conta do jogo entrar neste
    lugar, ela começa a própria lista e as duas nunca se misturam. Só números de espécie e a data da
    primeira captura que o PokeNexus viu (None = já estava capturado quando o PokeNexus começou a olhar).
    Uma vez capturado, fica (como no jogo)."""

    VERSAO = 1

    def __init__(self, arquivo: Path):
        self.arquivo = Path(arquivo)
        self.contas: dict[str, dict] = {}     # id do jogo -> {"desde": t, "capturados": {"25": t | None}}
        self.ultima: str | None = None        # a conta do jogo que entrou por último neste lugar
        self._ler()

    def _ler(self):
        try:
            d = json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(d, dict) or d.get("versao") != self.VERSAO:
            return
        for cid, c in (d.get("contas") or {}).items():
            if isinstance(c, dict) and isinstance(c.get("capturados"), dict):
                self.contas[str(cid)] = {"desde": c.get("desde"), "capturados": {
                    str(int(k)): v for k, v in c["capturados"].items() if str(k).isdigit()}}
        self.ultima = str(d["ultima"]) if d.get("ultima") is not None and str(d["ultima"]) in self.contas else None

    def _gravar(self):
        dados = {"versao": self.VERSAO, "ultima": self.ultima, "contas": self.contas}
        tmp = self.arquivo.with_suffix(".json.tmp")
        try:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            tmp.replace(self.arquivo)
        except OSError:
            pass

    def atualizar(self, conta_jogo, pegos: set[int], agora: float | None = None) -> list[int]:
        """Junta o que a conta do jogo `conta_jogo` tem capturado agora. Devolve as espécies NOVAS (para a tela
        atualizar só essas células). Grava só quando algo mudou."""
        if conta_jogo is None:
            return []
        cid, agora = str(conta_jogo), time.time() if agora is None else agora
        c = self.contas.get(cid)
        primeira = c is None
        if primeira:
            c = self.contas[cid] = {"desde": agora, "capturados": {}}
        novos = [n for n in sorted(pegos) if str(n) not in c["capturados"]]
        for n in novos:
            c["capturados"][str(n)] = None if primeira else agora
        mudou = bool(novos) or primeira or self.ultima != cid
        self.ultima = cid
        if mudou:
            self._gravar()
        return [] if primeira else novos

    def atual(self) -> dict[int, float | None]:
        """{número: quando} da conta do jogo que está neste lugar (ou a última que esteve)."""
        c = self.contas.get(self.ultima or "")
        return {int(k): v for k, v in (c or {}).get("capturados", {}).items()}

    def desde(self) -> float | None:
        return (self.contas.get(self.ultima or "") or {}).get("desde")


def juntar(contas: dict[str, dict[int, float | None]]) -> dict[int, dict]:
    """Modo "Todas as contas": {número: {"quando": a primeira captura, "donos": [nome da conta, ...]}}. None
    (já estava capturado quando o PokeNexus começou a olhar) é a mais antiga de todas."""
    out: dict[int, dict] = {}
    for nome, pegos in contas.items():
        for n, quando in pegos.items():
            e = out.get(n)
            if e is None:
                out[n] = {"quando": quando, "donos": [nome]}
                continue
            e["donos"].append(nome)
            if quando is None or (e["quando"] is not None and quando < e["quando"]):
                e["quando"] = quando
    return out

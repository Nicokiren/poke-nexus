"""Motor do Hunt Analyzer: simula o pokémon de UMA conta em cada hunt.

Reprodução em Python do motor da extensão "/hunt for PokeIdle" (src/engine.js, v1.0.1), com
as mesmas regras, constantes e passos — os números saem iguais aos dela (ver o teste de
equivalência em tests/). As funções que são do JOGO (XP/ouro por abate, efetividade,
recarga com Speed, golpe do TM, multiplicadores de XP) não estão aqui: chegam prontas da ponte
com o próprio jogo (hunts/bridge.js), sempre da versão no ar.
"""
import math
import time

INF = math.inf

# ---- regras do jogo que o cliente só documenta em texto (Pokepédia > Combate) ---------------
REGRAS = {
    "rand_medio": 0.925,      # aleatório(0,85–1,00)
    "stab": 1.5,
    "gap_jogador_ms": 900,    # intervalo mínimo entre golpes seus
    "gap_selvagem_s": 1.4,    # intervalo mínimo entre golpes dele
    "investida_power": 30,
    "investida_cd_ms": 2000,
    "piso_cd_ms": 400,        # piso do desconto fixo do IV de SPD
    "ms_por_iv_spd": 10,      # −10 ms por ponto de IV de SPD na Investida e no intervalo
    "hp_combate_mult": 12,    # hpDeCombate = máx(24, arred(hp × 12))
    "hp_combate_min": 24,
    "iv_selvagem_medio": 16,  # selvagem: IV sorteado 1–32 por mob
    "poder_minimo": 15,
    "lado_tm_aoe": 11,        # o disco AoE acerta um quadrado 11×11 centrado no pokémon
}

# ---- ritmo da hunt: medido em jogo (ajustável pela medição de cada conta, ver measure.py) ----
MEDIDO = {
    "retarget_s": 1.0,
    "ciclo_min_s": 1.8,
    "gap_onda_s": 2.8,
    "ms_onda_s": 2.6,
    "selvagem_s_por_tile": 1.9,
    "heroi_s_por_tile": 0.26,
    "f_busca": 0.31,
    "spawns_padrao": 15,
    "max_spawns": 16,
    "dist_padrao": 20.6,
    "slot_sinnoh_s": 30,
    "slot_outras_s": 65,
    "nivel_onda": 150,
    "respawn_s": 3,
    "amostras_hp": 32,
    "max_ataques_por_abate": 4000,
    "aoe_alvos_por_golpe": 2.2,
    "aoe_alvos_min": 1,
    "aoe_alvos_max": 6,
    "aoe_max_engajados": 15,
}

STATS = ("hp", "atk", "def", "spAtk", "spDef", "speed")
BASE_DE = {"hp": "baseHp", "atk": "baseAtk", "def": "baseDef",
           "spAtk": "baseSpAtk", "spDef": "baseSpDef", "speed": "baseSpeed"}


def js_round(x: float) -> float:
    """Math.round do JavaScript (0,5 sobe), diferente do round() do Python."""
    return math.floor(x + 0.5)


def nn(v, padrao):
    """O `??` do JavaScript: só troca None (null/undefined), não 0."""
    return padrao if v is None else v


def _num(v, padrao=0.0):
    try:
        n = float(v)
        return n if math.isfinite(n) else padrao
    except (TypeError, ValueError):
        return padrao


def tem_aoe(pk: dict) -> bool:
    v = pk.get("tmAoe", pk.get("tm_aoe"))
    return v is True or v == "true" or v == 1


def mediana(xs):
    s = sorted(xs)
    n = len(s)
    return s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantis(valores, n):
    v = sorted(valores)
    return [v[min(len(v) - 1, math.floor(((i + 0.5) / n) * len(v)))] for i in range(n)]


def tipos_de(esp: dict):
    return [t for t in (esp.get("type1"), esp.get("type2")) if t]


def _iv_spd(iv):
    return min(32, max(1, js_round(_num(iv) or 1)))


def cd_pelo_iv(ms, iv):
    return max(REGRAS["piso_cd_ms"], ms - _iv_spd(iv) * REGRAS["ms_por_iv_spd"])


def _poder(power):
    # Math.max(15, undefined) dá NaN no JS; aqui um golpe sem poder também não causa dano.
    if power is None:
        return math.nan
    return max(REGRAS["poder_minimo"], _num(power, math.nan))


def dano(nivel, power, atk, defe, stab, efet):
    base = ((2 * nivel / 5 + 2) * power * max(1, atk) / max(1, defe)) / 50 + 2
    return base * (REGRAS["stab"] if stab else 1) * efet * REGRAS["rand_medio"]


def stats_selvagem(esp, nivel, iv=REGRAS["iv_selvagem_medio"]):
    """Stats do selvagem: IV médio, qualidade 1, potência I."""
    return {k: (_num(esp.get(BASE_DE[k])) + 2 * iv) * nivel / 100 for k in STATS}


# ---- XP: bônus que multiplicam (Pokepédia > Níveis e XP) ------------------------------------
def bonus_xp(eu: dict, base: dict, tipos_boost: list, vip_mult: float, agora_ms: float | None = None):
    """Todos os multiplicadores de XP ativos agora. `base` = multXpPokemon/Treinador do jogo
    (XP Boost, VIP, guild e Boost da Guild, já na conta do jogo); aqui entram os demais:
    Twitch, Kick, evento e Boost dos atrasados."""
    agora = time.time() * 1000 if agora_ms is None else agora_ms
    eu = eu or {}
    loja = eu.get("loja") or {}
    boosts = loja.get("boosts") or {}
    itens = []

    def boost_de(chave):
        if agora < _num(boosts.get(chave)):
            for b in tipos_boost or []:
                if b.get("chave") == chave:
                    return nn(b.get("mult"), 1)
        return 1

    if agora < _num(loja.get("vipAte")):
        itens.append({"nome": "VIP", "mult": vip_mult, "ambos": True, "base": True})
    if boost_de("xp") > 1:
        itens.append({"nome": "XP Boost", "mult": boost_de("xp"), "treinador": True, "base": True})
    if boost_de("pokexp") > 1:
        itens.append({"nome": "XP Boost Pokémon", "mult": boost_de("pokexp"), "pokemon": True, "base": True})
    guild_pct = _num(eu.get("guildBonusPct"))
    if guild_pct > 0:
        itens.append({"nome": "Ranking da guild", "mult": 1 + guild_pct / 100, "ambos": True, "base": True})
    if agora < _num((eu.get("guild") or {}).get("boostAte")):
        prod = 1.0
        for i in itens:
            if i.get("base") and (i.get("ambos") or i.get("pokemon")):
                prod *= i["mult"]
        m = base["pokemon"] / prod
        if m > 1.0001:
            itens.append({"nome": "Boost da Guild", "mult": m, "ambos": True, "base": True})

    extra = {"pokemon": 1.0, "treinador": 1.0}

    def somar(item):
        itens.append(item)
        if item.get("ambos") or item.get("pokemon"):
            extra["pokemon"] *= item["mult"]
        if item.get("ambos") or item.get("treinador"):
            extra["treinador"] *= item["mult"]

    tw = eu.get("twitch") or {}
    if tw.get("assistindo") and _num(tw.get("pctAtual")) > 0:
        somar({"nome": "Twitch", "mult": 1 + _num(tw["pctAtual"]) / 100, "ambos": True})
    kk = eu.get("kick") or {}
    if agora < _num((kk.get("bonus") or {}).get("xp")) and _num(kk.get("pct")) > 0:
        somar({"nome": "Kick", "mult": 1 + _num(kk["pct"]) / 100, "ambos": True})
    ev = eu.get("evento")
    if ev and agora < _num(ev.get("terminaEm")):
        tr, pk = _num(ev.get("xpTreinadorPct")), _num(ev.get("xpPokemonPct"))
        if tr and tr == pk:
            somar({"nome": "Evento", "mult": 1 + tr / 100, "ambos": True})
        else:
            if pk:
                somar({"nome": "Evento (pokémon)", "mult": 1 + pk / 100, "pokemon": True})
            if tr:
                somar({"nome": "Evento (treinador)", "mult": 1 + tr / 100, "treinador": True})
    at = loja.get("atrasados")
    if at and _num(at.get("mult")) > 1 and _num(eu.get("level")) < _num(at.get("alvo")):
        somar({"nome": "Atrasados", "mult": _num(at["mult"]), "ambos": True})
    return {"pokemon": base["pokemon"] * extra["pokemon"],
            "treinador": base["treinador"] * extra["treinador"], "itens": itens}


# ---- combate --------------------------------------------------------------------------------
def tipo_da_investida(tipos, ef, alvo_tipos):
    """A Investida sai no 1º tipo; só passa para o 2º se o alvo for imune ao 1º."""
    t1 = tipos[0] if tipos else None
    t2 = tipos[1] if len(tipos) > 1 else None
    if t2 and ef(t1, _i(alvo_tipos, 0), _i(alvo_tipos, 1)) == 0:
        return t2
    return t1


def _i(lst, k):
    return lst[k] if len(lst) > k else None


def segundos_por_abate(golpes, investida, gap_s, hps, morto_s):
    """Segundos de luta por abate: a cada ataque, o golpe pronto de maior dano; sem golpe pronto
    vem a Investida; todo ataque ocupa o intervalo global. As recargas correm no tempo morto."""
    ordem = sorted([i for i, g in enumerate(golpes) if g["d"] > 0], key=lambda i: -golpes[i]["d"])
    # Mesmas contas, na mesma ordem, do engine.js; só com listas simples no laço (é o trecho
    # que roda milhões de vezes numa análise).
    ds = [golpes[i]["d"] for i in ordem]
    cds = [golpes[i]["cdS"] for i in ordem]
    pronto = [0.0] * len(ordem)
    faixa = range(len(ordem))
    prox_inv = 0.0
    t = 0.0
    luta = 0.0
    max_atq = MEDIDO["max_ataques_por_abate"]
    inv_d, inv_cd = investida["d"], investida["cdS"]
    tem_inv = inv_d > 0
    for hp in hps:
        feito = 0.0
        ini = t
        ultimo = t
        ataques = 0
        while feito < hp:
            ataques += 1
            if ataques > max_atq:
                return INF
            for k in faixa:
                if pronto[k] <= t:
                    feito += ds[k]
                    pronto[k] = t + cds[k]
                    ultimo = t
                    t += gap_s
                    break
            else:
                if tem_inv and prox_inv <= t:
                    feito += inv_d
                    prox_inv = t + inv_cd
                    ultimo = t
                    t += gap_s
                else:
                    prox = prox_inv if tem_inv else INF
                    for p in pronto:
                        if p < prox:
                            prox = p
                    if not math.isfinite(prox):
                        return INF
                    t = max(t, prox)
        luta += ultimo - ini
        t = ultimo + morto_s
    return luta / len(hps)


def ameaca_do_selvagem(esp, nivel, pk, ef, mult_dano):
    """O que o selvagem faz com você: dano por segundo e o pior golpe (rolagem máxima)."""
    st = stats_selvagem(esp, nivel)
    tipos_pk = pk["tipos"]
    tipos_esp = tipos_de(esp)
    danos = []
    for a in esp.get("attacks") or []:
        if nn(a.get("learnLevel"), 1) > nivel:
            continue
        fisico = a.get("category") != "SPECIAL"
        danos.append(dano(nivel, _poder(a.get("power")), st["atk"] if fisico else st["spAtk"],
                          pk["stats"]["def"] if fisico else pk["stats"]["spDef"],
                          a.get("type") in tipos_esp, ef(a.get("type"), _i(tipos_pk, 0), _i(tipos_pk, 1))))
    tipo_inv = tipo_da_investida(tipos_esp, ef, tipos_pk)
    inv = dano(nivel, REGRAS["investida_power"], st["atk"], pk["stats"]["def"], True,
               ef(tipo_inv, _i(tipos_pk, 0), _i(tipos_pk, 1)))
    media = (sum(danos) / len(danos)) * 0.92 + inv * 0.08 if danos else inv
    return {
        "dps": media * mult_dano / REGRAS["gap_selvagem_s"],
        "hit_medio": media * mult_dano,
        "hit_max": max([inv, *danos]) / REGRAS["rand_medio"] * mult_dano,
    }


def teto_de_reposicao(n, hunt):
    """Acima do nível 150 o servidor repõe por slot, não por onda: é o teto físico da hunt."""
    if _num(hunt.get("nivel")) <= MEDIDO["nivel_onda"]:
        return INF
    sinnoh = hunt.get("regiao") == "sinnoh" or str(hunt.get("slug")).endswith("_sinnoh")
    return n * 3600 / (MEDIDO["slot_sinnoh_s"] if sinnoh else MEDIDO["slot_outras_s"])


def abates_por_hora(dists, ciclo_s, hunt):
    d = sorted(dists)
    n = len(d)
    d_med = sum(d) / n
    caminho = d_med * MEDIDO["heroi_s_por_tile"] * MEDIDO["f_busca"]
    sv, hv = MEDIDO["selvagem_s_por_tile"], MEDIDO["heroi_s_por_tile"]
    f_encontro = sv * hv / (sv + hv)
    t = 0.0
    for x in d:
        t = max(t + ciclo_s + caminho, x * f_encontro)
    por_onda = n * 3600 / (t + MEDIDO["gap_onda_s"])
    return min(3600 / ciclo_s, por_onda, teto_de_reposicao(n, hunt))


def limite_aoe(dists, hunt):
    d = sorted(dists)
    d_ritmo = d[-2] if len(d) > 1 else d[0]
    raio = (REGRAS["lado_tm_aoe"] - 1) / 2
    chegada = max(0, d_ritmo - raio) * MEDIDO["selvagem_s_por_tile"]
    return min(len(d) * 3600 / (chegada + MEDIDO["gap_onda_s"]), teto_de_reposicao(len(d), hunt))


def abates_por_hora_aoe(dists, ciclo_s, hunt, alvos):
    return min(3600 * alvos / ciclo_s, limite_aoe(dists, hunt))


def _contra_selvagem(esp, nivel, pk, golpes_pk, ef, gap_s, cd_inv_s, morto_s, mult_hp, mult_dano, preco_item):
    """Tudo do combate contra um selvagem num nível que não depende da hunt: dano de cada golpe,
    segundos por abate, ameaça dele e o loot que vale ouro."""
    tipos_alvo = tipos_de(esp)
    st = stats_selvagem(esp, nivel)
    golpes = []
    for g in golpes_pk:
        fisico = g.get("category") != "SPECIAL"
        d = dano(pk["level"], _poder(g.get("power")), pk["stats"]["atk"] if fisico else pk["stats"]["spAtk"],
                 st["def"] if fisico else st["spDef"], g.get("type") in pk["tipos"],
                 ef(g.get("type"), _i(tipos_alvo, 0), _i(tipos_alvo, 1)))
        golpes.append({"d": d, "cdS": _num(g.get("cooldownMs")) / 1000, "g": g})
    tipo_inv = tipo_da_investida(pk["tipos"], ef, tipos_alvo)
    investida = {"d": dano(pk["level"], REGRAS["investida_power"], pk["stats"]["atk"], st["def"], True,
                           ef(tipo_inv, _i(tipos_alvo, 0), _i(tipos_alvo, 1))),
                 "cdS": cd_inv_s}
    hps = []
    for k in range(MEDIDO["amostras_hp"]):
        iv = 1 + math.floor(k * 32 / MEDIDO["amostras_hp"] + 0.5)
        hp_stat = (_num(esp.get("baseHp")) + 2 * iv) * nivel / 100
        hps.append(max(REGRAS["hp_combate_min"], js_round(hp_stat * REGRAS["hp_combate_mult"])) * mult_hp)
    s = segundos_por_abate(golpes, investida, gap_s, hps, morto_s)
    am = ameaca_do_selvagem(esp, nivel, pk, ef, mult_dano) if math.isfinite(s) else None
    loot = []
    for l in esp.get("loot") or []:
        preco = preco_item.get(l.get("name"), 0)
        if not preco or not (_num(l.get("chance")) > 0):
            continue
        loot.append((l["chance"], nn(l.get("minCount"), 1) + nn(l.get("maxCount"), 1), preco))
    return tipos_alvo, golpes, s, am, loot


def simular_hunt(h, pk, golpes_pk, ef, ctx, opcoes):
    """Uma hunt: tempo para derrotar, abates/h, XP/h, ouro/h, risco e mortes/h."""
    especies = ctx["especies"]
    lista = []
    for e in h.get("especies") or []:
        esp = especies.get(e.get("pokeId"))
        pontos = _num(e.get("pontos"))
        if esp and pontos > 0:
            lista.append((esp, pontos))
    total = sum(p for _, p in lista)
    if not total:
        return None
    nivel = nn(h.get("nivel"), 1)
    slug = h.get("slug")

    n_spawns = max(1, min(MEDIDO["max_spawns"], js_round(total) or MEDIDO["spawns_padrao"]))
    medida = ctx["geo"](slug) if ctx.get("geo") else None
    dists = quantis(medida["dists"], n_spawns) if medida and medida.get("dists") else [MEDIDO["dist_padrao"]] * n_spawns
    morto_s = MEDIDO["ms_onda_s"] / len(dists) + MEDIDO["retarget_s"]
    iv_speed = (pk.get("ivs") or {}).get("speed")
    gap_s = cd_pelo_iv(REGRAS["gap_jogador_ms"], iv_speed) / 1000
    cd_inv_s = cd_pelo_iv(REGRAS["investida_cd_ms"], iv_speed) / 1000

    ttk = dps = hit_max = hit_medio = xp_kill = ouro_kill = loot_kill = ef_media = 0.0
    melhor_golpe, melhor_dano = None, -1.0
    alvos = []
    mult_hp = nn(ctx["consts"].get("multHpSelvagem"), 5)
    mult_dano = nn(ctx["consts"].get("multDanoSelvagem"), 1.8)
    recompensa = ctx["recompensa"].get(slug, {})
    preco_item = ctx["preco_item"]
    # O mesmo selvagem no mesmo nível aparece em várias hunts: o combate contra ele é calculado
    # uma vez por análise (o resultado é idêntico; só não se repete a conta).
    cache = ctx.get("_cache")
    for esp, pontos in lista:
        w = pontos / total
        chave = (esp["pokeId"], nivel, morto_s)
        c = cache.get(chave) if cache is not None else None
        if c is None:
            c = _contra_selvagem(esp, nivel, pk, golpes_pk, ef, gap_s, cd_inv_s, morto_s, mult_hp, mult_dano,
                                 preco_item)
            if cache is not None:
                cache[chave] = c
        tipos_alvo, golpes, s, am, loot = c
        for g in golpes:
            if g["d"] * w > melhor_dano:
                melhor_dano, melhor_golpe = g["d"] * w, g["g"]
        if not math.isfinite(s):
            ttk = INF
            break
        ttk += w * s

        dps += w * am["dps"]
        hit_medio += w * am["hit_medio"]
        hit_max = max(hit_max, am["hit_max"])

        xp, ouro = recompensa.get(esp["pokeId"], recompensa.get(str(esp["pokeId"]), (0, 0)))
        xp_kill += w * xp
        ouro_kill += w * ouro
        for chance, qtd, preco in loot:
            loot_kill += w * (chance / 100000) * qtd / 2 * preco
        alvos.append((w, tipos_alvo))
    for w, tipos_alvo in alvos:
        ef_media += w * (ef(melhor_golpe.get("type"), _i(tipos_alvo, 0), _i(tipos_alvo, 1)) if melhor_golpe else 1)

    nivel_treinador = (ctx.get("eu") or {}).get("level")
    base = {
        "slug": slug, "nome": h.get("nome") or slug, "nivel": nivel,
        "regiao": h.get("regiao") or h.get("area"),
        "liberada": (INF if nivel_treinador is None else nivel_treinador) >= nivel,
        "geo_medida": bool(medida and medida.get("dists")),
        "melhor_golpe": {"nome": melhor_golpe.get("name"), "tipo": melhor_golpe.get("type")} if melhor_golpe else None,
        "efetividade": ef_media,
        "especies": [esp["pokeId"] for esp, _ in lista],
        "selvagens": [esp.get("nome") or str(esp["pokeId"]) for esp, _ in lista],
    }
    if not math.isfinite(ttk):
        return {**base, "inviavel": True, "motivo": "não mata", "xp_pokemon_h": 0, "xp_treinador_h": 0,
                "ouro_h": 0, "kph": 0, "ttk": INF, "mortes_h": 0, "um_hit": False, "hit_pct": 0,
                "kph_medido": None, "aoe": False, "engajados": 1}

    ciclo_s = max(ttk + MEDIDO["retarget_s"], MEDIDO["ciclo_min_s"])
    kph = abates_por_hora(dists, ciclo_s, h)
    modo_aoe = False
    engajados = 1.0
    if opcoes.get("aoe"):
        k_aoe = abates_por_hora_aoe(dists, ciclo_s, h, opcoes["alvos_aoe"])
        if k_aoe > kph:
            kph, modo_aoe = k_aoe, True
        # Lei de Little: selvagens vivos ao mesmo tempo ≈ ritmo de chegada × tempo de vida.
        engajados = min(MEDIDO["aoe_max_engajados"], 1 + kph * ttk / 3600)

    # Morte: com poção automática só morre quem leva, de uma vez, mais que o HP inteiro; sem
    # poção, morre quando o dano acumulado nos abates passa do HP.
    hp_pk = pk.get("maxHp")
    if hp_pk is None:
        hp_pk = max(REGRAS["hp_combate_min"], js_round(pk["stats"]["hp"] * REGRAS["hp_combate_mult"]))
    dano_por_abate = dps * engajados * ttk
    hit_pior = hit_max + (engajados - 1) * hit_medio
    um_hit = hit_pior >= hp_pk
    if opcoes.get("com_pocao", True):
        abates_por_vida = hp_pk / hit_pior if um_hit else 999
    else:
        abates_por_vida = hp_pk / max(1e-6, dano_por_abate)
    d_med = sum(dists) / len(dists)
    tempo_morte = MEDIDO["respawn_s"] + d_med * MEDIDO["heroi_s_por_tile"]
    vida_s = abates_por_vida * (3600 / kph if kph > 0 else 0)
    uptime = vida_s / (vida_s + tempo_morte)
    mortes_h = 0 if abates_por_vida >= 999 else 3600 / (vida_s + tempo_morte)
    kph_modelo = kph * uptime
    # O ranking é sempre o modelo de onda cheia; o medido é só referência.
    kph_medido = ctx["ritmo"](slug) if ctx.get("ritmo") else None

    mult_pk = opcoes["bonus_xp"]["pokemon"]
    mult_tr = opcoes["bonus_xp"]["treinador"]
    return {
        **base, "inviavel": False,
        "ttk": ttk, "kph": kph_modelo, "kph_modelo": kph_modelo, "kph_medido": kph_medido,
        "mortes_h": mortes_h, "um_hit": um_hit, "hit_pct": hit_pior / hp_pk,
        "hit_pior": hit_pior, "hp_pk": hp_pk, "dano_por_abate": dano_por_abate,
        "aoe": modo_aoe, "engajados": engajados,
        "_ciclo_s": ciclo_s, "_limite_aoe": limite_aoe(dists, h),
        "xp_pokemon_h": kph_modelo * xp_kill * mult_pk,
        "xp_treinador_h": kph_modelo * xp_kill * mult_tr,
        "ouro_h": kph_modelo * (ouro_kill + loot_kill),
        "ouro_kill": ouro_kill, "loot_kill": loot_kill, "xp_kill": xp_kill,
    }


def calibrar_aoe(pk, golpes, ef, ctx, op):
    """Recalibra os alvos por golpe do AoE com as hunts em que a conta já caçou 10+ min com este
    pokémon: abates/h medido × ciclo de abate ÷ 3600 (fora as limitadas pela chegada)."""
    if not ctx.get("ritmo"):
        return None
    obs = []
    sem_medida = {**ctx, "ritmo": None}
    for h in ctx["hunts"]:
        medido = ctx["ritmo"](h.get("slug"))
        if not medido:
            continue
        r = simular_hunt(h, pk, golpes, ef, sem_medida, {**op, "alvos_aoe": MEDIDO["aoe_alvos_por_golpe"]})
        if not r or r["inviavel"] or medido >= 0.9 * r["_limite_aoe"]:
            continue
        obs.append(medido * r["_ciclo_s"] / 3600)
    if not obs:
        return None
    return {"alvos": min(MEDIDO["aoe_alvos_max"], max(MEDIDO["aoe_alvos_min"], mediana(obs))), "hunts": len(obs)}


def analisar(pk_raw: dict, especie: dict, golpes: list, ctx: dict, opcoes: dict) -> dict:
    """Analisa todas as hunts para o pokémon `pk_raw` (um item de estado.pokemons).

    ctx: especies (pokeId -> espécie), hunts, consts, ef(atq, d1, d2), recompensa, preco_item,
         eu, geo(slug), ritmo(slug), bonus_base, tipos_boost, vip_mult.
    opcoes: com_pocao (True), ordem ('xp'|'ouro'), so_liberadas (True).
    """
    op = {"com_pocao": True, "ordem": "xp", "so_liberadas": True, **opcoes}
    stats = pk_raw.get("stats")
    if not stats:
        raise ValueError("o jogo não mandou os stats deste pokémon")
    pk = {**pk_raw, "level": nn(pk_raw.get("level"), 1),
          "tipos": pk_raw.get("tipos") or tipos_de(especie), "stats": stats}
    inicio = time.perf_counter()
    ctx = {**ctx, "_cache": {}}            # combate por (selvagem, nível): vale só nesta análise
    op["aoe"] = tem_aoe(pk)
    op["bonus_xp"] = bonus_xp(ctx.get("eu"), ctx["bonus_base"], ctx.get("tipos_boost") or [],
                              ctx.get("vip_mult", 1.5))
    calibracao = calibrar_aoe(pk, golpes, ctx["ef"], ctx, op) if op["aoe"] else None
    op["alvos_aoe"] = calibracao["alvos"] if calibracao else MEDIDO["aoe_alvos_por_golpe"]
    linhas = []
    for h in ctx["hunts"]:
        r = simular_hunt(h, pk, golpes, ctx["ef"], ctx, op)
        if r:
            linhas.append(r)
    chave = "ouro_h" if op["ordem"] == "ouro" else "xp_pokemon_h"
    linhas.sort(key=lambda l: (-l[chave], l["nivel"]))
    return {
        "pokemon": pk, "especie": especie, "golpes": golpes,
        "aoe": {"alvos_por_golpe": op["alvos_aoe"], "calibrado_em": calibracao["hunts"] if calibracao else 0}
        if op["aoe"] else None,
        "bonus_xp": op["bonus_xp"],
        "linhas": [l for l in linhas if l["liberada"]] if op["so_liberadas"] else linhas,
        "todas": linhas,
        "total": len(linhas),
        "ms": js_round((time.perf_counter() - inicio) * 1000),
    }

// Ponte com o PokeIdle para o Hunt Analyzer do PokeNexus.
//
// Roda numa página ISOLADA do pokeidle.io (/robots.txt: mesmo site, sem o jogo, sem login, sem
// WebSocket). Importa ao vivo os módulos públicos do próprio jogo e os catálogos JSON — o mesmo
// caminho da extensão "/hunt for PokeIdle" — para que fórmulas e catálogo sejam SEMPRE os da
// versão no ar. Quando o jogo muda um golpe, um cooldown ou uma curva de XP, o PokeNexus muda
// junto. O motor de simulação em si fica em Python (hunts/calculator.py).
(function () {
  'use strict';
  if (window.__pnHunt) return;

  const url = (p) => `${location.origin}/${p}`;
  const json = (p, opcional) => fetch(url(p), { cache: 'no-cache' }).then((r) => {
    if (r.ok) return r.json();
    if (opcional) return null;
    throw new Error(`${p}: HTTP ${r.status}`);
  }).catch((e) => { if (opcional) return null; throw e; });

  const MODULOS = {
    cooldown: 'shared/cooldown-golpes.mjs',
    especiais: 'shared/golpes-especiais.mjs',
    planilhas: 'shared/golpes-planilhas.mjs',
    outland: 'shared/outland.mjs',
    baseOutland: 'shared/herdar-base-outland.mjs',
    golpesOrre: 'shared/herdar-golpes-orre.mjs',
    megas: 'shared/megas.mjs',
    evolucoes: 'shared/evolucoes-cruzadas.mjs',
    alias: 'shared/alias-item.mjs',
    tm: 'shared/tm-elemental.mjs',
    recompensa: 'shared/recompensa-hunt.mjs',
    analyser: 'hunt-analyser.mjs',
  };

  let mod = null;
  let especies = null;   // Map pokeId -> espécie (como o cliente monta)
  let versao = null;

  async function versaoNoAr() {
    try {
      const html = await fetch(url('app'), { cache: 'no-cache' }).then((r) => r.text());
      return (html.match(/estilo\.css\?v=([\w.\-]+)/) || [])[1] || null;
    } catch { return null; }
  }

  // O catálogo de espécies como o cliente oficial monta (só o que mexe em combate).
  function montarCatalogo(fontes) {
    const { cr, novos, outlandNovos, overrides } = fontes;
    const lista = [...(cr?.creatures ?? [])];
    if (novos?.creatures?.length) lista.push(...novos.creatures);
    if (outlandNovos?.creatures?.length) lista.push(...outlandNovos.creatures);
    mod.outland.aplicarRemapOutlandLista(lista);
    for (const o of overrides?.overrides ?? []) {
      const c = lista.find((x) => x.pokeId === o.pokeId);
      if (!c) continue;
      for (const k of ['baseHp', 'baseAtk', 'baseDef', 'baseSpAtk', 'baseSpDef', 'baseSpeed']) {
        if (typeof o[k] === 'number') c[k] = o[k];
      }
      if (Array.isArray(o.attacks)) c.attacks = o.attacks.map((a) => ({ ...a }));
    }
    mod.planilhas.aplicarGolpesDasPlanilhas((id) => lista.filter((c) => c.pokeId === id));
    mod.baseOutland.herdarBaseOutland(lista);
    mod.evolucoes.aplicarCadeiasTruncadas(lista);
    mod.evolucoes.normalizarEvolveLevel600(lista);
    const mapa = new Map();
    for (const c of lista) {
      if (mod.outland.isEspelhoFantasmaPokeId(c.pokeId)) continue;
      for (const l of c.loot ?? []) l.name = mod.alias.resolverNomeItem(l.name);
      mod.especiais.injetarGolpesEspeciais(c);
      mapa.set(c.pokeId, c);
    }
    mod.golpesOrre.herdarGolpesOrre(lista);
    for (const mega of mod.megas.criarEspeciesMega(lista)) mapa.set(mega.pokeId, mega);
    return mapa;
  }

  // Só os campos que a simulação usa — o resto do catálogo não precisa atravessar a ponte.
  const enxuta = (e) => ({
    pokeId: e.pokeId, nome: e.name, dex: e.dex ?? e.nationalDex ?? null,
    type1: e.type1 ?? null, type2: e.type2 ?? null,
    baseHp: e.baseHp ?? 0, baseAtk: e.baseAtk ?? 0, baseDef: e.baseDef ?? 0,
    baseSpAtk: e.baseSpAtk ?? 0, baseSpDef: e.baseSpDef ?? 0, baseSpeed: e.baseSpeed ?? 0,
    attacks: (e.attacks ?? []).map((a) => ({
      name: a.name, power: a.power, type: a.type, category: a.category,
      cooldownMs: a.cooldownMs, learnLevel: a.learnLevel ?? 1,
    })),
    loot: (e.loot ?? []).map((l) => ({ name: l.name, chance: l.chance, minCount: l.minCount, maxCount: l.maxCount })),
  });

  /** Carrega módulos + catálogo (uma vez por versão do jogo) e devolve o catálogo enxuto. */
  async function carregar() {
    const inicio = performance.now();
    const pares = await Promise.all(Object.entries(MODULOS).map(async ([k, p]) => [k, await import(url(p))]));
    mod = Object.fromEntries(pares);
    const [cr, novos, outlandNovos, overrides, itens, v] = await Promise.all([
      json('assets/creatures.json'),
      json('assets/creatures-novos.json', true),
      json('assets/creatures-outland-novos.json', true),
      json('assets/creatures-audit-overrides.json', true),
      json('assets/items.json', true),
      versaoNoAr(),
    ]);
    especies = montarCatalogo({ cr, novos, outlandNovos, overrides });
    versao = v;
    const precos = {};
    for (const i of itens?.items ?? itens ?? []) if (i?.name) precos[i.name] = Number(i.npcPrice) || 0;
    return {
      versao,
      especies: [...especies.values()].map(enxuta),
      precoItem: precos,
      vipMultXp: mod.analyser.VIP_MULT_XP ?? 1.5,
      tiposElementais: mod.analyser.TIPOS_ELEMENTAIS ?? [],
      ms: Math.round(performance.now() - inicio),
    };
  }

  /**
   * Tudo o que depende das funções do jogo para UMA análise:
   *  - efetividade amplificada da hunt para todas as combinações de tipos;
   *  - XP e ouro por abate de cada espécie em cada hunt (`recompensa-hunt.mjs`);
   *  - os golpes do pokémon (liberados até o nível, recarga com o desconto do Speed, + TM);
   *  - os multiplicadores de XP que o próprio jogo calcula (`multXpPokemon/Treinador`).
   */
  function preparar(p) {
    if (!mod || !especies) throw new Error('catálogo não carregado');
    const tabela = p.tabelaTipos ?? {};
    const fator = p.ampliacaoHunt ?? 1.5;
    const tipos = new Set([...(mod.analyser.TIPOS_ELEMENTAIS ?? []), ...Object.keys(tabela)]);
    for (const e of especies.values()) { if (e.type1) tipos.add(e.type1); if (e.type2) tipos.add(e.type2); }
    if (p.pk?.tmElemental) tipos.add(p.pk.tmElemental);
    const lista = [...tipos];
    const ef = {};
    // A partir do 1.287 o jogo tirou `efetividadeHunt` do hunt-analyser (a extensão /hunt quebrou por
    // isso). A conta é a mesma de antes e a que a Pokepédia do jogo documenta: a efetividade da tabela
    // (o total dos dois tipos do alvo) amplificada na hunt — ×v vira 1 + (v − 1)·fator na vantagem e
    // v ÷ fator na desvantagem; ×0 e ×1 ficam iguais. Se o jogo voltar a exportar a função, vale a dele.
    const amplificar = (v) => (v === 0 || v === 1 ? v : v > 1 ? 1 + (v - 1) * fator : v / fator);
    const efHunt = typeof mod.analyser.efetividadeHunt === 'function'
      ? (a, d1, d2) => mod.analyser.efetividadeHunt(a, d1, d2, tabela, fator)
      : (a, d1, d2) => amplificar(mod.analyser.efetividade(a, d1, d2, tabela));
    for (const a of lista) for (const d1 of lista) for (const d2 of [...lista, null]) {
      ef[`${a}|${d1}|${d2 ?? ''}`] = efHunt(a, d1, d2);
    }

    const recompensa = {};
    for (const h of p.hunts ?? []) {
      const r = (recompensa[h.slug] = {});
      for (const e of h.especies ?? []) {
        const esp = especies.get(e.pokeId);
        if (!esp) continue;
        r[e.pokeId] = [mod.recompensa.xpPorDerrota(h, h.nivel ?? 1, esp),
          mod.recompensa.ouroPorDerrotaHunt(h, h.nivel ?? 1, esp)];
      }
    }

    let golpes = null;
    const esp = p.pk ? especies.get(p.pk.speciesId) : null;
    if (esp) {
      const comSpeed = (cd) => mod.cooldown.cooldownGolpeComSpeed(cd, esp.baseSpeed, p.pk.ivs?.speed);
      golpes = (esp.attacks ?? [])
        .filter((a) => (a.learnLevel ?? 1) <= (p.pk.level ?? 1))
        .map((a) => ({ name: a.name, power: a.power, type: a.type, category: a.category,
          cooldownMs: comSpeed(a.cooldownMs) }));
      if (p.pk.tmElemental && mod.tm?.golpeTmElemental) {
        const tm = mod.tm.golpeTmElemental(p.pk.tmElemental);
        golpes.push({ name: tm.name, power: tm.power, type: tm.type, category: tm.category,
          cooldownMs: comSpeed(tm.cooldownMs), tm: true });
      }
    }

    const agora = Date.now();
    const eu = p.eu ?? {};
    const tiposBoost = p.tiposBoost ?? [];
    return {
      ef,
      recompensa,
      golpes,
      especie: esp ? enxuta(esp) : null,
      bonusBase: {
        pokemon: mod.analyser.multXpPokemon?.(eu, agora, tiposBoost) ?? 1,
        treinador: mod.analyser.multXpTreinador?.(eu, agora, tiposBoost) ?? 1,
      },
      agora,
    };
  }

  // `_interno` existe só para o teste de equivalência (compara com o motor original do /hunt).
  // ---------------------------------------------------------------- RMT (Mercado da Comunidade)
  // As taxas do mercado vêm do MESMO arquivo que o servidor usa para cobrar.
  async function taxasMercado(casos) {
    const t = await import(url('shared/taxa-mercado.mjs'));
    const fx = (f) => ({ ate: Number.isFinite(f.ate) ? f.ate : null, bp: f.bp });
    const out = {
      FAIXAS_ORB: t.FAIXAS_ORB.map(fx), TAXA_ORB_PLANA: t.TAXA_ORB_PLANA, TAXA_GOLD: t.TAXA_GOLD,
      PRECO_MIN_ORB: t.PRECO_MIN_ORB, PRECO_MIN_GOLD: t.PRECO_MIN_GOLD, versao: await versaoNoAr(),
    };
    // Só no teste de equivalência: as funções do jogo nos mesmos casos do Python.
    if (Array.isArray(casos)) out.casos = casos.map(([total, tipo]) => [t.taxaOrbDaVenda(total, tipo), t.liquidoOrbDaVenda(total, tipo)]);
    return out;
  }

  window.__pnHunt = { carregar, preparar, versaoNoAr, taxasMercado, _interno: () => ({ mod, especies }) };
})();

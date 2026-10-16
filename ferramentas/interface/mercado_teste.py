"""Uma página de TESTE com o Market do PokeIdle (Comprar > Pokébolas), sem login.

Monta só o HTML do modal, do jeito que o `app.js` do jogo monta (`renderMarket`, `pintarMarket`,
`palanqueCompra`), e usa o `estilo.css` e o `mobile.css` REAIS do jogo, baixados do site na versão pedida.
Não tem JavaScript do jogo, não conecta em nada e não tem conta: serve para medir o modal no mesmo
tamanho de página que o PokeNexus dá, e para abrir num navegador comum e comparar.

    .venv\\Scripts\\python.exe ferramentas\\interface\\mercado_teste.py --versao 1.300.2 --pasta <pasta>

Devolve (e imprime) o caminho do `market.html`.
"""
import argparse
import urllib.request
from pathlib import Path

# Os 6 palanques de Pokébolas da 1ª linha + 2ª linha (o print do usuário mostrava duas linhas).
BOLAS = [("Poké Ball", 1, 200), ("Great Ball", 2, 600), ("Super Ball", 3, 1200),
         ("Ultra Ball", 4, 2500), ("Dusk Ball", 4, 5000), ("Quick Ball", 4, 9000)]
CATEGORIAS = [("Pokébolas", "Para capturar"), ("Poções", "Para curar"), ("Revives", "Para reviver"),
              ("Ovos", "Mystery Eggs")]

# A regra do layout de celular do jogo (mobile.mjs, CONSULTAS): só a largura, num desktop.
SCRIPT_MOBILE = """
const consultas = ['(pointer: coarse) and (max-width: 1024px)', '(max-width: 720px)'];
const avaliar = () => document.documentElement.classList.toggle('mobile', consultas.some(q => matchMedia(q).matches));
for (const q of consultas) matchMedia(q).addEventListener('change', avaliar);
avaliar();
"""


def moeda(v: int) -> str:
    return f'<span class="mk-moeda"><img alt="ouro">{v:,}</span>'.replace(",", ".")


def palanque(nome: str, degrau: int, preco: int) -> str:
    return f"""
    <div class="mk-card mk-pal pal-n{degrau}" style="--pal-cor: var(--rar-rara)">
      <div class="mk-pal-palco">
        <span class="mk-pal-feixe"></span><span class="mk-pal-raios"></span><span class="mk-pal-halo"></span>
        <div class="mk-ico mk-pal-arte"><span style="display:block;width:52px;height:52px;border-radius:50%;background:#c33"></span></div>
        <span class="mk-pal-pedestal"></span>
        <span class="mk-tem" data-tem="0">você tem ×0</span>
      </div>
      <div class="mk-nome">{nome}</div>
      <div class="mk-sub">Captura ×{degrau}<span class="mk-medidor"><i class="on"></i><i></i><i></i><i></i></span></div>
      <div class="mk-pal-preco">{moeda(preco)}<small>cada</small></div>
      <div class="mk-rodape">
        <div class="mk-qtd"><button class="mk-passo" type="button">−</button><input type="number" value="1" min="1"><button class="mk-passo" type="button">+</button></div>
        <div class="mk-atalhos"><button class="mk-max mk-atalho" type="button">×10</button><button class="mk-max mk-atalho" type="button">×100</button><button class="mk-max mk-atalho" type="button">Máx</button></div>
        <button class="mk-acao mk-pal-comprar" type="button"><span>Comprar</span>{moeda(preco)}</button>
      </div>
    </div>"""


def pagina() -> str:
    cats = "".join(f'<button type="button" class="mk-cat{" on" if i == 0 else ""}"><span class="mk-cat-bolha"></span>'
                   f'<span class="mk-cat-txt"><b>{n}</b><small>{s}</small></span></button>'
                   for i, (n, s) in enumerate(CATEGORIAS))
    cards = "".join(palanque(*b) for b in BOLAS)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Market (teste)</title>
<link rel="stylesheet" href="estilo.css"><link rel="stylesheet" href="mobile.css">
<script>{SCRIPT_MOBILE}</script></head>
<body>
<div id="modal" class="modal">
  <div class="modal-caixa" data-modal="market">
    <div class="modal-topo"><h2 id="modal-titulo">Market</h2>
      <div class="modal-acoes"><button id="modal-fechar">×</button></div></div>
    <div class="modal-corpo" id="modal-corpo">
      <div class="mk-topo">
        <div class="cmp-switch mk-modos" data-lado="esq"><button type="button" class="cmp-op on">Comprar</button>
          <button type="button" class="cmp-op">Vender</button><span class="cmp-manopla"></span></div>
        <div class="mk-saldo">{moeda(123456)}</div>
      </div>
      <div id="mk-corpo" data-aba="compra" data-tela="compra:bolas">
        <div class="mk-com-lados">
          <nav class="mk-lado"><div class="mk-lado-titulo">Categorias</div>{cats}</nav>
          <div class="mk-grade mk-vitrine">
            <div class="mk-vitrine-cab"><span class="mk-vitrine-ico"></span><span class="mk-vitrine-txt">
              <b>Pokébolas</b><small>Cada bola tem uma chance de captura. Quanto melhor a bola, maior a chance.</small></span></div>
            {cards}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</body></html>"""


# Medida do modal, só leitura (o mesmo texto serve para a página de verdade do jogo).
MEDIR_JS = r"""(() => {
  const r = {iw: innerWidth, ih: innerHeight, dpr: devicePixelRatio,
             mobile: document.documentElement.classList.contains('mobile'),
             versao: (document.querySelector('script[src*="app.js"]')?.src.match(/v=([\d.]+)/) || [])[1] || null};
  const fundo = document.getElementById('modal');
  const cx = fundo && !fundo.classList.contains('hidden') ? fundo.querySelector('.modal-caixa') : null;
  if (cx && cx.dataset.modal === 'market') {
    const b = cx.getBoundingClientRect();
    const cs = getComputedStyle(cx);
    r.modal = {w: Math.round(b.width), h: Math.round(b.height), top: Math.round(b.top), height_css: cs.height,
               max_height: cs.maxHeight, overflow: cs.overflow};
    const g = cx.querySelector('#mk-corpo .mk-grade');
    if (g) {
      r.grade = {h: g.clientHeight, scroll_h: g.scrollHeight, rola: g.scrollHeight > g.clientHeight + 1,
                 colunas: getComputedStyle(g).gridTemplateColumns.split(' ').length,
                 linhas: getComputedStyle(g).gridTemplateRows};
      r.cards = [...g.querySelectorAll('.mk-pal')].map(c => {
        const cb = c.getBoundingClientRect(), bt = c.querySelector('.mk-pal-comprar')?.getBoundingClientRect();
        return {h: Math.round(cb.height), natural: c.scrollHeight,
                botao_fora_px: bt ? Math.max(0, Math.round(bt.bottom - (cb.bottom - 10))) : null};
      });
      r.cortados = r.cards.filter(c => c.botao_fora_px > 0).length;
    }
  }
  return JSON.stringify(r);
})()"""


def preparar(versao: str, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    for f in ("estilo.css", "mobile.css"):
        destino = pasta / f
        if not destino.exists():
            req = urllib.request.Request(f"https://pokeidle.io/{f}?v={versao}",
                                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                destino.write_bytes(resp.read())
    html = pasta / "market.html"
    html.write_text(pagina(), encoding="utf-8")
    return html


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--versao", default="1.300.2")
    ap.add_argument("--pasta", required=True)
    a = ap.parse_args()
    print(preparar(a.versao, Path(a.pasta)))

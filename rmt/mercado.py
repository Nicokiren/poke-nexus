"""NÃO USADO desde a compra na liberação (16/10/2026, rmt/rotina.py + rmt/canal.py); fica como referência.

O Mercado da Comunidade ("RMT") de UMA conta: age pelos botões do próprio jogo (DOM) e lê as
respostas do servidor pelo WebSocket (GameSession.mercado / mercado_eventos). Nada é forjado.

Segurança na própria camada de cliques: o clique só acontece DENTRO do modal do Mercado da
Comunidade, e nunca em depósito, saque, carteira, Loja ou compra de diamantes — mesmo que um
seletor errado aponte para lá (`_JS_CLICAR`).
"""
import asyncio
import time

from browser.cdp import CdpError

TIMEOUT = 15

# Clique protegido: só no modal do Mercado e nunca em dinheiro de verdade.
_JS_CLICAR = r"""(sel) => {
  const e = document.querySelector(sel);
  if (!e) return 'ausente';
  const proibido = e.closest('#cm-deposito, #cm-withdraw, .cm-carteira, [data-modal="withdraw"], [data-modal="diamantes"], '
    + '[data-modal="shop"], [data-modal="orbs"], [data-modal="loja"], #cm-dia-vender, #cm-dia-comprar, .cm-dia-vender')
    || /(deposit|withdraw|saque|sacar|orbs|diamante|pix|usdt)/i.test(`${e.id} ${e.className} ${e.dataset ? Object.values(e.dataset).join(' ') : ''}`);
  if (proibido) return 'proibido';
  const noMercado = e.closest('.cm-folha, #cm-lista, .cm-topo, .cm-filtros, .cm-painel, .cm-corpo, .dlg, .modal')
    || e.matches('button[data-modal="community"]');
  if (!noMercado) return 'fora do mercado';
  if (e.disabled) return 'desabilitado';
  e.click();
  return 'ok';
}"""
_JS_EXISTE = "(sel) => !!document.querySelector(sel)"
_JS_PREENCHER = r"""([sel, valor]) => {
  const e = document.querySelector(sel);
  if (!e) return false;
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e), 'value').set;
  setter.call(e, String(valor));
  e.dispatchEvent(new Event('input', { bubbles: true }));
  e.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}"""
_JS_MODAL = r"""() => {
  const lista = document.querySelector('#cm-lista');
  return { aberto: !!lista, folha: !!document.querySelector('.cm-folha'),
           tipo: document.querySelector('.cm-filtro[data-tipo].on')?.dataset.tipo ?? null,
           meus: !!document.querySelector('#cm-meus.on') };
}"""
_JS_FECHAR_FOLHA = r"""() => { const b = document.querySelector('.cm-folha .cm-fechar'); if (b) { b.click(); return true; } return false; }"""
_JS_FECHAR_MODAL = r"""() => {
  document.querySelector('.cm-folha .cm-fechar')?.click();
  const b = document.querySelector('#modal-fechar');
  if (b) { b.click(); return true; }
  return false;
}"""


class ErroMercado(RuntimeError):
    pass


class Mercado:
    def __init__(self, page, game):
        self.page = page
        self.game = game

    # ------------------------------------------------------------ primitivas
    async def _clicar(self, sel: str, obrigatorio=True) -> bool:
        r = await self.page.evaluate(_JS_CLICAR, sel)
        if r == "ok":
            return True
        if r == "proibido":
            raise ErroMercado(f"clique recusado por segurança ({sel})")
        if obrigatorio:
            raise ErroMercado(f"não consegui clicar em {sel}: {r}")
        return False

    async def _existe(self, sel: str) -> bool:
        return bool(await self.page.evaluate(_JS_EXISTE, sel))

    async def _esperar(self, sel: str, t=TIMEOUT):
        fim = time.monotonic() + t
        while not await self._existe(sel):
            if time.monotonic() > fim:
                raise ErroMercado(f"a tela do mercado não mostrou {sel}")
            await asyncio.sleep(0.25)

    async def _preencher(self, sel: str, valor):
        if not await self.page.evaluate(_JS_PREENCHER, [sel, valor]):
            raise ErroMercado(f"campo {sel} não apareceu")

    async def _resposta(self, teste, desde_seq: int, t=TIMEOUT):
        """Espera uma resposta `market` NOVA (seq > desde_seq) que passe no teste, ou um erro."""
        g = self.game
        fim = time.monotonic() + t
        t0 = time.monotonic()
        while time.monotonic() < fim:
            if g.mercado_seq > desde_seq:
                for chave, m in list(g.mercado.items()):
                    if m.get("_seq", 0) > desde_seq and teste(chave, m):
                        return m
            if g.ultimo_erro and g.ultimo_erro[0] >= t0:
                raise ErroMercado(f"o jogo recusou: {g.ultimo_erro[1]}")
            g.mercado_evento.clear()
            try:
                await asyncio.wait_for(g.mercado_evento.wait(), 0.5)
            except asyncio.TimeoutError:
                pass
        raise ErroMercado("o mercado não respondeu a tempo")

    async def _evento(self, tipos: tuple, depois: float, teste=lambda e: True, t=25) -> dict:
        g = self.game
        fim = time.monotonic() + t
        while time.monotonic() < fim:
            for quando, e in reversed(g.mercado_eventos):
                if quando >= depois and e.get("k") in tipos and teste(e):
                    return e
            if g.ultimo_erro and g.ultimo_erro[0] >= depois:
                raise ErroMercado(f"o jogo recusou: {g.ultimo_erro[1]}")
            g.mercado_evento.clear()
            try:
                await asyncio.wait_for(g.mercado_evento.wait(), 0.5)
            except asyncio.TimeoutError:
                pass
        raise ErroMercado("o jogo não confirmou a operação a tempo")

    # ------------------------------------------------------------ navegação
    async def abrir(self):
        estado = await self.page.evaluate(_JS_MODAL)
        if not estado["aberto"]:
            await self._clicar('button[data-modal="community"]')
            await self._esperar("#cm-lista")
        if await self._existe(".cm-folha"):
            await self.page.evaluate(_JS_FECHAR_FOLHA)

    async def fechar(self):
        try:
            await self.page.evaluate(_JS_FECHAR_MODAL)
        except CdpError:
            pass

    async def vitrine_de_itens(self):
        estado = await self.page.evaluate(_JS_MODAL)
        if estado["tipo"] != "item" or estado["meus"]:
            await self._clicar('.cm-filtro[data-tipo="item"]')
            await asyncio.sleep(0.4)
        if await self._existe('.cm-filtro[data-cat=""]:not(.on)'):
            await self._clicar('.cm-filtro[data-cat=""]')
            await asyncio.sleep(0.4)
        if await self._existe("#cm-busca"):
            await self._preencher("#cm-busca", "")

    async def abrir_item(self, item_id: int, moeda: str) -> list[dict]:
        """Abre o item na vitrine, na moeda pedida, e devolve os anúncios dele (do servidor)."""
        await self.abrir()
        await self.vitrine_de_itens()
        seq = self.game.mercado_seq
        await self._esperar(f'.cmi-linha[data-item="{item_id}"]')
        await self._clicar(f'.cmi-linha[data-item="{item_id}"]')
        if not await self._existe(f'.cmp-op.on[data-swmoeda="{moeda}"]'):
            await self._esperar(f'[data-swmoeda="{moeda}"]')
            await self._clicar(f'[data-swmoeda="{moeda}"]')
        chave = f"item:{item_id}:{moeda}"
        m = await self._resposta(lambda k, _m: k == chave, seq)
        return list(m.get("linhas") or [])

    # ------------------------------------------------------------ compra (em quantidade)
    async def cotar(self, item_id: int, moeda: str, qtd: int) -> dict:
        """Abre a "compra em quantidade" do item e pede a cotação de `qtd` (não compra nada)."""
        await self.abrir_item(item_id, moeda)
        if not await self._existe(".cmi-painel [data-lote]"):
            return {"qtd": 0, "faixas": [], "vendedores": [], "anuncios": 0, "motivo": "sem anúncio de outros jogadores"}
        await self._clicar(".cmi-painel [data-lote]")
        await self._esperar("#cml-num")
        return await self.recotar(item_id, moeda, qtd)

    async def recotar(self, item_id: int, moeda: str, qtd: int) -> dict:
        """Com a folha de compra aberta: digita a quantidade e espera a cotação DELA."""
        seq = self.game.mercado_seq
        await self._preencher("#cml-num", qtd)

        def bate(k, m):
            return (k == "cotacaoLote" and int(m.get("pedido") or 0) == qtd and m.get("moeda") == moeda
                    and int(m.get("itemId") or 0) == item_id)
        return await self._resposta(bate, seq)

    async def comprar_cotado(self, item_id: int, moeda: str, qtd: int) -> dict:
        """Clica no "Comprar" da folha (o jogo manda os tetos da cotação que está na tela)."""
        if not await self._existe("#cml-comprar:not([disabled])"):
            raise ErroMercado("o botão de comprar está desligado (saldo ou cotação)")
        t0 = time.monotonic()
        await self._clicar("#cml-comprar")
        return await self._evento(("marketCompradoLote",), t0,
                                  lambda e: int(e.get("itemId") or 0) == item_id and e.get("moeda") == moeda)

    async def fechar_folha(self):
        await self.page.evaluate(_JS_FECHAR_FOLHA)

    # ------------------------------------------------------------ meus anúncios
    async def meus(self) -> list[dict]:
        await self.abrir()
        seq = self.game.mercado_seq
        await self._clicar("#cm-meus")
        m = await self._resposta(lambda k, _m: k == "meus", seq)
        return list(m.get("linhas") or [])

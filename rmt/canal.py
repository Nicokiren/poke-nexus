"""Manda pedidos do Mercado pela MESMA conexão (WebSocket) que o jogo da conta já tem aberta, sem abrir
nenhuma tela: a página do jogo não pisca e o farm não é interrompido.

O pedido é exatamente o que o botão do jogo manda (`enviar(obj)` do app.js = `ws.send(JSON.stringify(obj))`):
- `{"t": "market.item", "itemId", "moeda"}`: a vitrine de UM item (os anúncios, com `compravelEm`);
- `{"t": "market.comprar", "id", "qtd", "preco", "moeda"}`: compra um anúncio; o servidor confere o preço.

O WebSocket do jogo é achado pelo DevTools (`Runtime.queryObjects` no protótipo do WebSocket): nada é
injetado na página e o código do jogo não é tocado. As respostas chegam pelo caminho de sempre
(game/pokeidle.py escuta os quadros recebidos).

Escolha do usuário (16/10/2026): antes o Mercado só agia pela tela, e cada olhada abria e fechava a
janela do mercado por cima do jogo.
"""
import asyncio
import json

from browser.cdp import CdpError

GRUPO = "pokenexus-mercado"
_ACHAR = """function (filtro) {
  const ok = this.filter((w) => w.readyState === 1 && new RegExp(filtro).test(w.url));
  return ok[ok.length - 1] ?? null;
}"""
_ENVIAR = "function (s) { if (this.readyState !== 1) return false; this.send(s); return true; }"


class CanalFechado(CdpError):
    """A conexão do jogo não está aberta (reconectando, login...)."""


class Canal:
    def __init__(self, page, filtro_url: str = r"pokeidle\.io"):
        self.page = page
        self.filtro_url = filtro_url             # só a conexão do jogo (os testes usam outra)
        self._ws: str | None = None              # objectId do WebSocket do jogo (DevTools)
        self._n = 0
        self._grupo = GRUPO

    async def _achar(self) -> str:
        self._n += 1
        self._grupo = grupo = f"{GRUPO}-{self._n}"
        p = await self.page.send("Runtime.evaluate", {"expression": "WebSocket.prototype", "objectGroup": grupo})
        proto = (p.get("result") or {}).get("objectId")
        if not proto:
            raise CanalFechado("não achei o WebSocket da página")
        q = await self.page.send("Runtime.queryObjects", {"prototypeObjectId": proto, "objectGroup": grupo})
        lista = (q.get("objects") or {}).get("objectId")
        r = await self.page.send("Runtime.callFunctionOn", {"objectId": lista, "functionDeclaration": _ACHAR,
                                                            "arguments": [{"value": self.filtro_url}],
                                                            "objectGroup": grupo})
        ws = (r.get("result") or {}).get("objectId")
        if not ws:
            raise CanalFechado("a conexão do jogo não está aberta")
        return ws

    async def enviar(self, msg: dict) -> None:
        texto = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
        for tentativa in (1, 2):
            try:
                if self._ws is None:
                    self._ws = await self._achar()
                r = await self.page.send("Runtime.callFunctionOn", {
                    "objectId": self._ws, "functionDeclaration": _ENVIAR,
                    "arguments": [{"value": texto}], "returnByValue": True})
                if (r.get("result") or {}).get("value") is True:
                    return
            except CdpError:
                if tentativa == 2:
                    raise
            self.esquecer()                      # o jogo reconectou: outra conexão, acha de novo
        raise CanalFechado("a conexão do jogo não está aberta")

    def esquecer(self):
        """Esquece o WebSocket achado (o jogo reconectou) e solta as referências dele no DevTools."""
        self._ws = None
        grupo = self._grupo
        try:
            asyncio.ensure_future(self.page.send("Runtime.releaseObjectGroup", {"objectGroup": grupo}))
        except Exception:
            pass

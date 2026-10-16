"""Cliente CDP (Chrome DevTools Protocol) mínimo, ligado a UMA página.

O Qt WebEngine expõe o DevTools em 127.0.0.1, mas não aceita a conexão "de navegador
inteiro" que o Playwright exige. Então cada conta conversa direto com a SUA página:
- Network.*        -> ouvir os quadros do WebSocket do jogo (só leitura)
- Runtime.evaluate -> ler o DOM e clicar nos botões do jogo
- Page.*           -> navegar e recarregar
"""
import asyncio
import itertools
import json
import time
import urllib.request

import websockets

# Funções JS auxiliares (recebem o seletor como argumento).
_JS_EXISTE = "(sel) => !!document.querySelector(sel)"
_JS_VISIVEL = """(sel) => { const e = document.querySelector(sel); if (!e) return false;
  const st = getComputedStyle(e);
  return !e.closest('.hidden') && st.display !== 'none' && st.visibility !== 'hidden'; }"""
_JS_CLICAR = """(sel) => { const e = document.querySelector(sel); if (!e || e.disabled) return false;
  e.click(); return true; }"""
_JS_ATRIBUTO = "([sel, nome]) => document.querySelector(sel)?.getAttribute(nome) ?? null"


class CdpError(RuntimeError):
    pass


def list_targets(port: int) -> list[dict]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


class CdpPage:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._ws = None
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._handlers: dict[str, list] = {}
        self._reader: asyncio.Task | None = None
        self._closed = False
        self._dom_ready = asyncio.Event()

    # ------------------------------------------------------------ conexão
    @classmethod
    async def attach(cls, port: int, marker_url: str, timeout: float = 20) -> "CdpPage":
        """Procura a página que está em `marker_url` e conecta nela."""
        loop = asyncio.get_running_loop()
        end = time.monotonic() + timeout
        while True:
            try:
                targets = await loop.run_in_executor(None, list_targets, port)
                for t in targets:
                    if t.get("type") == "page" and t.get("url") == marker_url:
                        page = cls(t["webSocketDebuggerUrl"])
                        await page._connect()
                        return page
            except OSError:
                pass
            if time.monotonic() > end:
                raise CdpError(f"página {marker_url} não apareceu no DevTools")
            await asyncio.sleep(0.3)

    async def _connect(self):
        self._ws = await websockets.connect(self.ws_url, max_size=None, ping_interval=None,
                                            open_timeout=10)
        self._reader = asyncio.create_task(self._read())
        self.on("Page.domContentEventFired", lambda _p: self._dom_ready.set())
        await self.send("Page.enable")
        await self.send("Inspector.enable")
        # Buffers pequenos: não precisamos guardar corpo de resposta nenhum.
        await self.send("Network.enable", {"maxTotalBufferSize": 1_000_000,
                                           "maxResourceBufferSize": 200_000})

    async def _read(self):
        try:
            async for raw in self._ws:
                # Com o Network ligado chegam eventos de TODA requisição da página (imagens,
                # scripts...). Só interpretamos os que alguém assina: o nome do evento vem no
                # começo da mensagem ({"method":"Network.x",...}), sem precisar ler o JSON inteiro.
                if raw.startswith('{"method":"'):
                    fim = raw.find('"', 11)
                    if raw[11:fim] not in self._handlers:
                        continue
                m = json.loads(raw)
                if "id" in m:
                    fut = self._pending.pop(m["id"], None)
                    if fut and not fut.done():
                        if "error" in m:
                            fut.set_exception(CdpError(m["error"].get("message", str(m["error"]))))
                        else:
                            fut.set_result(m.get("result", {}))
                else:
                    for cb in self._handlers.get(m.get("method"), []):
                        try:
                            cb(m.get("params", {}))
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            self._closed = True
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(CdpError("página fechada"))
            self._pending.clear()
            for cb in self._handlers.get("close", []):
                cb({})

    async def close(self):
        """Só desconecta o CDP (a página em si é fechada pelo Qt)."""
        if self._ws:
            await self._ws.close()
        if self._reader:
            await asyncio.gather(self._reader, return_exceptions=True)

    def is_closed(self) -> bool:
        return self._closed

    def on(self, event: str, cb):
        """Eventos CDP ("Network.webSocketFrameReceived"...) ou "close"."""
        self._handlers.setdefault(event, []).append(cb)

    async def send(self, method: str, params: dict | None = None, timeout: float = 30):
        if self._closed:
            raise CdpError("página fechada")
        i = next(self._ids)
        fut = asyncio.get_running_loop().create_future()
        self._pending[i] = fut
        await self._ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(i, None)

    # ------------------------------------------------------------ páginas
    async def evaluate(self, js_function: str, arg=None, timeout: float = 30):
        """Executa uma função JS na página e devolve o resultado (como no Playwright)."""
        expr = f"({js_function})({json.dumps(arg)})" if arg is not None else f"({js_function})()"
        r = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                                 "awaitPromise": True}, timeout)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise CdpError((d.get("exception") or {}).get("description") or d.get("text", "erro de JS"))
        return (r.get("result") or {}).get("value")

    async def goto(self, url: str, timeout: float = 60):
        self._dom_ready.clear()
        r = await self.send("Page.navigate", {"url": url}, timeout)
        if r.get("errorText"):
            raise CdpError(f"falha ao abrir {url}: {r['errorText']}")
        await asyncio.wait_for(self._dom_ready.wait(), timeout)

    async def reload(self, timeout: float = 60):
        self._dom_ready.clear()
        await self.send("Page.reload", {"ignoreCache": False}, timeout)
        await asyncio.wait_for(self._dom_ready.wait(), timeout)

    # ------------------------------------------------------------ DOM
    async def exists(self, selector: str) -> bool:
        return bool(await self.evaluate(_JS_EXISTE, selector))

    async def is_visible(self, selector: str) -> bool:
        return bool(await self.evaluate(_JS_VISIVEL, selector))

    async def get_attribute(self, selector: str, name: str):
        return await self.evaluate(_JS_ATRIBUTO, [selector, name])

    async def wait_for(self, selector: str, timeout: float = 8, visible: bool = True):
        end = time.monotonic() + timeout
        check = self.is_visible if visible else self.exists
        while not await check(selector):
            if time.monotonic() > end:
                raise CdpError(f"elemento não encontrado: {selector}")
            await asyncio.sleep(0.25)

    async def click_presente(self, selector: str, timeout: float = 5):
        """Clica no elemento mesmo escondido (ex.: o menu do layout de celular do jogo fica numa
        gaveta fechada, mas o botão é o mesmo)."""
        await self.wait_for(selector, timeout, visible=False)
        if not await self.evaluate(_JS_CLICAR, selector):
            raise CdpError(f"não deu para clicar em {selector}")

    async def click(self, selector: str, timeout: float = 5):
        """Espera o elemento aparecer e clica nele pelo DOM (sem coordenadas de mouse)."""
        await self.wait_for(selector, timeout)
        if not await self.evaluate(_JS_CLICAR, selector):
            raise CdpError(f"não deu para clicar em {selector}")

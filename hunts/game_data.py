"""Dados e fórmulas do jogo para o Hunt Analyzer, direto da versão no ar do PokeIdle.

Uma única página isolada (sem conta, sem login, sem o jogo, sem WebSocket) é compartilhada por
todas as contas: ela importa os módulos públicos do jogo e os catálogos JSON (hunts/bridge.js).
O catálogo de espécies é igual para todos; o que é de cada conta (pokémon, bônus, hunts
liberadas, medição) nunca passa por aqui misturado — cada análise manda os próprios dados.
"""
import asyncio
import itertools
import time
from pathlib import Path

from app.config import BUNDLE_DIR
from browser.cdp import CdpPage

BRIDGE_JS = BUNDLE_DIR / "hunts" / "bridge.js"
PAGINA_NEUTRA = "https://pokeidle.io/robots.txt"   # do site do jogo, mas sem o jogo
CHECAR_VERSAO_S = 600
OCIOSA_S = 600            # sem nenhuma análise por 10 min = a página de dados é fechada


class GameData:
    def __init__(self, web):
        self.web = web
        self.page: CdpPage | None = None
        self.catalogo: dict | None = None      # {versao, especies{pokeId: esp}, precoItem, vipMultXp}
        self._lock = asyncio.Lock()
        self._versao_checada = 0.0
        self._seq = itertools.count(1)
        self._usado_em = 0.0
        self.erro: str | None = None

    async def _abrir_pagina(self) -> bool:
        """Abre a página de dados se ela não estiver aberta. True = abriu agora (vazia)."""
        if self.page and not self.page.is_closed():
            return False
        marker = f"about:blank#pokenexus-dados-{next(self._seq)}"
        await asyncio.wrap_future(self.web.open_data_page(marker))
        self.page = await CdpPage.attach(self.web.port, marker)
        await self.page.goto(PAGINA_NEUTRA)
        src = BRIDGE_JS.read_text(encoding="utf-8")
        await self.page.evaluate(f"() => {{ {src}\n return !!window.__pnHunt; }}")
        return True

    async def fechar_se_ociosa(self):
        """Ninguém com a aba Hunts aberta há um tempo: fecha a página (e o processo dela). Ela
        volta sozinha, com os módulos do jogo recarregados, na próxima análise."""
        if self.page is None or self._lock.locked() or time.monotonic() - self._usado_em < OCIOSA_S:
            return
        async with self._lock:
            page, self.page = self.page, None
            try:
                await page.close()
            except Exception:
                pass
            await asyncio.wrap_future(self.web.close_data_page())

    async def garantir(self) -> dict:
        """O catálogo carregado (e atualizado se o jogo mudou de versão)."""
        async with self._lock:
            self._usado_em = time.monotonic()
            try:
                nova = await self._abrir_pagina()
                if self.catalogo is None or nova:
                    # Página nova: os módulos do jogo precisam ser importados nela de novo.
                    await self._carregar()
                elif time.monotonic() - self._versao_checada > CHECAR_VERSAO_S:
                    self._versao_checada = time.monotonic()
                    v = await self.page.evaluate("() => window.__pnHunt.versaoNoAr()")
                    if v and v != self.catalogo.get("versao"):
                        await self._carregar()
                self.erro = None
                return self.catalogo
            except Exception as e:
                self.erro = str(e)
                if self.page and self.page.is_closed():
                    self.page = None
                raise

    async def _carregar(self):
        bruto = await self.page.evaluate("() => window.__pnHunt.carregar()", timeout=120)
        self.catalogo = {
            "versao": bruto.get("versao"),
            "especies": {e["pokeId"]: e for e in bruto.get("especies") or []},
            "precoItem": bruto.get("precoItem") or {},
            "vipMultXp": bruto.get("vipMultXp") or 1.5,
            "carregado_em": time.time(),
            "ms": bruto.get("ms"),
        }
        self._versao_checada = time.monotonic()

    async def preparar(self, payload: dict) -> dict:
        """Efetividade, XP/ouro por abate, golpes do pokémon e bônus base — pelas funções do jogo."""
        await self.garantir()
        self._usado_em = time.monotonic()
        return await self.page.evaluate("(p) => window.__pnHunt.preparar(p)", payload, timeout=60)

    async def taxas_mercado(self, casos=None) -> dict:
        """Constantes de taxa do Mercado da Comunidade (shared/taxa-mercado.mjs da versão no ar)."""
        async with self._lock:
            self._usado_em = time.monotonic()
            await self._abrir_pagina()
        return await self.page.evaluate("(c) => window.__pnHunt.taxasMercado(c)", casos, timeout=60)

    async def recarregar(self):
        async with self._lock:
            self.catalogo = None
        await self.garantir()

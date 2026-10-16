"""Mercado 3.0: compra na liberação, para UMA conta (a lista de compras fica em rmt/compras.py).

Como funciona (pedido do usuário, 16/10/2026):
- Nada abre na tela. A vitrine de cada item LIGADO é pedida pela mesma conexão do jogo (rmt/canal.py,
  `market.item`), uma vez a cada `intervalo_s` (padrão 60 s). Todo anúncio novo fica retido
  `cooldownCompraMs` (2 min, vem do servidor) antes de poder ser comprado, então olhar uma vez por minuto
  basta para ver todos ANTES de liberarem.
- Achou anúncio até o preço máximo:
  - ainda retido: a compra é marcada para o instante em que ele libera (`compravelEm`, no relógio do
    servidor, mais MARGEM_MS). Na hora, UM pedido `market.comprar` com o preço do anúncio (o servidor
    confere). Quem pede nos primeiros 3 s depois de liberar entra no sorteio do jogo; perder não custa
    nada. Pedir mais de uma vez não dá mais chance, então a rotina não repete o pedido (só tenta de novo
    se o servidor disser que ainda estava retido, porque o relógio daqui adiantou);
  - já liberado: compra na hora.
- Sem dinheiro: espera e volta a comprar quando entrar saldo (não desliga). Limite do dia: espera o dia
  seguinte. Limite de unidades ou de gasto: desliga o item.
- Nunca compra anúncio das outras contas do PokeNexus (com o bloqueio ligado) e duas contas do PokeNexus
  nunca disputam o MESMO anúncio (`_RESERVAS`).
- Como nada é clicado, as batalhas e o controle manual não atrapalham. A compra para com a conta sem
  conexão, na tela de login ou com a automação pausada.
- Um erro do jogo não desliga o item de primeira (o anúncio pode ter sido vendido ou cancelado); 3 erros
  seguidos desligam, com o motivo.
"""
import asyncio
import time

from rmt.canal import Canal, CanalFechado
from rmt.compras import Lista
from rmt.regras import NOME_MOEDA

INTERVALO_PADRAO_S = 60
INTERVALO_MIN_S = 15            # olhar a vitrine mais que isso não ajuda (a retenção dá 2 min de aviso)
FOLGA_RETENCAO_S = 20           # o intervalo nunca passa da retenção menos isto (para não perder anúncio)
MARGEM_MS = 400                 # pede este tanto DEPOIS de liberar (o relógio daqui pode estar um pouco atrás)
CONFERIR_ANTES_S = 8            # confere a vitrine este tanto antes de liberar
TENTATIVAS_RETIDO = 3           # o servidor disse "ainda retido": tenta de novo (ainda dentro dos 3 s)
ESPERA_RETIDO_S = 0.6
RESPOSTA_S = 8                  # quanto espera o resultado de um pedido (o sorteio leva uns 3 s)
ESPERA_SALDO_S = 60
ERROS_PARA_DESLIGAR = 3

# anúncio -> a conta que pede (ou já pediu) ele: as contas do PokeNexus nunca disputam o mesmo anúncio.
# Só sai daqui se a compra marcada for cancelada (item desligado, sessão fechada), para outra conta poder.
_RESERVAS: dict[int, str] = {}
_MAX_RESERVAS = 3000

PERDEU = ("sorteioPerdeu",)
PENDENTE = ("market.sorteio", "market.sorteioEspera")
RETIDO = ("reten", "retid")
DO_MERCADO = ("saldo", "anuncio", "anúncio", "compra", "orbs", "gold")


def _hora(ms_servidor: float, agora_srv: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(time.time() + (ms_servidor - agora_srv) / 1000))


class RmtRotina:
    def __init__(self, worker, data, proprios):
        """worker: AccountWorker; data: GameData (não usado); proprios(): nicks (minúsculos) e ids de
        TODAS as contas do PokeNexus."""
        self.w = worker
        self.data = data
        self.proprios = proprios
        self.lista = Lista(worker.acc.profile_dir)
        self.ocupado = False
        self.status: dict = {}                   # item.id -> {"texto", "tipo", "quando"}
        self.menor_visto: dict = {}              # (item_id, moeda) -> menor preço visto na última olhada
        self._olhou: dict = {}                   # item.id -> quando pediu a vitrine (monotonic)
        self._agendados: dict[int, asyncio.Task] = {}   # anúncio -> compra marcada
        self._tentados: set[int] = set()         # anúncios já pedidos (um pedido por anúncio)
        self._erros: dict = {}                   # item.id -> erros seguidos

        self._lock = asyncio.Lock()              # um pedido de compra por vez nesta conta
        self._canal: Canal | None = None

    # ------------------------------------------------------------ estado
    @property
    def ligado(self) -> bool:
        return any(i.ligado for i in self.lista.itens)

    def _anotar(self, item, tipo: str, texto: str):
        self.status[item.id] = {"texto": texto, "tipo": tipo, "quando": time.time()}

    def ligar_item(self, iid: str):
        i = self.lista.item(iid)
        if i:
            i.ligado, i.desligado_por = True, ""
            self._olhou.pop(i.id, None)
            self._erros.pop(i.id, None)
            self.lista.salvar()
            self._anotar(i, "espera", "Ligado: vai olhar a vitrine em instantes")
            self.w.log(f"Mercado: ligou {i.resumo()} ({i.limites_txt()})")

    def desligar_item(self, iid: str, motivo: str = ""):
        i = self.lista.item(iid)
        if i and i.ligado:
            i.ligado, i.desligado_por = False, motivo
            self.lista.salvar()
            self._cancelar_do_item(i)
            self._anotar(i, "parado", f"Parado: {motivo}" if motivo else "Desligado")
            self.w.log(f"Mercado: desligou {i.item_nome}" + (f" ({motivo})" if motivo else ""))

    def parar(self, motivo: str = "parado pelo usuário"):
        """Desliga todos os itens da conta (Parar todas as compras)."""
        for i in self.lista.itens:
            if i.ligado:
                self.desligar_item(i.id, motivo)

    def ligar(self):          # compatibilidade: quem liga é cada item
        pass

    def _cancelar_do_item(self, item):
        for aid, t in list(self._agendados.items()):
            if getattr(t, "pn_item", None) == item.id:
                t.cancel()
                self._agendados.pop(aid, None)
                _RESERVAS.pop(aid, None)

    def suspender(self, motivo: str):
        """A sessão da conta fechou: a lista continua ligada; as compras marcadas são canceladas."""
        for aid, t in list(self._agendados.items()):
            t.cancel()
            _RESERVAS.pop(aid, None)
        self._agendados.clear()
        self._canal = None
        for i in self.lista.itens:
            if i.ligado:
                self._anotar(i, "parado", f"Parado: {motivo}")

    # ------------------------------------------------------------ condições
    def _conta_parada(self) -> str | None:
        """Por que a conta não pode comprar AGORA. Os itens ficam ligados e esperam."""
        w, g = self.w, self.w.game
        if g is None or w.page is None or not g.welcomed or not g.ws_open or g.error_key:
            return "a conta está sem conexão (ou na tela de login)"
        if w.mode == "pausado":
            return "a automação desta conta está pausada"
        return None

    def _intervalo(self) -> float:
        ret = float((self.w.game.mercado_info or {}).get("cooldownCompraMs") or 120_000) / 1000
        teto = max(INTERVALO_MIN_S, ret - FOLGA_RETENCAO_S)
        v = int(self.lista.config.intervalo_s or 0)
        if v < INTERVALO_MIN_S:                  # 0 era "sem espera entre compras" no Mercado antigo
            v = INTERVALO_PADRAO_S
        return min(teto, v)

    def _canal_da_pagina(self) -> Canal:
        if self._canal is None or self._canal.page is not self.w.page:
            self._canal = Canal(self.w.page)
        return self._canal

    # ------------------------------------------------------------ o laço
    async def tick(self):
        """Chamado a cada volta do laço da conta: pede a vitrine dos itens que já podem olhar de novo e
        marca as compras. Nada aqui espera resposta (a resposta chega pelo WebSocket)."""
        itens = [i for i in self.lista.itens if i.ligado]
        if not itens:
            return
        parada = self._conta_parada()
        if parada:
            for i in itens:
                self._anotar(i, "parado", f"Parado: {parada}")
            return
        agora = time.monotonic()
        for item in itens:
            self._avaliar(item)                  # o que já chegou (inclusive se a pessoa abriu o mercado)
            if agora - self._olhou.get(item.id, -1e9) < self._intervalo():
                continue
            self._olhou[item.id] = agora
            try:
                await self._canal_da_pagina().enviar({"t": "market.item", "itemId": item.item_id, "moeda": item.moeda})
            except CanalFechado:
                self._anotar(item, "parado", "Parado: a conexão do jogo está reabrindo")
                continue
            except Exception as e:
                self._anotar(item, "espera", f"Não consegui olhar a vitrine agora ({e}); tenta de novo")
                continue
            # a resposta chega pelo WebSocket e é avaliada na próxima volta (a retenção dá folga de sobra)


    def _linhas(self, item) -> list[dict]:
        m = self.w.game.mercado.get(f"item:{item.item_id}:{item.moeda}") or {}
        return list(m.get("linhas") or [])

    def _de_outra_conta(self, l: dict) -> bool:
        if not self.lista.config.bloquear_proprias:
            return False
        p = self.proprios()
        return l.get("vendedorId") in p or str(l.get("vendedor", "")).strip().lower() in p

    def _qtd_possivel(self, item, preco: int, disponivel: int) -> tuple[int, str]:
        """Quantas unidades dá para pedir agora, e o motivo se for 0."""
        item.virar_dia()
        m = NOME_MOEDA[item.moeda]
        g = self.w.game
        saldo = int(g.eu.get("orbs" if item.moeda == "orb" else "gold") or 0)
        qtd = disponivel
        if item.lim_unidades:
            qtd = min(qtd, item.lim_unidades - item.comprado_total)
        if item.lim_gasto:
            qtd = min(qtd, (item.lim_gasto - item.gasto_total) // preco)
        if item.lim_dia:
            qtd = min(qtd, (item.lim_dia - item.gasto_hoje) // preco)
            if qtd <= 0 and item.lim_dia - item.gasto_hoje < preco:
                return 0, f"limite do dia ({item.lim_dia} {m}): volta amanhã"
        if saldo < preco:
            return 0, f"saldo: sem {m} para pagar {preco} {m}"
        return max(0, min(qtd, saldo // preco)), ""

    def _avaliar(self, item):
        """Olha os anúncios que chegaram e marca (ou faz) as compras."""
        if not item.ligado:
            return
        m = NOME_MOEDA[item.moeda]
        if item.lim_unidades and item.comprado_total >= item.lim_unidades:
            return self.desligar_item(item.id, f"chegou ao limite de {item.lim_unidades} unidades")
        if item.lim_gasto and item.gasto_total >= item.lim_gasto:
            return self.desligar_item(item.id, f"chegou ao limite de gasto ({item.lim_gasto} {m})")
        linhas = self._linhas(item)
        if not linhas and item.id not in self.status:
            return
        g = self.w.game
        agora_srv = g.agora_servidor_ms()
        outros = [l for l in linhas if not self._de_outra_conta(l)]
        menor = min((int(l.get("preco") or 0) for l in outros), default=None)
        if menor:
            self.menor_visto[(item.item_id, item.moeda)] = menor
        bons = sorted((l for l in outros if 0 < int(l.get("preco") or 0) <= item.preco_max and int(l.get("qtd") or 0) > 0),
                      key=lambda l: (int(l.get("compravelEm") or 0), int(l["preco"])))
        for l in bons:
            aid = int(l["id"])
            if aid in self._tentados or aid in self._agendados or _RESERVAS.get(aid, self.w.acc.name) != self.w.acc.name:
                continue
            _RESERVAS[aid] = self.w.acc.name
            libera = int(l.get("compravelEm") or 0)
            t = asyncio.ensure_future(self._comprar_na_hora(item, l, libera))
            t.pn_item = item.id
            self._agendados[aid] = t
        # o status: o que está marcado, ou o menor preço do momento
        marcados = [(int(l.get("compravelEm") or 0), l) for l in bons if int(l["id"]) in self._agendados]
        if self.status.get(item.id, {}).get("tipo") in ("comprou", "pedindo", "perdeu") and \
                time.time() - self.status[item.id]["quando"] < 20:
            return                               # deixa o resultado da compra à vista por um tempo
        if marcados:
            libera, l = min(marcados, key=lambda x: x[0])
            if libera > agora_srv:
                falta = int((libera - agora_srv) / 1000)
                self._anotar(item, "agendado", f"Anúncio de {l.get('qtd')} por {l['preco']} {m} cada: compra às "
                             f"{_hora(libera, agora_srv)}, quando liberar (faltam {falta // 60}:{falta % 60:02d})")
            return
        intervalo = int(self._intervalo())
        if menor is None:
            self._anotar(item, "procurando", f"Procurando: nenhum anúncio de outro jogador agora (olha a cada {intervalo} s)")
        else:
            self._anotar(item, "procurando", f"Procurando: menor preço agora {menor} {m} (o seu máximo é "
                         f"{item.preco_max}; olha a cada {intervalo} s)")

    # ------------------------------------------------------------ uma compra
    async def _comprar_na_hora(self, item, anuncio: dict, libera_ms: int):
        aid = int(anuncio["id"])
        try:
            g = self.w.game
            espera = (libera_ms + MARGEM_MS - g.agora_servidor_ms()) / 1000
            if espera > CONFERIR_ANTES_S + 2:
                # pouco antes de liberar, olha a vitrine de novo: o vendedor pode ter tirado o anúncio
                await asyncio.sleep(espera - CONFERIR_ANTES_S)
                seq = g.mercado_seq
                await self._canal_da_pagina().enviar({"t": "market.item", "itemId": item.item_id, "moeda": item.moeda})
                fim = time.monotonic() + 4
                chave = f"item:{item.item_id}:{item.moeda}"
                while time.monotonic() < fim and (g.mercado.get(chave) or {}).get("_seq", 0) <= seq:
                    g.mercado_evento.clear()
                    try:
                        await asyncio.wait_for(g.mercado_evento.wait(), 0.3)
                    except asyncio.TimeoutError:
                        pass
                atual = next((l for l in self._linhas(item) if int(l.get("id") or 0) == aid), None)
                if (g.mercado.get(chave) or {}).get("_seq", 0) > seq and (
                        atual is None or int(atual.get("preco") or 0) > item.preco_max):
                    return self._anotar(item, "procurando", "O anúncio saiu (ou mudou de preço) antes de liberar; segue olhando")
                anuncio = atual or anuncio
                espera = (libera_ms + MARGEM_MS - g.agora_servidor_ms()) / 1000
            if espera > 0:
                await asyncio.sleep(espera)
            await self._pedir(item, anuncio)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._anotar(item, "espera", f"A compra não saiu ({e})")
        finally:
            self._agendados.pop(aid, None)
            if aid not in self._tentados:        # não chegou a pedir: outra conta pode
                _RESERVAS.pop(aid, None)
            for velho in list(_RESERVAS)[:-_MAX_RESERVAS]:
                _RESERVAS.pop(velho, None)

    async def _pedir(self, item, anuncio: dict):
        aid, preco, moeda = int(anuncio["id"]), int(anuncio["preco"]), item.moeda
        m = NOME_MOEDA[moeda]
        async with self._lock:
            if not item.ligado or item not in self.lista.itens:
                return
            parada = self._conta_parada()
            if parada:
                return self._anotar(item, "parado", f"Parado: {parada}")
            qtd, motivo = self._qtd_possivel(item, preco, int(anuncio.get("qtd") or 1))
            if qtd <= 0:
                if motivo.startswith("saldo"):
                    return self._anotar(item, "espera", "Esperando dinheiro: " + motivo[len("saldo: "):])
                if motivo:
                    return self._anotar(item, "espera", "Limite do dia: " + motivo[len("limite do dia "):])
                return self.desligar_item(item.id, "o que sobrou do limite não paga mais nenhuma unidade")
            self._tentados.add(aid)              # um pedido por anúncio (fora o "ainda retido")
            g = self.w.game
            saldo0 = int(g.eu.get("orbs" if moeda == "orb" else "gold") or 0)
            for tentativa in range(TENTATIVAS_RETIDO):
                t0 = time.monotonic()
                await self._canal_da_pagina().enviar({"t": "market.comprar", "id": aid, "qtd": qtd, "preco": preco, "moeda": moeda})
                if tentativa == 0:
                    self.w.log(f"Mercado: pediu {qtd}× {item.item_nome} por {preco} {m} cada (anúncio {aid})")
                    self._anotar(item, "pedindo", f"Pediu {qtd} por {preco} {m} cada: esperando o resultado")
                r = await self._resultado(t0, saldo0, moeda)
                if r[0] != "retido":
                    break
                await asyncio.sleep(ESPERA_RETIDO_S)
            tipo, info = r
            if tipo == "comprou":
                total = saldo0 - int(g.eu.get("orbs" if moeda == "orb" else "gold") or 0)
                total = total if total > 0 else qtd * preco
                item.registrar_compra(qtd, preco, total)
                self._erros.pop(item.id, None)
                self.lista.salvar()
                self.lista.registrar(acao="comprou", item_id=item.id, item=item.item_nome, moeda=moeda, qtd=qtd,
                                     preco=preco, total=total, anuncio=aid)
                self.w.log(f"Mercado: comprou {qtd}× {item.item_nome} por {total} {m}")
                self._anotar(item, "comprou", f"Comprou {qtd} por {preco} {m} cada")
            elif tipo == "perdeu":
                self.w.log(f"Mercado: outro jogador levou o anúncio {aid} de {item.item_nome} no sorteio")
                self._anotar(item, "perdeu", "Outro jogador levou no sorteio da liberação (não pagou nada); segue olhando")
            elif tipo == "sem_resposta":
                self._anotar(item, "espera", "O jogo não respondeu a compra a tempo; segue olhando")
            else:
                n = self._erros[item.id] = self._erros.get(item.id, 0) + 1
                self.w.log(f"Mercado: o jogo recusou a compra de {item.item_nome}: {info}")
                if n >= ERROS_PARA_DESLIGAR:
                    self.desligar_item(item.id, f"o jogo recusou {n} compras seguidas ({info})")
                else:
                    self._anotar(item, "espera", f"O jogo recusou ({info}); segue olhando")
            self._olhou.pop(item.id, None)       # olha a vitrine de novo na próxima volta

    async def _resultado(self, t0: float, saldo0: int, moeda: str) -> tuple[str, str]:
        """comprou | perdeu | retido | recusou | sem_resposta, pelo que o servidor mandou depois de t0."""
        g = self.w.game
        fim = time.monotonic() + RESPOSTA_S
        pendente = False
        while time.monotonic() < fim:
            for quando, e in g.mercado_eventos:
                if quando >= t0 and e.get("k") in ("marketComprado", "marketCompradoLote"):
                    return "comprou", str(e.get("descricao") or "")
            for quando, chave, _p in g.avisos:
                if quando < t0:
                    continue
                if any(p in chave for p in PERDEU):
                    return "perdeu", chave
                if chave in PENDENTE:
                    if not pendente:
                        pendente, fim = True, max(fim, time.monotonic() + RESPOSTA_S)
                    continue
                if any(p in chave.lower() for p in RETIDO):
                    return "retido", chave
                if chave.startswith(("market", "cm.")) or any(p in chave.lower() for p in DO_MERCADO):
                    return "recusou", chave
                # outro aviso qualquer (chat, farm): não é desta compra
            g.mercado_evento.clear()
            try:
                await asyncio.wait_for(g.mercado_evento.wait(), 0.3)
            except asyncio.TimeoutError:
                pass
        saldo = int(g.eu.get("orbs" if moeda == "orb" else "gold") or 0)
        if saldo < saldo0:                       # o evento não chegou, mas o dinheiro saiu
            return "comprou", "saldo baixou"
        return "sem_resposta", ""

    # ------------------------------------------------------------ para a tela
    def view(self) -> dict:
        g = self.w.game
        for i in self.lista.itens:
            i.virar_dia()
        return {
            "ocupado": bool(self._agendados) or self._lock.locked(), "config": self.lista.config,
            "itens": list(self.lista.itens), "status": dict(self.status),
            "conectada": bool(g and g.welcomed),
            "saldo": {"gold": (g.eu.get("gold") if g else None), "orb": (g.eu.get("orbs") if g else None)},
        }

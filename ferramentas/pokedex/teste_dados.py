"""Testes da Pokédex sem tela e sem rede: a lista (sprites ∩ catálogo), a chave do jogo, a leitura da
Pokédex do jogo pelas mensagens (welcome, estado com dexMud/dexFora, evento capturado, cheio, conta trocada) e o
arquivo da conta. Tudo com dados FALSOS montados aqui (nenhum dado de conta real).

    .venv\\Scripts\\python.exe ferramentas\\pokedex\\teste_dados.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from game import pokedex as P  # noqa: E402
from game.pokeidle import GameSession  # noqa: E402

falhas = []


def confere(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"{'ok   ' if ok else 'FALHA'} {nome}: {obtido!r}" + ("" if ok else f" (esperado {esperado!r})"))
    if not ok:
        falhas.append(nome)


# ------------------------------------------------------------ 1. a lista
tmp = Path(tempfile.mkdtemp(prefix="pn_dex_"))
sprites = tmp / "sprites"
sprites.mkdir()
for n in (1, 4, 6, 25, 152, 252, 400):            # 400: sprite sem espécie no catálogo falso
    (sprites / f"{n}.gif").write_bytes(b"GIF89a")
(sprites / "leia-me.txt").write_text("não é sprite")
(sprites / "x.gif").write_bytes(b"GIF89a")
confere("números dos sprites (ignora o que não é número)", sorted(P.numeros_dos_sprites(sprites)), [1, 4, 6, 25, 152, 252, 400])
catalogo = {
    1: {"nome": "Bulbasaur", "type1": "GRASS", "type2": "POISON"},
    4: {"nome": "Charmander", "type1": "FIRE"},
    6: {"nome": "Charizard", "type1": "FIRE", "type2": "FLYING"},
    25: {"nome": "Pikachu", "type1": "ELECTRIC"},
    152: {"nome": "Chikorita", "type1": "GRASS"},
    201: {"nome": "Unown", "type1": "PSYCHIC"},                # espécie sem sprite
    252: {"nome": "Treecko", "type1": "GRASS"},
    13252: {"nome": "Treecko", "type1": "GRASS"},              # clone Orre: não é entrada própria
    3006: {"nome": "Mega Charizard X", "type1": "FIRE"},       # Mega: fica de fora
    4019: {"nome": "Rattata Alola", "type1": "DARK"},          # Forma: fica de fora
    2050: {"nome": "Furious Scizor", "type1": "BUG"},          # Outland: fica de fora
}
lista = P.montar_lista(P.numeros_dos_sprites(sprites), catalogo)
confere("lista = sprites ∩ espécies base", [e["dex"] for e in lista], [1, 4, 6, 25, 152, 252])
confere("nome e tipos em português", (lista[0]["nome"], lista[0]["tipos"]), ("Bulbasaur", ["Planta", "Venenoso"]))
confere("região", [e["regiao"] for e in lista], ["Kanto", "Kanto", "Kanto", "Kanto", "Johto", "Hoenn"])
sem_cat = P.montar_lista(P.numeros_dos_sprites(sprites), None)
confere("sem catálogo: os sprites, sem nome", ([e["dex"] for e in sem_cat], sem_cat[0]["nome"]), ([1, 4, 6, 25, 152, 252, 400], ""))
confere("catálogo com chave texto", [e["dex"] for e in P.montar_lista({1, 4}, {"1": {"nome": "B"}, "4": {"nome": "C"}})], [1, 4])

# ------------------------------------------------------------ 2. a chave do jogo (shared/pokedex.mjs)
for pid, chave in ((25, 25), ("25", 25), (13252, 252), (14009, 9), (2050, 2050), (10530, 2030), (3006, 3006),
                   (4019, 4019), (1001, 1001), (0, None), (-3, None), ("x", None), (None, None)):
    confere(f"chave_pokedex({pid!r})", P.chave_pokedex(pid), chave)

# ------------------------------------------------------------ 3. capturado = c > 0
dex = {"1": {"k": 40, "c": 2}, "4": {"k": 9, "c": 0}, "6": {"k": 3}, "13252": {"k": 1, "c": 1}, "3006": {"k": 0, "c": 1},
       "25": "lixo", "x": {"c": 5}}
confere("só c > 0; 13xxx vira a base; Mega fica com a chave dela", sorted(P.capturados(dex)), [1, 252, 3006])
confere("visto sem captura (só k) não conta", 4 in P.capturados(dex) or 6 in P.capturados(dex), False)
confere("soma a chave do número e a do clone", sorted(P.capturados({"252": {"c": 0}, "13252": {"c": 1}})), [252])
confere("reforço: coleção e evento capturado", sorted(P.capturados({}, [25, 13152], [6])), [6, 25, 152])
pr = P.progresso(lista, {1, 25, 252, 3006})
confere("progresso", pr, {"total": (3, 6), "Kanto": (2, 4), "Johto": (0, 1), "Hoenn": (1, 1)})


# ------------------------------------------------------------ 4. a leitura pelas mensagens do jogo
class PaginaFalsa:
    def on(self, *_):
        pass


eventos = []
g = GameSession(PaginaFalsa(), lambda t, d: eventos.append(t))
frame = lambda m: g._on_frame(json.dumps(m))
frame({"t": "welcome", "estado": {"nick": "teste", "id": 77, "pokedex": {"1": {"k": 5, "c": 1}, "4": {"k": 2, "c": 0}},
                                   "pokemons": [{"id": 9, "speciesId": 25}]}, "hunts": []})
confere("welcome: Pokédex inteira", g.dex, {"1": {"k": 5, "c": 1}, "4": {"k": 2, "c": 0}})
confere("welcome: a Pokédex não vai para o estado do jogador", "pokedex" in g.eu, False)
s0 = g.dex_seq
frame({"t": "estado", "estado": {"xp": 10}})
confere("estado sem Pokédex: nada muda", (g.dex_seq, len(g.dex)), (s0, 2))
frame({"t": "estado", "estado": {"dexMud": {"4": {"k": 3, "c": 1}, "152": {"k": 1, "c": 0}}}})
confere("dexMud entra e troca", (g.dex["4"], g.dex["152"], g.dex_seq), ({"k": 3, "c": 1}, {"k": 1, "c": 0}, s0 + 1))
frame({"t": "estado", "estado": {"dexFora": [152]}})
confere("dexFora sai (chave número ou texto)", "152" in g.dex, False)
confere("a coleção continua igual", sorted(p["speciesId"] for p in g.pokemons.values()), [25])
frame({"t": "batalha", "ev": [{"k": "capturado", "pokemon": {"nome": "Treecko", "speciesId": 13252, "level": 5}}]})
confere("evento capturado", (g.dex_capturas, "batalha_fim" in eventos), ([13252], True))
confere("tudo junto", sorted(P.capturados(g.dex, [p["speciesId"] for p in g.pokemons.values()], g.dex_capturas)),
        [1, 4, 25, 252])
frame({"t": "estado", "estado": {"cheio": True, "nick": "outra", "id": 88, "pokedex": {"6": {"k": 1, "c": 1}}}})
confere("cheio (conta trocada): recomeça", g.dex, {"6": {"k": 1, "c": 1}})
frame({"t": "estado", "estado": {"cheio": True, "nick": "outra", "id": 88}})
confere("cheio sem Pokédex: vazia, como no jogo", g.dex, {})
for k in range(60):
    frame({"t": "batalha", "ev": [{"k": "capturado", "pokemon": {"speciesId": k + 1}}]})
confere("guarda só as últimas 50 capturas", (len(g.dex_capturas), g.dex_capturas[0]), (50, 11))
frame({"t": "chat", "msg": "oi", "pokedex": {"1": {"c": 1}}})
confere("mensagem que o PokeNexus não usa não é lida", g.dex, {})

# ------------------------------------------------------------ 5. o arquivo da conta
arq = tmp / "conta_01" / "pokedex.json"
c = P.PokedexConta(arq)
confere("sem arquivo: vazio", (c.atual(), c.ultima), ({}, None))
confere("1ª vez: não é novidade (já estava capturado)", c.atualizar(77, {1, 4}, agora=1000.0), [])
confere("1ª vez: sem data", c.atual(), {1: None, 4: None})
confere("captura nova: com data", (c.atualizar(77, {1, 4, 25}, agora=2000.0), c.atual()[25]), ([25], 2000.0))
confere("solto ou trocado continua contado", (c.atualizar(77, {1}, agora=3000.0), sorted(c.atual())), ([], [1, 4, 25]))
confere("outra conta do jogo no mesmo lugar: lista própria", (c.atualizar(88, {6}, agora=4000.0), c.atual()), ([], {6: None}))
d = json.loads(arq.read_text(encoding="utf-8"))
confere("arquivo: só números e datas, por conta do jogo", (sorted(d["contas"]), d["contas"]["77"]["capturados"]),
        (["77", "88"], {"1": None, "4": None, "25": 2000.0}))
c2 = P.PokedexConta(arq)
confere("relendo: a última conta", (c2.ultima, c2.atual()), ("88", {6: None}))
c2.atualizar(77, {1, 4, 25}, agora=5000.0)
confere("a conta de volta: a lista dela", sorted(c2.atual()), [1, 4, 25])
arq.write_text("{quebrado", encoding="utf-8")
confere("arquivo quebrado: começa vazio, sem erro", P.PokedexConta(arq).atual(), {})
confere("sem id da conta do jogo: não grava", P.PokedexConta(tmp / "z.json").atualizar(None, {1}), [])

# ------------------------------------------------------------ 6. todas as contas
j = P.juntar({"Conta 1": {1: None, 25: 900.0}, "Conta 2": {25: 500.0, 6: 700.0}, "Conta 3": {1: 100.0}})
confere("todas: donos", {n: e["donos"] for n, e in j.items()}, {1: ["Conta 1", "Conta 3"], 25: ["Conta 1", "Conta 2"], 6: ["Conta 2"]})
confere("todas: a primeira captura (sem data = a mais antiga)", {n: e["quando"] for n, e in j.items()}, {1: None, 25: 500.0, 6: 700.0})

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)

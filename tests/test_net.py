"""Rede do mundo compartilhado: um servidor de verdade e dois jogadores conectados neste computador."""
import time

import pytest

from game.net import protocol
from game.net.client import JoinError, WorldClient
from game.net.database import AccountError, Database
from game.net.server import WorldServer


def hello(name, x=5, y=5):
    return {"name": name, "look": {"hair": "curto"}, "map": "vila", "x": x, "y": y, "facing": "down"}


def join(port, name, x=5, y=5, password="1234"):
    """Conecta, cria a conta e entra no mundo. Devolve o cliente e quem já estava lá."""
    client = WorldClient()
    client.open("127.0.0.1", port)
    client.authenticate(name.lower(), password, register=True)
    return client, client.enter(hello(name, x, y))


def wait_for(client, kind, timeout=2.0):
    """Espera chegar uma mensagem do tipo `kind` (as outras ficam guardadas na lista)."""
    end = time.time() + timeout
    seen = []
    while time.time() < end:
        for message in client.poll():
            seen.append(message)
            if message["t"] == kind:
                return message
        time.sleep(0.01)
    raise AssertionError(f"não chegou '{kind}' (chegou: {seen})")


@pytest.fixture
def server():
    srv = WorldServer(host="127.0.0.1", port=0)
    srv.start()
    yield srv
    srv.stop()


def test_mensagens_viram_linhas_e_voltam():
    reader = protocol.LineReader()
    data = protocol.encode({"t": "move", "x": 1}) + protocol.encode({"t": "emote", "text": "Olá"})
    assert reader.feed(data[:7]) == []                     # pedaço incompleto: espera o resto
    assert [m["t"] for m in reader.feed(data[7:])] == ["move", "emote"]
    assert reader.feed(b"lixo que nao e json\n") == []


def test_endereco_com_e_sem_porta():
    assert protocol.parse_address("192.168.0.5") == ("192.168.0.5", protocol.PORT)
    assert protocol.parse_address(" 26.1.2.3:4000 ") == ("26.1.2.3", 4000)
    with pytest.raises(ValueError):
        protocol.parse_address("")


# ------------------------------------------------------------ banco de dados
def test_banco_cria_conta_e_confere_a_senha():
    db = Database(":memory:")
    ana = db.register("Ana", "segredo")
    assert db.login("ANA", "segredo") == ana                 # usuário não diferencia maiúsculas
    with pytest.raises(AccountError, match="incorretos"):
        db.login("ana", "errada")
    with pytest.raises(AccountError, match="incorretos"):
        db.login("ninguem", "segredo")
    with pytest.raises(AccountError, match="já existe"):
        db.register("ana", "outra")
    row = db.conn.execute("SELECT password_hash FROM accounts").fetchone()
    assert "segredo" not in row[0]                           # a senha nunca fica guardada


def test_banco_recusa_usuario_e_senha_invalidos():
    db = Database(":memory:")
    with pytest.raises(AccountError, match="Usuário"):
        db.register("a b", "1234")
    with pytest.raises(AccountError, match="Usuário"):
        db.register("ab", "1234")
    with pytest.raises(AccountError, match="senha"):
        db.register("ana", "12")


def test_banco_guarda_o_personagem_da_conta():
    db = Database(":memory:")
    ana = db.register("ana", "1234")
    assert db.load_character(ana) is None                    # conta nova ainda não tem personagem
    db.save_character(ana, {"name": "Ana", "bets": 10})
    db.save_character(ana, {"name": "Ana", "bets": 25})      # salvar de novo atualiza
    assert db.load_character(ana) == {"name": "Ana", "bets": 25}


def test_banco_continua_no_arquivo(tmp_path):
    path = str(tmp_path / "world.db")
    db = Database(path)
    db.save_character(db.register("ana", "1234"), {"name": "Ana"})
    db.close()
    again = Database(path)                                   # o servidor reabriu: tudo continua lá
    assert again.load_character(again.login("ana", "1234")) == {"name": "Ana"}
    again.close()


# ------------------------------------------------------------ login pela rede
def test_login_devolve_o_personagem_salvo(server):
    client = WorldClient()
    client.open("127.0.0.1", server.port)
    assert client.authenticate("ana", "1234", register=True) is None
    client.save_character({"name": "Ana", "coliseum_wins": 3})
    client.enter(hello("ANA"))
    client.close()
    time.sleep(0.1)
    again = WorldClient()
    again.open("127.0.0.1", server.port)
    assert again.authenticate("ana", "1234") == {"name": "Ana", "coliseum_wins": 3}
    again.close()


def test_senha_errada_deixa_tentar_de_novo(server):
    join(server.port, "ANA")[0].close()
    client = WorldClient()
    client.open("127.0.0.1", server.port)
    with pytest.raises(JoinError, match="incorretos"):
        client.authenticate("ana", "errada")
    assert client.connected                                  # a conexão continua aberta
    assert client.authenticate("ana", "1234") is None
    client.close()


def test_mesma_conta_nao_entra_duas_vezes(server):
    ana, _ = join(server.port, "ANA")
    other = WorldClient()
    other.open("127.0.0.1", server.port)
    with pytest.raises(JoinError, match="já está jogando"):
        other.authenticate("ana", "1234")
    ana.close()
    time.sleep(0.1)
    assert other.authenticate("ana", "1234") is None         # saiu: agora pode
    other.close()


def test_dois_jogadores_se_veem_andando(server):
    ana, others = join(server.port, "ANA")
    assert others == []
    beto, others = join(server.port, "BETO", 8, 8)
    assert [p["name"] for p in others] == ["ANA"]             # quem entra já vê quem estava
    joined = wait_for(ana, "join")
    assert joined["player"]["name"] == "BETO"
    beto.send({"t": "move", "map": "vila", "x": 9, "y": 8, "facing": "right", "run": True})
    move = wait_for(ana, "move")
    assert (move["id"], move["x"], move["facing"], move["run"]) == (beto.id, 9, "right", True)
    beto.send({"t": "emote", "text": "Oi!"})
    assert wait_for(ana, "emote")["text"] == "Oi!"
    beto.close()
    assert wait_for(ana, "leave")["id"] == beto.id
    ana.close()


def test_versao_diferente_e_recusada(server, monkeypatch):
    monkeypatch.setattr("game.net.client.VERSION", protocol.VERSION + 1)
    client = WorldClient()
    client.open("127.0.0.1", server.port)
    with pytest.raises(JoinError, match="Versão"):
        client.authenticate("ana", "1234", register=True)
    assert not client.connected


def test_ninguem_hospedando_explica_o_problema():
    probe = WorldServer(host="127.0.0.1", port=0)
    probe.start()
    port = probe.port
    probe.stop()                                              # porta livre, ninguém escutando
    with pytest.raises(JoinError, match="Não achei ninguém"):
        WorldClient().open("127.0.0.1", port)


def test_quem_hospeda_entra_no_proprio_mundo():
    host = WorldClient()
    host.host(0, ":memory:")
    assert host.hosting and host.connected
    host.authenticate("ana", "1234", register=True)
    assert host.enter(hello("ANA")) == []
    friend, _ = join(host.server.port, "BETO")
    assert wait_for(host, "join")["player"]["name"] == "BETO"
    host.close()
    assert wait_for(friend, "disconnected")                   # o mundo fechou: o amigo fica sabendo
    friend.close()


# ------------------------------------------------------------ duelos (PvP)
def test_desafio_aceito_comeca_o_duelo_nos_dois(server):
    ana, _ = join(server.port, "ANA")
    beto, _ = join(server.port, "BETO")
    ana.send({"t": "challenge", "to": beto.id, "fighter": {"name": "ANA"}})
    challenge = wait_for(beto, "challenge")
    assert (challenge["from"], challenge["name"]) == (ana.id, "ANA")
    beto.send({"t": "answer", "to": ana.id, "yes": True, "fighter": {"name": "BETO"}})
    start_a, start_b = wait_for(ana, "duel_start"), wait_for(beto, "duel_start")
    assert start_a["seed"] == start_b["seed"]                 # mesma semente: mesmos embaralhamentos
    assert (start_a["side"], start_b["side"]) == (0, 1)       # quem desafiou começa
    assert (start_a["foe"]["name"], start_b["foe"]["name"]) == ("BETO", "ANA")
    ana.send({"t": "duel", "action": {"card": 2}})
    assert wait_for(beto, "duel")["action"] == {"card": 2}    # a jogada vai só para o oponente
    beto.close()
    assert wait_for(ana, "duel_end")["reason"] == "left"      # saiu no meio: vitória por W.O.
    ana.close()


def test_desafio_recusado_ou_impossivel(server):
    ana, _ = join(server.port, "ANA")
    beto, _ = join(server.port, "BETO")
    ana.send({"t": "challenge", "to": beto.id, "fighter": {}})
    wait_for(beto, "challenge")
    beto.send({"t": "answer", "to": ana.id, "yes": False})
    assert "recusou" in wait_for(ana, "challenge_denied")["text"]
    beto.send({"t": "status", "battle": True})
    wait_for(ana, "status")
    ana.send({"t": "challenge", "to": beto.id, "fighter": {}})
    assert "batalha" in wait_for(ana, "challenge_denied")["text"]
    ana.send({"t": "challenge", "to": 999, "fighter": {}})
    assert "não está mais" in wait_for(ana, "challenge_denied")["text"]
    ana.close()
    beto.close()


def test_duelo_acabou_libera_os_dois(server):
    ana, _ = join(server.port, "ANA")
    beto, _ = join(server.port, "BETO")
    ana.send({"t": "challenge", "to": beto.id, "fighter": {}})
    wait_for(beto, "challenge")
    beto.send({"t": "answer", "to": ana.id, "yes": True, "fighter": {}})
    wait_for(ana, "duel_start")
    ana.send({"t": "duel_over"})
    beto.send({"t": "duel_over"})
    time.sleep(0.1)
    assert server.duels == {}
    beto.close()
    time.sleep(0.1)
    assert not [m for m in ana.poll() if m["t"] == "duel_end"]   # já tinha acabado: sem W.O.
    ana.close()


def test_mesa_de_troca_so_repassa_para_o_outro(server):
    ana, _ = join(server.port, "ANA")
    beto, _ = join(server.port, "BETO")
    ana.send({"t": "swap_ask", "to": beto.id})
    ask = wait_for(beto, "swap_ask")
    assert (ask["from"], ask["name"]) == (ana.id, "ANA") and "to" not in ask
    ana.send({"t": "swap_ask", "to": 999})                    # ninguém com esse número: some
    beto.send({"t": "swap_cards", "to": ana.id, "cards": ["murrao"]})
    assert wait_for(ana, "swap_cards")["cards"] == ["murrao"]
    ana.close()
    beto.close()

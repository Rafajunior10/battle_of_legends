"""Rede do mundo compartilhado: um servidor de verdade e dois jogadores conectados neste computador."""
import time

import pytest

from game.net import protocol
from game.net.client import JoinError, WorldClient
from game.net.server import WorldServer


def hello(name, x=5, y=5):
    return {"name": name, "look": {"hair": "curto"}, "map": "vila", "x": x, "y": y, "facing": "down"}


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


def test_dois_jogadores_se_veem_andando(server):
    ana, beto = WorldClient(), WorldClient()
    assert ana.connect("127.0.0.1", server.port, hello("ANA")) == []
    others = beto.connect("127.0.0.1", server.port, hello("BETO", 8, 8))
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
    with pytest.raises(JoinError, match="Versão"):
        WorldClient().connect("127.0.0.1", server.port, hello("ANA"))


def test_ninguem_hospedando_explica_o_problema():
    probe = WorldServer(host="127.0.0.1", port=0)
    probe.start()
    port = probe.port
    probe.stop()                                              # porta livre, ninguém escutando
    with pytest.raises(JoinError, match="Não achei ninguém"):
        WorldClient().connect("127.0.0.1", port, hello("ANA"))


def test_quem_hospeda_entra_no_proprio_mundo():
    host = WorldClient()
    assert host.host(hello("ANA"), port=0) == []
    assert host.hosting and host.connected
    friend = WorldClient()
    friend.connect("127.0.0.1", host.server.port, hello("BETO"))
    assert wait_for(host, "join")["player"]["name"] == "BETO"
    host.close()
    assert wait_for(friend, "disconnected")                   # o mundo fechou: o amigo fica sabendo
    friend.close()

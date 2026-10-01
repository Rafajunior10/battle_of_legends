"""A conexão de um jogador com o mundo compartilhado.

O jogo nunca espera a rede: uma thread fica lendo o que chega e põe numa fila (`inbox`); a cada quadro o lobby
pega o que tiver na fila (`poll`). Enviar é rápido (mensagens pequenas), então acontece direto.
"""
from __future__ import annotations

import contextlib
import queue
import socket
import threading

from game.net.protocol import VERSION, LineReader, encode
from game.net.server import WorldServer

CONNECT_TIMEOUT = 5.0


class JoinError(Exception):
    """Não deu para entrar no mundo; a mensagem é mostrada ao jogador."""


class WorldClient:
    def __init__(self):
        self.inbox: queue.Queue[dict] = queue.Queue()
        self.sock: socket.socket | None = None
        self.id: int | None = None
        self.send_lock = threading.Lock()
        self.server: WorldServer | None = None   # só existe em quem hospeda

    @property
    def connected(self) -> bool:
        return self.sock is not None

    @property
    def hosting(self) -> bool:
        return self.server is not None

    def connect(self, host: str, port: int, hello: dict) -> list[dict]:
        """Entra no mundo. Devolve os jogadores que já estavam lá. Levanta JoinError com o motivo."""
        try:
            sock = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
        except OSError as err:
            raise JoinError(f"Não achei ninguém hospedando em {host}:{port}. Confira o endereço e se o "
                                   "amigo já abriu o mundo (e se o firewall deixa o jogo usar a rede).") from err
        sock.sendall(encode(dict(hello, t="hello", version=VERSION)))
        reader = LineReader()
        welcome = None
        try:
            while welcome is None:                         # espera a resposta (com o timeout da conexão)
                data = sock.recv(4096)
                if not data:
                    break
                for message in reader.feed(data):
                    if message["t"] in ("welcome", "error"):
                        welcome = message
                    else:
                        self.inbox.put(message)
        except (OSError, ValueError) as err:
            sock.close()
            raise JoinError("A conexão caiu enquanto entrava no mundo.") from err
        if welcome is None or welcome["t"] == "error":
            sock.close()
            raise JoinError(welcome["text"] if welcome else "O servidor fechou a conexão.")
        sock.settimeout(None)
        self.sock = sock
        self.id = welcome["id"]
        threading.Thread(target=self._read_loop, args=(sock, reader), name="world-reader", daemon=True).start()
        return list(welcome.get("players", []))

    def host(self, hello: dict, port: int) -> list[dict]:
        """Abre o servidor neste computador e entra nele."""
        self.server = WorldServer(port=port)
        try:
            self.server.start()
        except OSError as err:
            self.server = None
            raise JoinError(f"Não consegui abrir o mundo na porta {port}. Talvez o jogo já esteja "
                                   "hospedando em outra janela.") from err
        return self.connect("127.0.0.1", self.server.port, hello)

    def _read_loop(self, sock: socket.socket, reader: LineReader) -> None:
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                for message in reader.feed(data):
                    self.inbox.put(message)
        except (OSError, ValueError):
            pass
        self.inbox.put({"t": "disconnected"})

    # ------------------------------------------------------------ uso pelo jogo
    def send(self, message: dict) -> None:
        if self.sock is None:
            return
        try:
            with self.send_lock:
                self.sock.sendall(encode(message))
        except OSError:
            self.inbox.put({"t": "disconnected"})

    def poll(self) -> list[dict]:
        """Tudo que chegou desde a última vez (sem esperar)."""
        messages = []
        while True:
            try:
                messages.append(self.inbox.get_nowait())
            except queue.Empty:
                return messages

    def close(self) -> None:
        if self.sock is not None:
            with contextlib.suppress(OSError):
                self.sock.close()
            self.sock = None
        if self.server is not None:
            self.server.stop()
            self.server = None

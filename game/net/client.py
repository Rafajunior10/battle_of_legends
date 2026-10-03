"""A conexão de um jogador com o mundo compartilhado.

Etapas: `open` (conecta) -> `authenticate` (login ou criar conta; devolve o personagem salvo) -> `enter`
(entra no mundo; devolve quem já está lá). Depois disso o jogo nunca espera a rede: uma thread fica lendo o
que chega e põe numa fila (`inbox`); a cada quadro o lobby pega o que tiver (`poll`). Enviar é rápido
(mensagens pequenas), então acontece direto.
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
    """Não deu para entrar (conexão, login, versão...); a mensagem é mostrada ao jogador."""


class WorldClient:
    def __init__(self):
        self.inbox: queue.Queue[dict] = queue.Queue()
        self.sock: socket.socket | None = None
        self.reader = LineReader()
        self.id: int | None = None
        self.send_lock = threading.Lock()
        self.server: WorldServer | None = None   # só existe em quem hospeda
        self.initial_players: list[dict] = []    # quem já estava no mundo quando você entrou
        self.initial_npcs: list[dict] = []       # onde cada NPC estava (a vida dos NPCs roda no servidor)
        self.initial_clock: dict | None = None   # dia e hora do mundo (o servidor manda no relógio)

    @property
    def connected(self) -> bool:
        return self.sock is not None

    @property
    def hosting(self) -> bool:
        return self.server is not None

    # ------------------------------------------------------------ etapas de entrada
    def open(self, host: str, port: int) -> None:
        try:
            self.sock = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
        except OSError as err:
            raise JoinError(f"Não achei ninguém hospedando em {host}:{port}. Confira o endereço e se o "
                            "mundo já está aberto (e se o firewall deixa o jogo usar a rede).") from err

    def host(self, port: int, db_path: str) -> None:
        """Abre o servidor neste computador (com o banco em `db_path`) e conecta nele."""
        try:
            self.server = WorldServer(port=port, db_path=db_path)
            self.server.start()
        except OSError as err:
            self.server = None
            raise JoinError(f"Não consegui abrir o mundo na porta {port}. Talvez o jogo já esteja "
                            "hospedando em outra janela.") from err
        self.open("127.0.0.1", self.server.port)

    def authenticate(self, user: str, password: str, register: bool = False) -> dict | None:
        """Login (ou cria a conta). Devolve o personagem salvo no servidor, ou None se a conta ainda não tem.
        Senha errada levanta JoinError, mas a conexão continua aberta para tentar de novo."""
        kind = "register" if register else "login"
        reply = self._request({"t": kind, "user": user, "password": password, "version": VERSION},
                              ("account", "denied"))
        if reply["t"] == "denied":
            raise JoinError(reply["text"])
        return reply.get("character")

    def enter(self, hello: dict) -> list[dict]:
        """Entra no mundo. Devolve os jogadores que já estavam lá e começa a ler a rede em segundo plano."""
        welcome = self._request(dict(hello, t="hello"), ("welcome",))
        self.id = welcome["id"]
        self.initial_players = list(welcome.get("players", []))
        self.initial_npcs = list(welcome.get("npcs", []))
        self.initial_clock = welcome.get("clock")
        self.sock.settimeout(None)
        threading.Thread(target=self._read_loop, name="world-reader", daemon=True).start()
        return self.initial_players

    def _request(self, message: dict, answers: tuple[str, ...]) -> dict:
        """Manda uma mensagem e espera a resposta (antes da thread de leitura existir)."""
        if self.sock is None:
            raise JoinError("Sem conexão com o mundo.")
        try:
            self.sock.sendall(encode(message))
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                for reply in self.reader.feed(data):
                    if reply["t"] == "error":
                        self.close()
                        raise JoinError(reply.get("text", "O servidor recusou a conexão."))
                    if reply["t"] in answers:
                        return reply
                    self.inbox.put(reply)
        except (OSError, ValueError) as err:
            self.close()
            raise JoinError("A conexão com o mundo caiu.") from err
        self.close()
        raise JoinError("O servidor fechou a conexão.")

    def _read_loop(self) -> None:
        sock = self.sock
        try:
            while sock is not None:
                data = sock.recv(4096)
                if not data:
                    break
                for message in self.reader.feed(data):
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

    def save_character(self, data: dict) -> None:
        """Grava o personagem no banco do servidor (chamado por Character.save quando online)."""
        self.send({"t": "save", "character": data})

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

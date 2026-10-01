"""O servidor do mundo compartilhado. Roda no computador de quem HOSPEDA, numa thread separada do jogo.

Ele é o "juiz" de quem está no mundo: guarda a última posição de cada jogador e repassa as novidades para os
outros. Não roda regra de jogo nenhuma (batalhas contra NPCs e monstros continuam em cada computador).
Cada jogador conectado ganha uma thread que só lê as mensagens dele.
"""
from __future__ import annotations

import contextlib
import socket
import threading

from game.net.protocol import MAX_PLAYERS, VERSION, LineReader, encode

STATE_KEYS = ("name", "look", "map", "x", "y", "facing", "battle")   # o que o servidor guarda de cada um


class WorldServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 0):
        """port=0: o sistema escolhe uma porta livre (usado nos testes); veja `self.port` depois do start()."""
        self.address = (host, port)
        self.port = port
        self.players: dict[int, dict] = {}       # id -> estado
        self.conns: dict[int, socket.socket] = {}
        self.lock = threading.Lock()
        self.next_id = 1
        self.sock: socket.socket | None = None
        self.running = False

    # ------------------------------------------------------------ ligar / desligar
    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.address)
        sock.listen()
        self.sock = sock
        self.port = sock.getsockname()[1]
        self.running = True
        threading.Thread(target=self._accept_loop, name="world-server", daemon=True).start()

    def stop(self) -> None:
        self.running = False
        if self.sock:
            with contextlib.suppress(OSError):
                self.sock.close()
        with self.lock:
            for conn in list(self.conns.values()):
                with contextlib.suppress(OSError):
                    conn.close()
            self.conns.clear()
            self.players.clear()

    # ------------------------------------------------------------ conexões
    def _accept_loop(self) -> None:
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return                                    # servidor fechado
            threading.Thread(target=self._serve, args=(conn,), name="world-client", daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        reader = LineReader()
        player_id = None
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                for message in reader.feed(data):
                    if player_id is None:
                        player_id = self._hello(conn, message)
                        if player_id is None:
                            return
                    else:
                        self._handle(player_id, message)
        except (OSError, ValueError):
            pass
        finally:
            if player_id is not None:
                self._leave(player_id)
            with contextlib.suppress(OSError):
                conn.close()

    def _hello(self, conn: socket.socket, message: dict) -> int | None:
        """Primeira mensagem: confere a versão e a vaga; responde com o id e quem já está no mundo."""
        if message.get("t") != "hello" or message.get("version") != VERSION:
            self._send(conn, {"t": "error", "text": "Versão do jogo diferente: os dois precisam da mesma versão."})
            return None
        with self.lock:
            if len(self.players) >= MAX_PLAYERS:
                self._send(conn, {"t": "error", "text": f"O mundo está cheio ({MAX_PLAYERS} jogadores)."})
                return None
            player_id = self.next_id
            self.next_id += 1
            state = {key: message.get(key) for key in STATE_KEYS}
            state["name"] = str(state["name"] or "???")[:12]
            state["battle"] = False
            others = [dict(p, id=pid) for pid, p in self.players.items()]
            self.players[player_id] = state
            self.conns[player_id] = conn
        self._send(conn, {"t": "welcome", "id": player_id, "players": others})
        self._broadcast({"t": "join", "player": dict(state, id=player_id)}, exclude=player_id)
        return player_id

    def _handle(self, player_id: int, message: dict) -> None:
        kind = message["t"]
        with self.lock:
            state = self.players.get(player_id)
            if state is None:
                return
            if kind == "move":
                for key in ("map", "x", "y", "facing"):
                    state[key] = message.get(key, state[key])
                out = {"t": "move", "id": player_id, "map": state["map"], "x": state["x"], "y": state["y"],
                       "facing": state["facing"], "run": bool(message.get("run"))}
            elif kind == "emote":
                out = {"t": "emote", "id": player_id, "text": str(message.get("text", ""))[:40]}
            elif kind == "status":
                state["battle"] = bool(message.get("battle"))
                out = {"t": "status", "id": player_id, "battle": state["battle"]}
            else:
                return                                    # mensagem desconhecida: ignora
        self._broadcast(out, exclude=player_id)

    def _leave(self, player_id: int) -> None:
        with self.lock:
            self.players.pop(player_id, None)
            self.conns.pop(player_id, None)
        self._broadcast({"t": "leave", "id": player_id})

    # ------------------------------------------------------------ envio
    def _send(self, conn: socket.socket, message: dict) -> None:
        with contextlib.suppress(OSError):
            conn.sendall(encode(message))

    def _broadcast(self, message: dict, exclude: int | None = None) -> None:
        with self.lock:
            targets = [conn for pid, conn in self.conns.items() if pid != exclude]
        for conn in targets:
            self._send(conn, message)

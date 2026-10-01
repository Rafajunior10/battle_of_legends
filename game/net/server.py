"""O servidor do mundo compartilhado. Roda no computador de quem HOSPEDA, numa thread separada do jogo.

Cada conexão passa por 3 etapas (uma `Session` guarda em qual está):
    1. login / register   confere a conta no banco (database.py) e devolve o personagem salvo (ou None)
    2. hello              entra no mundo: os outros veem você chegar
    3. no mundo           move / emote / status são repassados aos outros; save grava o personagem no banco;
                          challenge / answer / duel / duel_over cuidam dos duelos entre jogadores (PvP)
O servidor guarda os personagens e a posição de cada um. As regras do jogo (batalhas, loja) rodam no
computador de cada jogador, que manda o personagem atualizado com "save".
"""
from __future__ import annotations

import contextlib
import random
import socket
import threading
from dataclasses import dataclass

from game.net.database import AccountError, Database
from game.net.protocol import MAX_PLAYERS, VERSION, LineReader, encode

STATE_KEYS = ("name", "look", "map", "x", "y", "facing", "battle")   # o que o servidor guarda de cada um
DUEL_MESSAGES = {"challenge": "_challenge", "answer": "_answer", "duel": "_duel_action", "duel_over": "_duel_over"}
WRONG_VERSION = "Versão do jogo diferente: os dois precisam da mesma versão (baixe a última)."


@dataclass
class Session:
    """Em que etapa está uma conexão."""
    account_id: int | None = None
    player_id: int | None = None


class WorldServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 0, db_path: str = ":memory:"):
        """port=0: o sistema escolhe uma porta livre (testes); db_path: arquivo do banco (":memory:" nos testes)."""
        self.address = (host, port)
        self.port = port
        self.db = Database(db_path)
        self.players: dict[int, dict] = {}       # id no mundo -> estado (posição, aparência...)
        self.conns: dict[int, socket.socket] = {}
        self.accounts_online: set[int] = set()
        self.challenges: dict[int, tuple[int, dict]] = {}   # quem desafiou -> (desafiado, ficha de duelo)
        self.duels: dict[int, int] = {}                      # jogador -> oponente (os dois lados)
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
            self.accounts_online.clear()
            self.challenges.clear()
            self.duels.clear()
        self.db.close()

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
        session = Session()
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                for message in reader.feed(data):
                    if not self._dispatch(conn, session, message):
                        return
        except (OSError, ValueError):
            pass
        finally:
            self._disconnect(session)
            with contextlib.suppress(OSError):
                conn.close()

    def _dispatch(self, conn: socket.socket, session: Session, message: dict) -> bool:
        """Trata uma mensagem conforme a etapa da conexão. Devolve False para fechar a conexão."""
        kind = message["t"]
        if session.account_id is None:
            return self._authenticate(conn, session, message)
        if kind == "save":
            self._save(conn, session, message)
        elif session.player_id is None:
            if kind == "hello":
                return self._hello(conn, session, message)
        elif kind in DUEL_MESSAGES:
            getattr(self, DUEL_MESSAGES[kind])(session.player_id, message)
        else:
            self._handle(session.player_id, message)
        return True

    # ------------------------------------------------------------ etapa 1: conta
    def _authenticate(self, conn: socket.socket, session: Session, message: dict) -> bool:
        if message.get("version") != VERSION or message["t"] not in ("login", "register"):
            self._send(conn, {"t": "error", "text": WRONG_VERSION})
            return False
        username, password = str(message.get("user", "")), str(message.get("password", ""))
        try:
            if message["t"] == "register":
                account_id = self.db.register(username, password)
            else:
                account_id = self.db.login(username, password)
        except AccountError as err:
            self._send(conn, {"t": "denied", "text": str(err)})
            return True                                   # pode tentar de novo
        with self.lock:
            if account_id in self.accounts_online:
                self._send(conn, {"t": "denied", "text": "Essa conta já está jogando em outro computador."})
                return True
            self.accounts_online.add(account_id)
        session.account_id = account_id
        self._send(conn, {"t": "account", "character": self.db.load_character(account_id)})
        return True

    def _save(self, conn: socket.socket, session: Session, message: dict) -> None:
        character = message.get("character")
        if not isinstance(character, dict):
            return
        try:
            self.db.save_character(session.account_id, character)
        except AccountError as err:
            self._send(conn, {"t": "notice", "text": str(err)})

    # ------------------------------------------------------------ etapa 2: entrar no mundo
    def _hello(self, conn: socket.socket, session: Session, message: dict) -> bool:
        """Entra no mundo: responde com o id e quem já está lá, e avisa os outros."""
        with self.lock:
            if len(self.players) >= MAX_PLAYERS:
                self._send(conn, {"t": "error", "text": f"O mundo está cheio ({MAX_PLAYERS} jogadores)."})
                return False
            player_id = self.next_id
            self.next_id += 1
            state = {key: message.get(key) for key in STATE_KEYS}
            state["name"] = str(state["name"] or "???")[:12]
            state["battle"] = False
            others = [dict(p, id=pid) for pid, p in self.players.items()]
            self.players[player_id] = state
            self.conns[player_id] = conn
        session.player_id = player_id
        self._send(conn, {"t": "welcome", "id": player_id, "players": others})
        self._broadcast({"t": "join", "player": dict(state, id=player_id)}, exclude=player_id)
        return True

    # ------------------------------------------------------------ etapa 3: no mundo
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

    # ------------------------------------------------------------ duelos (PvP)
    def _challenge(self, player_id: int, message: dict) -> None:
        """Desafio: guarda a ficha de quem desafiou e pergunta ao desafiado."""
        target = message.get("to")
        with self.lock:
            me, other = self.players.get(player_id), self.players.get(target)
            refusal = self._duel_refusal(player_id, target, other)
            if refusal is None:
                self.challenges[player_id] = (target, message.get("fighter") or {})
        if refusal is not None:
            self._send_to(player_id, {"t": "challenge_denied", "text": refusal})
            return
        self._send_to(target, {"t": "challenge", "from": player_id, "name": me["name"]})

    def _duel_refusal(self, player_id: int, target: int, other: dict | None) -> str | None:
        """Por que não dá para desafiar agora (None = pode). Chamar com o lock."""
        if other is None or target == player_id:
            return "Esse jogador não está mais no mundo."
        if player_id in self.duels:
            return "Você já está num duelo."
        if other["battle"] or target in self.duels:
            return f"{other['name']} está numa batalha agora. Tente daqui a pouco."
        return None

    def _answer(self, player_id: int, message: dict) -> None:
        """Resposta do desafiado. Aceitou: o servidor sorteia a semente e começa o duelo nos dois."""
        challenger = message.get("to")
        with self.lock:
            pending = self.challenges.get(challenger)
            if pending is None or pending[0] != player_id:
                return                                    # o desafio já foi cancelado
            del self.challenges[challenger]
            me = self.players.get(player_id)
            ok = bool(message.get("yes")) and self._duel_refusal(challenger, player_id, me) is None
            if ok:
                self.duels[challenger], self.duels[player_id] = player_id, challenger
        if not ok:
            name = me["name"] if me else "O jogador"
            self._send_to(challenger, {"t": "challenge_denied", "text": f"{name} recusou o duelo."})
            return
        seed = random.getrandbits(31)
        self._send_to(challenger, {"t": "duel_start", "seed": seed, "side": 0, "foe": message.get("fighter") or {}})
        self._send_to(player_id, {"t": "duel_start", "seed": seed, "side": 1, "foe": pending[1]})

    def _duel_action(self, player_id: int, message: dict) -> None:
        """Uma jogada: vai só para o oponente."""
        with self.lock:
            foe = self.duels.get(player_id)
        if foe is not None:
            self._send_to(foe, {"t": "duel", "action": message.get("action")})

    def _duel_over(self, player_id: int, message: dict) -> None:
        with self.lock:
            foe = self.duels.pop(player_id, None)
            if foe is not None:
                self.duels.pop(foe, None)

    def _leave_duels(self, player_id: int) -> None:
        """Quem sai do mundo abandona o duelo (o oponente vence) e os desafios pendentes."""
        with self.lock:
            foe = self.duels.pop(player_id, None)
            if foe is not None:
                self.duels.pop(foe, None)
            self.challenges.pop(player_id, None)
            for challenger, (target, _) in list(self.challenges.items()):
                if target == player_id:
                    del self.challenges[challenger]
        if foe is not None:
            self._send_to(foe, {"t": "duel_end", "reason": "left"})

    def _disconnect(self, session: Session) -> None:
        with self.lock:
            if session.account_id is not None:
                self.accounts_online.discard(session.account_id)
            if session.player_id is None:
                return
        self._leave_duels(session.player_id)
        with self.lock:
            self.players.pop(session.player_id, None)
            self.conns.pop(session.player_id, None)
        self._broadcast({"t": "leave", "id": session.player_id})

    # ------------------------------------------------------------ envio
    def _send(self, conn: socket.socket, message: dict) -> None:
        with contextlib.suppress(OSError):
            conn.sendall(encode(message))

    def _send_to(self, player_id: int, message: dict) -> None:
        with self.lock:
            conn = self.conns.get(player_id)
        if conn is not None:
            self._send(conn, message)

    def _broadcast(self, message: dict, exclude: int | None = None) -> None:
        with self.lock:
            targets = [conn for pid, conn in self.conns.items() if pid != exclude]
        for conn in targets:
            self._send(conn, message)

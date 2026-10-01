"""O "idioma" da rede: cada mensagem é um dicionário em JSON, numa linha só (terminada em "\\n"), em UTF-8.

Mensagens do jogador para o servidor:
    hello   {name, look, map, x, y, facing, version}   primeira mensagem: quem eu sou e onde estou
    move    {map, x, y, facing, run}                    comecei um passo para (x, y) / virei / troquei de mapa
    emote   {text}                                      balão de fala
    status  {battle}                                    entrei ou saí de uma batalha
Mensagens do servidor para o jogador:
    welcome {id, players}       seu número e quem já está no mundo
    join    {player}            alguém entrou        leave {id}   alguém saiu
    move / emote / status       o mesmo de cima, com o "id" de quem fez
    error   {text}              conexão recusada (versão diferente, servidor cheio...)
Só mensagens pequenas viajam: cada passo vira uma mensagem, e cada computador anima o passo sozinho.
"""
from __future__ import annotations

import contextlib
import json
import socket

PORT = 50550
VERSION = 1                  # muda quando o formato das mensagens mudar (versões diferentes não se conectam)
MAX_LINE = 64 * 1024         # mensagem maior que isso é lixo: a conexão é fechada
MAX_PLAYERS = 8
EMOTES = ["Oi!", "Bora duelar?", "Me segue!", "Valeu!", "Kkkkk", "Tchau!"]


def encode(message: dict) -> bytes:
    return (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class LineReader:
    """Junta os pedaços que chegam pela rede e devolve as mensagens completas (uma por linha)."""

    def __init__(self):
        self.buffer = b""

    def feed(self, data: bytes) -> list[dict]:
        self.buffer += data
        if len(self.buffer) > MAX_LINE and b"\n" not in self.buffer:
            raise ValueError("mensagem grande demais")
        *lines, self.buffer = self.buffer.split(b"\n")
        messages = []
        for line in lines:
            try:
                message = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue                          # linha estragada: ignora
            if isinstance(message, dict) and isinstance(message.get("t"), str):
                messages.append(message)
        return messages


def parse_address(text: str) -> tuple[str, int]:
    """'192.168.0.5' ou '192.168.0.5:50550' -> (host, porta)."""
    text = text.strip()
    if not text:
        raise ValueError("Digite o endereço de quem está hospedando.")
    host, _, port = text.partition(":")
    if port and not port.isdigit():
        raise ValueError("A porta (depois dos dois-pontos) precisa ser um número.")
    return host, int(port) if port else PORT


def local_addresses() -> list[str]:
    """Endereços deste computador que um amigo pode usar para entrar (rede de casa, Radmin, ZeroTier...)."""
    found = []
    with contextlib.suppress(OSError):
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    try:                                          # o endereço que o PC usa para sair para a internet
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            found.append(probe.getsockname()[0])
    except OSError:
        pass
    seen = []
    for address in found:
        if not address.startswith("127.") and address not in seen:
            seen.append(address)
    return seen or ["127.0.0.1"]

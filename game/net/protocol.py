"""O "idioma" da rede: cada mensagem é um dicionário em JSON, numa linha só (terminada em "\\n"), em UTF-8.

Mensagens do jogador para o servidor:
    login / register {user, password, version}   entrar na conta / criar conta (sempre a primeira mensagem)
    save    {character}                          grava o personagem no banco do servidor
    hello   {name, look, map, x, y, facing}      entrar no mundo: quem eu sou e onde estou
    move    {map, x, y, facing, run, sit}        comecei um passo para (x, y) / virei / troquei de mapa / sentei
    emote   {text}                               balão de fala
    status  {battle}                             entrei ou saí de uma batalha
    challenge {to, fighter}                      desafiar o jogador `to` para um duelo (fighter: core/duel.py)
    answer    {to, yes, fighter}                 aceitar (ou não) o desafio de `to`
    duel      {action}                           uma jogada no duelo (vai só para o oponente)
    duel_over                                    o duelo acabou
    swap_ask / swap_cards / swap_offer / swap_answer {to, ...}   mesa de troca (scenes/cafe.py); o servidor
                                                 entrega só para `to`, com "from" e "name" de quem mandou
Mensagens do servidor para o jogador:
    account {character}         login ok: o personagem salvo (ou null, conta nova)
    denied  {text}              login/cadastro recusado (pode tentar de novo)
    welcome {id, players}       seu número no mundo e quem já está lá
    join    {player}            alguém entrou        leave {id}   alguém saiu
    move / emote / status       o mesmo de cima, com o "id" de quem fez
    error   {text}              conexão recusada (versão diferente, servidor cheio...)
    challenge {from, name}      alguém te desafiou    challenge_denied {text}   o desafio não rolou
    duel_start {seed, side, foe}  o duelo começou (semente dos baralhos, seu lado, ficha do oponente)
    duel {action}               jogada do oponente    duel_end {reason}   o oponente saiu (vitória por W.O.)
Só mensagens pequenas viajam: cada passo vira uma mensagem, e cada computador anima o passo sozinho.
"""
from __future__ import annotations

import contextlib
import json
import socket

PORT = 50550
VERSION = 4                  # muda quando o formato das mensagens mudar (versões diferentes não se conectam)
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

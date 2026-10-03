"""Banco de dados do servidor (SQLite): as contas e os personagens de todo mundo.

Fica no computador de quem hospeda, no arquivo world.db (na pasta do jogo). O SQLite já vem com o Python.
    accounts    id, usuário (único, sem diferenciar maiúsculas), hash da senha, sal, data de criação
    characters  conta -> personagem inteiro em JSON (o mesmo formato do save: Character)
    meta        dados do mundo (ex.: "clock": o dia e a hora)

Senha nunca é guardada: guardamos um HASH (PBKDF2-SHA256 com "sal" aleatório). Para conferir o login,
calculamos o hash da senha digitada com o mesmo sal e comparamos.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time

HASH_ROUNDS = 200_000
MIN_PASSWORD = 4
USERNAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-.")
MAX_USERNAME = 16
MAX_CHARACTER_JSON = 256 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS characters (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(id),
    data TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""


class AccountError(Exception):
    """Login ou cadastro recusado; a mensagem é mostrada ao jogador."""


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ROUNDS).hex()


def check_username(username: str) -> str:
    name = username.strip().lower()
    if not 3 <= len(name) <= MAX_USERNAME or not set(name) <= USERNAME_CHARS:
        raise AccountError(f"Usuário: de 3 a {MAX_USERNAME} letras, números, ponto, - ou _ (sem espaço).")
    return name


class Database:
    def __init__(self, path: str):
        """path: arquivo do banco (":memory:" nos testes). As threads do servidor dividem uma conexão só,
        protegida por um lock (o SQLite aguenta isso tranquilamente para poucos jogadores)."""
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.executescript(SCHEMA)

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    # ------------------------------------------------------------ contas
    def register(self, username: str, password: str) -> int:
        name = check_username(username)
        if len(password) < MIN_PASSWORD:
            raise AccountError(f"A senha precisa ter pelo menos {MIN_PASSWORD} caracteres.")
        salt = os.urandom(16)
        try:
            with self.lock, self.conn:
                cur = self.conn.execute(
                    "INSERT INTO accounts (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                    (name, _hash(password, salt), salt.hex(), time.time()))
        except sqlite3.IntegrityError as err:
            raise AccountError(f"O usuário '{name}' já existe. Escolha outro ou faça login.") from err
        return cur.lastrowid

    def login(self, username: str, password: str) -> int:
        name = username.strip().lower()
        with self.lock:
            row = self.conn.execute("SELECT id, password_hash, salt FROM accounts WHERE username = ?",
                                    (name,)).fetchone()
        if row is None or not hmac.compare_digest(row[1], _hash(password, bytes.fromhex(row[2]))):
            raise AccountError("Usuário ou senha incorretos.")
        return row[0]

    # ------------------------------------------------------------ personagens
    def load_character(self, account_id: int) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT data FROM characters WHERE account_id = ?", (account_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_character(self, account_id: int, data: dict) -> None:
        text = json.dumps(data, ensure_ascii=False)
        if len(text) > MAX_CHARACTER_JSON:
            raise AccountError("Personagem grande demais para salvar.")
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO characters (account_id, data, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(account_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                (account_id, text, time.time()))

    # ------------------------------------------------------------ dados do mundo (ex.: o relógio)
    def get_meta(self, key: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_meta(self, key: str, value: dict) -> None:
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
                              "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))

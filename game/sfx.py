"""Efeitos sonoros e músicas chiptune gerados por código (sem arquivos de áudio)."""
import array
import random
import threading

import pygame

_ok = False
_rate = 22050
_channels = 1
_sounds = {}
_track_bytes = {}   # preenchido pela thread de geração
_tracks = {}
_current = None
_wanted = None
_channel = None

NOTE_INDEX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
              "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def note_freq(name):
    if name in ("R", "-"):
        return 0.0
    midi = 12 * (int(name[-1]) + 1) + NOTE_INDEX[name[:-1]]
    return 440.0 * 2 ** ((midi - 69) / 12)


def _render(notes, wave, vol, decay=False):
    """notes: lista de (frequência, segundos). Devolve uma lista de amostras float."""
    out = []
    for freq, dur in notes:
        n = max(1, int(_rate * dur))
        if freq <= 0:
            out.extend([0.0] * n)
            continue
        step = freq / _rate
        phase = 0.0
        fade = max(1, min(300, n // 3))
        for i in range(n):
            if wave == "square":
                s = 1.0 if phase < 0.5 else -1.0
            elif wave == "pulse":
                s = 1.0 if phase < 0.25 else -1.0
            elif wave == "tri":
                s = 4.0 * abs(phase - 0.5) - 1.0
            else:
                s = random.uniform(-1.0, 1.0)
            env = 1.0 - (i / n) * 0.85 if decay else 1.0
            if i > n - fade:
                env *= (n - i) / fade
            out.append(s * vol * env)
            phase += step
            if phase >= 1.0:
                phase -= 1.0
    return out


def _to_bytes(samples):
    data = array.array("h", [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    if _channels == 2:
        stereo = array.array("h", bytes(len(data) * 4))
        stereo[0::2] = data
        stereo[1::2] = data
        data = stereo
    return data.tobytes()


def _parse(seq, unit, gate=1.0):
    notes = []
    for tok in seq.split():
        name, _, length = tok.partition(":")
        dur = unit * float(length or 1)
        freq = note_freq(name)
        if gate < 1.0 and freq > 0:
            notes += [(freq, dur * gate), (0.0, dur * (1 - gate))]
        else:
            notes.append((freq, dur))
    return notes


def _mix(*voices):
    size = max(len(v) for v in voices)
    out = [0.0] * size
    for v in voices:
        for i, s in enumerate(v):
            out[i] += s
    return out


# ---------------------------------------------------------------- músicas
LOBBY_MELODY = ("C5:2 E5:2 G5:2 E5:2 F5:2 A5:2 G5:4 E5:2 G5:2 C6:2 B5:2 A5:2 G5:2 E5:4 "
                "F5:2 E5:2 D5:2 F5:2 E5:2 D5:2 C5:4 D5:2 E5:2 F5:2 A5:2 G5:6 R:2")
LOBBY_BASS = "C3:4 G3:4 F3:4 G3:4 C3:4 E3:4 F3:4 C3:4 F3:4 G3:4 C3:4 A2:4 D3:4 F3:4 G3:4 G2:4"

BATTLE_MELODY = ("A4:1 A4:1 C5:1 A4:1 E5:2 D5:2 C5:1 C5:1 D5:1 C5:1 B4:2 G4:2 "
                 "A4:1 A4:1 C5:1 E5:1 A5:2 G5:2 F5:2 E5:2 D5:2 E5:2 "
                 "F5:2 E5:2 D5:2 C5:2 D5:2 C5:2 B4:4 C5:2 B4:2 A4:2 G#4:2 A4:6 R:2")
BATTLE_BASS = " ".join(f"{n}2:1 {n}3:1 " * 4 for n in "AGFEFGEA")


def _build_music():
    lobby_unit = 60 / 120 / 2
    battle_unit = 60 / 150 / 2
    tracks = {
        "lobby": _mix(_render(_parse(LOBBY_MELODY, lobby_unit, 0.85), "pulse", 0.16),
                      _render(_parse(LOBBY_BASS, lobby_unit, 0.8), "tri", 0.28)),
        "battle": _mix(_render(_parse(BATTLE_MELODY, battle_unit, 0.8), "square", 0.13),
                       _render(_parse(BATTLE_BASS, battle_unit, 0.7), "tri", 0.3)),
    }
    for name, samples in tracks.items():
        _track_bytes[name] = _to_bytes(samples)


# ------------------------------------------------------------ efeitos (SFX)
SFX = {
    "cursor": ([(1320, 0.03)], "square", 0.2, False),
    "transform": ([(262, 0.05), (330, 0.05), (392, 0.05), (523, 0.05), (659, 0.05), (784, 0.05), (1047, 0.3)],
                  "pulse", 0.22, False),
    "confirm": ([(880, 0.05), (1320, 0.08)], "square", 0.2, False),
    "cancel": ([(660, 0.05), (440, 0.07)], "square", 0.2, False),
    "bump": ([(110, 0.08)], "square", 0.25, True),
    "error": ([(140, 0.1), (0, 0.03), (140, 0.1)], "square", 0.22, False),
    "hit": ([(1, 0.18)], "noise", 0.4, True),
    "slash": ([(1, 0.1)], "noise", 0.3, True),
    "flame": ([(1, 0.35)], "noise", 0.3, True),
    "bolt": ([(1, 0.05), (0, 0.03), (1, 0.25)], "noise", 0.45, True),
    "heal": ([(523, 0.06), (659, 0.06), (784, 0.06), (1047, 0.12)], "tri", 0.45, False),
    "shield": ([(392, 0.06), (523, 0.06), (392, 0.06), (523, 0.1)], "pulse", 0.2, False),
    "energy": ([(784, 0.05), (1047, 0.05), (1568, 0.1)], "pulse", 0.18, False),
    "card": ([(660, 0.04), (990, 0.05)], "pulse", 0.2, False),
    "poison": ([(300, 0.06), (250, 0.06), (200, 0.1)], "square", 0.2, False),
    "faint": ([(600, 0.08), (500, 0.08), (400, 0.08), (300, 0.08), (200, 0.2)], "square", 0.2, False),
    "win": ([(523, 0.1), (659, 0.1), (784, 0.1), (1047, 0.35)], "square", 0.2, False),
    "lose": ([(392, 0.15), (330, 0.15), (262, 0.4)], "square", 0.2, False),
    "encounter": ([(880, 0.05), (0, 0.02), (880, 0.05), (0, 0.02), (1320, 0.18)], "square", 0.22, False),
    "save": ([(659, 0.06), (784, 0.06), (1047, 0.06), (1319, 0.12)], "pulse", 0.2, False),
    "pierce": ([(1, 0.04), (0, 0.02), (1, 0.12)], "noise", 0.35, True),
    "break": ([(1568, 0.04), (1175, 0.04), (880, 0.05), (1, 0.12)], "pulse", 0.2, True),
    "stun": ([(988, 0.04), (0, 0.02), (988, 0.04), (0, 0.02), (988, 0.08)], "square", 0.16, False),
    "ice": ([(1568, 0.03), (1319, 0.03), (1760, 0.05), (1, 0.08)], "tri", 0.35, True),
    "freeze": ([(1760, 0.05), (1568, 0.05), (1319, 0.05), (1047, 0.2)], "tri", 0.4, False),
    "aura": ([(523, 0.05), (784, 0.05), (1047, 0.1)], "tri", 0.35, False),
    "smoke": ([(1, 0.25)], "noise", 0.18, True),
    "coin": ([(988, 0.05), (1319, 0.14)], "square", 0.18, False),
    "pack": ([(392, 0.05), (523, 0.05), (659, 0.05), (784, 0.05), (1047, 0.15)], "pulse", 0.2, False),
    "reveal": ([(1047, 0.04), (1568, 0.1)], "tri", 0.4, False),
    "levelup": ([(523, 0.08), (659, 0.08), (784, 0.08), (1047, 0.08), (784, 0.08), (1047, 0.3)],
                "square", 0.18, False),
}


def pre_init():
    pygame.mixer.pre_init(22050, -16, 1, 512)


def init():
    """Deve ser chamado depois de pygame.init()."""
    global _ok, _rate, _channels, _channel
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(22050, -16, 1, 512)
        rate, size, channels = pygame.mixer.get_init()
    except (pygame.error, TypeError):
        return
    if size != -16:
        return
    _rate, _channels, _ok = rate, channels, True
    pygame.mixer.set_num_channels(16)
    pygame.mixer.set_reserved(1)
    _channel = pygame.mixer.Channel(0)
    _channel.set_volume(0.6)
    for name, (notes, wave, vol, decay) in SFX.items():
        _sounds[name] = pygame.mixer.Sound(buffer=_to_bytes(_render(notes, wave, vol, decay)))
    threading.Thread(target=_build_music, daemon=True).start()


def play(name):
    sound = _sounds.get(name)
    if sound:
        sound.play()


def music(name):
    """Troca a música de fundo (None para silêncio)."""
    global _wanted
    _wanted = name


def update():
    """Chamado todo frame: cria as músicas prontas e troca a faixa quando pedido."""
    global _current
    if not _ok:
        return
    for name in list(_track_bytes):
        _tracks[name] = pygame.mixer.Sound(buffer=_track_bytes.pop(name))
    if _wanted == _current:
        return
    if _wanted is None:
        _channel.fadeout(200)
        _current = None
    elif _wanted in _tracks:
        _channel.play(_tracks[_wanted], loops=-1, fade_ms=300)
        _current = _wanted

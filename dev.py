"""Modo de desenvolvimento: roda o jogo e reinicia sozinho quando algum .py muda.

    python dev.py            abre direto no lobby com o seu save (pula o título)
    python dev.py --titulo   abre na tela de título, como no jogo normal

Ctrl+C no terminal encerra.
"""
import contextlib
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(ROOT, "game")
POLL = 0.5   # segundos entre verificações


def snapshot():
    """{caminho: data de modificação} dos .py do jogo (main.py e a pasta game/; testes não reiniciam o jogo)."""
    paths = [os.path.join(ROOT, "main.py")]
    for folder, dirs, names in os.walk(GAME_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        paths += [os.path.join(folder, n) for n in names if n.endswith(".py")]
    files = {}
    for path in paths:
        with contextlib.suppress(OSError):   # arquivo apagado no meio da varredura
            files[path] = os.path.getmtime(path)
    return files


def changed(old, new):
    paths = [p for p in new if old.get(p) != new[p]] + [p for p in old if p not in new]
    return sorted({os.path.relpath(p, ROOT) for p in paths})


def start(env):
    print("\n\033[92m▶ Iniciando o jogo...\033[0m", flush=True)
    return subprocess.Popen([sys.executable, os.path.join(ROOT, "main.py")], cwd=ROOT, env=env)


def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    env = dict(os.environ)
    if "--titulo" not in sys.argv:
        env["CARD_QUEST_AUTOLOAD"] = "1"
    print("\033[96mModo dev: o jogo reinicia sozinho quando você salvar um arquivo .py. "
          "Ctrl+C para sair.\033[0m")
    files = snapshot()
    proc = start(env)
    reported = False
    try:
        while True:
            time.sleep(POLL)
            new = snapshot()
            diff = changed(files, new)
            if diff:
                time.sleep(0.2)   # espera o editor terminar de gravar
                files = snapshot()
                print(f"\n\033[93m↻ Mudou: {', '.join(diff)}\033[0m", flush=True)
                stop(proc)
                proc = start(env)
                reported = False
            elif proc.poll() is not None and not reported:
                code = proc.returncode
                if code == 0:
                    print("\n\033[90mJogo fechado. Salve um arquivo para abrir de novo, ou Ctrl+C para sair.\033[0m")
                else:
                    print(f"\n\033[91m✖ O jogo deu erro (código {code}). Corrija e salve que ele reinicia.\033[0m")
                reported = True
    except KeyboardInterrupt:
        stop(proc)
        print("\nAté mais!")


if __name__ == "__main__":
    main()

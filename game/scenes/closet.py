"""Closet da suíte: trocar de roupa. É a tela de criação de personagem só com as peças de roupa (as escolhas
e a prévia girando são as mesmas); PRONTO veste a roupa, salva e volta para o quarto. B volta sem trocar."""
from dataclasses import asdict

from game.engine import sfx
from game.graphics import sprites
from game.scenes.create import CreateScene

CLOTHES = {"top", "shirt", "bottom", "legs", "shoes", "hat", "hat_color"}


class ClosetScene(CreateScene):
    TITLE = "CLOSET"
    FIELDS = CLOTHES
    HAS_NAME = False
    DONE_HINT = "Aperte {a} para vestir. {b} volta sem trocar."

    def __init__(self, game, lobby):
        super().__init__(game)
        self.lobby = lobby
        self.values = asdict(game.character.appearance)    # começa com a roupa que você está usando

    def finish(self):
        ch = self.game.character
        ch.wear(self.look)
        ch.save()
        sfx.play("save")
        self.lobby.player.frames = sprites.player_frames(ch)
        if self.game.net:                                  # os outros jogadores veem a roupa nova
            self.game.net.send({"t": "look", "look": asdict(ch.appearance)})
        self.lobby.say("Roupa nova! Ficou ótimo.")
        self.game.transition_to(lambda: self.lobby)

    def back(self):
        sfx.play("cancel")
        self.game.transition_to(lambda: self.lobby)

class Scene:
    """Base para todas as telas do jogo."""

    def __init__(self, game):
        self.game = game

    def on_enter(self):
        pass

    def handle(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

"""Demo entry point for the Farkle game."""
import pygame
from farkle.game import Game
from farkle.ui.screens.app import App
from farkle.ui.settings import WIDTH, HEIGHT

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("God Farkle")
    font = pygame.font.SysFont("Arial", 26)
    clock = pygame.time.Clock()
    # Use unseeded randomness for live demo; enable random relic offer shuffling.
    game = Game(screen, font, clock, rng_seed=None)
    # Configure relic manager for randomized offers
    try:
        game.relic_manager.randomize_offers = True
    except Exception:
        pass
    app = App(game)
    app.run()

if __name__ == "__main__":
    main()

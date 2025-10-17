"""Demo entry point for the Farkle game."""
import pygame
from game import Game
from screens.app import App
from settings import WIDTH, HEIGHT

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("God Farkle")
    font = pygame.font.SysFont("Arial", 26)
    clock = pygame.time.Clock()
    game = Game(screen, font, clock)
    app = App(game)
    app.run()

if __name__ == "__main__":
    main()

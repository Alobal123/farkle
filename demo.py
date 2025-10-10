"""Demo entry point for the Farkle game."""
import pygame, sys
from game import Game
from settings import WIDTH, HEIGHT

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("God Farkle")
    font = pygame.font.SysFont("Arial", 26)
    clock = pygame.time.Clock()
    Game(screen, font, clock).run()

if __name__ == "__main__":
    main()

import pygame, sys
from game import Game

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Farkle - Push Your Luck")
font = pygame.font.SysFont("Arial", 26)
clock = pygame.time.Clock()

if __name__ == "__main__":
    # Keep initialization here; pass resources into Game
    WIDTH, HEIGHT = 800, 600  # Ensure same constants for potential external imports
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Farkle - Push Your Luck")
    font = pygame.font.SysFont("Arial", 26)
    clock = pygame.time.Clock()
    Game(screen, font, clock).run()

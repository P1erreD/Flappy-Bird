# flappybird.py
# -------------------------------------------------------------
# Flappy Bird minimaliste en un seul fichier (Python + pygame)
# Auteurs: Vous 💛
# Licence: MIT
# -------------------------------------------------------------
# Exigences:
#   - Python 3.10+
#   - pygame >= 2.3
# Lancement:
#   - pip install pygame
#   - python flappybird.py
# -------------------------------------------------------------

import json
import math
import os
import random
import sys
from dataclasses import dataclass

import pygame

# -------------------------------------------------------------
# Constantes globales
# -------------------------------------------------------------
WIDTH, HEIGHT = 288, 512  # taille de fenêtre fixe
FPS = 60
TITLE = "Flappy Bird - mini"

# Couleurs (R, G, B)
SKY = (135, 206, 235)
PIPE_GREEN = (76, 175, 80)
PIPE_DARK = (56, 142, 60)
GROUND_BROWN = (156, 102, 31)
GROUND_DARK = (121, 85, 61)
BIRD_YELLOW = (255, 204, 0)
BIRD_ORANGE = (255, 140, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Physique oiseau
GRAVITY = 0.35  # px/frame^2
FLAP_VELOCITY = -6.5  # px/frame
MAX_FALL_SPEED = 12
BIRD_RADIUS = 12

# Sol
GROUND_HEIGHT = 64
GROUND_SPEED_PARALLAX = 1.0  # facteur par rapport à la vitesse des tuyaux

# Tuyaux
PIPE_WIDTH = 52
GAP_START = 140
GAP_MIN = 100
PIPE_SPEED_START = 2.5
PIPE_SPEED_MAX = 5.0
PIPE_SPAWN_INTERVAL = 1.2  # secondes
SAFE_MARGIN_TOP = 40
SAFE_MARGIN_BOTTOM = 80  # distance mini au-dessus du sol

# Progression de difficulté
DIFF_EVERY = 10  # tous les N points
DIFF_SPEED_STEP = 0.2
DIFF_GAP_STEP = 5

# UI
BIG_FONT_SIZE = 48
MID_FONT_SIZE = 28
SMALL_FONT_SIZE = 18

# Fichier de sauvegarde du meilleur score
BEST_FILE = "best_score.json"

# Etats de jeu
MENU, PLAYING, PAUSED, GAME_OVER = "MENU", "PLAYING", "PAUSED", "GAME_OVER"


# -------------------------------------------------------------
# Utilitaires
# -------------------------------------------------------------
def clamp(value: float, a: float, b: float) -> float:
    """Contraindre value dans [a, b]."""
    return max(a, min(b, value))


def circle_rect_collision(cx: float, cy: float, r: float, rx: float, ry: float, rw: float, rh: float) -> bool:
    """Collision cercle-rectangle (approximation standard par clamp)."""
    closest_x = clamp(cx, rx, rx + rw)
    closest_y = clamp(cy, ry, ry + rh)
    dx = cx - closest_x
    dy = cy - closest_y
    return dx * dx + dy * dy <= r * r


# -------------------------------------------------------------
# Classes principales
# -------------------------------------------------------------
@dataclass
class Bird:
    x: float
    y: float
    vy: float = 0.0

    def flap(self):
        """Appliquer une impulsion vers le haut."""
        self.vy = FLAP_VELOCITY

    def update(self):
        """Mettre à jour la physique de l'oiseau (gravité + clamp vitesse)."""
        self.vy = clamp(self.vy + GRAVITY, -999, MAX_FALL_SPEED)
        self.y += self.vy

    def get_circle(self):
        """Retourne (cx, cy, r) pour les collisions."""
        return (self.x, self.y, BIRD_RADIUS)

    def draw(self, surf: pygame.Surface):
        """Dessiner l'oiseau (formes primitives)."""
        # Corps (cercle)
        pygame.draw.circle(surf, BIRD_YELLOW, (int(self.x), int(self.y)), BIRD_RADIUS)
        # Bec (petit triangle orienté vers la droite)
        bx = int(self.x + BIRD_RADIUS - 2)
        by = int(self.y)
        points = [(bx, by), (bx + 8, by - 3), (bx + 8, by + 3)]
        pygame.draw.polygon(surf, BIRD_ORANGE, points)
        # Aile (arc simple dépendant de la vitesse)
        tilt = clamp(-self.vy * 3, -30, 30)
        wing_r = BIRD_RADIUS - 4
        rect = pygame.Rect(int(self.x - wing_r), int(self.y - wing_r), wing_r * 2, wing_r * 2)
        start_angle = math.radians(200 + tilt)
        end_angle = math.radians(340 + tilt)
        pygame.draw.arc(surf, BIRD_ORANGE, rect, start_angle, end_angle, 2)


class PipePair:
    def __init__(self, x: float, gap_y: float, gap_size: float):
        self.x = x
        self.gap_y = gap_y
        self.gap_size = gap_size
        self.width = PIPE_WIDTH
        self.passed = False  # pour le scoring

    def update(self, speed: float):
        self.x -= speed

    def is_off_screen(self) -> bool:
        return self.x + self.width < 0

    def collides_with(self, circle) -> bool:
        cx, cy, r = circle
        top_rect = (self.x, 0, self.width, self.gap_y - self.gap_size / 2)
        bottom_rect = (
            self.x,
            self.gap_y + self.gap_size / 2,
            self.width,
            HEIGHT - GROUND_HEIGHT - (self.gap_y + self.gap_size / 2),
        )
        return circle_rect_collision(cx, cy, r, *top_rect) or circle_rect_collision(cx, cy, r, *bottom_rect)

    def draw(self, surf: pygame.Surface):
        # Tuyau du haut
        top_h = int(self.gap_y - self.gap_size / 2)
        if top_h > 0:
            top_rect = pygame.Rect(int(self.x), 0, self.width, top_h)
            pygame.draw.rect(surf, PIPE_GREEN, top_rect)
            # Bord sombre
            pygame.draw.rect(surf, PIPE_DARK, (int(self.x), top_h - 8, self.width, 8))
        # Tuyau du bas
        bottom_y = int(self.gap_y + self.gap_size / 2)
        bottom_h = HEIGHT - GROUND_HEIGHT - bottom_y
        if bottom_h > 0:
            bottom_rect = pygame.Rect(int(self.x), bottom_y, self.width, bottom_h)
            pygame.draw.rect(surf, PIPE_GREEN, bottom_rect)
            pygame.draw.rect(surf, PIPE_DARK, (int(self.x), bottom_y, self.width, 8))


class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.state = MENU
        self.font_big = pygame.font.SysFont(None, BIG_FONT_SIZE)
        self.font_mid = pygame.font.SysFont(None, MID_FONT_SIZE)
        self.font_small = pygame.font.SysFont(None, SMALL_FONT_SIZE)
        self.best_score = 0
        self.load_best()
        self.reset(full=True)
        self.menu_blink_timer = 0.0

    # --------------------- persistance ---------------------
    def load_best(self):
        """Charger le meilleur score depuis un fichier JSON (si présent)."""
        try:
            if os.path.exists(BEST_FILE):
                with open(BEST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.best_score = int(data.get("best", 0))
        except Exception:
            # En cas d'erreur I/O ou JSON, ignorer silencieusement
            self.best_score = 0

    def save_best(self):
        """Sauvegarder le meilleur score dans un JSON."""
        try:
            with open(BEST_FILE, "w", encoding="utf-8") as f:
                json.dump({"best": int(self.best_score)}, f)
        except Exception:
            pass

    # ----------------------- logique -----------------------
    def reset(self, full: bool = False):
        """Réinitialiser une partie. Si full=True, revenir au MENU."""
        self.score = 0
        self.bird = Bird(x=WIDTH * 0.25, y=HEIGHT * 0.5)
        self.pipes: list[PipePair] = []
        self.pipe_speed = PIPE_SPEED_START
        self.gap_size = GAP_START
        self.spawn_timer = 0.0
        self.ground_x = 0.0  # pour l'animation du sol
        if full:
            self.state = MENU

    def spawn_pipe(self):
        """Faire apparaître une nouvelle paire de tuyaux avec un écart vertical aléatoire."""
        min_y = SAFE_MARGIN_TOP + self.gap_size / 2
        max_y = HEIGHT - GROUND_HEIGHT - SAFE_MARGIN_BOTTOM - self.gap_size / 2
        gap_y = random.uniform(min_y, max_y) if max_y > min_y else (HEIGHT - GROUND_HEIGHT) / 2
        self.pipes.append(PipePair(WIDTH, gap_y, self.gap_size))

    def update_difficulty(self):
        """Augmenter la difficulté par paliers selon le score."""
        if self.score > 0 and self.score % DIFF_EVERY == 0:
            # augmenter vitesse
            new_speed = min(self.pipe_speed + DIFF_SPEED_STEP, PIPE_SPEED_MAX)
            # réduire la taille de l'écart
            new_gap = max(self.gap_size - DIFF_GAP_STEP, GAP_MIN)
            self.pipe_speed = new_speed
            self.gap_size = new_gap

    def handle_input(self, event: pygame.event.Event):
        """Gérer les entrées clavier/souris selon l'état courant."""
        if event.type == pygame.QUIT:
            self.quit_game()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.quit_game()
            if self.state == MENU:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.state = PLAYING
            elif self.state == PLAYING:
                if event.key == pygame.K_p:
                    self.state = PAUSED
                elif event.key == pygame.K_r:
                    self.reset(full=False)
                elif event.key in (pygame.K_SPACE, pygame.K_UP):
                    self.bird.flap()
            elif self.state == PAUSED:
                if event.key == pygame.K_p:
                    self.state = PLAYING
            elif self.state == GAME_OVER:
                if event.key == pygame.K_r:
                    self.reset(full=False)
                    self.state = PLAYING
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # clic gauche = flap dans MENU/PLAYING/GAME_OVER (pour redémarrer)
            if self.state == MENU:
                self.state = PLAYING
            elif self.state == PLAYING:
                self.bird.flap()
            elif self.state == GAME_OVER:
                self.reset(full=False)
                self.state = PLAYING

    def update(self, dt: float):
        """Mettre à jour la logique selon l'état de jeu."""
        if self.state == MENU:
            self.menu_blink_timer += dt
            # On anime doucement l'oiseau au menu (flottement)
            self.bird.vy = math.sin(pygame.time.get_ticks() / 500) * 0.5
            self.bird.y = HEIGHT * 0.5 + math.sin(pygame.time.get_ticks() / 600) * 10
            self.animate_ground(dt)
            return

        if self.state == PAUSED:
            return

        if self.state == GAME_OVER:
            self.animate_ground(dt)
            return

        # PLAYING
        self.bird.update()
        self.animate_ground(dt)

        # Spawning des tuyaux
        self.spawn_timer += dt
        if self.spawn_timer >= PIPE_SPAWN_INTERVAL:
            self.spawn_timer = 0.0
            self.spawn_pipe()

        # Mise à jour des tuyaux + scoring
        circle = self.bird.get_circle()
        for pipe in list(self.pipes):
            pipe.update(self.pipe_speed)
            # Score: lorsque l'oiseau dépasse le centre du tuyau (une seule fois)
            center_x = pipe.x + pipe.width / 2
            if not pipe.passed and self.bird.x > center_x:
                pipe.passed = True
                self.score += 1
                self.update_difficulty()

            # Collision avec les tuyaux
            if pipe.collides_with(circle):
                self.trigger_game_over()

        # Nettoyage des tuyaux hors écran
        self.pipes = [p for p in self.pipes if not p.is_off_screen()]

        # Collision avec le sol
        if self.bird.y + BIRD_RADIUS >= HEIGHT - GROUND_HEIGHT:
            self.trigger_game_over()

    def animate_ground(self, dt: float):
        """Animation du sol défilant (simple bande)."""
        self.ground_x -= self.pipe_speed * GROUND_SPEED_PARALLAX
        # bouclage
        ground_tex_w = 24  # largeur d'un motif
        if self.ground_x <= -ground_tex_w:
            self.ground_x += ground_tex_w

    def trigger_game_over(self):
        """Basculer en état GAME_OVER et mettre à jour le meilleur score."""
        self.state = GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.save_best()

    def quit_game(self):
        """Sauvegarder et quitter proprement."""
        self.save_best()
        pygame.quit()
        sys.exit(0)

    # ----------------------- rendu -------------------------
    def draw(self):
        # Ciel
        self.screen.fill(SKY)

        # Arrière-plan minimal (quelques nuages stylisés)
        self.draw_clouds()

        # Tuyaux
        for pipe in self.pipes:
            pipe.draw(self.screen)

        # Sol
        self.draw_ground()

        # Oiseau (au-dessus du sol)
        self.bird.draw(self.screen)

        # HUD / Etats
        if self.state == MENU:
            self.draw_menu()
        elif self.state == PLAYING:
            self.draw_score()
        elif self.state == PAUSED:
            self.draw_score()
            self.draw_center_text("Pause", self.font_big)
        elif self.state == GAME_OVER:
            self.draw_score(game_over=True)
            self.draw_game_over()

        pygame.display.flip()

    def draw_text_shadow(self, text: str, font: pygame.font.Font, x: int, y: int, center=True):
        """Dessiner un texte blanc avec ombre noire pour la lisibilité."""
        surf = font.render(text, True, WHITE)
        shadow = font.render(text, True, BLACK)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
            shadow_rect = rect.copy()
            shadow_rect.move_ip(2, 2)
        else:
            rect.topleft = (x, y)
            shadow_rect = rect.move(2, 2)
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(surf, rect)

    def draw_score(self, game_over: bool = False):
        """Afficher le score courant (et optionnellement le meilleur)."""
        self.draw_text_shadow(str(self.score), self.font_big, WIDTH // 2, 32, center=True)
        if game_over:
            self.draw_text_shadow(f"Meilleur: {self.best_score}", self.font_small, WIDTH // 2, 64, center=True)

    def draw_menu(self):
        """Dessiner l'écran de menu."""
        self.draw_text_shadow("FLAPPY", self.font_big, WIDTH // 2, HEIGHT // 2 - 90)
        self.draw_text_shadow("BIRD", self.font_big, WIDTH // 2, HEIGHT // 2 - 50)
        self.draw_text_shadow(f"Record: {self.best_score}", self.font_small, WIDTH // 2, HEIGHT // 2)
        # Astuce clignotante
        blink = (int(self.menu_blink_timer * 2) % 2) == 0
        if blink:
            self.draw_text_shadow("Espace / Clic pour jouer", self.font_small, WIDTH // 2, HEIGHT // 2 + 40)

    def draw_game_over(self):
        """Dessiner l'écran de fin de partie avec instructions."""
        self.draw_center_text("GAME OVER", self.font_big, dy=-20)
        self.draw_center_text("R pour recommencer", self.font_small, dy=20)
        self.draw_center_text("Esc pour quitter", self.font_small, dy=40)

    def draw_center_text(self, text: str, font: pygame.font.Font, dy: int = 0):
        self.draw_text_shadow(text, font, WIDTH // 2, HEIGHT // 2 + dy, center=True)

    def draw_ground(self):
        """Dessiner une bande de sol défilante simple."""
        ground_y = HEIGHT - GROUND_HEIGHT
        pygame.draw.rect(self.screen, GROUND_BROWN, (0, ground_y, WIDTH, GROUND_HEIGHT))
        # Motif (petites dalles) qui défilent
        tile_w = 24
        x = int(self.ground_x)
        for i in range(-1, WIDTH // tile_w + 3):
            rx = x + i * tile_w
            pygame.draw.rect(self.screen, GROUND_DARK, (rx, ground_y + 40, tile_w - 4, 10))

    def draw_clouds(self):
        """Dessiner quelques nuages stylisés (option décoratif)."""
        t = pygame.time.get_ticks() / 1000.0
        # Nuage 1
        cx = WIDTH - (t * 15 % (WIDTH + 60))
        cy = 80
        self.draw_cloud(int(cx), cy)
        # Nuage 2
        cx2 = WIDTH - (t * 10 % (WIDTH + 120)) + 60
        cy2 = 140
        self.draw_cloud(int(cx2), cy2, scale=0.8)

    def draw_cloud(self, x: int, y: int, scale: float = 1.0):
        r = int(18 * scale)
        pygame.draw.circle(self.screen, WHITE, (x, y), r)
        pygame.draw.circle(self.screen, WHITE, (x + int(1.2 * r), y + int(0.2 * r)), int(0.9 * r))
        pygame.draw.circle(self.screen, WHITE, (x - int(1.0 * r), y + int(0.1 * r)), int(0.8 * r))


# -------------------------------------------------------------
# Boucle principale
# -------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    game = Game(screen)

    running = True
    while running:
        dt = game.clock.tick(FPS) / 1000.0  # secondes

        # Entrées
        for event in pygame.event.get():
            game.handle_input(event)

        # Mise à jour
        game.update(dt)

        # Rendu
        game.draw()


if __name__ == "__main__":
    main()
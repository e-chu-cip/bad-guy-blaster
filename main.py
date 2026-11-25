"""Bad Guy Blasters.

A small Pygame project designed to be read and changed by a new programmer.
Run it with: python3 main.py
"""

import math
import random
from array import array
from dataclasses import dataclass

import pygame


# These are constants: named values that do not change while the game runs.
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
PLAY_WIDTH = 730
FPS = 60
PLAYER_SPEED = 4
BULLET_SPEED = 9
EASY_MATH_TIME = 10
HARD_MATH_TIME = 15
FIRST_PROBLEM_DELAY = 15_000
NEXT_PROBLEM_DELAY = 30_000
HIDEOUT_TIME = 10_000
HIDEOUT_EXIT = (145, 45)
ICE_COST = 8
FIRE_COST = {"red": 5, "green": 3, "blue": 2, "yellow": 1}
BOMB_COST = {"red": 7, "green": 4, "blue": 2, "yellow": 2}
BOMB_RADIUS = 100

# Short pages keep the guide readable without scrolling.
HOW_TO_PLAY_PAGES = (
    ("Move, aim, and survive", (
        "Your goal: defeat every robot and clear all 10 levels!",
        "Start with 3 lives, 3 Basic bullets, and 2 Mega bullets.",
        "Move with WASD or the arrow keys. Walls block your path.",
        "Shots travel in the direction you last moved. Aim before firing!",
        "SPACE fires a Basic bullet. M fires a Mega bullet.",
        "Avoid touching enemies: most cost 1 life; yellow robots cost 3!",
        "Reach level 5 to earn an extra life. No lives left means game over.",
        "Press ENTER on the main menu to start your adventure.",
    )),
    ("Solve math to earn ammunition", (
        "Your first question arrives after 15 seconds; later ones after 30.",
        "The action pauses during math, so take a moment to think.",
        "Type your answer, use BACKSPACE to fix it, then press ENTER.",
        "Watch the timer: each question gives you 10 or 15 seconds.",
        "A correct answer earns 1 or 2 Basic bullets, as shown on screen.",
        "You get one attempt. A wrong answer or timeout earns no bullets.",
        "For an extra Mega bullet, solve two 2-bullet questions in a row",
        "within 20 seconds total. The second question appears right away.",
        "Out of bullets? Dodge enemies and wait for the next question!",
    )),
    ("Know your enemies", (
        "Red: one Basic bullet defeats it.",
        "Green: needs two Basic hits. After the first, it disappears",
        "for 5 seconds, then returns. One Mega bullet defeats it outright.",
        "Blue: Basic bullets cannot defeat it. Use Mega, poison, or a bomb.",
        "Yellow: fast and dangerous! Touching it costs 3 lives.",
        "Defeat a yellow robot to collect a poison potion. While holding it,",
        "touch a robot to defeat it and use up the potion.",
        "Mega bullets defeat any regular robot in one hit.",
        "Black zombies live in the white world. Dodge them or use ice:",
        "bullets and poison cannot hurt them. They do not count for a level.",
    )),
    ("Explore, shop, and use your Bag", (
        "SHIFT enters the Hide Out in the black world: 10 safe seconds.",
        "You get 2 visits per game. SHIFT again leaves early.",
        "From level 2, walk into the tornado portal to visit the white world.",
        "Step away from its arrival portal, then back in to return.",
        "In the white world, press TAB to shop. Robot kills earn credits.",
        "Press B or click Bag. Click an item to turn it Active or Inactive.",
        "Ice freezes the next enemy you touch for 4 seconds, using one ice.",
        "Fire gives +30% speed for 10 seconds. Turning it off saves time.",
        "With Bomb active, Z throws one bomb in the black world.",
        "Bombs pass through walls and defeat up to 3 nearby robots.",
        "Bag and Store pause the game. TAB or ESC closes either menu.",
    )),
)

# Counts for each level, in the order red, green, blue, yellow.
LEVEL_ENEMIES = [
    (3, 0, 0, 0),
    (2, 1, 0, 0),
    (3, 1, 0, 0),
    (4, 1, 1, 0),
    (4, 2, 1, 0),
    (5, 2, 1, 1),
    (6, 2, 2, 1),
    (6, 3, 3, 1),
    (7, 3, 3, 2),
    (8, 3, 3, 2),
]

NAVY = (8, 12, 32)
BLUE = (35, 90, 210)
BRIGHT_BLUE = (45, 135, 255)
LIGHT_BLUE = (70, 180, 255)
YELLOW = (255, 220, 50)
RED = (225, 65, 70)
GREEN = (80, 220, 130)
WHITE = (245, 245, 245)
GRAY = (145, 155, 180)
LIGHT_GRAY = (205, 205, 215)
BLACK = (15, 15, 20)
POISON_PURPLE = (190, 80, 255)


def make_sound(start_frequency, end_frequency, duration, volume, bell=False):
    """Create a short sound effect without needing a separate audio file."""
    mixer_settings = pygame.mixer.get_init()
    if not mixer_settings:
        return None

    sample_rate, sample_format, channels = mixer_settings
    if abs(sample_format) != 16:
        return None

    sample_count = int(sample_rate * duration)
    samples = array("h")
    phase = 0.0
    for sample_number in range(sample_count):
        progress = sample_number / sample_count
        frequency = start_frequency + (end_frequency - start_frequency) * progress
        phase += 2 * math.pi * frequency / sample_rate
        fade = (1 - progress) ** 2
        tone = math.sin(phase)
        if bell:
            # Higher partials fade quickly, leaving a softly ringing bell tone.
            tone = (tone + 0.5 * math.sin(phase * 2.76) * (1 - progress) ** 3
                    + 0.25 * math.sin(phase * 5.4) * (1 - progress) ** 6) / 1.75
        sample = int(tone * 32767 * volume * fade)
        samples.extend([sample] * channels)
    return pygame.mixer.Sound(buffer=samples)


@dataclass
class MathProblem:
    """One question and the facts the game needs to check it."""

    question: str
    answer: int
    reward: int

    @property
    def time_limit(self):
        """Give two-bullet questions more time than one-bullet questions."""
        return EASY_MATH_TIME if self.reward == 1 else HARD_MATH_TIME


def make_math_problem(level, two_bullet=False):
    """Return a random math problem. Higher levels unlock harder questions."""
    choices = ["add", "subtract"]
    if level >= 2:
        choices.append("multiply")
    if level >= 3:
        choices.append("divide")

    kind = random.choice(choices)

    if kind == "add":
        largest = min(20 + level * 8, 99)
        # Always start with two digits; a one-digit second number is easier.
        a = random.randint(10, largest)
        b = random.randint(10 if two_bullet else 1, largest)
        reward = 1 if b < 10 else 2
        return MathProblem(f"{a} + {b} = ?", a + b, reward)

    if kind == "subtract":
        # Start with a two-digit number to avoid one-digit minus one-digit.
        a = random.randint(10, min(25 + level * 7, 99))
        b = random.randint(10 if two_bullet else 1, a)  # Keep answers nonnegative.
        reward = 1 if b < 10 else 2
        return MathProblem(f"{a} - {b} = ?", a - b, reward)

    if kind == "multiply":
        a = random.randint(10 if two_bullet else 2, min(20 + level * 8, 99))
        b = random.randint(2, 9)
        reward = 1 if a < 10 else 2
        return MathProblem(f"{a} x {b} = ?", a * b, reward)

    # Build division backward so it always has a whole-number answer.
    divisor = random.randint(2, 9)
    answer = random.randint(math.ceil(10 / divisor), 99 // divisor)
    dividend = answer * divisor
    return MathProblem(f"{dividend} / {divisor} = ?", answer, 2)


def build_walls(level):
    """Create a Pac-Man-like maze. More wall pieces appear on later levels."""
    walls = [
        pygame.Rect(0, 0, PLAY_WIDTH, 20),
        pygame.Rect(0, SCREEN_HEIGHT - 20, PLAY_WIDTH, 20),
        pygame.Rect(0, 0, 20, SCREEN_HEIGHT),
        pygame.Rect(PLAY_WIDTH - 20, 0, 20, SCREEN_HEIGHT),
        pygame.Rect(130, 110, 200, 24),
        pygame.Rect(420, 110, 180, 24),
        pygame.Rect(240, 260, 250, 24),
        pygame.Rect(100, 410, 190, 24),
        pygame.Rect(430, 460, 190, 24),
    ]
    extra_walls = [
        pygame.Rect(85, 540, 180, 24),
        pygame.Rect(560, 225, 24, 150),
        pygame.Rect(355, 510, 24, 120),
        pygame.Rect(90, 190, 24, 125),
        pygame.Rect(320, 350, 155, 24),
    ]
    walls.extend(extra_walls[: min(5, (level - 1) // 2)])
    return walls


def move_without_walking_through_walls(rect, dx, dy, walls):
    """Move a rectangle one direction at a time and stop it at walls."""
    rect.x += dx
    for wall in walls:
        if rect.colliderect(wall):
            if dx > 0:
                rect.right = wall.left
            elif dx < 0:
                rect.left = wall.right

    rect.y += dy
    for wall in walls:
        if rect.colliderect(wall):
            if dy > 0:
                rect.bottom = wall.top
            elif dy < 0:
                rect.top = wall.bottom


class Enemy:
    """A chasing robot. Its color tells the player its special power."""

    def __init__(self, x, y, speed, kind="red"):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.kind = kind
        self.world = "black"
        self.portal_ready_at = 0
        self.frozen_until = 0
        self.speed = PLAYER_SPEED if kind == "yellow" else speed
        # Mega bullets deal two damage. Blue shields block Basic bullets.
        # Keep green damage when it disappears and returns somewhere else.
        self.bullet_hits = 0
        self.hits_required = 2 if kind in ("green", "blue") else 1
        self.active = True
        self.reappear_at = 0
        self.change_timer = 0
        self.dx = self.speed
        self.dy = 0
        self.leftover_x = 0.0
        self.leftover_y = 0.0

    def take_bullet_hit(self, mega=False):
        """Record one hit and describe what should happen to this robot."""
        if self.kind == "blue" and not mega:
            return "blocked"
        self.bullet_hits += 2 if mega else 1
        if self.kind == "green" and self.bullet_hits == 1:
            return "respawn"
        if self.bullet_hits < self.hits_required:
            return "damaged"
        return "defeated"

    def update(self, player, walls):
        if pygame.time.get_ticks() < self.frozen_until:
            return
        if not self.active:
            return
        self.change_timer -= 1
        if self.change_timer <= 0:
            # Usually chase the player, but sometimes choose a random turn.
            self.leftover_x = 0
            self.leftover_y = 0
            x_distance = player.centerx - self.rect.centerx
            y_distance = player.centery - self.rect.centery
            if random.random() < 0.75:
                if abs(x_distance) > abs(y_distance):
                    self.dx = math.copysign(self.speed, x_distance)
                    self.dy = 0
                else:
                    self.dx = 0
                    self.dy = math.copysign(self.speed, y_distance)
            else:
                self.dx, self.dy = random.choice(
                    [(self.speed, 0), (-self.speed, 0), (0, self.speed), (0, -self.speed)]
                )
            self.change_timer = random.randint(25, 70)

        # Rectangles move in whole pixels, so save each fractional piece for later.
        # This lets the robots get a tiny bit faster on every new level.
        self.leftover_x += self.dx
        self.leftover_y += self.dy
        step_x = int(self.leftover_x)
        step_y = int(self.leftover_y)
        self.leftover_x -= step_x
        self.leftover_y -= step_y
        old_position = self.rect.copy()
        move_without_walking_through_walls(self.rect, step_x, step_y, walls)
        # A subpixel step is not a wall collision. Keep accumulating it until
        # slow enemies (especially zombies) have a whole pixel to move.
        if (step_x or step_y) and self.rect.topleft == old_position.topleft:
            self.change_timer = 0  # Pick a new direction after bumping a wall.
            self.leftover_x = 0
            self.leftover_y = 0

    def draw(self, screen):
        if not self.active:
            return
        colors = {
            "zombie": BLACK,
            "red": RED,
            "green": GREEN,
            "blue": BRIGHT_BLUE,
            "yellow": YELLOW,
        }
        pygame.draw.rect(screen, colors[self.kind], self.rect, border_radius=6)
        if pygame.time.get_ticks() < self.frozen_until:
            pygame.draw.rect(screen, LIGHT_BLUE, self.rect.inflate(6, 6), 3, border_radius=6)
        pygame.draw.circle(screen, WHITE, (self.rect.x + 9, self.rect.y + 10), 4)
        pygame.draw.circle(screen, WHITE, (self.rect.x + 21, self.rect.y + 10), 4)
        pygame.draw.rect(screen, BLACK, (self.rect.x + 8, self.rect.y + 21, 14, 3))
        if self.kind == "blue" and self.bullet_hits == 0:
            pygame.draw.rect(screen, WHITE, (self.rect.x + 3, self.rect.y - 5, 24, 3))
        if self.kind == "yellow":
            # The purple bottle shows that this robot is carrying poison.
            pygame.draw.rect(
                screen,
                POISON_PURPLE,
                (self.rect.right - 5, self.rect.y + 15, 8, 12),
                border_radius=3,
            )
            pygame.draw.rect(screen, WHITE, (self.rect.right - 3, self.rect.y + 12, 4, 4))


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("Bad Guy Blasters")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.big_font = pygame.font.Font(None, 54)
        self.font = pygame.font.Font(None, 34)
        self.small_font = pygame.font.Font(None, 25)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.shoot_sound = make_sound(950, 400, 0.12, 0.25)
            self.enemy_disappear_sound = make_sound(500, 90, 0.28, 0.3)
            self.math_bell_sound = make_sound(880, 880, 0.8, 0.35, bell=True)
        except pygame.error:
            # The game still works on a computer with no available audio device.
            self.shoot_sound = None
            self.enemy_disappear_sound = None
            self.math_bell_sound = None
        self.running = True
        self.reset_game()

    def reset_game(self):
        self.test_mode = False
        self.test_settings = {"level": 1, "lives": 3, "bullets": 3, "mega": 2, "poison": False}
        self.level = 1
        self.lives = 3
        self.bullets_left = 3
        self.mega_bullets = 2
        self.mega_enabled = True
        self.ice = 0
        self.fire_packs = 0
        self.bombs = 0
        self.bomb_enabled = True
        self.bomb_credits = dict.fromkeys(BOMB_COST, 0)
        self.ice_armed = False
        self.fire_until = 0
        self.fire_remaining = 0
        self.red_credits = 0
        self.fire_credits = dict.fromkeys(("red", "green", "blue", "yellow"), 0)
        self.overlay = None
        self.help_page = 0
        self.move_remainder = pygame.Vector2()
        self.mega_progress = []
        self.fireworks = []
        self.facing = pygame.Vector2(1, 0)
        self.bullets = []
        self.has_poison = False
        self.hideout = pygame.Rect(30, 38, 95, 60)
        self.hideout_clear_zone = pygame.Rect(20, 20, 250, 180)
        self.hideout_active = False
        self.hideout_uses = 2
        self.message = "Solve the problem to earn bullets!"
        self.message_until = pygame.time.get_ticks() + 3000
        self.game_state = "ready"
        self.start_level(first_problem_delay=FIRST_PROBLEM_DELAY)

    def menu_buttons(self):
        """Share button positions between drawing and mouse handling."""
        if self.overlay:
            names = ("mega", "ice", "fire", "bomb") if self.overlay == "bag" else ("buy_ice", "buy_fire", "buy_bomb")
            buttons = {name: pygame.Rect(280, 230 + i * 70, 440, 55) for i, name in enumerate(names)}
            buttons["close"] = pygame.Rect(390, 575, 220, 50)
            return buttons
        if self.game_state == "ready":
            return {"test": pygame.Rect(260, 600, 220, 50),
                    "how_to_play": pygame.Rect(520, 600, 220, 50)}
        if self.game_state == "how_to_play":
            buttons = {"help_close": pygame.Rect(390, 600, 220, 50)}
            if self.help_page > 0:
                buttons["help_previous"] = pygame.Rect(130, 600, 220, 50)
            if self.help_page < len(HOW_TO_PLAY_PAGES) - 1:
                buttons["help_next"] = pygame.Rect(650, 600, 220, 50)
            return buttons
        if self.game_state == "test_setup":
            buttons = {}
            for row, name in enumerate(("level", "lives", "bullets", "mega")):
                y = 220 + row * 75
                buttons[f"{name}_minus"] = pygame.Rect(510, y, 50, 45)
                buttons[f"{name}_plus"] = pygame.Rect(690, y, 50, 45)
            buttons["poison"] = pygame.Rect(510, 520, 230, 45)
            buttons["back"] = pygame.Rect(250, 610, 230, 55)
            buttons["start_test"] = pygame.Rect(520, 610, 230, 55)
            return buttons
        buttons = {"bag": pygame.Rect(755, 648, 100, 38)} if self.game_state == "playing" else {}
        if self.test_mode:
            buttons["back"] = pygame.Rect(860, 648, 135, 38)
        return buttons

    def handle_click(self, position):
        for action, rect in self.menu_buttons().items():
            if not rect.collidepoint(position):
                continue
            if action == "bag":
                self.open_overlay("bag")
            elif action == "close":
                self.close_overlay()
            elif action == "mega":
                if self.mega_enabled or self.mega_bullets:
                    self.mega_enabled = not self.mega_enabled
            elif action == "ice":
                if self.ice_armed or self.ice:
                    self.ice_armed = not self.ice_armed
            elif action == "fire":
                # The menu pauses time, so use the time it was opened.
                now = self.pause_started
                if self.fire_until > now:
                    self.fire_remaining = self.fire_until - now
                    self.fire_until = 0
                elif self.fire_remaining:
                    self.fire_until = now + self.fire_remaining
                    self.fire_remaining = 0
                elif self.fire_packs:
                    self.fire_packs -= 1
                    self.fire_until = now + 10000
            elif action == "bomb":
                if self.bomb_enabled or self.bombs:
                    self.bomb_enabled = not self.bomb_enabled
            elif action == "buy_bomb":
                if all(self.bomb_credits[k] >= v for k, v in BOMB_COST.items()):
                    for kind, count in BOMB_COST.items():
                        self.bomb_credits[kind] -= count
                    self.bombs += 1
            elif action == "buy_ice":
                if self.red_credits >= ICE_COST:
                    self.red_credits -= ICE_COST
                    self.ice += 1
            elif action == "buy_fire":
                cost = FIRE_COST
                if all(self.fire_credits[k] >= v for k, v in cost.items()):
                    for kind, count in cost.items():
                        self.fire_credits[kind] -= count
                    self.fire_packs += 1
            elif action == "test":
                self.game_state = "test_setup"
            elif action == "how_to_play":
                self.help_page = 0
                self.game_state = "how_to_play"
            elif action == "help_close":
                self.game_state = "ready"
            elif action == "help_previous":
                self.help_page -= 1
            elif action == "help_next":
                self.help_page += 1
            elif action == "back":
                self.reset_game()
            elif action == "start_test":
                self.start_test()
            elif action == "poison":
                self.test_settings["poison"] = not self.test_settings["poison"]
            else:
                name, direction = action.split("_")
                minimum = 0 if name in ("bullets", "mega") else 1
                value = self.test_settings[name] + (1 if direction == "plus" else -1)
                self.test_settings[name] = max(minimum, min(10, value) if name == "level" else value)
            return

    def open_overlay(self, name):
        self.overlay = name
        self.pause_started = pygame.time.get_ticks()

    def close_overlay(self):
        elapsed = pygame.time.get_ticks() - self.pause_started
        # Pause all timers, including math, effects, and hidden-world enemies.
        for name in ("next_problem_at", "problem_started", "problem_first_started",
                     "invincible_until", "message_until", "hideout_started"):
            if hasattr(self, name):
                setattr(self, name, getattr(self, name) + elapsed)
        if self.fire_until:
            self.fire_until += elapsed
        for enemy in self.enemies + self.zombies:
            enemy.reappear_at += elapsed
            enemy.portal_ready_at += elapsed
            enemy.frozen_until += elapsed
        self.fireworks = [(p, v, c, t + elapsed) for p, v, c, t in self.fireworks]
        self.overlay = None

    def record_kill(self, enemy):
        if enemy.kind in self.bomb_credits:
            self.bomb_credits[enemy.kind] += 1
        if enemy.kind in self.fire_credits:
            self.fire_credits[enemy.kind] += 1
        if enemy.kind == "red":
            self.red_credits += 1

    def freeze_on_touch(self, enemy, now):
        if now < enemy.frozen_until:
            return True
        if self.ice_armed and self.ice:
            self.ice -= 1
            self.ice_armed = False
            enemy.frozen_until = now + 4000
            self.message = "Frozen for 4 seconds!"
            self.message_until = now + 2000
            return True
        return False

    def start_test(self):
        """Start a fresh game using exactly the selected test settings."""
        settings = self.test_settings.copy()
        self.reset_game()
        self.test_settings = settings
        self.test_mode = True
        self.level = settings["level"]
        self.lives = settings["lives"]
        self.bullets_left = settings["bullets"]
        self.mega_bullets = settings["mega"]
        self.has_poison = settings["poison"]
        self.game_state = "playing"
        self.start_level(first_problem_delay=FIRST_PROBLEM_DELAY)
        self.message = "Test game! Use Main Menu to return."

    def draw_button(self, rect, label, highlighted=False, subtitle=None):
        color = BLUE if rect.collidepoint(pygame.mouse.get_pos()) else (35, 55, 100)
        if highlighted:
            color = YELLOW
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, YELLOW if highlighted else LIGHT_BLUE, rect, 2, border_radius=8)
        text_color = BLACK if highlighted else WHITE
        text = self.font.render(label, True, text_color)
        center = (rect.centerx, rect.centery - 10) if subtitle else rect.center
        self.screen.blit(text, text.get_rect(center=center))
        if subtitle:
            text = self.small_font.render(subtitle, True, text_color)
            self.screen.blit(text, text.get_rect(center=(rect.centerx, rect.centery + 14)))

    def draw_test_setup(self):
        self.screen.fill(NAVY)
        title = self.big_font.render("TEST GAME", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(500, 110)))
        hint = self.small_font.render("Click + or - to choose your starting settings", True, WHITE)
        self.screen.blit(hint, hint.get_rect(center=(500, 165)))
        for row, name in enumerate(("level", "lives", "bullets", "mega")):
            y = 220 + row * 75
            label = self.font.render("Mega bullets" if name == "mega" else name.title(), True, WHITE)
            self.screen.blit(label, (260, y + 10))
            value = self.font.render(str(self.test_settings[name]), True, YELLOW)
            self.screen.blit(value, value.get_rect(center=(625, y + 22)))
        self.screen.blit(self.font.render("Poison", True, WHITE), (260, 530))
        for action, rect in self.menu_buttons().items():
            if action == "poison":
                label = "Yes" if self.test_settings["poison"] else "No"
            elif action == "back":
                label = "Main Menu"
            elif action == "start_test":
                label = "Start Test"
            else:
                label = "+" if action.endswith("plus") else "-"
            self.draw_button(rect, label)

    def start_level(self, first_problem_delay=0):
        self.mega_pair_offered = False
        self.blue_rounds_waited = 0
        self.mega_question = False
        self.mega_progress.clear()
        self.walls = build_walls(self.level)
        self.player = pygame.Rect(*HIDEOUT_EXIT, 30, 30)
        self.bullets.clear()
        enemy_starts = [
            (650, 620), (640, 55), (60, 620), (350, 180), (650, 350),
            (300, 620), (180, 340), (520, 560), (350, 50), (650, 180),
            (510, 330), (170, 570), (430, 620), (60, 480),
            (430, 200), (220, 180),
        ]
        enemy_speed = min(1.0 + (self.level - 1) * 0.12, 2.1)
        enemy_kinds = [
            kind
            for kind, count in zip(("red", "green", "blue", "yellow"), LEVEL_ENEMIES[self.level - 1])
            for _ in range(count)
        ]
        self.enemies = [
            Enemy(x, y, enemy_speed, enemy_kinds[number])
            for number, (x, y) in enumerate(enemy_starts[:len(enemy_kinds)])
        ]
        self.world = "black"
        self.black_walls = self.walls
        self.fences = [pygame.Rect(190, 160, 190, 22), pygame.Rect(440, 350, 180, 22),
                       pygame.Rect(120, 510, 190, 22)]
        self.trees = [pygame.Rect(100, 250, 48, 55), pygame.Rect(510, 140, 48, 55),
                      pygame.Rect(340, 380, 48, 55), pygame.Rect(560, 530, 48, 55)]
        self.white_walls = self.black_walls[:4] + self.fences + self.trees
        self.store = pygame.Rect(600, 35, 100, 75)
        self.white_walls.append(self.store)
        self.portal = None
        self.portal_armed = False
        self.zombies = []
        if self.level >= 2:
            # Fit the portal and its arrival area in both worlds.
            candidates = [pygame.Rect(x, y, 54, 64)
                          for x in range(40, PLAY_WIDTH - 90, 20)
                          for y in range(40, SCREEN_HEIGHT - 90, 20)]
            candidates = [rect for rect in candidates if not any(
                rect.inflate(35, 35).colliderect(obstacle)
                for obstacle in self.black_walls + self.white_walls + [self.hideout_clear_zone]
            ) and not any(rect.colliderect(enemy.rect) for enemy in self.enemies)]
            self.portal = random.choice(candidates)
            self.portal_armed = True
            spots = [pygame.Rect(x, y, 30, 30)
                     for x in range(50, PLAY_WIDTH - 60, 60)
                     for y in range(60, SCREEN_HEIGHT - 60, 60)]
            spots = [rect for rect in spots if not any(rect.colliderect(wall) for wall in self.white_walls)
                     and not rect.colliderect(self.portal.inflate(180, 180))]
            for rect in random.sample(spots, 4):
                zombie = Enemy(rect.x, rect.y, enemy_speed * 0.25, "zombie")
                zombie.world = "white"
                self.zombies.append(zombie)
        self.invincible_until = pygame.time.get_ticks() + 1500
        if first_problem_delay:
            self.math_active = False
            self.next_problem_at = pygame.time.get_ticks() + first_problem_delay
        else:
            self.new_problem()

    def new_problem(self, two_bullet=False):
        if two_bullet:
            # The second question belongs to the same opportunity, not a new round.
            self.mega_question = True
        else:
            needs_mega = self.mega_bullets == 0 and any(
                enemy.kind == "blue" for enemy in self.enemies
            )
            self.blue_rounds_waited = self.blue_rounds_waited + 1 if needs_mega else 0
            self.mega_question = (
                not self.mega_pair_offered
                or self.blue_rounds_waited >= 3
                or random.random() < 1 / 3
            )
            if self.mega_question:
                self.mega_pair_offered = True
                self.blue_rounds_waited = 0
            self.mega_progress.clear()
        self.problem = make_math_problem(self.level, two_bullet=self.mega_question)
        self.typed_answer = ""
        self.problem_started = pygame.time.get_ticks()
        self.problem_first_started = self.problem_started
        self.math_active = True
        if self.math_bell_sound:
            self.math_bell_sound.play()

    def handle_key(self, event):
        if self.game_state == "how_to_play":
            if event.key == pygame.K_ESCAPE:
                self.game_state = "ready"
            elif event.key == pygame.K_LEFT:
                self.help_page = max(0, self.help_page - 1)
            elif event.key == pygame.K_RIGHT:
                self.help_page = min(len(HOW_TO_PLAY_PAGES) - 1, self.help_page + 1)
            return
        if self.overlay:
            if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                self.close_overlay()
            return
        if self.game_state == "playing" and event.key == pygame.K_b:
            self.open_overlay("bag")
            return
        if self.game_state == "playing" and event.key == pygame.K_TAB and self.world == "white":
            self.open_overlay("store")
            return
        if self.game_state == "test_setup":
            if event.key == pygame.K_RETURN:
                self.start_test()
            return
        if self.game_state == "ready":
            if event.key == pygame.K_RETURN:
                self.game_state = "playing"
                # The opening countdown begins only after the player is ready.
                self.next_problem_at = pygame.time.get_ticks() + FIRST_PROBLEM_DELAY
                self.message = "Go! Your first math problem arrives in 15 seconds."
                self.message_until = pygame.time.get_ticks() + 2500
            return

        if self.game_state != "playing":
            if event.key == pygame.K_r:
                self.reset_game()
            return

        if self.hideout_active:
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.leave_hideout()
            return

        if self.math_active:
            if event.key == pygame.K_RETURN:
                self.check_answer()
            elif event.key == pygame.K_BACKSPACE:
                self.typed_answer = self.typed_answer[:-1]
            elif event.unicode.isdigit() and len(self.typed_answer) < 3:
                self.typed_answer += event.unicode
            return

        if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            self.enter_hideout()
        elif event.key == pygame.K_SPACE:
            self.shoot()
        elif event.key == pygame.K_m:
            self.shoot(mega=True)
        elif event.key == pygame.K_z:
            self.launch_bomb()

    def enter_hideout(self):
        if self.hideout_active or self.math_active or self.game_state != "playing":
            return
        if self.world == "white":
            self.message = "Return through the portal to use the Hide Out."
            self.message_until = pygame.time.get_ticks() + 2000
            return
        if self.hideout_uses == 0:
            self.message = "No Hide Out visits left this game!"
            self.message_until = pygame.time.get_ticks() + 2000
            return
        self.hideout_uses -= 1
        self.hideout_active = True
        self.hideout_started = pygame.time.get_ticks()
        self.player.center = self.hideout.center
        # Move nearby robots away so none can wait beside the exit.
        for enemy in self.enemies:
            if enemy.world == "black" and enemy.active and enemy.rect.colliderect(self.hideout_clear_zone):
                self.find_respawn_spot(enemy)

    def leave_hideout(self):
        now = pygame.time.get_ticks()
        self.hideout_active = False
        self.player.topleft = HIDEOUT_EXIT
        self.next_problem_at += now - self.hideout_started
        self.invincible_until = now + 1800
        self.message = "Back outside!"
        self.message_until = now + 1800

    def update_enemies(self, now):
        for enemy in self.enemies:
            enemy_walls = self.white_walls if enemy.world == "white" else self.black_walls + [self.hideout]
            target = self.player if enemy.world == self.world else self.portal
            if self.hideout_active:
                if enemy.world == "black":
                    enemy_walls = enemy_walls + [self.hideout_clear_zone]
                target = pygame.Rect(600, 580, 30, 30)
            if not enemy.active and now >= enemy.reappear_at:
                self.find_respawn_spot(enemy)
            enemy.update(target or self.player, enemy_walls)
            if (self.portal and enemy.active and enemy.world != self.world
                    and now >= max(enemy.portal_ready_at, enemy.frozen_until) and enemy.rect.colliderect(self.portal)):
                if self.world == "black" or sum(e.world == "white" for e in self.enemies) < 2:
                    enemy.world = self.world
                    enemy.rect.center = self.portal.center
                    enemy.portal_ready_at = now + 1500
                    enemy.change_timer = 0
        if self.world == "white":
            for zombie in self.zombies:
                zombie.update(self.player, self.white_walls)

    def update_portal(self, now):
        if self.portal is None:
            return
        if not self.player.colliderect(self.portal):
            self.portal_armed = True
        elif self.portal_armed:
            self.world = "white" if self.world == "black" else "black"
            self.walls = self.white_walls if self.world == "white" else self.black_walls
            self.player.center = self.portal.center
            self.portal_armed = False
            self.bullets.clear()
            self.fireworks.clear()
            self.invincible_until = now + 1500
            self.message = f"Welcome to the {self.world} world!"
            self.message_until = now + 2000

    def check_answer(self):
        if not self.typed_answer:
            return
        if int(self.typed_answer) == self.problem.answer:
            self.bullets_left += self.problem.reward
            self.message = f"Correct! +{self.problem.reward} bullet{'s' if self.problem.reward > 1 else ''}"
            if self.mega_question:
                elapsed = pygame.time.get_ticks() - self.problem_first_started
                self.mega_progress.append(elapsed)
                if len(self.mega_progress) == 2:
                    if sum(self.mega_progress) <= 20_000:
                        self.mega_bullets += 1
                        self.message += " +1 Mega!"
                    self.mega_progress.clear()
                else:
                    self.new_problem(two_bullet=True)
                    self.message += " Next: finish the Mega pair!"
                    self.message_until = pygame.time.get_ticks() + 2500
                    return
            self.math_active = False
            self.next_problem_at = pygame.time.get_ticks() + NEXT_PROBLEM_DELAY
        else:
            self.fail_problem()
        self.message_until = pygame.time.get_ticks() + 2500

    def fail_problem(self, timed_out=False):
        """End the only attempt without awarding or removing ammunition."""
        now = pygame.time.get_ticks()
        self.typed_answer = ""
        self.mega_progress.clear()
        prefix = "Time's up!" if timed_out else "Incorrect!"
        self.message = f"{prefix} Answer: {self.problem.answer}. No reward."
        self.message_until = now + 2500
        self.math_active = False
        self.next_problem_at = now + NEXT_PROBLEM_DELAY

    def shoot(self, mega=False):
        if self.hideout_active:
            return
        if mega and not self.mega_enabled:
            self.message = "Mega bullets are inactive. Activate them in the Bag."
            self.message_until = pygame.time.get_ticks() + 1800
            return
        ammunition = self.mega_bullets if mega else self.bullets_left
        if ammunition <= 0:
            self.message = "No Mega bullets! Solve two 2-bullet problems in 20s." if mega else "No bullets—solve the next math problem!"
            self.message_until = pygame.time.get_ticks() + 1800
            return
        direction = self.facing.normalize()
        size = 15 if mega else 10
        rect = pygame.Rect(0, 0, size, size)
        rect.center = self.player.center
        bullet = {
            "rect": rect,
            "velocity": direction * BULLET_SPEED,
            "mega": mega,
        }
        self.bullets.append(bullet)
        if mega:
            self.mega_bullets -= 1
        else:
            self.bullets_left -= 1
        if self.shoot_sound:
            self.shoot_sound.play()

    def launch_bomb(self):
        """Throw one wall-passing purple ball in the direction we are facing."""
        if self.game_state != "playing" or self.math_active or self.hideout_active:
            return
        if not self.bomb_enabled:
            self.message = "Bombs are inactive. Activate them in the Bag."
            self.message_until = pygame.time.get_ticks() + 1800
            return
        if self.world != "black" or self.bombs <= 0:
            self.message = "Bombs only work in the black world!" if self.world != "black" else "Buy a bomb at the store first!"
            self.message_until = pygame.time.get_ticks() + 2500
            return
        rect = pygame.Rect(0, 0, 32, 32)
        rect.center = self.player.center
        self.bullets.append({"rect": rect, "velocity": self.facing.normalize() * BULLET_SPEED,
                             "mega": False, "bomb": True})
        self.bombs -= 1
        if self.shoot_sound:
            self.shoot_sound.play()

    def explode_bomb(self, target):
        """Defeat the target and at most two nearby regular robots."""
        origin = pygame.Vector2(target.rect.center)
        neighbors = [enemy for enemy in self.enemies
                     if enemy is not target and enemy.kind in BOMB_COST
                     and enemy.active and enemy.world == "black"
                     and origin.distance_to(enemy.rect.center) <= BOMB_RADIUS]
        neighbors.sort(key=lambda enemy: origin.distance_squared_to(enemy.rect.center))
        self.make_firework(target.rect.center, POISON_PURPLE)
        for enemy in [target] + neighbors[:2]:
            self.make_firework(enemy.rect.center, POISON_PURPLE)
            self.hit_enemy_with_bullet(enemy, mega=True)

    def update_player(self):
        keys = pygame.key.get_pressed()
        moving_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        moving_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        moving_down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        moving_up = keys[pygame.K_w] or keys[pygame.K_UP]
        speed = PLAYER_SPEED * (1.3 if pygame.time.get_ticks() < self.fire_until else 1)
        dx = (moving_right - moving_left) * speed
        dy = (moving_down - moving_up) * speed
        if dx or dy:
            direction = pygame.Vector2(dx, dy)
            if direction.length() > speed:
                direction.scale_to_length(speed)
            self.facing = direction.normalize()
            self.move_remainder += direction
            dx, dy = int(self.move_remainder.x), int(self.move_remainder.y)
            self.move_remainder -= pygame.Vector2(dx, dy)
            move_without_walking_through_walls(self.player, dx, dy, self.walls)

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet["rect"].x += round(bullet["velocity"].x)
            bullet["rect"].y += round(bullet["velocity"].y)
            bomb = bullet.get("bomb", False)
            hit_wall = not bomb and any(bullet["rect"].colliderect(wall) for wall in self.walls)
            hit_enemy = next(
                (
                    enemy
                    for enemy in self.enemies
                    if enemy.world == self.world and enemy.active and bullet["rect"].colliderect(enemy.rect)
                    and (not bomb or (self.world == "black" and enemy.kind in BOMB_COST))
                ),
                None,
            )
            if hit_wall:
                hit_enemy = None
            if hit_enemy:
                if bomb:
                    self.explode_bomb(hit_enemy)
                else:
                    self.hit_enemy_with_bullet(hit_enemy, mega=bullet["mega"])
            if hit_wall or hit_enemy or not self.screen.get_rect().colliderect(bullet["rect"]):
                if bullet["mega"]:
                    colors = {"red": RED, "green": GREEN, "blue": BRIGHT_BLUE, "yellow": YELLOW}
                    color = colors[hit_enemy.kind] if hit_enemy else WHITE
                    self.make_firework(bullet["rect"].center, color)
                self.bullets.remove(bullet)

    def make_firework(self, position, color):
        """A short burst of sparks; the explosion is visual, not extra damage."""
        now = pygame.time.get_ticks()
        for number in range(24):
            angle = number * math.tau / 24
            speed = random.uniform(65, 180)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            self.fireworks.append((pygame.Vector2(position), velocity, color, now))

    def draw_fireworks(self):
        now = pygame.time.get_ticks()
        self.fireworks = [spark for spark in self.fireworks if now - spark[3] < 700]
        for origin, velocity, color, started in self.fireworks:
            age = (now - started) / 1000
            position = origin + velocity * age + pygame.Vector2(0, 80 * age * age)
            tail = position - velocity * 0.045
            fade = 1 - age / 0.7
            tint = tuple(int(channel * fade) for channel in color)
            pygame.draw.line(self.screen, tint, tail, position, 2)
            pygame.draw.circle(self.screen, tint, position, max(1, int(4 * fade)))

    def hit_enemy_with_bullet(self, enemy, mega=False):
        """Apply the special bullet rules for each robot color."""
        now = pygame.time.get_ticks()
        hit_result = enemy.take_bullet_hit(mega)

        if hit_result == "respawn":
            enemy.active = False
            enemy.reappear_at = now + 5000
            if self.enemy_disappear_sound:
                self.enemy_disappear_sound.play()
            self.message = "Green robot will return in 5 seconds!"
            self.message_until = now + 2000
            return

        if hit_result in ("damaged", "blocked"):
            self.message = "Blue shield! Use a Mega bullet."
            self.message_until = now + 1800
            return

        if enemy.kind == "yellow":
            self.has_poison = True
            self.message = "Poison potion collected! Touch one robot to use it."
            self.message_until = now + 2500

        if enemy in self.enemies:
            self.record_kill(enemy)
            self.enemies.remove(enemy)
            if self.enemy_disappear_sound:
                self.enemy_disappear_sound.play()

    def find_respawn_spot(self, enemy):
        """Put a returning green robot in a random open part of the maze."""
        for _ in range(200):
            test_rect = pygame.Rect(
                random.randint(30, PLAY_WIDTH - 60),
                random.randint(30, SCREEN_HEIGHT - 60),
                30,
                30,
            )
            too_close_to_player = test_rect.colliderect(self.player.inflate(160, 160))
            walls = self.white_walls if enemy.world == "white" else self.black_walls + [self.hideout_clear_zone]
            hits_wall = any(test_rect.colliderect(wall) for wall in walls)
            hits_enemy = any(
                other is not enemy and other.world == enemy.world and other.active and test_rect.colliderect(other.rect)
                for other in self.enemies
            )
            if not too_close_to_player and not hits_wall and not hits_enemy:
                enemy.rect.topleft = test_rect.topleft
                enemy.active = True
                enemy.change_timer = 0
                return

        # This corner is a backup in the unlikely event no random spot worked.
        enemy.rect.topleft = (45, SCREEN_HEIGHT - 70)
        enemy.active = True

    def handle_enemy_touch(self, enemy, now):
        """Handle poison first, then the normal collision rules."""
        if self.hideout_active:
            return
        if self.freeze_on_touch(enemy, now):
            return
        if self.has_poison:
            self.has_poison = False
            collected_new_poison = enemy.kind == "yellow"
            if enemy in self.enemies:
                self.record_kill(enemy)
                self.enemies.remove(enemy)
                if self.enemy_disappear_sound:
                    self.enemy_disappear_sound.play()
            if collected_new_poison:
                self.has_poison = True
            self.message = "Poison used! That robot is defeated."
            self.message_until = now + 2000
            self.invincible_until = now + 500
        elif now > self.invincible_until:
            damage = 3 if enemy.kind == "yellow" else 1
            self.lose_life(damage)
            if enemy.kind == "yellow":
                self.message = f"Yellow poison! {self.lives} lives left."
                self.message_until = now + 2500

    def lose_life(self, damage=1):
        self.fire_credits = dict.fromkeys(self.fire_credits, 0)
        self.lives = max(0, self.lives - damage)
        if self.lives <= 0:
            self.game_state = "lost"
            return
        self.player.topleft = HIDEOUT_EXIT
        if self.world == "white":
            self.player.center = self.portal.center
            self.portal_armed = False
        self.invincible_until = pygame.time.get_ticks() + 1800
        self.message = f"Ouch! {self.lives} lives left."
        self.message_until = pygame.time.get_ticks() + 1800

    def update(self):
        if self.overlay or self.game_state != "playing":
            return

        now = pygame.time.get_ticks()
        if self.hideout_active:
            self.update_enemies(now)
            self.update_bullets()
            if now - self.hideout_started >= HIDEOUT_TIME:
                self.leave_hideout()
            return
        if self.math_active:
            seconds_used = (now - self.problem_started) / 1000
            if seconds_used >= self.problem.time_limit:
                self.fail_problem(timed_out=True)
            return  # Math time freezes the action.

        self.update_player()
        self.update_portal(now)
        self.update_bullets()
        self.update_enemies(now)

        touching_enemy = next(
            (
                enemy
                for enemy in self.enemies
                if enemy.world == self.world and enemy.active and self.player.colliderect(enemy.rect)
            ),
            None,
        )
        if touching_enemy:
            self.handle_enemy_touch(touching_enemy, now)

        if self.world == "white" and self.game_state == "playing" and now > self.invincible_until:
            zombie = next((z for z in self.zombies if self.player.colliderect(z.rect)), None)
            if zombie and not self.freeze_on_touch(zombie, now):
                self.zombies.remove(zombie)
                self.lose_life()

        if self.game_state != "playing":
            return

        if not self.enemies:
            if not self.mega_pair_offered:
                self.new_problem()
                return
            if self.level == 10:
                self.game_state = "won"
            else:
                self.level += 1
                if self.level == 5:
                    self.lives += 1
                self.bullets_left += 2
                self.start_level()
                self.message = "Level 5! +1 life!" if self.level == 5 else f"Level {self.level}!"
                self.message_until = now + 1800
        elif now >= self.next_problem_at:
            self.new_problem()

    def draw_player(self):
        color = GREEN
        if pygame.time.get_ticks() < self.invincible_until:
            color = LIGHT_BLUE if self.world == "white" else WHITE
        pygame.draw.circle(self.screen, color, self.player.center, 15)
        pygame.draw.circle(self.screen, BLACK, (self.player.centerx + 5, self.player.centery - 5), 3)
        gun_end = pygame.Vector2(self.player.center) + self.facing.normalize() * 23
        gun_color = LIGHT_BLUE if self.ice_armed else YELLOW
        pygame.draw.line(self.screen, gun_color, self.player.center, gun_end, 7)
        if pygame.time.get_ticks() < self.fire_until:
            pygame.draw.circle(self.screen, (255, 135, 30), self.player.center, 18, 3)
        if self.has_poison:
            bottle_x = self.player.left - 7
            bottle_y = self.player.centery + 2
            pygame.draw.rect(
                self.screen,
                POISON_PURPLE,
                (bottle_x, bottle_y, 10, 13),
                border_radius=4,
            )
            pygame.draw.rect(self.screen, WHITE, (bottle_x + 3, bottle_y - 4, 4, 5))

    def draw_panel(self):
        panel = pygame.Rect(PLAY_WIDTH, 0, SCREEN_WIDTH - PLAY_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, (22, 28, 52), panel)
        self.screen.blit(self.font.render(f"LEVEL  {self.level} / 10", True, WHITE), (755, 30))
        self.screen.blit(self.font.render(f"Lives: {self.lives}", True, GREEN), (755, 75))
        for label, count, color, size, y in (
            ("Basic", self.bullets_left, YELLOW, 12, 120),
            ("Mega", self.mega_bullets, LIGHT_GRAY, 18, 150),
        ):
            icon = pygame.Rect(0, 0, size, size)
            icon.center = (765, y)
            pygame.draw.ellipse(self.screen, color, icon)
            text = self.font.render(f"{label}: {count}", True, color)
            self.screen.blit(text, text.get_rect(midleft=(785, y)))
        poison_text = "Poison: READY" if self.has_poison else "Poison: none"
        poison_color = POISON_PURPLE if self.has_poison else GRAY
        self.screen.blit(self.small_font.render(poison_text, True, poison_color), (755, 165))

        if self.math_active:
            now = pygame.time.get_ticks()
            seconds_left = max(0, self.problem.time_limit - int((now - self.problem_started) / 1000))
            self.screen.blit(self.small_font.render("MATH TIME—GAME PAUSED", True, LIGHT_BLUE), (745, 190))
            self.screen.blit(self.big_font.render(self.problem.question, True, WHITE), (755, 230))
            answer_box = pygame.Rect(755, 290, 210, 55)
            pygame.draw.rect(self.screen, WHITE, answer_box, 3, border_radius=8)
            answer_text = self.big_font.render(self.typed_answer, True, YELLOW)
            self.screen.blit(answer_text, (answer_box.x + 12, answer_box.y + 7))
            self.screen.blit(self.font.render(f"Time: {seconds_left}", True, RED), (755, 365))
            self.screen.blit(
                self.small_font.render(f"Worth {self.problem.reward} bullet(s)", True, YELLOW),
                (755, 405),
            )
            self.screen.blit(self.small_font.render("Type, then press ENTER", True, GRAY), (750, 445))
        else:
            self.screen.blit(self.small_font.render("NEXT MATH PROBLEM", True, LIGHT_BLUE), (755, 200))
            countdown_now = self.hideout_started if self.hideout_active else pygame.time.get_ticks()
            seconds = max(0, math.ceil((self.next_problem_at - countdown_now) / 1000))
            self.screen.blit(self.big_font.render(str(seconds), True, WHITE), (830, 235))

        progress = f"Mega: {len(self.mega_progress)}/2 solved"
        self.screen.blit(self.small_font.render(progress, True, LIGHT_GRAY), (750, 478))
        if self.mega_progress:
            remaining = max(0, (20_000 - sum(self.mega_progress)) / 1000)
            detail = f"Next 2-bullet: {remaining:.1f}s left"
        else:
            detail = "Two 2-bullet answers in 20s"
        self.screen.blit(self.small_font.render(detail, True, GRAY), (750, 503))
        instructions = ["Move: WASD / arrows", "SPACE: Basic / M: Mega", "Z: Bomb / TAB: Store",
                        f"Hide Out: SHIFT ({self.hideout_uses} left)"]
        for number, line in enumerate(instructions):
            self.screen.blit(self.small_font.render(line, True, WHITE), (750, 545 + number * 28))
        if self.game_state == "playing" and not self.overlay:
            self.draw_button(self.menu_buttons()["bag"], "Bag (B)")

    def draw_inventory(self):
        self.screen.fill((25, 30, 48))
        title = "BAG — GAME PAUSED" if self.overlay == "bag" else "WHITE WORLD STORE"
        text = self.big_font.render(title, True, WHITE)
        self.screen.blit(text, text.get_rect(center=(500, 80)))
        if self.overlay == "bag":
            active = {"mega": self.mega_enabled, "ice": self.ice_armed,
                      "fire": self.fire_until > self.pause_started, "bomb": self.bomb_enabled}
            labels = {"mega": f"Mega: {self.mega_bullets} (M)",
                      "ice": f"Ice: {self.ice}", "fire": f"Fire: {self.fire_packs}",
                      "bomb": f"Bombs: {self.bombs} (Z)", "close": "Close"}
            hint = "Click an item to activate or deactivate it. Close to resume."
            details = f"Basic bullets: {self.bullets_left} (SPACE). Fire: +30% speed."
        else:
            labels = {"buy_ice": "Ice gun", "buy_fire": "Fire pack", "buy_bomb": "Bomb", "close": "Leave store"}
            hint = f"Ice credits: {self.red_credits} red kills"
            c = self.fire_credits
            details = "Fire credits: " + ", ".join(
                f"{kind} {c[kind]}/{count}" for kind, count in FIRE_COST.items()
            )
            bomb_progress = "Bomb credits: " + ", ".join(
                f"{k} {self.bomb_credits[k]}/{v}" for k, v in BOMB_COST.items())
            text = self.small_font.render(bomb_progress, True, WHITE)
            self.screen.blit(text, text.get_rect(center=(500, 435)))
            rule = self.small_font.render("Losing a life resets Fire credits. Purchases spend credits.", True, GRAY)
            self.screen.blit(rule, rule.get_rect(center=(500, 460)))
            stock = self.font.render(f"Owned: {self.ice} ice guns, {self.fire_packs} fire packs, {self.bombs} bombs", True, WHITE)
            self.screen.blit(stock, stock.get_rect(center=(500, 510)))
        for line, y in ((hint, 150), (details, 190)):
            text = self.small_font.render(line, True, WHITE)
            self.screen.blit(text, text.get_rect(center=(500, y)))
        for action, rect in self.menu_buttons().items():
            highlighted = False
            subtitle = None
            if action == "buy_ice":
                highlighted = self.red_credits >= ICE_COST
                subtitle = f"Cost: {ICE_COST} red kills"
            elif action == "buy_fire":
                highlighted = all(self.fire_credits[k] >= v for k, v in FIRE_COST.items())
                subtitle = "Cost: " + ", ".join(f"{v} {k}" for k, v in FIRE_COST.items()) + " kills"
            elif action == "buy_bomb":
                highlighted = all(self.bomb_credits[k] >= v for k, v in BOMB_COST.items())
                subtitle = "Cost: " + ", ".join(f"{v} {k}" for k, v in BOMB_COST.items()) + " kills"
            elif self.overlay == "bag" and action in active:
                highlighted = active[action]
                subtitle = "Active — click to deactivate" if highlighted else "Inactive — click to activate"
                if action == "fire":
                    remaining = max(0, self.fire_until - self.pause_started) if highlighted else self.fire_remaining
                    subtitle += f" ({remaining / 1000:.1f}s saved)" if remaining else ""
            self.draw_button(rect, labels[action], highlighted, subtitle)
            if action in ("bomb", "buy_bomb"):
                pygame.draw.circle(self.screen, POISON_PURPLE, (rect.left - 45, rect.centery), 22)
            if action in ("ice", "buy_ice"):
                # An icy blue gun, with a barrel, grip, and white glint.
                x, y = rect.left - 70, rect.centery
                pygame.draw.rect(self.screen, LIGHT_BLUE, (x, y - 10, 48, 15), border_radius=3)
                pygame.draw.rect(self.screen, LIGHT_BLUE, (x + 8, y, 12, 22), border_radius=3)
                pygame.draw.line(self.screen, WHITE, (x + 5, y - 7), (x + 40, y - 7), 2)

    def draw_hideout(self):
        """A small wooden house in the upper-left corner of the maze."""
        pygame.draw.rect(self.screen, (153, 96, 48), self.hideout)
        for y in range(self.hideout.top + 10, self.hideout.bottom, 10):
            pygame.draw.line(self.screen, (94, 54, 27), (30, y), (124, y), 2)
        pygame.draw.polygon(self.screen, (105, 51, 28), [(25, 40), (77, 21), (130, 40)])
        pygame.draw.rect(self.screen, (60, 35, 22), (68, 66, 20, 32))
        pygame.draw.circle(self.screen, YELLOW, (82, 83), 2)
        label = self.small_font.render("Hide Out", True, WHITE)
        self.screen.blit(label, label.get_rect(center=(77, 53)))

    def draw_hideout_interior(self):
        self.screen.fill((115, 70, 36))
        for y in range(0, SCREEN_HEIGHT, 45):
            pygame.draw.line(self.screen, (73, 43, 24), (0, y), (PLAY_WIDTH, y), 3)
        pygame.draw.rect(self.screen, (63, 36, 24), (270, 380, 190, 240))
        pygame.draw.circle(self.screen, YELLOW, (435, 510), 7)
        pygame.draw.circle(self.screen, GREEN, (365, 340), 25)
        seconds = max(0, math.ceil((HIDEOUT_TIME - pygame.time.get_ticks() + self.hideout_started) / 1000))
        for text, y, font in (
            ("HID OUT", 115, self.big_font),
            (f"Safe inside: {seconds} seconds", 190, self.font),
            ("The badguys are outside, away from the house.", 245, self.small_font),
            ("Press SHIFT to leave early", 650, self.font),
        ):
            surface = font.render(text, True, WHITE)
            self.screen.blit(surface, surface.get_rect(center=(PLAY_WIDTH // 2, y)))
        self.draw_panel()
        if self.test_mode:
            self.draw_button(self.menu_buttons()["back"], "Menu")

    def draw_ready_screen(self):
        """Show the controls and wait until the player presses Enter."""
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 225))
        self.screen.blit(shade, (0, 0))

        title = self.big_font.render("BAD GUY BLASTERS", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 125)))

        directions = [
            "GET READY!",
            "Move: WASD / arrows. Hide Out: SHIFT (2 visits)",
            "SPACE: shoot. Bag: choose ammo/items. TAB: store",
            "Type math answers and press ENTER",
            "You have 3 lives—clear all 10 levels!",
        ]
        for number, line in enumerate(directions):
            color = LIGHT_BLUE if number == 0 else WHITE
            text_surface = self.font.render(line, True, color)
            self.screen.blit(
                text_surface,
                text_surface.get_rect(center=(SCREEN_WIDTH // 2, 230 + number * 48)),
            )

        begin = self.big_font.render("Hit Enter to Begin Game", True, GREEN)
        self.screen.blit(begin, begin.get_rect(center=(SCREEN_WIDTH // 2, 550)))
        self.draw_button(self.menu_buttons()["test"], "Test Mode")
        self.draw_button(self.menu_buttons()["how_to_play"], "How to Play")

    def draw_how_to_play(self):
        self.screen.fill(NAVY)
        title = self.big_font.render("HOW TO PLAY", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(500, 65)))
        heading, lines = HOW_TO_PLAY_PAGES[self.help_page]
        text = self.font.render(heading, True, LIGHT_BLUE)
        self.screen.blit(text, text.get_rect(center=(500, 125)))
        for row, line in enumerate(lines):
            self.screen.blit(self.small_font.render(line, True, WHITE), (90, 180 + row * 32))
        footer = f"{self.help_page + 1} / {len(HOW_TO_PLAY_PAGES)}   |   Arrow keys: turn pages   |   ESC: main menu"
        text = self.small_font.render(footer, True, GRAY)
        self.screen.blit(text, text.get_rect(center=(500, 565)))
        labels = {"help_previous": "Previous", "help_next": "Next", "help_close": "Main Menu"}
        for action, rect in self.menu_buttons().items():
            self.draw_button(rect, labels[action])

    def draw(self):
        if self.game_state == "how_to_play":
            self.draw_how_to_play()
            pygame.display.flip()
            return
        if self.overlay:
            self.draw_inventory()
            pygame.display.flip()
            return
        if self.hideout_active:
            self.draw_hideout_interior()
            pygame.display.flip()
            return
        if self.game_state == "test_setup":
            self.draw_test_setup()
            pygame.display.flip()
            return
        self.screen.fill(WHITE if self.world == "white" else NAVY)
        if self.world == "white":
            brown = (125, 75, 35)
            for fence in self.white_walls[:4] + self.fences:
                pygame.draw.rect(self.screen, brown, fence, 3)
                for x in range(fence.left, fence.right, 18):
                    pygame.draw.line(self.screen, brown, (x, fence.top), (x, fence.bottom), 5)
            for tree in self.trees:
                pygame.draw.rect(self.screen, brown, (tree.centerx - 6, tree.y + 20, 12, 35))
                pygame.draw.circle(self.screen, (55, 115, 55), (tree.centerx, tree.y + 20), 25)
            pygame.draw.rect(self.screen, RED, self.store)
            pygame.draw.polygon(self.screen, (130, 35, 35), [(595, 38), (650, 21), (705, 38)])
            pygame.draw.rect(self.screen, (70, 25, 25), (635, 73, 28, 37))
            label = self.small_font.render("STORE", True, WHITE)
            self.screen.blit(label, label.get_rect(center=(650, 55)))
        else:
            for wall in self.walls:
                pygame.draw.rect(self.screen, BLUE, wall, border_radius=5)
                pygame.draw.rect(self.screen, LIGHT_BLUE, wall, 3, border_radius=5)
            self.draw_hideout()
        if self.portal:
            color = BLACK if self.world == "white" else WHITE
            phase = pygame.time.get_ticks() / 150
            for ring in range(8):
                width = 50 - ring * 5
                x = self.portal.centerx + math.sin(phase + ring * 0.6) * 4
                pygame.draw.ellipse(self.screen, color,
                                    (x - width / 2, self.portal.y + ring * 7, width, 10), 3)
        for bullet in self.bullets:
            color = POISON_PURPLE if bullet.get("bomb") else LIGHT_GRAY if bullet["mega"] else YELLOW
            pygame.draw.ellipse(self.screen, color, bullet["rect"])
        self.draw_fireworks()
        for enemy in self.enemies:
            if enemy.world == self.world:
                enemy.draw(self.screen)
        if self.world == "white":
            for zombie in self.zombies:
                zombie.draw(self.screen)
        self.draw_player()
        self.draw_panel()

        if self.game_state == "ready":
            self.draw_ready_screen()

        if self.game_state != "ready" and pygame.time.get_ticks() < self.message_until:
            message_surface = self.small_font.render(self.message, True, WHITE)
            background = message_surface.get_rect(center=(PLAY_WIDTH // 2, 665)).inflate(25, 12)
            pygame.draw.rect(self.screen, BLACK, background, border_radius=8)
            self.screen.blit(message_surface, message_surface.get_rect(center=background.center))

        if self.game_state in ("won", "lost"):
            shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 190))
            self.screen.blit(shade, (0, 0))
            title = "YOU WON ALL 10 LEVELS!" if self.game_state == "won" else "GAME OVER"
            title_surface = self.big_font.render(title, True, YELLOW)
            self.screen.blit(title_surface, title_surface.get_rect(center=(500, 300)))
            restart = self.font.render("Press R to play again", True, WHITE)
            self.screen.blit(restart, restart.get_rect(center=(500, 365)))

        if self.test_mode:
            self.draw_button(self.menu_buttons()["back"], "Menu")

        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == "how_to_play":
                            self.handle_key(event)
                        elif self.overlay:
                            self.close_overlay()
                        else:
                            self.running = False
                    else:
                        self.handle_key(event)

            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    Game().run()

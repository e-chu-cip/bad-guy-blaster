import os
import unittest
from collections import Counter
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Enemy, FIRST_PROBLEM_DELAY, Game, HOW_TO_PLAY_PAGES


class LevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game.reset_game()

    def start_level(self, level):
        self.game.level = level
        self.game.game_state = "playing"
        self.game.start_level(first_problem_delay=FIRST_PROBLEM_DELAY)

    def test_every_level_spawns_the_requested_robots(self):
        expected = [(3, 0, 0, 0), (2, 1, 0, 0), (3, 1, 0, 0),
                    (4, 1, 1, 0), (4, 2, 1, 0), (5, 2, 1, 1),
                    (6, 2, 2, 1), (6, 3, 3, 1), (7, 3, 3, 2),
                    (8, 3, 3, 2), (8, 4, 4, 2), (9, 5, 4, 2),
                    (10, 5, 5, 2), (10, 6, 5, 3), (11, 6, 6, 3)]
        for level, counts in enumerate(expected, 1):
            with self.subTest(level=level):
                self.start_level(level)
                actual = Counter(enemy.kind for enemy in self.game.enemies)
                self.assertEqual(tuple(actual[k] for k in ("red", "green", "blue", "yellow")), counts)
                self.assertEqual(len(self.game.zombies), 4 if level >= 2 else 0)
                for enemy in self.game.enemies[16:]:
                    self.assertFalse(any(enemy.rect.colliderect(wall) for wall in self.game.black_walls))
                    self.assertFalse(enemy.rect.colliderect(self.game.hideout_clear_zone))
                    self.assertFalse(enemy.rect.colliderect(self.game.player))
                    self.assertFalse(any(enemy.rect.colliderect(other.rect)
                                         for other in self.game.enemies if other is not enemy))

    def test_portal_admits_two_robots_before_level_11_and_four_after(self):
        for level in range(2, 16):
            with self.subTest(level=level):
                self.start_level(level)
                self.game.world = "white"
                self.game.enemies = [Enemy(*self.game.portal.topleft, 1, "red") for _ in range(6)]
                with patch.object(Enemy, "update"):
                    self.game.update_enemies(10_000)
                    limit = 2 if level <= 10 else 4
                    self.assertEqual(sum(e.world == "white" for e in self.game.enemies), limit)
                    self.game.update_enemies(10_000)
                    self.assertEqual(sum(e.world == "white" for e in self.game.enemies), limit)
                    self.game.world = "black"
                    self.game.update_enemies(20_000)
                    self.assertTrue(all(e.world == "black" for e in self.game.enemies))

    def test_game_advances_through_new_levels_and_wins_only_after_15(self):
        for level in range(10, 16):
            with self.subTest(level=level):
                self.start_level(level)
                self.game.enemies.clear()
                self.game.mega_pair_offered = True
                self.game.update()
                if level == 10:
                    self.assertEqual(self.game.game_state, "life_offer")
                    self.game.handle_click(self.game.menu_buttons()["skip_life"].center)
                if level < 15:
                    self.assertEqual(self.game.level, level + 1)
                    self.assertEqual(self.game.game_state, "playing")
                    self.assertTrue(self.game.enemies)
                else:
                    self.assertEqual(self.game.game_state, "won")

    def test_test_mode_can_select_and_start_level_15(self):
        self.game.game_state = "test_setup"
        for _ in range(20):
            self.game.handle_click(self.game.menu_buttons()["level_plus"].center)
        self.assertEqual(self.game.test_settings["level"], 15)
        self.game.start_test()
        self.assertEqual(self.game.level, 15)
        self.assertEqual(len(self.game.enemies), 26)

    def test_how_to_play_pages_fit_on_screen(self):
        self.game.game_state = "how_to_play"
        for page, (_, lines) in enumerate(HOW_TO_PLAY_PAGES):
            with self.subTest(page=page):
                self.game.help_page = page
                self.game.draw_how_to_play()
                for line in lines:
                    self.assertLessEqual(self.game.small_font.size(line)[0], 820)
                self.assertLess(180 + (len(lines) - 1) * 32 + self.game.small_font.get_height(), 550)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import FIRST_PROBLEM_DELAY, Game


class LifeOfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def complete_level_ten(self, bullets):
        self.game.reset_game()
        self.game.level = 10
        self.game.game_state = "playing"
        with patch("pygame.time.get_ticks", return_value=1000):
            self.game.start_level(first_problem_delay=FIRST_PROBLEM_DELAY)
            self.game.enemies.clear()
            self.game.mega_pair_offered = True
            self.game.bullets_left = bullets
            self.game.update()
        self.assertEqual(self.game.level, 10)
        self.assertEqual(self.game.game_state, "life_offer")

    def test_buy_life_spends_three_normal_bullets_only_once(self):
        self.complete_level_ten(3)
        lives = self.game.lives
        mega = self.game.mega_bullets
        self.game.draw()
        self.game.handle_click(self.game.menu_buttons()["trade_life"].center)
        self.assertEqual(self.game.level, 11)
        self.assertEqual(self.game.game_state, "playing")
        self.assertEqual(self.game.lives, lives + 1)
        self.assertEqual(self.game.bullets_left, 2)  # 3 - 3 + the usual level bonus.
        self.assertEqual(self.game.mega_bullets, mega)
        self.game.finish_life_offer(buy_life=True)
        self.assertEqual((self.game.lives, self.game.bullets_left, self.game.level),
                         (lives + 1, 2, 11))

    def test_insufficient_normal_ammo_cannot_buy_even_with_mega_bullets(self):
        for bullets in (0, 2):
            with self.subTest(bullets=bullets):
                self.complete_level_ten(bullets)
                lives = self.game.lives
                self.game.mega_bullets = 20
                self.game.draw()
                self.game.handle_click(self.game.menu_buttons()["trade_life"].center)
                self.assertEqual(self.game.game_state, "life_offer")
                self.assertEqual((self.game.lives, self.game.bullets_left), (lives, bullets))
                self.game.handle_click(self.game.menu_buttons()["skip_life"].center)
                self.assertEqual(self.game.level, 11)
                self.assertEqual((self.game.lives, self.game.bullets_left, self.game.mega_bullets),
                                 (lives, bullets + 2, 20))

    def test_declining_with_enough_ammo_preserves_lives_and_bullets(self):
        self.complete_level_ten(8)
        lives = self.game.lives
        self.game.handle_click(self.game.menu_buttons()["skip_life"].center)
        self.assertEqual((self.game.level, self.game.lives, self.game.bullets_left), (11, lives, 10))

    def test_offer_pauses_gameplay_and_preserves_remaining_fire_boost(self):
        self.complete_level_ten(5)
        self.game.fire_until = 5000  # Four seconds left when the offer opened.
        lives = self.game.lives
        with patch("pygame.time.get_ticks", return_value=11_000):
            self.game.update()
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.assertEqual(self.game.game_state, "life_offer")
            self.assertEqual((self.game.level, self.game.lives, self.game.bullets_left), (10, lives, 5))
            self.game.handle_click(self.game.menu_buttons()["skip_life"].center)
        self.assertEqual(self.game.fire_until, 15_000)

    def test_offer_waits_for_guaranteed_math_round(self):
        self.game.reset_game()
        self.game.level = 10
        self.game.game_state = "playing"
        self.game.start_level(first_problem_delay=FIRST_PROBLEM_DELAY)
        self.game.enemies.clear()
        self.game.update()
        self.assertEqual(self.game.game_state, "playing")
        self.assertTrue(self.game.math_active)
        self.assertEqual(self.game.level, 10)


if __name__ == "__main__":
    unittest.main()

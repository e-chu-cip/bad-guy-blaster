import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Enemy, Game


class HideoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game.reset_game()
        self.game.game_state = "playing"

    def test_robots_can_hurt_player_above_and_on_house_outside_shift_visit(self):
        for player_position in ((60, 20), (60, 55)):
            with self.subTest(player_position=player_position):
                self.game.reset_game()
                self.game.game_state = "playing"
                self.game.player.topleft = player_position
                self.game.invincible_until = 0
                enemy = Enemy(160, player_position[1], 2, "red")
                self.game.enemies = [enemy]
                starting_lives = self.game.lives
                # Deterministically chase the stationary player, without math pauses.
                with patch("main.random.random", return_value=0), \
                        patch("pygame.time.get_ticks", return_value=1000), \
                        patch.object(self.game, "update_player"):
                    self.game.next_problem_at = 100_000
                    for _ in range(100):
                        self.game.update()
                        if self.game.lives < starting_lives:
                            break
                self.assertEqual(self.game.lives, starting_lives - 1)

    def test_shift_visit_still_keeps_robots_away_and_prevents_shooting(self):
        enemy = Enemy(300, 50, 2, "red")
        enemy.dx, enemy.dy = -2, 0
        enemy.change_timer = 1000
        self.game.enemies = [enemy]
        with patch("pygame.time.get_ticks", return_value=1000):
            self.game.enter_hideout()
            self.assertTrue(self.game.hideout_active)
            self.assertEqual(self.game.hideout_uses, 1)
            ammo = self.game.bullets_left
            self.game.shoot()
            self.assertEqual(self.game.bullets, [])
            self.assertEqual(self.game.bullets_left, ammo)
            for _ in range(100):
                self.game.update_enemies(1000)
                self.assertFalse(enemy.rect.colliderect(self.game.hideout_clear_zone))
            self.game.leave_hideout()
            self.assertFalse(self.game.hideout_active)


if __name__ == "__main__":
    unittest.main()

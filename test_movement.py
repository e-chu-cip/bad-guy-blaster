import unittest
from unittest.mock import patch

import pygame

from main import Enemy


class EnemyMovementTests(unittest.TestCase):
    def test_zombies_accumulate_small_steps_in_every_direction(self):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            with self.subTest(direction=(dx, dy)):
                zombie = Enemy(100, 100, 0.672, "zombie")
                zombie.change_timer = 100
                zombie.dx = dx * zombie.speed
                zombie.dy = dy * zombie.speed
                for _ in range(10):
                    zombie.update(pygame.Rect(300, 300, 30, 30), [])
                self.assertEqual(zombie.rect.topleft, (100 + dx * 6, 100 + dy * 6))

    def test_wall_collision_still_triggers_a_new_direction(self):
        zombie = Enemy(100, 100, 0.672, "zombie")
        zombie.change_timer = 100
        wall = pygame.Rect(130, 90, 20, 60)
        for _ in range(2):
            zombie.update(pygame.Rect(300, 100, 30, 30), [wall])
        self.assertEqual(zombie.rect.topleft, (100, 100))
        self.assertEqual(zombie.change_timer, 0)

    def test_frozen_zombies_stay_still(self):
        zombie = Enemy(100, 100, 0.672, "zombie")
        zombie.frozen_until = 2000
        with patch("pygame.time.get_ticks", return_value=1000):
            for _ in range(10):
                zombie.update(pygame.Rect(300, 100, 30, 30), [])
        self.assertEqual(zombie.rect.topleft, (100, 100))


if __name__ == "__main__":
    unittest.main()

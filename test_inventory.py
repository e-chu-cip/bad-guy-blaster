import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Enemy, Game


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.timer = patch("pygame.time.get_ticks", return_value=1000)
        self.clock = self.timer.start()
        self.addCleanup(self.timer.stop)
        self.game.reset_game()
        self.game.game_state = "playing"
        self.game.open_overlay("bag")

    def click(self, item):
        self.game.handle_click(self.game.menu_buttons()[item].center)
        self.assertEqual(self.game.overlay, "bag")

    def test_disabled_mega_cannot_shoot_or_spend_ammo(self):
        self.click("mega")
        self.game.shoot(mega=True)
        self.assertEqual(self.game.mega_bullets, 2)
        self.assertEqual(self.game.bullets, [])
        self.click("mega")
        self.game.close_overlay()
        self.game.shoot(mega=True)
        self.assertEqual(self.game.mega_bullets, 1)
        self.assertTrue(self.game.bullets[0]["mega"])

    def test_disabled_bomb_cannot_launch_or_spend_stock(self):
        self.game.bombs = 2
        self.click("bomb")
        self.game.launch_bomb()
        self.assertEqual(self.game.bombs, 2)
        self.assertEqual(self.game.bullets, [])
        self.click("bomb")
        self.assertEqual(self.game.bombs, 2)
        self.game.close_overlay()
        self.game.launch_bomb()
        self.assertEqual(self.game.bombs, 1)
        self.assertTrue(self.game.bullets[0]["bomb"])

    def test_ice_only_freezes_and_consumes_stock_when_active(self):
        self.game.ice = 1
        enemy = Enemy(100, 100, 1, "red")
        self.click("ice")
        self.click("ice")
        self.assertFalse(self.game.freeze_on_touch(enemy, 1000))
        self.assertEqual(self.game.ice, 1)
        self.click("ice")
        self.game.close_overlay()
        self.assertTrue(self.game.freeze_on_touch(enemy, 1000))
        self.assertEqual(self.game.ice, 0)
        self.assertFalse(self.game.ice_armed)

    def test_fire_can_save_and_resume_remaining_time_without_another_pack(self):
        self.game.fire_packs = 1
        self.click("fire")
        self.clock.return_value = 6000
        self.game.close_overlay()
        self.assertEqual(self.game.fire_until, 16000)
        self.clock.return_value = 9000
        self.game.open_overlay("bag")
        self.click("fire")
        self.assertEqual(self.game.fire_remaining, 7000)
        self.clock.return_value = 12000
        self.game.close_overlay()
        self.assertEqual(self.game.fire_until, 0)
        self.clock.return_value = 20000
        self.game.open_overlay("bag")
        self.click("fire")
        self.clock.return_value = 23000
        self.game.close_overlay()
        self.assertEqual(self.game.fire_until, 30000)
        self.assertEqual(self.game.fire_packs, 0)

    def test_empty_items_cannot_be_activated(self):
        self.game.mega_enabled = False
        self.game.bomb_enabled = False
        self.game.mega_bullets = 0
        for item in ("mega", "ice", "fire", "bomb"):
            self.click(item)
        self.assertFalse(self.game.mega_enabled)
        self.assertFalse(self.game.bomb_enabled)
        self.assertFalse(self.game.ice_armed)
        self.assertEqual(self.game.fire_until, 0)
        self.game.draw_inventory()


if __name__ == "__main__":
    unittest.main()

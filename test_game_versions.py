import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Game


class GameVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game.reset_game()

    def test_public_menu_has_help_but_no_test_mode(self):
        with patch("main.TEST_MODE_ENABLED", False):
            self.assertEqual(set(self.game.menu_buttons()), {"how_to_play", "online_board"})
            self.game.draw_ready_screen()
            self.game.handle_click((370, 625))  # Former Test Mode button.
            self.assertEqual(self.game.game_state, "ready")
            self.game.start_test()
            self.assertFalse(self.game.test_mode)
            self.assertEqual(self.game.game_state, "ready")
            self.game.handle_click(self.game.menu_buttons()["how_to_play"].center)
            self.assertEqual(self.game.game_state, "how_to_play")
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.assertEqual(self.game.game_state, "playing")
            self.assertFalse(self.game.test_mode)

    def test_local_test_mode_retains_custom_start_settings(self):
        with patch("main.TEST_MODE_ENABLED", True):
            self.game.draw_ready_screen()
            self.game.handle_click(self.game.menu_buttons()["test"].center)
            self.assertEqual(self.game.game_state, "test_setup")
            self.game.test_settings.update(level=5, lives=8, bullets=20, mega=10, poison=True)
            self.game.handle_click(self.game.menu_buttons()["start_test"].center)
            self.assertTrue(self.game.test_mode)
            self.assertEqual((self.game.level, self.game.lives, self.game.bullets_left,
                              self.game.mega_bullets, self.game.has_poison), (5, 8, 20, 10, True))
            self.game.handle_click(self.game.menu_buttons()["back"].center)
            self.assertEqual(self.game.game_state, "ready")
            self.assertIn("test", self.game.menu_buttons())


if __name__ == "__main__":
    unittest.main()

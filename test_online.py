import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Game, LEVEL_ENEMIES
from online import RunClock, ScoresClient


class ClockTests(unittest.TestCase):
    def test_pause_math_and_level_totals(self):
        clock = RunClock()
        clock.start(1000)
        clock.pause(3500)
        self.assertEqual(clock.total(20_000), 2500)
        clock.resume(20_000)
        first = clock.complete(1, 22_000)
        self.assertEqual(first, {"level": 1, "level_ms": 4500, "total_ms": 4500})
        clock.next_level(30_000)
        clock.resume(30_000)
        self.assertEqual(clock.complete(2, 31_000), {"level": 2, "level_ms": 1000, "total_ms": 5500})


class OnlineGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game.reset_game()
        self.game.scores = ScoresClient()
        self.game.scores.enabled = True
        # Inspect requests without sending any test data to the public service.
        self.game.scores.update = lambda now: None

    def start(self):
        with patch("pygame.time.get_ticks", return_value=1000):
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    def clear_level(self):
        self.game.enemies.clear()
        self.game.math_active = False
        self.game.mega_pair_offered = True
        self.game.invincible_until = 100_000

    def test_normal_start_count_and_no_count_for_test_mode(self):
        self.start()
        self.assertEqual([x['path'] for x in self.game.scores.pending], ['start'])
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode=''))
        self.assertEqual(len(self.game.scores.pending), 1)
        self.game.reset_game()
        self.game.scores.pending.clear()
        with patch('main.TEST_MODE_ENABLED', True):
            self.game.start_test()
        self.assertTrue(self.game.run_clock.test)
        self.assertFalse(self.game.scores.pending)

    def test_summary_records_once_and_leaderboard_pauses_clock(self):
        self.start()
        self.clear_level()
        with patch("pygame.time.get_ticks", return_value=5000):
            self.game.update()
        self.assertEqual(self.game.game_state, 'level_summary')
        self.assertEqual(self.game.run_clock.splits[0]['total_ms'], 4000)
        self.game.draw()
        with patch("pygame.time.get_ticks", return_value=20_000):
            self.game.handle_click(self.game.menu_buttons()['online_board'].center)
            self.game.draw()
            self.game.handle_click(self.game.menu_buttons()['online_return'].center)
            self.game.handle_click(self.game.menu_buttons()['online_continue'].center)
        self.assertEqual(self.game.level, 2)
        self.assertEqual(self.game.run_clock.total(21_000), 5000)
        self.assertEqual(len(self.game.run_clock.splits), 1)

    def test_killing_last_enemy_in_update_still_shows_summary(self):
        self.start()
        self.game.mega_pair_offered = True
        with patch.object(self.game, 'update_bullets', side_effect=self.game.enemies.clear), \
                patch("pygame.time.get_ticks", return_value=5000):
            self.game.update()
        self.assertEqual(self.game.game_state, 'level_summary')
        self.assertEqual(self.game.level, 1)

    def test_store_pause_and_math_and_hideout_time(self):
        self.start()
        with patch("pygame.time.get_ticks", return_value=3000):
            self.game.open_overlay('bag')
        with patch("pygame.time.get_ticks", return_value=9000):
            self.game.close_overlay()
        self.assertEqual(self.game.run_clock.total(10_000), 3000)
        # Math and Hide Out are both 'playing' and continue to count.
        with patch("pygame.time.get_ticks", return_value=10_000):
            self.game.new_problem()
        with patch("pygame.time.get_ticks", return_value=11_000):
            self.game.update()
        self.assertEqual(self.game.run_clock.total(11_000), 4000)

    def test_generated_nickname_is_visible_and_can_be_submitted_unchanged(self):
        self.start()
        generated = self.game.nickname
        self.assertTrue(generated.startswith('Player-'))
        self.game.lose_life(100)
        self.game.draw()
        self.assertIn('online_nickname', self.game.menu_buttons())
        field = self.game.menu_buttons()['online_nickname']
        self.assertEqual(self.game.screen.get_at((field.left + 8, field.top + 8))[:3], (255, 255, 255))
        self.game.handle_click(self.game.menu_buttons()['online_submit'].center)
        submitted = [x for x in self.game.scores.pending if x['path'] == 'finish']
        self.assertEqual(submitted[0]['body']['nickname'], generated)

    def test_nickname_box_replaces_generated_name_and_supports_select_all(self):
        self.start()
        self.game.lose_life(100)
        self.game.handle_click(self.game.menu_buttons()['online_nickname'].center)
        for char in 'Rocket':
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=ord(char.lower()), unicode=char))
        self.assertEqual(self.game.nickname, 'Rocket')
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=pygame.KMOD_META))
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, unicode='B'))
        self.assertEqual(self.game.nickname, 'B')
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        self.assertEqual(self.game.nickname, '')
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertFalse(self.game.result_submitted)
        for char in 'WWWWWWWWWWWWWWWW':
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w, unicode=char))
        self.game.draw()  # Long names remain clipped inside the box.
        self.assertEqual(len(self.game.nickname), 16)
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        name = self.game.nickname
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode='a'))
        self.assertEqual(self.game.nickname, name)

    def test_final_level_and_death_freeze_clock_and_submit_only_once(self):
        self.start()
        self.game.level = len(LEVEL_ENEMIES)
        self.clear_level()
        with patch("pygame.time.get_ticks", return_value=5000):
            self.game.update()
        self.assertEqual(self.game.game_state, 'won')
        self.game.draw()
        self.assertEqual(self.game.run_clock.total(20_000), 4000)
        self.game._submit_result()
        self.game._submit_result()
        self.assertEqual(sum(x['path'] == 'finish' for x in self.game.scores.pending), 1)
        self.game.reset_game()
        self.start()
        with patch("pygame.time.get_ticks", return_value=6000):
            self.game.lose_life(100)
        self.assertEqual(self.game.game_state, 'lost')
        self.assertEqual(self.game.run_clock.total(20_000), 5000)


if __name__ == '__main__':
    unittest.main()

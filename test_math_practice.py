import os
import random
import unittest
from collections import Counter
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Game, make_practice_problems


class PracticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game.reset_game()

    def open_practice(self, minutes=2):
        self.game.handle_click(self.game.menu_buttons()["practice"].center)
        self.assertEqual(self.game.game_state, "practice_setup")
        self.game.handle_click(self.game.menu_buttons()[f"practice_{minutes}"].center)
        self.assertEqual(self.game.game_state, "practice_playing")

    def test_generated_sets_are_distinct_correct_and_in_requested_ranges(self):
        for seed in range(50):
            with self.subTest(seed=seed), patch("main.random", random.Random(seed)):
                problems = make_practice_problems()
                self.assertEqual(len(problems), 15)
                self.assertEqual(len({p.question for p in problems}), 15)
                operations = Counter()
                small = Counter()
                for problem in problems:
                    left, operation, right, _, _ = problem.question.split()
                    a, b = int(left), int(right)
                    operations[operation] += 1
                    if operation in ('+', '-'):
                        self.assertTrue(1 <= a <= 99 and 1 <= b <= 99)
                        small[operation] += a <= 9 and b <= 9
                        answer = a + b if operation == '+' else a - b
                        self.assertGreaterEqual(answer, 0)
                    elif operation == 'x':
                        self.assertTrue(1 <= a <= 20 and 1 <= b <= 20)
                        answer = a * b
                    else:
                        self.assertTrue(1 <= b <= 12)
                        self.assertEqual(a % b, 0)
                        answer = a // b
                        self.assertTrue(1 <= answer <= 12)
                    self.assertEqual(problem.answer, answer)
                self.assertEqual(operations, {'+': 4, '-': 4, 'x': 4, '/': 3})
                self.assertGreaterEqual(small['+'], 2)
                self.assertGreaterEqual(small['-'], 2)

    def test_each_duration_is_one_total_timer_and_timeout_preserves_game(self):
        for minutes in (2, 4, 6):
            with self.subTest(minutes=minutes):
                self.game.reset_game()
                before = (self.game.level, self.game.lives, self.game.bullets_left, self.game.mega_bullets)
                with patch("pygame.time.get_ticks", return_value=1000):
                    self.open_practice(minutes)
                    self.assertEqual(self.game.practice_deadline, 1000 + minutes * 60_000)
                    self.game.practice_answer = str(self.game.practice_problems[0].answer)
                    self.game.submit_practice_answer()
                with patch("pygame.time.get_ticks", return_value=1000 + minutes * 60_000):
                    self.game.update()
                    self.assertEqual(self.game.game_state, "practice_results")
                    self.assertEqual(len(self.game.practice_answers), 1)
                    self.game.draw()
                    self.game.handle_click(self.game.menu_buttons()["practice_back"].center)
                self.assertEqual(self.game.game_state, "ready")
                self.assertEqual(before, (self.game.level, self.game.lives, self.game.bullets_left,
                                          self.game.mega_bullets))

    def test_answer_editing_scoring_completion_and_review(self):
        self.open_practice(6)
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1, unicode='1'))
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        self.assertEqual(self.game.practice_answer, '')
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.game.practice_answers, [])
        for index, problem in enumerate(self.game.practice_problems):
            self.game.practice_answer = str(problem.answer if index else problem.answer + 1)
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            if index == 0:
                self.assertEqual(self.game.game_state, "practice_feedback")
                self.game.draw()
                self.game.handle_click(self.game.menu_buttons()["practice_continue"].center)
        self.assertEqual(self.game.game_state, "practice_results")
        self.assertEqual(sum(a == p.answer for a, p in zip(self.game.practice_answers,
                                                         self.game.practice_problems)), 14)
        for page in range(3):
            self.assertEqual(self.game.practice_review_page, page)
            self.game.draw()
            if page < 2:
                self.game.handle_click(self.game.menu_buttons()["practice_next"].center)
        self.game.handle_click(self.game.menu_buttons()["practice_again"].center)
        self.game.handle_click(self.game.menu_buttons()["practice_4"].center)
        self.assertEqual(self.game.practice_answers, [])

    def test_wrong_answer_feedback_cannot_be_resubmitted_and_timer_keeps_running(self):
        self.open_practice()
        self.game.practice_answer = str(self.game.practice_problems[0].answer + 1)
        deadline = self.game.practice_deadline
        self.game.submit_practice_answer()
        self.assertEqual(self.game.game_state, "practice_feedback")
        self.game.submit_practice_answer()
        self.assertEqual(len(self.game.practice_answers), 1)
        self.game.draw()
        self.assertEqual(self.game.screen.get_at((0, 0))[:3], (255, 255, 255))
        with patch("pygame.time.get_ticks", return_value=deadline):
            self.game.update()
        self.assertEqual(self.game.game_state, "practice_results")
        self.assertEqual(self.game.practice_deadline, deadline)

    def test_last_wrong_answer_shows_correction_before_results(self):
        self.open_practice(6)
        for problem in self.game.practice_problems[:-1]:
            self.game.practice_answer = str(problem.answer)
            self.game.submit_practice_answer()
        self.game.practice_answer = str(self.game.practice_problems[-1].answer + 1)
        self.game.submit_practice_answer()
        self.assertEqual(self.game.game_state, "practice_feedback")
        self.game.draw()
        self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.game.game_state, "practice_results")

    def test_deadline_rejects_late_answers_before_next_update(self):
        self.open_practice()
        self.game.practice_answer = str(self.game.practice_problems[0].answer)
        with patch("pygame.time.get_ticks", return_value=self.game.practice_deadline):
            self.game.handle_click(self.game.menu_buttons()["practice_submit"].center)
        self.assertEqual(self.game.game_state, "practice_results")
        self.assertEqual(self.game.practice_answers, [])

    def test_practice_is_available_without_test_mode_but_not_during_game(self):
        with patch("main.TEST_MODE_ENABLED", False):
            self.open_practice()
            self.game.draw()
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.assertEqual(self.game.game_state, "ready")
            self.game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.assertNotIn('practice', self.game.menu_buttons())
            self.game.start_practice(2)
            self.assertEqual(self.game.game_state, "playing")


if __name__ == "__main__":
    unittest.main()

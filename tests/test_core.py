import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from trainer import score, solve, load_words, save_progress, practice

class TrainerTests(unittest.TestCase):
    def test_score_and_blank_tiles(self):
        self.assertEqual(score('quiz', 'quiz'), 22)
        self.assertEqual(score('quiz', 'qui?'), 12)
        self.assertEqual(score('bee', 'be?'), 4)
        self.assertIsNone(score('bee', 'be'))
        self.assertIsNone(score('quiz', 'quit'))

    def test_solve_sorted_and_no_reuse(self):
        result = solve('cat?', {'cat', 'act', 'tact', 'cattle', 'zoo'})
        self.assertEqual([item['word'] for item in result], ['act', 'cat', 'tact'])
        self.assertEqual(result[-1]['score'], 5)
        with self.assertRaises(ValueError):
            solve('123', {'cat'})

    def test_dictionary_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'words.txt'
            path.write_text('Cat\ncat\nACT\n')
            self.assertEqual(load_words(path), {'cat', 'act'})
            path.write_text('bad-word')
            with self.assertRaises(ValueError):
                load_words(path)

    def test_progress_preserves_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'nested/history.json'
            save_progress(path, {'score': 3})
            save_progress(path, {'score': 8})
            self.assertEqual(json.loads(path.read_text()), [{'score': 3}, {'score': 8}])

    def test_practice_duplicate_and_late_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.json'
            with patch('builtins.input', side_effect=['cat', 'cat', 'act']), patch('time.monotonic', side_effect=[0, 1, 2, 61]), patch('builtins.print'):
                practice('cat', {'cat', 'act'}, 60, path)
            record = json.loads(path.read_text())[0]
            self.assertEqual(record['words'], ['cat'])
            self.assertEqual(record['score'], 5)

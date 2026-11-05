"""Regression tests for malformed router keyword configuration."""
import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'meta-skill' / 'scripts' / 'route.py'
spec = importlib.util.spec_from_file_location('meta_skill_route', MODULE)
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)

class RouterKeywordValidationTests(unittest.TestCase):
    def test_rejects_non_string_keyword(self):
        index = {'tasks': [{'id': 'test', 'tier': 'standard_coding', 'keywords': [None]}], 'aliases': {'standard_coding': 'test-model'}, 'models': {}, 'settings': {}}
        with self.assertRaises(ValueError):
            route.route_prompt('test prompt', index)

    def test_accepts_valid_keyword_types(self):
        index = {'tasks': [{'id': 'test', 'tier': 'standard_coding', 'keywords': ['test']}], 'aliases': {'standard_coding': 'test-model'}, 'models': {}, 'settings': {'minimum_route_confidence': 0, 'minimum_route_margin': 0}}
        result = route.route_prompt('test prompt', index)
        self.assertEqual(result['task_id'], 'test')

    def test_rejects_invalid_token_settings(self):
        base = {'tasks': [{'id': 'test', 'tier': 'standard_coding', 'keywords': ['test']}],
                'aliases': {'standard_coding': 'test-model'}, 'models': {}}
        for settings in ({'token_budget_per_task': 0},
                         {'token_budget_per_task': -1},
                         {'estimated_output_tokens': 0},
                         {'estimated_output_tokens': -10}):
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    route.route_prompt('test prompt', {**base, 'settings': settings})

if __name__ == '__main__':
    unittest.main()

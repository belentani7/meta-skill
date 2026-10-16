"""A fallback must have a verified context window, not just a cheap price."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'meta-skill' / 'scripts'))
from route import route_prompt
from estimate_savings import estimate_savings


def catalog(primary_context=10000, fallback_context=None):
    return {
        'aliases': {'primary': 'model-a', 'fallback': 'model-b'},
        'tasks': [{'id': 'testing', 'tier': 'primary', 'keywords': ['pytest'],
                   'fallback': ['fallback']}],
        'settings': {'default_tier': 'primary', 'max_cost_per_task_usd': 0.1},
        'models': {
            'primary': [{'id': 'model-a', 'context': primary_context,
                         'prompt_per_1k_usd': 1, 'completion_per_1k_usd': 1}],
            'fallback': [{'id': 'model-b', 'context': fallback_context,
                          'prompt_per_1k_usd': 0.001, 'completion_per_1k_usd': 0.001}],
        },
    }


class VerifiedFallbackTests(unittest.TestCase):
    def test_router_rejects_unknown_or_invalid_fallback_context(self):
        for primary_context in (1, 10000):
            for context in (None, 0, -1, True, 'unknown', float('inf')):
                with self.subTest(primary=primary_context, context=context):
                    result = route_prompt('pytest', catalog(primary_context, context))
                    self.assertIsNone(result['tier'])
                    self.assertTrue(result['decision'].startswith('blocked_by_'))

    def test_savings_does_not_price_an_unverified_fallback_as_savings(self):
        workload = [{'task_id': 'testing', 'requests': 1,
                     'avg_input_tokens': 100, 'avg_output_tokens': 100,
                     'max_input_tokens': 100, 'max_output_tokens': 100}]
        for primary_context in (1, 10000):
            for context in (None, 0, -1, True, 'unknown', float('inf')):
                with self.subTest(primary=primary_context, context=context):
                    result = estimate_savings(workload, catalog(primary_context, context), 'primary')
                    self.assertIsNone(result['observations'][0]['routed_tier'])
                    self.assertIsNone(result['estimated_savings_usd'])

    def test_verified_fallback_still_routes(self):
        result = route_prompt('pytest', catalog(fallback_context=10000))
        self.assertEqual(result['tier'], 'fallback')


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import unittest

from latitude_telemetry_hermes.builder import _reasoning_attributes


class ReasoningAttributesTests(unittest.TestCase):
    def test_explicit_responses_effort_matches_config(self) -> None:
        attrs = _reasoning_attributes(
            {
                "reasoning_config": {"enabled": True, "effort": "xhigh"},
                "request": {"body": {"reasoning": {"effort": "xhigh"}}},
            }
        )
        self.assertEqual(attrs["hermes.reasoning_effort.configured"], "xhigh")
        self.assertEqual(attrs["hermes.reasoning_effort.effective"], "xhigh")
        self.assertEqual(attrs["hermes.reasoning_effort.source"], "explicit_effort")
        self.assertIs(attrs["hermes.reasoning_effort.explicit"], True)
        self.assertEqual(attrs["gen_ai.request.reasoning_effort"], "xhigh")

    def test_provider_clamp_is_visible(self) -> None:
        attrs = _reasoning_attributes(
            {
                "reasoning_config": {"enabled": True, "effort": "xhigh"},
                "request": {
                    "body": {"extra_body": {"reasoning": {"effort": "high"}}}
                },
            }
        )
        self.assertEqual(attrs["hermes.reasoning_effort.configured"], "xhigh")
        self.assertEqual(attrs["hermes.reasoning_effort.effective"], "high")

    def test_native_reasoning_without_dial_is_provider_default(self) -> None:
        attrs = _reasoning_attributes(
            {
                "reasoning_config": {"enabled": True, "effort": "xhigh"},
                "request": {"body": {"model": "grok-4.5"}},
            }
        )
        self.assertEqual(attrs["hermes.reasoning_effort.configured"], "xhigh")
        self.assertEqual(
            attrs["hermes.reasoning_effort.effective"], "provider_default"
        )
        self.assertEqual(attrs["hermes.reasoning_effort.source"], "provider_default")
        self.assertIs(attrs["hermes.reasoning_effort.explicit"], False)
        self.assertNotIn("gen_ai.request.reasoning_effort", attrs)

    def test_explicit_thinking_disable_is_visible(self) -> None:
        attrs = _reasoning_attributes(
            {
                "reasoning_config": {"enabled": False},
                "request": {
                    "body": {
                        "extra_body": {"thinking": {"type": "disabled"}}
                    }
                },
            }
        )
        self.assertEqual(attrs["hermes.reasoning_effort.configured"], "none")
        self.assertEqual(attrs["hermes.reasoning_effort.effective"], "none")
        self.assertIs(attrs["hermes.reasoning.effective_enabled"], False)


if __name__ == "__main__":
    unittest.main()
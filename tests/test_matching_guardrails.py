"""Matching guardrail unit tests — fail-closed parse + quarantine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from matching import _parse_fit_json
from matching.quarantine import (
    QUARANTINE_AFTER,
    load_quarantine,
    record_failure,
    save_quarantine,
)


class ParseFitJsonTest(unittest.TestCase):
    def test_valid_strong_and_full_stack_role(self) -> None:
        result = _parse_fit_json(
            '{"fit":"strong","role":"full_stack","reasoning":"Required Python is on the profile."}'
        )
        self.assertGreaterEqual(
            len(result),
            3,
            "parser must return fit, role, and reasoning",
        )
        fit, role = result[0], result[1]
        self.assertEqual(fit, "strong")
        self.assertEqual(role, "full_stack")

    def test_missing_role_is_invalid(self) -> None:
        result = _parse_fit_json('{"fit":"strong","reasoning":"good overlap"}')
        self.assertEqual(result[0], "invalid")

    def test_intern_role_is_invalid(self) -> None:
        result = _parse_fit_json(
            '{"fit":"maybe","role":"intern","reasoning":"stretch"}'
        )
        self.assertEqual(result[0], "invalid")

    def test_malformed_is_invalid_not_maybe(self) -> None:
        result = _parse_fit_json("not json at all")
        self.assertEqual(result[0], "invalid")
        self.assertNotEqual(result[0], "maybe")
        self.assertIn("malformed", str(result[-1]).lower())

    def test_unknown_fit_is_invalid(self) -> None:
        result = _parse_fit_json('{"fit":"superb","reasoning":"x"}')
        self.assertEqual(result[0], "invalid")


class QuarantineAcceptanceTest(unittest.TestCase):
    """P0 acceptance: observe a real quarantine event (forced via record_failure)."""

    def test_third_failure_quarantines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quarantine.json"
            store: dict = {}
            url = "https://example.com/poison-job"
            for i in range(QUARANTINE_AFTER):
                entry = record_failure(store, url, error=f"invalid: boom {i}")
            self.assertTrue(entry.quarantined)
            self.assertEqual(entry.attempts, QUARANTINE_AFTER)
            self.assertIn("Quarantined after", entry.note)
            save_quarantine(store, path=path)
            reloaded = load_quarantine(path=path)
            self.assertTrue(reloaded[url].quarantined)
            print("P0 ACCEPTANCE: quarantine event observed for", url)


if __name__ == "__main__":
    unittest.main()

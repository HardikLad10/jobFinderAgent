"""Apply-email tests: name the resume and keep the model's full reasoning."""

from __future__ import annotations

import unittest

from delivery import build_email
from matching import MatchResult

# Longer than the old 120-character cap. Literal, so a trim cannot hide.
_FULL_STACK_REASONING = (
    "The Piramal claims tool was React and REST, and RainStorm is a Python "
    "distributed system. The posting's required Python is covered. Preferred "
    "Go is missing, so this is a maybe."
)


def _match(
    *,
    role: str,
    fit: str = "strong",
    reasoning: str = "Required Python is on the profile.",
) -> MatchResult:
    return MatchResult(
        title="Software Engineer",
        company="Asana",
        location="San Francisco",
        url="https://example.com/job",
        posted_date="2026-10-01",
        sponsorship_flag="unknown",
        fit=fit,
        role=role,
        reasoning=reasoning,
    )


class BuildEmailResumeTest(unittest.TestCase):
    def test_full_stack_email_names_resume_and_keeps_full_reasoning(self) -> None:
        reasoning = _FULL_STACK_REASONING
        self.assertGreater(len(reasoning), 120)

        built = build_email([_match(role="full_stack", reasoning=reasoning)])

        self.assertIsNotNone(built)
        subject, text, html = built
        self.assertEqual(subject, "Job matches: 1 strong, 0 maybe")
        self.assertIn("Software Engineer — Asana — San Francisco", text)
        self.assertIn("Send the Full Stack resume", text)
        self.assertIn(reasoning, text)
        self.assertIn("https://example.com/job", text)
        self.assertIn("Send the Full Stack resume", html)
        self.assertIn(reasoning, html)

    def test_new_grad_email_names_new_grad_resume(self) -> None:
        built = build_email([_match(role="new_grad")])
        self.assertIsNotNone(built)
        self.assertIn("Send the New Grad resume", built[1])

    def test_ai_fde_email_names_ai_fde_resume(self) -> None:
        built = build_email([_match(role="ai_fde")])
        self.assertIsNotNone(built)
        self.assertIn("Send the AI/FDE resume", built[1])


if __name__ == "__main__":
    unittest.main()

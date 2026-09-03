"""Filter unit tests — lock the four historical production bugs."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from filtering import FilteredJob, apply_survivor_ceiling, filter_postings, load_filter_config
from ingestion.schema import JobPosting


def _job(
    *,
    title: str = "Software Engineer",
    location: str = "Chicago, IL",
    url: str = "https://example.com/job/1",
    posted_date: str = "2026-08-10T12:00:00+00:00",
    description: str = "Build software.",
    company: str = "Example",
) -> JobPosting:
    return JobPosting(
        title=title,
        company=company,
        location=location,
        posted_date=posted_date,
        url=url,
        description=description,
    )


class FilterHistoricalBugsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = load_filter_config()
        cls.now = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)

    def _kept_urls(self, postings: list[JobPosting]) -> set[str]:
        kept = filter_postings(
            postings,
            filter_config=self.cfg,
            seen_urls=set(),
            now=self.now,
        )
        return {item.posting.url for item in kept}

    def test_bare_remote_eu_dropped(self) -> None:
        """Bug 1: bare `remote` must not admit EU seats."""
        jobs = [
            _job(url="u-eu", location="Remote - Ireland"),
            _job(url="u-us", location="Remote US"),
            _job(url="u-chi", location="Chicago, IL"),
        ]
        kept = self._kept_urls(jobs)
        self.assertNotIn("u-eu", kept)
        self.assertIn("u-us", kept)
        self.assertIn("u-chi", kept)

    def test_comma_in_does_not_match_india(self) -> None:
        """Bug 2: India must not pass via a brittle `, in` token."""
        jobs = [
            _job(url="u-india", location="Bangalore, India"),
            _job(url="u-indy", location="Indianapolis, IN"),
        ]
        kept = self._kept_urls(jobs)
        self.assertNotIn("u-india", kept)
        self.assertIn("u-indy", kept)

    def test_il_token_does_not_match_oakville_manville(self) -> None:
        """Bug 3: stripping ` il ` must not let Oakville/Manville through."""
        jobs = [
            _job(url="u-oak", location="Oakville, ON"),
            _job(url="u-man", location="Manville, NJ"),
            _job(url="u-il", location="Naperville, IL"),
        ]
        kept = self._kept_urls(jobs)
        self.assertNotIn("u-oak", kept)
        self.assertNotIn("u-man", kept)
        self.assertIn("u-il", kept)

    def test_level_only_and_recruiter_titles_dropped(self) -> None:
        """Bug 4: level-only / recruiter–non-SWE titles must not reach Claude."""
        jobs = [
            _job(url="u-entry", title="Entry Level Lot Attendant"),
            _job(url="u-newgrad", title="New Grad Automotive Detailer"),
            _job(
                url="u-rec",
                title="Technical Recruiter, Software Engineering",
            ),
            _job(url="u-swe", title="Software Engineer, New Grad"),
        ]
        kept = self._kept_urls(jobs)
        self.assertNotIn("u-entry", kept)
        self.assertNotIn("u-newgrad", kept)
        self.assertNotIn("u-rec", kept)
        self.assertIn("u-swe", kept)

    def test_fde_and_ai_engineer_kept_solutions_engineer_dropped(self) -> None:
        """FDE / AI Engineer / intern variants in; Solutions Engineer out."""
        jobs = [
            _job(url="u-fde", title="Forward Deployed Engineer"),
            _job(url="u-fde-intern", title="FDE Intern"),
            _job(url="u-ai-fde", title="AI Forward Deployed Engineer"),
            _job(url="u-ai", title="AI Engineer"),
            _job(url="u-ai-intern", title="AI Engineer Intern"),
            _job(url="u-aiml", title="AI/ML Engineer, New Grad"),
            _job(url="u-se", title="Solutions Engineer"),
            _job(url="u-sa", title="Solutions Architect"),
            _job(url="u-train", title="Training Coordinator"),
        ]
        kept = self._kept_urls(jobs)
        self.assertEqual(
            kept,
            {
                "u-fde",
                "u-fde-intern",
                "u-ai-fde",
                "u-ai",
                "u-ai-intern",
                "u-aiml",
            },
        )


class SurvivorCeilingTest(unittest.TestCase):
    def test_keeps_newest_first(self) -> None:
        jobs = [
            FilteredJob(
                posting=_job(url="old", posted_date="2026-08-01T00:00:00+00:00"),
                sponsorship_flag="none_found",
            ),
            FilteredJob(
                posting=_job(url="new", posted_date="2026-08-10T00:00:00+00:00"),
                sponsorship_flag="none_found",
            ),
            FilteredJob(
                posting=_job(url="mid", posted_date="2026-08-05T00:00:00+00:00"),
                sponsorship_flag="none_found",
            ),
        ]
        kept, dropped = apply_survivor_ceiling(jobs, max_survivors=2)
        self.assertEqual(dropped, 1)
        self.assertEqual([j.posting.url for j in kept], ["new", "mid"])


if __name__ == "__main__":
    unittest.main()

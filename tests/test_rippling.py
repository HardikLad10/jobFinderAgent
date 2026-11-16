"""Rippling client tests. HTTP is stubbed."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ingestion.errors import IngestionError
from ingestion.rippling import fetch_rippling_jobs


LIST_PAGE_0 = {
    "items": [
        {
            "id": "job-swe",
            "name": "Software Engineer",
            "url": "https://ats.rippling.com/acme/jobs/job-swe",
            "locations": [
                {
                    "name": "Austin, TX",
                    "workplaceType": "ON_SITE",
                }
            ],
        },
        {
            "id": "job-sales",
            "name": "Account Executive",
            "url": "https://ats.rippling.com/acme/jobs/job-sales",
            "locations": [{"name": "Chicago, IL", "workplaceType": "ON_SITE"}],
        },
    ],
    "page": 0,
    "pageSize": 100,
    "totalItems": 2,
    "totalPages": 2,
}
LIST_PAGE_1 = {
    "items": [
        {
            "id": "job-remote",
            "name": "Backend Engineer",
            "url": "https://ats.rippling.com/acme/jobs/job-remote",
            "locations": [
                {"name": "United States", "workplaceType": "REMOTE"},
            ],
        }
    ],
    "page": 1,
    "pageSize": 100,
    "totalItems": 3,
    "totalPages": 2,
}
DETAIL = {
    "createdOn": "2026-11-02T11:50:55.300000-08:00",
    "description": {
        "company": "<p>Acme builds tools.</p>",
        "role": "<p>Python required. Visa sponsorship available.</p>",
    },
}


class RipplingClientTest(unittest.TestCase):
    def test_pages_and_skips_non_software_titles(self) -> None:
        calls: list[str] = []

        def fake_get(url: str, *, company_name: str) -> dict:
            calls.append(url)
            if "page=0" in url:
                return LIST_PAGE_0
            if "page=1" in url:
                return LIST_PAGE_1
            if url.endswith("/jobs/job-swe"):
                return DETAIL
            if url.endswith("/jobs/job-remote"):
                return DETAIL
            raise AssertionError(url)

        with patch("ingestion.rippling.get_json", side_effect=fake_get):
            jobs = fetch_rippling_jobs("Acme", "acme")

        titles = [job.title for job in jobs]
        self.assertEqual(titles, ["Software Engineer", "Backend Engineer"])
        self.assertNotIn("job-sales", " ".join(calls))
        remote = jobs[1]
        self.assertEqual(remote.location, "Remote - United States")
        self.assertIn("Python required", jobs[0].description)
        self.assertIn("Acme builds tools", jobs[0].description)
        self.assertEqual(jobs[0].posted_date, "2026-11-02T11:50:55.300000-08:00")
        self.assertEqual(jobs[0].url, "https://ats.rippling.com/acme/jobs/job-swe")

    def test_detail_failure_keeps_the_posting(self) -> None:
        def fake_get(url: str, *, company_name: str) -> dict:
            if "page=0" in url:
                return {
                    "items": [
                        {
                            "id": "job-swe",
                            "name": "Software Engineer",
                            "url": "https://ats.rippling.com/acme/jobs/job-swe",
                            "locations": [{"name": "Austin, TX"}],
                        }
                    ],
                    "totalItems": 1,
                    "totalPages": 1,
                }
            raise IngestionError("detail down")

        with patch("ingestion.rippling.get_json", side_effect=fake_get):
            jobs = fetch_rippling_jobs("Acme", "acme")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].description, "")
        self.assertEqual(jobs[0].posted_date, "")


if __name__ == "__main__":
    unittest.main()
